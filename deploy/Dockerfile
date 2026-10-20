FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ELEICOES_ROOT=/app HOME=/tmp
WORKDIR /app
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && mkdir -p /app/data
USER 10001:10001
CMD ["uvicorn","eleicoes_sp.public_api:app","--host","0.0.0.0","--port","8080","--workers","1","--no-proxy-headers","--no-access-log","--limit-concurrency","24","--timeout-keep-alive","5"]
