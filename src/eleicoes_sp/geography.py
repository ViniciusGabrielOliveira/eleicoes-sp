"""Malhas IBGE e áreas de referência estimadas dos bairros dos locais TSE."""
import collections
import gzip
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
import zipfile
from datetime import datetime,timezone

import shapefile
from pyproj import Transformer
from shapely import make_valid,voronoi_polygons
from shapely.geometry import MultiPoint,Point,shape,mapping
from shapely.ops import transform,unary_union

from .download import ROOT
from .query import connection

GEO=ROOT/'data/geo'
SOURCES={
 'municipalities.json':'https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios?orderBy=nome',
 'municipalities.geojson':'https://servicodados.ibge.gov.br/api/v3/malhas/estados/35?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio',
 'neighborhoods.zip':'https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/bairros/shp/UF/SP/SP_bairros_CD2022.zip'}

def normalized(value):
    return re.sub('[^A-Z0-9]','',unicodedata.normalize('NFKD',value.upper()).encode('ascii','ignore').decode())

def build_geography():
    GEO.mkdir(parents=True,exist_ok=True)
    for name,url in SOURCES.items():
        path=GEO/name
        if not path.exists():
            with urllib.request.urlopen(url,timeout=120) as response:
                data=response.read()
            if data[:2]==b'\x1f\x8b': data=gzip.decompress(data)
            path.write_bytes(data)
    ibge=json.loads((GEO/'municipalities.json').read_bytes())
    by_name={normalized(m['nome']):m for m in ibge}
    # Grafia TSE/IBGE conferida na tabela oficial de localidades baixada.
    aliases={'SAOLUISDOPARAITINGA':'SAOLUIZDOPARAITINGA'}
    with connection() as con:
        cities=con.execute('SELECT municipality,municipality_name FROM municipalities').fetchall()
        sites=con.execute("""SELECT DISTINCT municipality,neighborhood,latitude,longitude
            FROM locations WHERE year=2026 AND round=1 AND neighborhood IS NOT NULL
            AND latitude BETWEEN -26 AND -19 AND longitude BETWEEN -54 AND -44""").fetchall()
        neighborhoods=con.execute("""SELECT DISTINCT municipality,neighborhood FROM sections
            WHERE neighborhood IS NOT NULL ORDER BY municipality,neighborhood""").fetchall()
    catalog=[];code_map={}
    for code,name in cities:
        m=by_name[aliases.get(normalized(name),normalized(name))]
        immediate=m['regiao-imediata']; intermediate=immediate['regiao-intermediaria']
        record=dict(municipality=code,name=name,ibge=m['id'],region=str(intermediate['id']),
            region_name=intermediate['nome'],immediate=str(immediate['id']),immediate_name=immediate['nome'])
        catalog.append(record);code_map[str(m['id'])]=record
    assert len(catalog)==645 and len(code_map)==645
    boundaries=json.loads((GEO/'municipalities.geojson').read_bytes())
    city_shapes={};city_features=[]
    for f in boundaries['features']:
        city=code_map[f['properties']['codarea']]
        polygon=make_valid(shape(f['geometry']))
        city_shapes[city['municipality']]=polygon
        anchor=polygon.representative_point()
        city_features.append(dict(type='Feature',geometry=mapping(polygon),properties={**city,'key':str(city['municipality']),'kind':'municipality','anchor':[anchor.x,anchor.y]}))
    z=zipfile.ZipFile(GEO/'neighborhoods.zip')
    reader=shapefile.Reader(shp=io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('.shp')))),
        dbf=io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('.dbf')))),encoding='utf8')
    official=collections.defaultdict(list)
    for record in reader.iterShapeRecords():
        r=record.record.as_dict();city=code_map.get(r['CD_MUN'])
        if city:
            official[(city['municipality'],normalized(r['NM_BAIRRO']))].append(make_valid(shape(record.shape.__geo_interface__)))
    seeds=collections.defaultdict(lambda:collections.defaultdict(set))
    for city,name,lat,lon in sites:
        point=Point(lon,lat)
        if city_shapes[city].buffer(.002).covers(point):
            seeds[city][(lon,lat)].add(name)
    names=collections.defaultdict(list)
    for city,name in neighborhoods:names[city].append(name)
    project=Transformer.from_crs(4326,3857,always_xy=True).transform
    unproject=Transformer.from_crs(3857,4326,always_xy=True).transform
    features=[];unmapped=[]
    for city in catalog:
        code=city['municipality'];boundary=city_shapes[code]
        name_counts=collections.Counter(normalized(n) for n in names[code])
        points=[(xy,next(iter(ns))) for xy,ns in seeds[code].items() if len(ns)==1]
        exact={}
        for name in names[code]:
            if name_counts[normalized(name)]>1:continue
            geometries=official.get((code,normalized(name)),[])
            if not geometries:continue
            polygon=unary_union(geometries).intersection(boundary)
            own=[Point(xy) for xy,n in points if n==name]
            # O nome sozinho não basta: verificar os locais de votação dentro da malha.
            if own and sum(polygon.buffer(.0001).covers(p) for p in own)/len(own)>=.5:
                exact[name]=polygon
        occupied=unary_union(list(exact.values())) if exact else None
        estimated=collections.defaultdict(list)
        if points:
            projected=[transform(project,Point(xy)) for xy,_ in points]
            border=transform(project,boundary)
            cells=([border] if len(projected)==1 else
                list(voronoi_polygons(MultiPoint(projected),extend_to=border.envelope,ordered=True).geoms))
            for (_,name),cell in zip(points,cells):
                if name in exact:continue
                clipped=transform(unproject,cell.intersection(border))
                if occupied is not None:clipped=clipped.difference(occupied)
                if not clipped.is_empty:estimated[name].append(clipped)
        for name in names[code]:
            polygon=exact.get(name)
            kind='official'
            if polygon is None:
                kind='estimated';polygon=unary_union(estimated[name]) if estimated[name] else None
            key=f'{code}|{name}'
            if polygon is None or polygon.is_empty:
                unmapped.append(key);continue
            polygon=make_valid(polygon.simplify(.00004,preserve_topology=True))
            anchor=polygon.representative_point()
            features.append(dict(type='Feature',geometry=mapping(polygon),properties=dict(
                key=key,municipality=code,name=name,municipality_name=city['name'],kind=kind,anchor=[anchor.x,anchor.y])))
    payload=dict(municipalities=sorted(catalog,key=lambda c:c['name']),
        neighborhoods=[dict(key=f'{c}|{n}',municipality=c,name=n,geometry=next((f['properties']['kind'] for f in features if f['properties']['key']==f'{c}|{n}'),None)) for c,n in neighborhoods],
        regions=[dict(id=k,name=n) for k,n in sorted({(c['region'],c['region_name']) for c in catalog})],
        immediate_regions=[dict(id=k,name=n) for k,n in sorted({(c['immediate'],c['immediate_name']) for c in catalog})])
    def save(name,data):
        part=GEO/(name+'.part');part.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')));part.replace(GEO/name)
    save('catalog.json',payload)
    save('cities.json',dict(type='FeatureCollection',features=city_features))
    save('areas.json',dict(type='FeatureCollection',features=features))
    quality=dict(generated_at=datetime.now(timezone.utc).isoformat(),municipalities=len(catalog),
        official=sum(f['properties']['kind']=='official' for f in features),
        estimated=sum(f['properties']['kind']=='estimated' for f in features),unmapped=unmapped,
        method='Voronoi dos locais TSE com coordenadas válidas, recortado pelo município IBGE. Não representa limites oficiais nem residência.',
        sources={name:dict(url=url,sha256=hashlib.sha256((GEO/name).read_bytes()).hexdigest()) for name,url in SOURCES.items()})
    save('quality.json',quality)
    (ROOT/'reports/geography.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in quality.items() if k not in ('unmapped','sources')},ensure_ascii=False),flush=True)

if __name__=='__main__':build_geography()
