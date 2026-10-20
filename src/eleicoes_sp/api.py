import csv
import io
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from .download import ROOT

from .query import connection, filters, report, rows, status

app = FastAPI(title="Eleições SP · 2026", version="0.1.0",
    description="Votos públicos agregados. Bairro corresponde ao local de votação. "
        "Consultas de leitura em snapshot auditado; dados oficiais do TSE.")
# Evita que relatórios simultâneos consumam toda a memória da máquina.
CAPACITY = threading.BoundedSemaphore(2)
app.add_middleware(GZipMiddleware,minimum_size=1000)

def run_query(fn):
    if not CAPACITY.acquire(blocking=False):
        raise HTTPException(429, "Duas consultas em execução; tente novamente", headers={"Retry-After":"1"})
    try:
        with connection() as con:
            return fn(con)
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        CAPACITY.release()

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/atlas/" if (ROOT/'frontend/dist/frontend/browser/index.html').exists() else '/docs')

@app.get("/health")
def health():
    return run_query(lambda con: {"status":"ok", "scope":"SP/2026",
        "generated_at": status(con)["generated_at"]})

@app.get("/quality")
def quality():
    return run_query(status)

@app.get("/offices")
def offices():
    return run_query(lambda con: rows(con, "SELECT * FROM offices ORDER BY office"))

@app.get("/municipalities")
def municipalities(q: str = Query("",max_length=120)):
    return run_query(lambda con: rows(con, """SELECT * FROM municipalities
        WHERE contains(strip_accents(upper(municipality_name)),strip_accents(upper(?)))
        ORDER BY municipality_name""", [q]))

@app.get("/neighborhoods")
def neighborhoods(municipality: int, round: int = Query(1,ge=1,le=2)):
    return run_query(lambda con: rows(con, """SELECT neighborhood,count(DISTINCT (zone,section)) AS sections
        FROM sections WHERE municipality=? AND round=? GROUP BY neighborhood ORDER BY neighborhood""",
        [municipality,round]))

@app.get("/candidates")
def candidates(q: str = Query("",max_length=120), office: int | None = None,
               party: str | None = Query(None,max_length=30), round: int = Query(1,ge=1,le=2),
               limit: int = Query(50,ge=1,le=500), offset: int = Query(0,ge=0)):
    clauses = ["round=?", "(contains(strip_accents(upper(candidate_name)),strip_accents(upper(?))) OR number::VARCHAR=?)"]
    params = [round,q,q]
    if office is not None:
        clauses.append("office=?"); params.append(office)
    if party:
        clauses.append("party=?"); params.append(party.upper())
    return run_query(lambda con: rows(con, f"SELECT * FROM candidate_search WHERE {' AND '.join(clauses)} ORDER BY votes DESC,candidate_id LIMIT ? OFFSET ?",params+[limit,offset]))

@app.get("/reports/votes")
def vote_report(office: int = Query(...,description="1 presidente; 3 governador; 5 senador; 6 deputado federal; 7 deputado estadual"),
    round: int = Query(1,ge=1,le=2),
    group_by: Literal["municipality","neighborhood","location","section"] = "neighborhood",
    candidate_id: int | None = None, party: str | None = Query(None,max_length=30),
    municipality: int | None = None, neighborhood: str | None = Query(None,max_length=200),
    zone: int | None = None, location: int | None = None, section: int | None = None,
    address: str | None = Query(None,max_length=200), election: int | None = None,
    match_status: Literal["matched","address_changed","ambiguous_location","missing_location","missing_neighborhood","vote_conflict"] | None = None,
    min_votes: int = Query(0,ge=0), limit: int = Query(100,ge=1,le=5000), offset: int = Query(0,ge=0),
    format: Literal["json","csv"] = "json"):
    values = locals().copy()
    values.pop("format")
    result = run_query(lambda con: report(con,**values))
    if format == "json":
        return result
    output = io.StringIO()
    if result["rows"]:
        writer = csv.DictWriter(output, fieldnames=result["rows"][0].keys())
        writer.writeheader(); writer.writerows(result["rows"])
    return Response(output.getvalue(),media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":"attachment; filename=votos-sp-2026.csv"})

@app.get("/reports/turnout")
def turnout(office: int, round: int = Query(1,ge=1,le=2), municipality: int | None = None,
            neighborhood: str | None = Query(None,max_length=200),
            limit: int = Query(100,ge=1,le=5000), offset: int = Query(0,ge=0)):
    if neighborhood and municipality is None:
        raise HTTPException(422,"Informe o município ao filtrar um bairro")
    clauses, params = filters({"municipality":municipality,"neighborhood":neighborhood},"s.")
    condition = " AND ".join(["t.office=?","t.round=?"]+clauses)
    return run_query(lambda con: rows(con,f"""SELECT t.office,t.round,t.municipality,
      m.municipality_name,s.neighborhood,sum(eligible)::BIGINT AS eligible,
      sum(turnout)::BIGINT AS turnout,sum(abstentions)::BIGINT AS abstentions,
      round(100.0*sum(abstentions)/nullif(sum(eligible),0),4) AS abstention_pct,
      sum(nominal_votes)::BIGINT AS nominal_votes,sum(blank_votes)::BIGINT AS blank_votes,
      sum(null_votes)::BIGINT AS null_votes,sum(party_votes)::BIGINT AS party_votes
      FROM turnout t LEFT JOIN sections s USING(year,election,round,municipality,zone,section)
      JOIN municipalities m ON t.municipality=m.municipality
      WHERE {condition} GROUP BY ALL ORDER BY eligible DESC,t.municipality,s.neighborhood
      LIMIT ? OFFSET ?""",[office,round]+params+[limit,offset]))

from .map_api import router as map_router
app.include_router(map_router)
frontend=ROOT/'frontend/dist/frontend/browser'
if frontend.exists():
    app.mount('/atlas',StaticFiles(directory=frontend,html=True),name='atlas')
