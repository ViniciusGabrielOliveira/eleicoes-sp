"""Casos contábeis: candidato filtrado não pode virar 100% artificialmente."""
import duckdb
import pytest

from eleicoes_sp.query import report

@pytest.fixture
def con():
    db = duckdb.connect()
    db.execute("""CREATE TABLE local_results(year INTEGER,election INTEGER,round INTEGER,
      office INTEGER,office_name VARCHAR,municipality INTEGER,municipality_name VARCHAR,
      neighborhood VARCHAR,zone INTEGER,location INTEGER,section INTEGER,location_name VARCHAR,
      address VARCHAR,match_status VARCHAR,candidate_id BIGINT,number INTEGER,
      candidate_name VARCHAR,party VARCHAR,result_status VARCHAR,vote_kind VARCHAR,votes BIGINT)""")
    base = [2026,6259,1,6,"Deputado Federal",71072,"SÃO PAULO","CENTRO",1,101,1,
            "ESCOLA","RUA A, 1","matched"]
    cases = [
        base+[100,1010,"ANA","AAA","ELEITO","nominal",30],
        base+[200,2020,"BRUNO","BBB","NÃO ELEITO","nominal",70],
        base+[-1,10,"LEGENDA","AAA",None,"party",40],
        base+[-1,95,"BRANCO",None,None,"blank",20],
        base[:2]+[2]+base[3:]+[100,1010,"ANA","AAA","ELEITO","nominal",900],
        base[:3]+[7,"Deputado Estadual"]+base[5:]+[100,1010,"ANA","AAA","ELEITO","nominal",900],
        base[:7]+[None]+base[8:]+[100,1010,"ANA","AAA","ELEITO","nominal",10],
    ]
    db.executemany("INSERT INTO local_results VALUES ("+",".join("?" for _ in cases[0])+")",cases)
    db.execute("CREATE VIEW results AS SELECT * FROM local_results")
    yield db
    db.close()

def test_denominator_before_candidate_and_party_filter(con):
    for selection in ({"candidate_id":100},{"party":"AAA"}):
        data=report(con,6,municipality=71072,neighborhood="centro",**selection)["rows"]
        assert len(data)==1
        assert data[0]["votes"]==30
        assert data[0]["nominal_total"]==100
        assert data[0]["nominal_share_pct"]==30
        assert data[0]["position"]==2
        assert data[0]["gap_to_leader"]==40

def test_missing_neighborhood_preserves_votes(con):
    data=report(con,6,candidate_id=100)["rows"]
    assert sum(r["votes"] for r in data)==40
    assert any(r["neighborhood"] is None for r in data)

def test_section_uses_detail_and_preserves_denominator(con):
    result=report(con,6,candidate_id=100,municipality=71072,neighborhood="CENTRO",section=1,group_by="section")
    assert result["source_table"]=="results"
    assert result["rows"][0]["nominal_total"]==100

def test_neighborhood_requires_municipality(con):
    with pytest.raises(ValueError,match="município"):
        report(con,6,neighborhood="CENTRO")

def test_filters_are_parameters(con):
    assert report(con,6,municipality=71072,neighborhood="' OR 1=1 --")["rows"]==[]
    with pytest.raises(ValueError):
        report(con,6,group_by="municipality; DROP TABLE local_results")

def test_min_votes_does_not_change_denominator(con):
    data=report(con,6,municipality=71072,neighborhood="CENTRO",min_votes=50)["rows"]
    assert len(data)==1 and data[0]["nominal_total"]==100

def test_materialized_reports_match_dynamic_results(con):
    from eleicoes_sp.summaries import build_summaries
    cases = [dict(office=6,candidate_id=100,municipality=71072,neighborhood="CENTRO"),
             dict(office=6,group_by="municipality"),
             dict(office=6,group_by="section",municipality=71072,section=1)]
    before = [report(con,**case)["rows"] for case in cases]
    build_summaries(con)
    for case,expected in zip(cases,before):
        actual=report(con,**case)
        assert actual["rows"]==expected
        assert actual["source_table"].startswith("summary_")
    # Um subconjunto de locais muda o universo do bairro: precisa recalcular.
    assert report(con,6,zone=1)["source_table"]=="local_results"
