"""Descoberta oficial, downloads retomáveis e proveniência dos arquivos."""
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(os.environ.get("ELEICOES_ROOT", Path(__file__).resolve().parents[2])).resolve()
RAW = ROOT / "data/raw"
SOURCES = {
    "votes_sp": ("resultados-2026", "votacao_secao_2026_SP.zip"),
    "votes_br": ("resultados-2026", "votacao_secao_2026_BR.zip"),
    "locations": ("eleitorado-2026", "eleitorado_local_votacao_2026.zip"),
    "candidates": ("candidatos-2026", "consulta_cand_2026.zip"),
    "turnout": ("resultados-2026", "detalhe_votacao_secao_2026.zip"),
}

def fetch_one(item):
    key, (dataset, filename) = item
    metadata = json.load(urllib.request.urlopen(
        f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={dataset}", timeout=60))
    resource = next(r for r in metadata["result"]["resources"]
                    if r["url"].rsplit("/", 1)[-1] == filename)
    url = resource["url"]
    if urlparse(url).hostname != "cdn.tse.jus.br" or not url.startswith("https://"):
        raise ValueError("Origem não autorizada: " + url)
    folder = RAW / key
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    manifest_path = folder / "source.json"
    if target.exists() and manifest_path.exists():
        print(f"{key}: arquivo local preservado (use --refresh para atualizar)", flush=True)
        return
    part = target.with_suffix(".zip.part")
    for attempt in range(4):
        offset = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                append = offset > 0 and response.status == 206
                headers = dict(response.headers)
                with part.open("ab" if append else "wb") as output:
                    while chunk := response.read(4 * 1024 * 1024):
                        output.write(chunk)
            with zipfile.ZipFile(part) as archive:
                members = [{"name": x.filename, "bytes": x.file_size} for x in archive.infolist()]
            with part.open("rb") as downloaded:
                digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
            part.replace(target)
            manifest_path.write_text(json.dumps({
                "key": key, "dataset": dataset, "resource_id": resource["id"],
                "url": url, "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "sha256": digest, "bytes": target.stat().st_size,
                "http_headers": headers, "members": members,
                "resource": resource,
            }, ensure_ascii=False, indent=2))
            print(f"{key}: {target.stat().st_size:,} bytes; {len(members)} arquivos", flush=True)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

def download(refresh=False):
    if refresh:
        for key in SOURCES:
            (RAW / key / "source.json").unlink(missing_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(fetch_one, SOURCES.items()))
