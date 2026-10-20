"""Agregações e posições calculadas na carga, para não recalcular o estado a cada busca."""
GROUPS = {
    "municipality": ["municipality", "municipality_name"],
    "neighborhood": ["municipality", "municipality_name", "neighborhood"],
    "location": ["municipality", "municipality_name", "zone", "location", "location_name", "address", "neighborhood"],
    "section": ["municipality", "municipality_name", "zone", "section", "location", "location_name", "address", "neighborhood"],
}

def build_summaries(con):
    for name,fields in GROUPS.items():
        print(f"Preparando relatório por {name}",flush=True)
        dimensions=["year","election","round","office","office_name"]+fields
        group=",".join(dimensions)
        source="results" if name=="section" else "local_results"
        con.execute(f"""CREATE OR REPLACE TABLE summary_{name} AS WITH grouped AS (
            SELECT {group},candidate_id,number,candidate_name,party,result_status,
                sum(votes)::BIGINT AS votes FROM {source} WHERE vote_kind='nominal' GROUP BY ALL)
          SELECT *,sum(votes) OVER(PARTITION BY {group})::BIGINT AS nominal_total,
            dense_rank() OVER(PARTITION BY {group} ORDER BY votes DESC) AS position,
            max(votes) OVER(PARTITION BY {group})::BIGINT AS leader_votes
          FROM grouped ORDER BY office,round,candidate_id,municipality""")
