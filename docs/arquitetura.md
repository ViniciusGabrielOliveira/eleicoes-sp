# Eleições SP — decisões de 20/10/2026

Escopo confirmado pelo usuário: somente 2026; votos registrados no estado de São Paulo.
Não incluir outros estados nem resultados de 2022/2024. Arquivos nacionais são necessários
quando o TSE não oferece um recorte estadual, mas as tabelas analíticas devem reter somente SP.

## Stack e motivo

- DuckDB 1.5.6: armazenamento colunar, SQL vetorizado e processamento com spill para disco.
- Python: coordena downloads e transformações; as somas, joins e filtros grandes rodam no motor nativo do DuckDB.
- FastAPI: API local de leitura, consultas parametrizadas e documentação OpenAPI.
- Parquet: exportação compactada e portável para outros motores analíticos.

Go é uma boa opção para uma API com grande concorrência, mas não substitui o motor analítico.
Adicioná-lo agora exigiria manter dois ambientes sem evidência de ganho no gargalo principal.
Rust e Polars são alternativas para transformações específicas; não são necessários para a primeira carga SQL.
PostgreSQL/PostGIS passa a ser útil para contas, permissões, anotações e polígonos de bairros.
ClickHouse passa a ser candidato quando a concorrência ou a escala ultrapassar uma máquina;
a migração deve ser decidida por benchmark de consultas e carga concorrente, não só por número de linhas.

Esta máquina tem aproximadamente 10 GiB de RAM. Limitar DuckDB a 2 GB e dois threads por
processo de importação. Publicar snapshots completos por troca atômica de arquivo: a API
abre o snapshot somente para leitura. Nunca importar diretamente no arquivo atendido pela API.

## Relacionamentos

Preservar ano, código da eleição, turno, UF, município TSE, zona, seção, cargo e número votável
na chave dos fatos. Seção e zona isoladas não são identificadores globais.
O código municipal TSE não é o código IBGE: nunca os tratar como equivalentes.

Votos por seção → local de votação → bairro/endereço, preservando os campos originais.
Usar o local explicitado no arquivo de votos quando disponível. Dimensão de locais deve ser
única antes do join: cadastros podem repetir um local por seção ou perfil e multiplicar votos.
Relacionamentos ausentes ou ambíguos devem permanecer visíveis, com medidas de cobertura.
Os arquivos de locais são atualizáveis: registrar data de extração, HTTP Last-Modified e checksum.
Um cadastro de 2026 baixado depois da votação não prova que o endereço foi o mesmo no dia
do pleito; mudança de local entre turnos exige fonte histórica correspondente.

## Filtros e relatórios

| Grupo | Filtros ou medidas | Fonte / limite |
|---|---|---|
| Eleição | Turno, cargo, código da eleição | Votação por seção |
| Candidato | Nome/número, partido, situação da candidatura/resultado | Candidaturas; usar ID da candidatura, não nome para identidade |
| Território | Município, bairro do local, zona, local, seção, endereço | Votos + cadastro de locais; bairros restritos ao município |
| Desempenho | Votos, participação nos votos nominais, posição, diferença para líder, concentração territorial | Calcular denominador antes de filtrar candidato/partido |
| Comparação | Dois candidatos no mesmo recorte; evolução entre turnos | Sem inferir transferência individual de votos |
| Participação | Aptos, comparecimento, abstenção, brancos, nulos, legenda | Detalhe da apuração; não somar aptos de cargos diferentes |
| Qualidade | Local ausente, bairro ausente, conflito de cadastro, cobertura de votos relacionados | Auditoria da importação |
| Mapa (posterior) | Coordenadas, distância e polígono de bairro/distrito | Validar coordenadas e licenças; bairro textual não é polígono oficial |
| Contexto (posterior) | Perfil agregado da seção; contexto IBGE | Nunca concluir como um grupo demográfico votou a partir da soma da seção |

Para senador em 2026 existem duas escolhas por eleitor: participação nos votos é participação
nas escolhas nominais, não percentual dos eleitores. Diferenciar votos de legenda de votos
nominais, brancos e nulos. Nunca misturar cargos/turnos em um denominador.

Primeira entrega: importação, auditoria, busca de candidatos, filtros territoriais,
ranking e relatório por município/bairro/local/seção, exportação CSV e API local.
Mapas, comparação entre turnos e análise demográfica são extensões, não presumir implementadas.

## Fontes oficiais consultadas

- https://dadosabertos.tse.jus.br/dataset/resultados-2026
- https://dadosabertos.tse.jus.br/dataset/eleitorado-2026
- https://dadosabertos.tse.jus.br/dataset/candidatos-2026
- https://duckdb.org/docs/current/data/parquet/overview
- https://www.duckdb.org/docs/preview/connect/concurrency
- https://www.duckdb.org/docs/preview/guides/performance/how_to_tune_workloads
- https://go.dev/doc/effective_go
- https://clickhouse.com/resources/engineering/when-to-use-columnar-database

Observação do portal TSE em 20/10/2026: há aviso de 39 registros de aptos duplicados
no processo nacional de transferência temporária. Não aplicar uma subtração arbitrária em SP;
preservar os totais de origem e identificar o escopo exato antes de qualquer correção.
