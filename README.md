# Eleições SP · 2026

Base analítica local para avaliar candidatos a presidente, governador, senador,
deputado federal e deputado estadual pelos votos registrados em São Paulo.
Escopo confirmado: **somente 2026**, todos os **645 municípios de SP**.

## Usar agora

O atlas fica em **http://127.0.0.1:8026/atlas/**, com mapa navegável de pixels proporcionais,
filtros múltiplos de cidades/bairros/regiões e legenda de candidatos com cores editáveis.
A API continua em **http://127.0.0.1:8026/docs**.

O mapa aceita um cargo por vez. Ao aproximar, a visão automática passa de municípios
para bairros; selecionar bairros também ativa o detalhe. O zoom enquadra o recorte selecionado.
Os blocos têm área proporcional ao número absoluto de votos, independentemente do tamanho
geográfico do bairro. A escala corrente em votos por quadrícula fica abaixo do mapa.
Ao passar o mouse pelo bairro ou bloco, aparecem os cinco mais votados: nome, votos locais
e percentual sobre o total nacional da mesma candidatura no mesmo turno. Para presidente,
esse denominador inclui todas as UFs e exterior; para cargos estaduais de SP, é o total em SP.
Sem escolher candidatos, mostra os seis mais votados e agrupa os demais em cinza.
Escolher até dez candidatos preserva todos os outros votos no denominador.
Com candidatos selecionados, o desenho mostra somente seus votos e omite "Outros";
o tamanho dos símbolos e o total do painel passam a corresponder aos candidatos filtrados,
sem aumentar a área por voto. Cidades e bairros usam símbolos circulares, inclusive após filtrar e aproximar o mapa.

As regiões são as **11 intermediárias e 53 imediatas do IBGE**, e não as regiões
administrativas estaduais nem as zonas eleitorais do TRE. O cadastro cruza os 645 códigos
municipais TSE com os códigos IBGE por nome normalizado e uma divergência de grafia revisada.

Foram obtidos limites compatíveis para 481 bairros; 6.380 usam áreas aproximadas de
proximidade dos locais de votação, recortadas pelo município. Elas não equivalem a
limites oficiais. O usuário autorizou esse complemento em 20/10/2026. O botão
"Incluir áreas aproximadas" permite ocultá-las; o clique na área informa sua origem.
Áreas sem coordenadas válidas continuam nos totais e na contagem de votos sem área exibida.
Ver [metodologia do mapa](docs/mapa.md) e [auditoria geográfica](reports/geography.json).

Para reconstruir o front ou as malhas:

```bash
.venv/bin/eleicoes geography
.venv/bin/eleicoes national-totals
cd frontend
npm ci
npm run build -- --base-href /atlas/
```

Depois de compilar pela primeira vez, reinicie a API para montar `/atlas/`.

```bash
cd /home/vini/Projects/eleicoes-sp
.venv/bin/eleicoes serve
```

Fluxo de consulta:

1. `/candidates`: procure pelo nome ou número; copie o `candidate_id`.
2. `/municipalities`: procure a cidade; copie `municipality` (código TSE).
3. `/neighborhoods`: liste os bairros do município.
4. `/reports/votes`: informe cargo, candidato, município e bairro. Escolha
   `group_by=neighborhood`, `municipality`, `location` ou `section`.
5. Para baixar o relatório, use `format=csv`. A exportação respeita a página consultada;
   o limite é 5.000 linhas, com `offset` para as próximas páginas.

Exemplos de consultas locais:

```bash
curl 'http://127.0.0.1:8026/candidates?office=6&limit=10'
curl 'http://127.0.0.1:8026/municipalities?q=Campinas'
curl 'http://127.0.0.1:8026/neighborhoods?municipality=71072'
curl 'http://127.0.0.1:8026/reports/votes?office=6&municipality=71072&neighborhood=VILA%20MARIANA&limit=20'
curl 'http://127.0.0.1:8026/reports/turnout?office=6&municipality=71072'
```

| Cargo | Código |
|---|---:|
| Presidente | 1 |
| Governador | 3 |
| Senador | 5 |
| Deputado federal | 6 |
| Deputado estadual | 7 |

Filtros: turno, eleição, cargo, candidato, partido, município, bairro, zona, local,
seção, trecho do endereço, votos mínimos e qualidade do relacionamento.
Bairro requer município para evitar somar bairros homônimos de cidades diferentes.

Relatórios retornam votos, percentual dos votos nominais do território, posição,
votos do líder e diferença para ele. O denominador e a posição incluem todos os candidatos
do mesmo cargo/turno/território, mesmo quando você filtra um único candidato ou partido.
Abstenção, comparecimento, brancos, nulos e legenda ficam no relatório de participação.

## Dados importados em 20/10/2026

- 17.891.697 registros de votação; 103.656 seções distintas.
- 11.079 combinações município/zona/local identificadas nos resultados.
- 2.450 registros candidato/cargo/eleição/turno com votos nominais em SP.
- Primeiro turno nas bases baixadas. O segundo turno será importado quando publicado;
  consultas ao turno ainda ausente retornam lista vazia.
- Todos os votos preservados nos relacionamentos e nas agregações.
- Votos nominais conferidos seção a seção com a base oficial de apuração dos cinco cargos.
- 99,57% dos votos de todos os cargos relacionados com segurança ao bairro do local.

Os 888 registros de seção com local ausente e 60 com endereço divergente incluem as duas
abrangências da eleição (federal e estadual); não representam 948 seções físicas distintas.
A auditoria detalhada está em [reports/quality.json](reports/quality.json), a conferência de
todas as categorias em [reports/reconciliation.json](reports/reconciliation.json) e os locais
pendentes em [reports/unmatched_locations.csv](reports/unmatched_locations.csv).

**Bairro significa bairro do local de votação, não residência do eleitor.** Bairros são
os textos do cadastro TSE; não equivalem necessariamente aos distritos ou polígonos oficiais.
Cadastros têm data de extração e podem refletir alterações: endereço divergente fica sem
bairro atribuído. Os votos continuam disponíveis em todos os totais e sob bairro nulo.

Para senador, o eleitor tem duas escolhas em 2026. O percentual é de votos nominais,
não de eleitores. Não somar aptos ou comparecimento de cargos diferentes.

## Reproduzir ou atualizar

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/eleicoes download
.venv/bin/eleicoes build
.venv/bin/eleicoes status
.venv/bin/eleicoes benchmark
.venv/bin/pytest -q
```

Para atualizar após nova publicação do TSE:

```bash
.venv/bin/eleicoes download --refresh
.venv/bin/eleicoes build
.venv/bin/eleicoes national-totals
```

O importador descobre URLs na API oficial CKAN do TSE, baixa ZIPs em streaming e registra
URL, ID do recurso, cabeçalhos HTTP, horário UTC, tamanho e SHA-256 em `data/raw/*/source.json`.
Downloads sem `--refresh` preservam os arquivos existentes. CSVs TSE são convertidos de Latin-1
para UTF-8 em blocos; o cálculo usa SQL nativo, sem carregar o CSV inteiro em Python.
Os ZIPs nacionais de presidente e outras bases são preservados como fontes; as tabelas finais
de votos e locais contêm somente SP. Candidaturas incluem SP e as presidenciais nacionais.
Campos como CPF e título de candidato não são importados para o banco analítico.

Uma carga constrói outro arquivo DuckDB e só troca o snapshot atendido após as validações.
Uma falha de chave, conservação de votos ou conferência com a apuração impede a publicação.
Reserve espaço para CSVs de staging, banco temporário e spill em disco além dos ZIPs.
O servidor escuta apenas em `127.0.0.1`; não há autenticação nem configuração de hospedagem pública.

## Stack e desempenho

DuckDB + SQL para cálculo colunar; Python para importação; FastAPI para a API de leitura;
Parquet para portabilidade. Go pode ser adotado na camada HTTP se a concorrência justificar.
Nesta escala, as primeiras medições já justificam começar com um único motor analítico.
Referências e comparação com ClickHouse, PostgreSQL/PostGIS, Go e Rust em
[docs/arquitetura.md](docs/arquitetura.md).

Agregações e posições por município, bairro, local e seção são calculadas durante a carga.
Filtros compatíveis leem essas tabelas; recortes adicionais recalculam a partir dos fatos
ou dos locais para manter o denominador correto. API limitada a duas consultas simultâneas;
consultas excedentes recebem HTTP 429 para evitar esgotar a memória.

Medição local inicial, três repetições por consulta, até 100 linhas e cache do sistema:

| Consulta | Mediana |
|---|---:|
| Candidato por bairro, todo o estado | 37 ms |
| Candidato por local, capital | 35 ms |
| Candidato por seção, capital | 46 ms |
| Ranking por município, todo o estado | 51 ms |

São exemplos medidos, não garantia para qualquer combinação de filtros, disco frio ou grande
concorrência. [reports/benchmark.json](reports/benchmark.json) contém as medições reproduzíveis.

## Próximas extensões

Comparação explícita entre turnos, normalização revisável de nomes de bairros,
ampliação de limites oficiais municipais, polígonos de distritos e contexto IBGE.
Não inferir o voto individual ou de grupos demográficos a partir dos totais das seções.

Dados públicos do [TSE — resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026),
[eleitorado 2026](https://dadosabertos.tse.jus.br/dataset/eleitorado-2026) e
[candidatos 2026](https://dadosabertos.tse.jus.br/dataset/candidatos-2026).

Publicação: [guia de operação e isolamento](docs/publicacao.md). Front via GitHub Pages;
backend local em containers com ngrok, sem portas públicas no computador.
