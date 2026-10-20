#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
export ELEICOES_ORIGINS="${ELEICOES_ORIGINS:-https://viniciusgabrieloliveira.github.io}"
case "${1:-status}" in
 start) docker compose -f deploy/compose.yaml up -d ;;
 stop) docker compose -f deploy/compose.yaml down ;;
 status) docker compose -f deploy/compose.yaml ps ;;
 logs) docker compose -f deploy/compose.yaml logs --tail 30 api gateway ;;
 *) echo 'Uso: scripts/public-api.sh start|stop|status|logs';exit 2 ;;
esac
