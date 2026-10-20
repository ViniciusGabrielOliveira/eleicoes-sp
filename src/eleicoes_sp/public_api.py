"""Superfície pública mínima: somente consultas usadas pelo atlas."""
import os
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from .api import app as internal

ALLOWED={'/health','/candidates','/map/catalog','/map/geometry/municipality',
    '/map/geometry/neighborhood','/map/data','/map/area-candidates'}
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
origins=[v.strip() for v in os.environ.get('ELEICOES_ORIGINS','').split(',') if v.strip()]
if not origins or '*' in origins:
    raise RuntimeError('Defina ELEICOES_ORIGINS com origens HTTPS explícitas')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET'],allow_headers=['ngrok-skip-browser-warning'],allow_credentials=False)
app.add_middleware(GZipMiddleware,minimum_size=1000)

@app.middleware('http')
async def public_boundary(request:Request,call_next):
    if request.url.path not in ALLOWED:return JSONResponse({'detail':'Not found'},status_code=404)
    if request.method not in ('GET','HEAD','OPTIONS'):return JSONResponse({'detail':'Method not allowed'},status_code=405)
    if len(request.scope.get('query_string',b''))>32768:return JSONResponse({'detail':'Query too long'},status_code=414)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    return response

# Compartilha somente as rotas explicitamente autorizadas, sem arquivos locais ou /docs.
for route in internal.routes:
    if getattr(route,'path',None) in ALLOWED or getattr(route,'path',None)=='/map/geometry/{level}':
        app.router.routes.append(route)

from .map_api import router as map_router
app.include_router(map_router)
