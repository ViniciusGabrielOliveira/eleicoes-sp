# Atlas Eleitoral SP · 2026

Front Angular 22 com Leaflet e camada canvas proporcional. Os dados vêm da API FastAPI local; não há dados eleitorais fictícios.

Consulte [o README do projeto](../README.md) e [a metodologia](../docs/mapa.md).

## Executar

Na raiz do projeto, prepare os dados e malhas com `.venv/bin/eleicoes geography`.
Dentro desta pasta:

```bash
npm ci
npm run build -- --base-href /atlas/
```

Na raiz, inicie ou reinicie `.venv/bin/eleicoes serve`. Abra http://127.0.0.1:8026/atlas/.
A mesma API serve os arquivos compilados e as consultas, sem configuração de CORS.

## Validar

```bash
npm test -- --watch=false
npx playwright test
```

Os testes de navegador exigem a API ativa e Chromium disponível. Para usar uma instalação
existente, informe `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. As capturas são salvas em `../reports/`.
