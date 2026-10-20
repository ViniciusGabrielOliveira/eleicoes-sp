import importlib
from fastapi.testclient import TestClient

def public_client(monkeypatch):
    monkeypatch.setenv('ELEICOES_ORIGINS','https://atlas.example')
    from eleicoes_sp import public_api
    return TestClient(importlib.reload(public_api).app)

def test_only_public_read_routes_are_accessible(monkeypatch):
    client=public_client(monkeypatch)
    for path in ['/docs','/openapi.json','/atlas/','/reports/votes','/quality','/data/warehouse/eleicoes.duckdb','/.env','/map/geometry/other']:
        assert client.get(path).status_code==404
    assert client.post('/map/data').status_code==405
    for path in ['/health','/map/catalog','/map/data?municipalities=71072','/map/geometry/municipality','/map/area-candidates?office=1&key=71072']:
        assert client.get(path).status_code==200
    assert client.get('/map/data?'+('x'*32769)).status_code==414

def test_cors_allows_only_configured_frontend(monkeypatch):
    client=public_client(monkeypatch)
    allowed=client.get('/health',headers={'Origin':'https://atlas.example'})
    assert allowed.headers['access-control-allow-origin']=='https://atlas.example'
    assert allowed.headers['x-content-type-options']=='nosniff'
    denied=client.get('/health',headers={'Origin':'https://unrelated.example'})
    assert 'access-control-allow-origin' not in denied.headers
    assert client.options('/map/data',headers={'Origin':'https://atlas.example','Access-Control-Request-Method':'GET'}).status_code==200
