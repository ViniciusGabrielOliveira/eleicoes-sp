"""Referência nacional de candidatos, sem importar fatos por seção de outras UFs."""
import json
import os
import zipfile
from datetime import datetime,timezone

import duckdb

from .download import ROOT,RAW,fetch_one
from .pipeline import literal,WAREHOUSE,stage
from .query import connection,rows

REFERENCE=WAREHOUSE/'candidate_totals.parquet'

def build_national(refresh=False):
    folder=RAW/'national_totals'
    if refresh:(folder/'source.json').unlink(missing_ok=True)
    if not (folder/'source.json').exists():
        fetch_one(('national_totals',('resultados-2026','votacao_candidato_munzona_2026.zip')))
    paths=[]
    with zipfile.ZipFile(folder/'votacao_candidato_munzona_2026.zip') as archive:
        for name in archive.namelist():
            if not name.endswith(('_BR.csv','_SP.csv')):continue
            path=ROOT/'data/staging/national_totals'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(name) as source,path.open('wb') as dest:
                while chunk:=source.read(4*1024*1024):dest.write(chunk.decode('latin1').encode('utf8'))
            paths.append(str(path))
    con=duckdb.connect();con.execute("SET threads=2;SET memory_limit='1GB';SET enable_progress_bar=false")
    con.execute(f"""CREATE TABLE munzona_reference AS SELECT ANO_ELEICAO::SMALLINT AS year,
        CD_ELEICAO::INTEGER AS election,NR_TURNO::SMALLINT AS round,CD_CARGO::SMALLINT AS office,
        SQ_CANDIDATO::BIGINT AS candidate_id,min(NM_URNA_CANDIDATO) AS name,
        sum(QT_VOTOS_NOMINAIS::BIGINT)::BIGINT AS national_votes,
        sum(QT_VOTOS_NOMINAIS::BIGINT) FILTER(WHERE SG_UF='SP')::BIGINT AS sp_votes,
        bool_or(SG_UF='ZZ') AS includes_overseas
        FROM read_csv([{','.join(literal(p) for p in paths)}],delim=';',all_varchar=true,union_by_name=true)
        WHERE ANO_ELEICAO='2026' AND CD_CARGO IN ('1','3','5','6','7') GROUP BY ALL""")
    # Mesma geração das seções do mapa: não misturar revisões posteriores de arquivos.
    # O arquivo por município/zona de 20/10 omite candidaturas presentes nas seções de 06/10.
    president=stage('votes_br',['_BR.csv'])
    con.execute(f"""CREATE TABLE candidate_totals AS SELECT ANO_ELEICAO::SMALLINT AS year,
        CD_ELEICAO::INTEGER AS election,NR_TURNO::SMALLINT AS round,CD_CARGO::SMALLINT AS office,
        SQ_CANDIDATO::BIGINT AS candidate_id,min(NM_VOTAVEL) AS name,
        sum(QT_VOTOS::BIGINT)::BIGINT AS national_votes,
        sum(QT_VOTOS::BIGINT) FILTER(WHERE SG_UF='SP')::BIGINT AS sp_votes,
        bool_or(SG_UF='ZZ') AS includes_overseas
        FROM {president} WHERE ANO_ELEICAO='2026' AND CD_CARGO='1'
        AND SQ_CANDIDATO::BIGINT>0 GROUP BY ALL""")
    with connection() as local:
        state=local.execute("""SELECT year,election,round,office,candidate_id,candidate_name,
            votes,votes,false FROM candidate_search WHERE office<>1""").fetchall()
    con.executemany('INSERT INTO candidate_totals VALUES (?,?,?,?,?,?,?,?,?)',state)
    temp=REFERENCE.with_suffix('.parquet.part')
    con.execute(f"COPY candidate_totals TO {literal(temp)} (FORMAT PARQUET,COMPRESSION ZSTD)")
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),
        source=json.loads((folder/'source.json').read_text()),
        scope='Presidência: todas as UFs e exterior; cargos estaduais: candidaturas de SP',
        denominator='Mesmo snapshot das seções: nacional para presidente, total da candidatura em SP para cargos estaduais',
        section_sources={k:json.loads((RAW/k/'source.json').read_text()) for k in ['votes_br','votes_sp']},
        munzona_comparison=rows(con,"""SELECT s.office,s.round,
            count(*) FILTER(WHERE m.candidate_id IS NULL) AS omitted_in_later_munzona_release,
            count(*) FILTER(WHERE s.national_votes<>m.national_votes) AS differing_totals
            FROM candidate_totals s LEFT JOIN munzona_reference m
            USING(year,election,round,office,candidate_id) GROUP BY ALL ORDER BY office,round"""),
        totals=rows(con,'SELECT office,round,sum(national_votes)::BIGINT AS votes,count(*) AS candidates FROM candidate_totals GROUP BY ALL ORDER BY office,round'))
    con.close()
    with connection() as local:
        report['snapshot_comparison']=rows(local,f"""SELECT s.office,s.round,
            count(*) FILTER(WHERE n.candidate_id IS NULL) AS missing_candidates,
            count(*) FILTER(WHERE s.votes<>coalesce(n.sp_votes,0)) AS changed_since_section_snapshot,
            count(*) FILTER(WHERE s.votes>n.national_votes) AS snapshot_exceeds_national
            FROM candidate_search s LEFT JOIN read_parquet({literal(temp)}) n
            USING(year,election,round,office,candidate_id) GROUP BY ALL ORDER BY office,round""")
    if any(r['missing_candidates'] or r['changed_since_section_snapshot'] or r['snapshot_exceeds_national']
           for r in report['snapshot_comparison']):
        temp.unlink(missing_ok=True)
        raise ValueError('Referência nacional não corresponde ao snapshot de seções; publicação interrompida')
    temp.replace(REFERENCE)
    (ROOT/'reports/national_totals.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('source','section_sources')},ensure_ascii=False,indent=2))

if __name__=='__main__':build_national()
