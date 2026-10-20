"""Carga em lote com publicação de snapshot auditado, sem pandas nem CSV inteiro em RAM."""
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .download import ROOT, RAW, SOURCES

WAREHOUSE = ROOT / "data/warehouse"
DATABASE = WAREHOUSE / "eleicoes.duckdb"

def literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def stage(key, suffixes):
    archive_path = RAW / key / SOURCES[key][1]
    paths = []
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not any(name.endswith(s) for s in suffixes):
                continue
            target = ROOT / "data/staging" / key / Path(name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            source_hash = json.loads((RAW / key / "source.json").read_text())["sha256"]
            marker = target.with_suffix(".source")
            if not target.exists() or not marker.exists() or marker.read_text() != source_hash:
                part = target.with_suffix(".part")
                with archive.open(name) as source, part.open("wb") as output:
                    while chunk := source.read(4 * 1024 * 1024):
                        output.write(chunk.decode("latin1").encode("utf8"))
                part.replace(target)
                marker.write_text(source_hash)
            paths.append(str(target))
    if not paths:
        raise ValueError(f"Nenhum CSV esperado em {archive_path}")
    return ("read_csv([" + ",".join(literal(p) for p in paths) +
        "], delim=';', header=true, all_varchar=true, union_by_name=true, strict_mode=true)")

def build():
    start = time.perf_counter()
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    output = WAREHOUSE / f"build-{os.getpid()}.duckdb"
    con = duckdb.connect(str(output))
    con.execute("SET memory_limit='2GB'; SET threads=2; SET preserve_insertion_order=false; SET enable_progress_bar=false")
    con.execute(f"SET temp_directory={literal(ROOT / 'data/tmp')}")
    try:
        sources = {
            "votes_sp": stage("votes_sp", ["_SP.csv"]),
            "votes_br": stage("votes_br", ["_BR.csv"]),
            "locations": stage("locations", ["_SP.csv"]),
            "candidates": stage("candidates", ["_SP.csv", "_BR.csv"]),
            "turnout": stage("turnout", ["_SP.csv", "_BR.csv"]),
        }
        print("CSV preparados; importando votos de SP", flush=True)
        con.execute("""CREATE MACRO normalized(s) AS
            regexp_replace(upper(strip_accents(trim(s))), '[^A-Z0-9]', '', 'g');
            CREATE MACRO cleaned(s) AS CASE WHEN s IN ('#NULO','#NE','-1','-3','')
                THEN NULL ELSE trim(s) END;""")
        con.execute(f"""CREATE TABLE vote_source AS
          SELECT ANO_ELEICAO::SMALLINT AS year, CD_ELEICAO::INTEGER AS election,
            NR_TURNO::SMALLINT AS round, SG_UF AS uf, CD_MUNICIPIO::INTEGER AS municipality,
            NM_MUNICIPIO AS municipality_name, NR_ZONA::INTEGER AS zone,
            NR_SECAO::INTEGER AS section, CD_CARGO::SMALLINT AS office,
            DS_CARGO AS office_name, NR_VOTAVEL::INTEGER AS number,
            NM_VOTAVEL AS vote_name, QT_VOTOS::BIGINT AS votes,
            NR_LOCAL_VOTACAO::INTEGER AS location,
            SQ_CANDIDATO::BIGINT AS candidate_id, NM_LOCAL_VOTACAO AS location_name,
            DS_LOCAL_VOTACAO_ENDERECO AS address
          FROM ({' UNION ALL '.join('SELECT * FROM '+sources[k] for k in ['votes_sp','votes_br'])})
          WHERE SG_UF='SP' AND ANO_ELEICAO='2026'""")
        duplicate = con.execute("""SELECT count(*) FROM (SELECT year,election,round,municipality,
            zone,section,office,number FROM vote_source GROUP BY ALL HAVING count(*)>1)""").fetchone()[0]
        if duplicate:
            raise ValueError(f"{duplicate} chaves de votação duplicadas; publicação interrompida")
        if con.execute("SELECT count(*) FROM vote_source WHERE votes<0").fetchone()[0]:
            raise ValueError("Votos negativos")
        con.execute("""CREATE TABLE municipalities AS SELECT DISTINCT municipality, municipality_name
            FROM vote_source;
            CREATE TABLE offices AS SELECT DISTINCT office, office_name FROM vote_source;""")
        con.execute(f"""CREATE TABLE locations AS SELECT
            AA_ELEICAO::SMALLINT AS year, NR_TURNO::SMALLINT AS round,
            CD_MUNICIPIO::INTEGER AS municipality, NR_ZONA::INTEGER AS zone,
            NR_LOCAL_VOTACAO::INTEGER AS location,
            min(NM_LOCAL_VOTACAO) AS location_name, min(DS_ENDERECO) AS address,
            CASE WHEN count(DISTINCT coalesce(normalized(cleaned(NM_BAIRRO)),''))=1
                 THEN min(cleaned(NM_BAIRRO)) END AS neighborhood,
            min(NR_CEP) AS postal_code,
            min(try_cast(replace(NR_LATITUDE,',','.') AS DOUBLE)) AS latitude,
            min(try_cast(replace(NR_LONGITUDE,',','.') AS DOUBLE)) AS longitude,
            count(DISTINCT normalized(DS_ENDERECO)) AS address_variants,
            count(DISTINCT coalesce(normalized(cleaned(NM_BAIRRO)),'')) AS neighborhood_variants
          FROM {sources['locations']} WHERE SG_UF='SP' AND AA_ELEICAO='2026' GROUP BY ALL""")
        con.execute("""CREATE TABLE sections AS WITH base AS (
            SELECT year,election,round,municipality,zone,section,
                min(location) AS location, min(location_name) AS location_name,
                min(address) AS address, count(DISTINCT location) AS location_variants,
                count(DISTINCT normalized(address)) AS vote_address_variants
            FROM vote_source GROUP BY ALL)
          SELECT b.*, CASE WHEN b.location_variants=1 AND b.vote_address_variants=1
              AND l.address_variants=1 AND l.neighborhood_variants=1
              AND normalized(b.address)=normalized(l.address)
              THEN l.neighborhood END AS neighborhood,
            CASE WHEN b.location_variants>1 OR b.vote_address_variants>1 THEN 'vote_conflict'
                 WHEN l.location IS NULL THEN 'missing_location'
                 WHEN l.address_variants>1 OR l.neighborhood_variants>1 THEN 'ambiguous_location'
                 WHEN normalized(b.address)<>normalized(l.address) THEN 'address_changed'
                 WHEN l.neighborhood IS NULL THEN 'missing_neighborhood'
                 ELSE 'matched' END AS match_status,
            l.latitude,l.longitude
          FROM base b LEFT JOIN locations l USING(year,round,municipality,zone,location)""")
        con.execute(f"""CREATE TABLE candidates AS SELECT DISTINCT
            ANO_ELEICAO::SMALLINT AS year, CD_ELEICAO::INTEGER AS election,
            NR_TURNO::SMALLINT AS round, SQ_CANDIDATO::BIGINT AS candidate_id,
            CD_CARGO::SMALLINT AS office, NR_CANDIDATO::INTEGER AS number,
            NM_CANDIDATO AS full_name, NM_URNA_CANDIDATO AS ballot_name,
            SG_PARTIDO AS party, DS_SITUACAO_CANDIDATURA AS registration_status,
            DS_SIT_TOT_TURNO AS result_status
          FROM {sources['candidates']} WHERE SG_UF IN ('SP','BR') AND ANO_ELEICAO='2026'""")
        if con.execute("""SELECT count(*) FROM (SELECT year,election,round,candidate_id
            FROM candidates GROUP BY ALL HAVING count(*)>1)""").fetchone()[0]:
            raise ValueError("Cadastro de candidatos ambíguo")
        con.execute("""CREATE TABLE votes AS SELECT year,election,round,municipality,zone,section,
            office,number,candidate_id,vote_name,votes,
            CASE WHEN candidate_id>0 THEN 'nominal' WHEN number=95 THEN 'blank'
                 WHEN number=96 THEN 'null' WHEN number=97 THEN 'annulled'
                 WHEN number BETWEEN 10 AND 99 THEN 'party' ELSE 'other' END AS vote_kind
          FROM vote_source ORDER BY office,round,municipality,candidate_id,zone,section;
          CREATE VIEW results AS SELECT v.*,s.location,s.location_name,s.address,
            s.neighborhood,s.match_status,m.municipality_name,
            coalesce(c.ballot_name,v.vote_name) AS candidate_name,c.party,c.result_status,
            o.office_name
          FROM votes v JOIN sections s USING(year,election,round,municipality,zone,section)
          JOIN municipalities m USING(municipality)
          JOIN offices o USING(office)
          LEFT JOIN candidates c USING(year,election,round,candidate_id);
          CREATE TABLE local_results AS SELECT year,election,round,municipality,municipality_name,
            zone,location,location_name,address,neighborhood,match_status,office,office_name,
            number,candidate_id,candidate_name,party,result_status,vote_kind,
            sum(votes)::BIGINT AS votes
          FROM results GROUP BY ALL
          ORDER BY office,round,municipality,neighborhood,candidate_id;
          CREATE TABLE candidate_search AS SELECT year,election,round,office,office_name,
            candidate_id,number,candidate_name,party,result_status,sum(votes)::BIGINT AS votes
          FROM local_results WHERE vote_kind='nominal' GROUP BY ALL;""")
        con.execute(f"""CREATE TABLE turnout AS SELECT
            ANO_ELEICAO::SMALLINT AS year,CD_ELEICAO::INTEGER AS election,
            NR_TURNO::SMALLINT AS round,CD_MUNICIPIO::INTEGER AS municipality,
            NR_ZONA::INTEGER AS zone,NR_SECAO::INTEGER AS section,CD_CARGO::SMALLINT AS office,
            QT_APTOS::BIGINT AS eligible,QT_COMPARECIMENTO::BIGINT AS turnout,
            QT_ABSTENCOES::BIGINT AS abstentions,QT_VOTOS_NOMINAIS::BIGINT AS nominal_votes,
            QT_VOTOS_BRANCOS::BIGINT AS blank_votes,QT_VOTOS_NULOS::BIGINT AS null_votes,
            QT_VOTOS_LEGENDA::BIGINT AS party_votes,QT_VOTOS_ANULADOS_APU_SEP::BIGINT AS annulled_votes
          FROM {sources['turnout']} WHERE SG_UF='SP' AND ANO_ELEICAO='2026'""")
        if con.execute("""SELECT count(*) FROM (SELECT year,election,round,municipality,zone,section,office
            FROM turnout GROUP BY ALL HAVING count(*)>1)""").fetchone()[0]:
            raise ValueError("Apuração por seção possui chaves duplicadas")
        original = con.execute("SELECT count(*),sum(votes) FROM vote_source").fetchone()
        joined = con.execute("SELECT count(*),sum(votes) FROM results").fetchone()
        aggregate = con.execute("SELECT sum(votes) FROM local_results").fetchone()[0]
        if original != joined or original[1] != aggregate or not original[0]:
            raise ValueError(f"Falha de conservação de votos: {original}, {joined}, {aggregate}")
        def records(query):
            cursor = con.execute(query)
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        quality = {
            "scope": "SP/2026", "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_rows": original[0], "total_votes_all_offices": original[1],
            "joins_preserve_rows_and_votes": True,
            "geography": records("SELECT match_status,count(*) AS sections FROM sections GROUP BY ALL"),
            "vote_coverage": records("SELECT match_status,sum(votes)::BIGINT AS votes FROM local_results GROUP BY ALL"),
            "totals": records("SELECT election,round,office,office_name,vote_kind,sum(votes)::BIGINT AS votes FROM local_results GROUP BY ALL ORDER BY office,vote_kind"),
            "reconciliation": records("""WITH a AS (SELECT year,election,round,municipality,zone,section,office,
                sum(votes) FILTER(WHERE vote_kind='nominal') AS calculated FROM votes GROUP BY ALL)
              SELECT office,round,count(*) AS sections,
                count(*) FILTER(WHERE coalesce(a.calculated,0)<>t.nominal_votes) AS mismatched_sections,
                sum(t.nominal_votes)::BIGINT AS official_nominal,
                sum(coalesce(a.calculated,0))::BIGINT AS calculated_nominal
              FROM turnout t LEFT JOIN a USING(year,election,round,municipality,zone,section,office)
              GROUP BY ALL ORDER BY office,round"""),
            "sources": {k: json.loads((RAW/k/"source.json").read_text()) for k in SOURCES},
        }
        from .audit import reconcile
        quality["all_vote_kinds_reconciliation"] = reconcile(con)
        if any(r["mismatched_sections"] or r["missing_official_sections"]
               for r in quality["all_vote_kinds_reconciliation"]):
            raise ValueError("Divergência com a totalização oficial; snapshot não publicado")
        from .summaries import build_summaries
        build_summaries(con)
        quality["elapsed_seconds"] = round(time.perf_counter()-start, 2)
        con.execute("CREATE TABLE metadata AS SELECT ?::JSON AS quality", [json.dumps(quality)])
        con.execute("DROP TABLE vote_source; ANALYZE; CHECKPOINT")
        for table in ("votes","sections","locations","candidates"):
            con.execute(f"COPY {table} TO {literal(WAREHOUSE / (table+'.parquet.part'))} (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"""COPY (SELECT year,election,round,municipality,zone,location,
            location_name,address,match_status,count(*) AS sections FROM sections
            WHERE match_status<>'matched' GROUP BY ALL ORDER BY municipality,zone,location)
            TO {literal(ROOT / 'reports/unmatched_locations.csv')} (HEADER,DELIMITER ';')""")
        con.close()
        output.replace(DATABASE)
        for table in ("votes","sections","locations","candidates"):
            (WAREHOUSE / (table+".parquet.part")).replace(WAREHOUSE / (table+".parquet"))
        (ROOT / "reports/quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2))
        (ROOT / "reports/reconciliation.json").write_text(json.dumps(quality["all_vote_kinds_reconciliation"],indent=2))
        print(json.dumps({k:v for k,v in quality.items() if k!='sources'},ensure_ascii=False,indent=2),flush=True)
    except BaseException:
        con.close()
        output.unlink(missing_ok=True)
        raise
