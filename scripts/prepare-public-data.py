"""Copia somente os cinco arquivos públicos necessários, nunca a pasta pessoal."""
import hashlib
import json
import shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
target=root/'deploy/runtime/data'
files=['warehouse/eleicoes.duckdb','warehouse/candidate_totals.parquet',
       'geo/catalog.json','geo/cities.json','geo/areas.json']
manifest=[]
for name in files:
    source=root/'data'/name
    if source.is_symlink() or not source.is_file():raise RuntimeError(f'Arquivo inválido: {name}')
    dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
    part=dest.with_suffix(dest.suffix+'.part')
    shutil.copyfile(source,part);part.chmod(0o444);part.replace(dest)
    manifest.append({'file':name,'bytes':dest.stat().st_size,'sha256':hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()})
(root/'deploy/runtime/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Preparados {len(manifest)} arquivos permitidos; {sum(f["bytes"] for f in manifest)/1024**2:.1f} MiB')

context=root/'deploy/runtime/build-context'
context.mkdir(parents=True,exist_ok=True)
for name in ['pyproject.toml','requirements.lock']:
    shutil.copyfile(root/name,context/name)
shutil.copyfile(root/'deploy/Dockerfile',context/'Dockerfile')
for source in (root/'src').rglob('*.py'):
    if source.is_symlink():raise RuntimeError('Código simbólico não permitido')
    dest=context/source.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,dest)
print('Contexto Docker separado: somente Dockerfile, dependências e código Python')
