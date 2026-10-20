"""Relatórios parametrizados; denominadores independentes do candidato escolhido."""
import json
from contextlib import contextmanager
from time import perf_counter

import duckdb

from .pipeline import DATABASE
from .summaries import GROUPS

@contextmanager
def connection(database=DATABASE):
    if not database.exists():
        raise FileNotFoundError("Execute eleicoes download e eleicoes build primeiro")
    con = duckdb.connect(str(database), read_only=True,
        config={"threads": 2, "memory_limit": "1GB"})
    try:
        yield con
    finally:
        con.close()

def rows(con, sql, params=()):
    cursor = con.execute(sql, params)
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]

def filters(values, prefix=""):
    clauses, params = [], []
    for field in ("election", "municipality", "zone", "location", "section", "match_status"):
        if values.get(field) is not None:
            clauses.append(f"{prefix}{field}=?")
            params.append(values[field])
    if values.get("neighborhood") is not None:
        clauses.append(f"upper(strip_accents(trim({prefix}neighborhood)))=upper(strip_accents(trim(?)))")
        params.append(values["neighborhood"])
    if values.get("address"):
        clauses.append(f"contains(upper(strip_accents({prefix}address)),upper(strip_accents(?)))")
        params.append(values["address"])
    return clauses, params

def report(con, office, round=1, group_by="neighborhood", candidate_id=None, party=None,
           min_votes=0, limit=100, offset=0, **values):
    if group_by not in GROUPS:
        raise ValueError("Agrupamento inválido")
    if values.get("neighborhood") and not values.get("municipality"):
        raise ValueError("Informe o município ao filtrar um bairro")
    if not 1 <= limit <= 5000 or offset < 0 or min_votes < 0:
        raise ValueError("Limite, deslocamento ou votos mínimos inválidos")
    fields = GROUPS[group_by]
    # Eleição, cargo e turno sempre participam da chave e da janela.
    dimensions = ["year", "election", "round", "office", "office_name"] + fields
    group = ",".join(dimensions)
    ordering = ",".join(["votes DESC","candidate_id"]+dimensions)
    clauses, params = filters(values)
    if office not in (1,3,5,6,7) or round not in (1,2):
        raise ValueError("Cargo ou turno inválido")
    clauses = ["office=?", "round=?"] + clauses
    params = [office, round] + params
    # Filtro de seção precisa ler os fatos, demais consultas usam a agregação por local.
    source = "results" if group_by == "section" or values.get("section") is not None else "local_results"
    selection = ["votes>=?"]
    selected_params = [min_votes]
    if candidate_id is not None:
        selection.append("candidate_id=?")
        selected_params.append(candidate_id)
    if party:
        selection.append("party=?")
        selected_params.append(party.upper())
    summary=f"summary_{group_by}"
    active={key for key,value in values.items() if value is not None and value != ""}
    compatible=active.issubset(set(dimensions))
    exists=con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name=?",[summary]).fetchone()[0]
    if compatible and exists:
        sql=f"""SELECT *,round(100.0*votes/nullif(nominal_total,0),4) AS nominal_share_pct,
            leader_votes-votes AS gap_to_leader FROM {summary}
            WHERE {' AND '.join(clauses+selection)}
            ORDER BY {ordering} LIMIT ? OFFSET ?"""
        source=summary
    else:
        sql = f"""WITH territory AS (
        SELECT * FROM {source} WHERE {' AND '.join(clauses)} AND vote_kind='nominal'
      ), grouped AS (
        SELECT {group},candidate_id,number,candidate_name,party,result_status,
            sum(votes)::BIGINT AS votes FROM territory GROUP BY ALL
      ), ranked AS (
        SELECT *, sum(votes) OVER(PARTITION BY {group})::BIGINT AS nominal_total,
          dense_rank() OVER(PARTITION BY {group} ORDER BY votes DESC) AS position,
          max(votes) OVER(PARTITION BY {group})::BIGINT AS leader_votes
        FROM grouped
      ) SELECT *,round(100.0*votes/nullif(nominal_total,0),4) AS nominal_share_pct,
          leader_votes-votes AS gap_to_leader
        FROM ranked WHERE {' AND '.join(selection)}
        ORDER BY {ordering} LIMIT ? OFFSET ?"""
    start = perf_counter()
    data = rows(con, sql, params + selected_params + [limit, offset])
    return {"rows": data, "returned": len(data), "limit": limit, "offset": offset,
        "elapsed_ms": round_ms(perf_counter()-start),
        "metric": "Participação nos votos nominais do mesmo cargo, turno e território",
        "geography": "Bairro do local de votação; não residência do eleitor",
        "source_table": source}

def round_ms(seconds):
    return int(seconds * 1000000) / 1000

def status(con):
    return json.loads(con.execute("SELECT quality FROM metadata").fetchone()[0])
