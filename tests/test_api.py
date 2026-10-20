"""Validação integrada contra o snapshot real, quando disponível."""
import asyncio

import httpx
import pytest

from eleicoes_sp.api import app
from eleicoes_sp.pipeline import DATABASE

pytestmark = pytest.mark.skipif(not DATABASE.exists(),reason="Snapshot real ainda não importado")

def request(path):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            return await client.get(path)
    return asyncio.run(run())

def test_real_candidate_report_and_csv():
    candidates=request("/candidates?office=6&limit=1").json()
    candidate=candidates[0]["candidate_id"]
    url=f"/reports/votes?office=6&candidate_id={candidate}&municipality=71072&group_by=section&limit=3"
    result=request(url)
    assert result.status_code==200
    report=result.json()
    assert report["source_table"]=="summary_section"
    assert len(report["rows"])==3
    assert all(0<=r["nominal_share_pct"]<=100 for r in report["rows"])
    csv=request(url+"&format=csv")
    assert csv.status_code==200 and "nominal_share_pct" in csv.text.splitlines()[0]

def test_real_scope_quality_and_turnout():
    quality=request("/quality").json()
    assert quality["scope"]=="SP/2026"
    assert quality["joins_preserve_rows_and_votes"]
    assert all(r["mismatched_sections"]==0 for r in quality["reconciliation"])
    turnout=request("/reports/turnout?office=6&municipality=71072")
    assert turnout.status_code==200
    assert all(r["turnout"]+r["abstentions"]==r["eligible"] for r in turnout.json())

def test_invalid_api_filters():
    assert request("/reports/votes?office=6&neighborhood=CENTRO").status_code==422
    assert request("/reports/votes?office=6&limit=5001").status_code==422
    assert request("/reports/votes?office=6&group_by=invalid").status_code==422
