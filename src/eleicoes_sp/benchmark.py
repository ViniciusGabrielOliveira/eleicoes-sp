import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import perf_counter

from .download import ROOT
from .query import connection, report

def benchmark():
    with connection() as con:
        candidate = con.execute("SELECT candidate_id FROM candidate_search WHERE office=6 ORDER BY votes DESC LIMIT 1").fetchone()[0]
    queries = {
        "candidate_by_neighborhood_statewide": dict(office=6,candidate_id=candidate),
        "candidate_by_location_capital": dict(office=6,candidate_id=candidate,municipality=71072,group_by="location"),
        "candidate_by_section_capital": dict(office=6,candidate_id=candidate,municipality=71072,group_by="section"),
        "ranking_by_municipality_statewide": dict(office=6,group_by="municipality"),
    }
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"repetitions":3,
            "limit":100,"queries":{},"cache":"OS cache compartilhado; não representa disco frio"}
    def measure(values):
        start=perf_counter()
        with connection() as con:
            data=report(con,**values)
        return (perf_counter()-start)*1000,len(data["rows"])
    for name,values in queries.items():
        timings=[measure(values) for _ in range(3)]
        result["queries"][name]={"median_ms":round(statistics.median(t[0] for t in timings),2),
            "max_ms":round(max(t[0] for t in timings),2),"rows_returned":timings[0][1]}
    with ThreadPoolExecutor(2) as pool:
        timings=list(pool.map(measure,[queries["candidate_by_neighborhood_statewide"]]*2))
    result["concurrent_two_queries_ms"]=[round(t[0],2) for t in timings]
    (ROOT/"reports/benchmark.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
