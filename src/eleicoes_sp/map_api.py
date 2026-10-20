"""Consultas do mapa: multisseleção sem alterar os denominadores."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter,HTTPException,Query
from fastapi.responses import FileResponse

from .download import ROOT
from .query import rows
from .pipeline import literal,WAREHOUSE

router=APIRouter(prefix='/map',tags=['Mapa'])
GEO=ROOT/'data/geo'

@lru_cache(maxsize=2)
def catalog_version(version):
    return json.loads((GEO/'catalog.json').read_text())

def catalog():
    path=GEO/'catalog.json'
    if not path.exists():raise HTTPException(503,'Execute eleicoes geography primeiro')
    return catalog_version(path.stat().st_mtime_ns)

@router.get('/catalog')
def get_catalog():return catalog()

@router.get('/geometry/{level}')
def geometry(level:Literal['municipality','neighborhood']):
    return FileResponse(GEO/('cities.json' if level=='municipality' else 'areas.json'),media_type='application/geo+json')

def map_data(con,office,round,level,municipalities=(),regions=(),immediate_regions=(),neighborhoods=(),candidate_ids=()):
    if office not in (1,3,5,6,7):raise ValueError('Cargo inválido')
    cat=catalog();allowed={c['municipality'] for c in cat['municipalities']}
    if regions:
        allowed&={c['municipality'] for c in cat['municipalities'] if c['region'] in regions}
    if immediate_regions:
        allowed&={c['municipality'] for c in cat['municipalities'] if c['immediate'] in immediate_regions}
    if municipalities:allowed&=set(municipalities)
    if not allowed:return dict(areas=[],candidates=[],total=0,mapped_total=0,unmapped_total=0)
    if len(candidate_ids)>10:raise ValueError('Selecione até dez candidatos')
    if level=='neighborhood' or neighborhoods:
        source='summary_neighborhood'
        key="municipality::VARCHAR || '|' || coalesce(neighborhood,'#SEM_BAIRRO')"
    else:
        source='summary_municipality';key='municipality::VARCHAR'
    clauses=['office=?','round=?','municipality IN (SELECT unnest(?::INTEGER[]))']
    params=[office,round,sorted(allowed)]
    if neighborhoods:
        clauses.append(f"({key}) IN (SELECT unnest(?::VARCHAR[]))");params.append(list(neighborhoods))
    outkey=key if level=='neighborhood' else 'municipality::VARCHAR'
    base=f"SELECT *,{outkey} AS area_key FROM {source} WHERE {' AND '.join(clauses)}"
    totals=rows(con,f"SELECT area_key,sum(votes)::BIGINT AS total FROM ({base}) GROUP BY area_key",params)
    chosen=list(candidate_ids)
    if not chosen:
        chosen=[r['candidate_id'] for r in rows(con,f"SELECT candidate_id,sum(votes) AS total FROM ({base}) GROUP BY candidate_id ORDER BY total DESC,candidate_id LIMIT 6",params)]
    candidates=rows(con,f"""SELECT candidate_id,min(candidate_name) AS name,min(party) AS party,
        min(number) AS number,sum(votes)::BIGINT AS votes FROM ({base})
        WHERE candidate_id IN (SELECT unnest(?::BIGINT[])) GROUP BY candidate_id
        ORDER BY votes DESC,candidate_id""",params+[chosen])
    distribution=rows(con,f"""SELECT area_key,candidate_id,sum(votes)::BIGINT AS votes FROM ({base})
        WHERE candidate_id IN (SELECT unnest(?::BIGINT[])) GROUP BY area_key,candidate_id""",params+[chosen])
    by_area={r['area_key']:{} for r in totals}
    for r in distribution:by_area[r['area_key']][str(r['candidate_id'])]=r['votes']
    reference=WAREHOUSE/'candidate_totals.parquet'
    national_join=(f'LEFT JOIN read_parquet({literal(reference)}) n USING(year,election,round,office,candidate_id)'
        if reference.exists() else "LEFT JOIN (SELECT NULL::SMALLINT AS year,NULL::INTEGER AS election,NULL::SMALLINT AS round,NULL::SMALLINT AS office,NULL::BIGINT AS candidate_id,NULL::BIGINT AS national_votes) n USING(year,election,round,office,candidate_id)")
    hover_params=list(params)
    hover_base=base
    if candidate_ids:
        hover_base=f"SELECT * FROM ({base}) WHERE candidate_id IN (SELECT unnest(?::BIGINT[]))"
        hover_params.append(list(candidate_ids))
    grouped=(f"SELECT year,election,round,office,area_key,candidate_id,candidate_name AS name,party,votes FROM ({hover_base})" + ("" if candidate_ids else " WHERE position<=5")
        if not (level=='municipality' and neighborhoods) else
        f"SELECT year,election,round,office,area_key,candidate_id,min(candidate_name) AS name,min(party) AS party,sum(votes)::BIGINT AS votes FROM ({hover_base}) GROUP BY ALL")
    # Filtrar antes de ranquear permite incluir selecionados fora do top cinco geral.
    top_five=rows(con,f"""WITH grouped AS ({grouped}),
        ranked AS (SELECT *,row_number() OVER(PARTITION BY area_key ORDER BY votes DESC,candidate_id) AS position
            FROM grouped)
        SELECT area_key,candidate_id,ranked.name,party,votes,position,n.national_votes,
            CASE WHEN n.national_votes>=votes AND n.national_votes>0
                THEN 100.0*votes/n.national_votes END AS national_share_pct
        FROM ranked {national_join} WHERE position<=5 ORDER BY area_key,position""",hover_params)
    by_top={r['area_key']:[] for r in totals}
    for row in top_five:
        key=row.pop('area_key');by_top[key].append(row)
    # Vencedor e margem sempre usam todos os candidatos, antes de qualquer filtro.
    leaders={}
    if office==1:
        leader_rows=rows(con,f"""WITH grouped AS (
            SELECT area_key,candidate_id,min(candidate_name) AS name,min(party) AS party,
                sum(votes)::BIGINT AS votes FROM ({base}) GROUP BY area_key,candidate_id),
            ranked AS (SELECT *,row_number() OVER(PARTITION BY area_key ORDER BY votes DESC,candidate_id) AS rank
                FROM grouped)
            SELECT * FROM ranked WHERE rank<=2 ORDER BY area_key,rank""",params)
        for row in leader_rows:leaders.setdefault(row['area_key'],[]).append(row)
    known=({str(c['municipality']) for c in cat['municipalities']} if level=='municipality' else
        {n['key'] for n in cat['neighborhoods'] if n['geometry'] is not None})
    areas=[dict(key=r['area_key'],total=r['total'],votes=by_area[r['area_key']],
        others=r['total']-sum(by_area[r['area_key']].values()),top_five=by_top[r['area_key']]) for r in totals]
    for area in areas:
        ranked=leaders.get(area['key'],[])
        if ranked:
            first=ranked[0];second=ranked[1] if len(ranked)>1 else None
            gap=first['votes']-(second['votes'] if second else 0)
            area['winner']=dict(candidate_id=first['candidate_id'],name=first['name'],party=first['party'],
                votes=first['votes'],runner_up=second,tied=gap==0,
                margin_votes=gap,margin_pp=100.0*gap/area['total'] if area['total'] else 0)
    total=sum(a['total'] for a in areas);mapped=sum(a['total'] for a in areas if a['key'] in known)
    return dict(areas=areas,candidates=candidates,total=total,mapped_total=mapped,
        unmapped_total=total-mapped,level=level,office=office,round=round,
        metric='Votos nominais; outros candidatos preservados no denominador')

@router.get('/data')
def get_data(office:int=1,round:int=Query(1,ge=1,le=2),
    level:Literal['municipality','neighborhood']='municipality',
    municipalities:list[int]=Query(default=[]),regions:list[str]=Query(default=[]),
    immediate_regions:list[str]=Query(default=[]),neighborhoods:list[str]=Query(default=[]),
    candidate_ids:list[int]=Query(default=[])):
    from .api import run_query
    return run_query(lambda con:map_data(con,office,round,level,municipalities,regions,
        immediate_regions,neighborhoods,candidate_ids))


def area_candidates(con,office,round,level,key,neighborhoods=(),candidate_ids=()):
    """Candidatos com votos no território; filtro preserva o denominador local."""
    if office not in (1,3,5,6,7) or round not in (1,2):
        raise ValueError('Cargo ou turno inválido')
    if level not in ('municipality','neighborhood'):raise ValueError('Nível inválido')
    parts=key.split('|',1)
    try:municipality=int(parts[0])
    except ValueError:raise ValueError('Território inválido')
    clauses=['office=?','round=?','municipality=?','votes>0']
    params=[office,round,municipality]
    source='summary_municipality'
    if level=='neighborhood':
        if len(parts)!=2:raise ValueError('Bairro inválido')
        source='summary_neighborhood';clauses.append('neighborhood=?');params.append(parts[1])
    elif neighborhoods:
        source='summary_neighborhood'
        clauses.append("(municipality::VARCHAR || '|' || coalesce(neighborhood,'#SEM_BAIRRO')) IN (SELECT unnest(?::VARCHAR[]))")
        params.append(list(neighborhoods))
    selection="WHERE candidate_id IN (SELECT unnest(?::BIGINT[]))" if candidate_ids else ""
    if candidate_ids:params.append(list(candidate_ids))
    return rows(con,f"""WITH grouped AS (
        SELECT candidate_id,min(candidate_name) AS name,min(party) AS party,min(number) AS number,
            sum(votes)::BIGINT AS votes FROM {source} WHERE {' AND '.join(clauses)} GROUP BY candidate_id),
        shares AS (SELECT *,100.0*votes/sum(votes) OVER() AS local_share_pct FROM grouped)
        SELECT * FROM shares {selection} ORDER BY votes DESC,candidate_id""",params)


@router.get('/area-candidates')
def get_area_candidates(office:int,round:int=Query(1,ge=1,le=2),
    level:Literal['municipality','neighborhood']='municipality',key:str=Query(max_length=500),
    neighborhoods:list[str]=Query(default=[]),candidate_ids:list[int]=Query(default=[],max_length=10)):
    from .api import run_query
    return run_query(lambda con:area_candidates(con,office,round,level,key,neighborhoods,candidate_ids))
