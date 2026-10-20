# Contexto do projeto

Leia `/home/vini/.agents/INSTRUCTIONS.md` e as decisões em `docs/arquitetura.md`.

Escopo autorizado e confirmado em 20/10/2026: eleições de **2026 somente**, votos registrados
em **São Paulo**, todos os municípios do estado. Não trocar por 2022 ou 2024 para preencher lacunas.
A solicitação posterior autorizou totais nacionais agregados para os denominadores do hover;
a visualização geográfica e os fatos por seção continuam restritos a SP.

Implementado: download TSE com proveniência, importação e relacionamentos DuckDB, auditoria
de conservação e totalização por seção, relatórios materializados, API FastAPI e CSV.
Estado da primeira carga: primeiro turno; 17.891.697 registros, 103.656 seções, 645 municípios;
99,57% dos votos com bairro associado com endereço compatível. Consulte os relatórios para
atualizações, não trate esses números como estado permanente.

Bairro é o do local de votação. Nunca afirmar que é o de residência dos eleitores.
Preservar votos sem bairro e conflitos; nunca resolver endereço divergente por suposição.
Percentuais e posição devem considerar todos os candidatos do mesmo território/cargo/turno,
antes de aplicar o filtro de candidato ou partido. Senador 2026 tem duas escolhas por eleitor.

Comandos: `.venv/bin/eleicoes download`, `build`, `status`, `benchmark`, `serve`.
API local: `http://127.0.0.1:8026/docs`. Testes: `.venv/bin/pytest -q`.
Dados e ambiente virtual ficam fora do Git; não importar CPF ou título para o banco analítico.
Nunca publicar diretamente em banco atendido: criar e auditar outro snapshot e trocar o arquivo.

Front implementado em `frontend/`: Angular 22, Leaflet e canvas, templates HTML separados,
signals e Signal Forms. Componentes → serviço Election → repositório HTTP.
Atlas local em `http://127.0.0.1:8026/atlas/`, servido pela própria API após o build.
Build obrigatório: `npm run build -- --base-href /atlas/` dentro de frontend.
Node funcional instalado em `/home/vini/.nvm/versions/node/v24.16.0/bin`; npm do sistema
estava quebrado em 20/10/2026. Não alterar instalação global para resolver o projeto.

Mapa: 11 regiões intermediárias e 53 imediatas IBGE; não chamar essa divisão de regiões
administrativas estaduais ou zonas TRE. Malhas e catálogo em `data/geo`, regenerados por
`eleicoes geography`. 481 bairros oficiais compatíveis e 6.380 áreas aproximadas; usuário
autorizou aproximações identificadas em 20/10/2026. Leia `docs/mapa.md`.
Não inferir residência a partir de local de votação. Após correção explícita do usuário,
blocos agora têm área proporcional ao número absoluto de votos, com escala única por vista.
Não voltar a preencher o bairro conforme seu tamanho geográfico. Manter candidatos agrupados.
Os contornos são referência; blocos deslocados têm linhas até a âncora. Não inferir localização
dos votos individuais dentro do bairro. A escala corrente de votos por quadrícula aparece na tela.
Hover: cinco candidatos mais votados no bairro, votos e percentual sobre o total nacional de
cada candidatura no mesmo turno. Esse percentual NÃO usa o total de votos do bairro ou de SP
como denominador para presidente. Referência nacional em candidate_totals.parquet, preparada
por `eleicoes national-totals` após atualizar a base. Para cargos estaduais, o total da
candidatura no país corresponde à sua votação em SP. Leia `docs/mapa.md`.
Não renormalizar percentuais ao escolher candidatos: manter "Outros" no denominador.
Correção posterior do usuário: no DESENHO, filtrar candidatos deve ocultar todos os demais,
inclusive a categoria "Outros". Redimensionar símbolos pela soma dos votos selecionados sem
alterar a escala original por voto. Legenda e total do painel mostram só os candidatos filtrados.
Percentuais de origem e ranking nacional do hover não são renormalizados. Sem filtro,
continuar mostrando os seis mais votados + "Outros". Cidades e bairros usam círculos com fatias
proporcionais em área, inclusive após o zoom automático do filtro de cidade. Não aplicar faixas retas recortadas num
círculo, porque isso distorce a área por candidato.
Comparação explícita entre turnos continua como extensão futura.

Correção posterior do usuário: o hover respeita o filtro de candidatos e lista até cinco
selecionados em ordem de votos locais, inclusive candidatos fora do top cinco geral.
Sem filtro, manter top cinco geral; denominadores nacionais continuam inalterados.

Hover de votos somente sobre as pizzas; não associar tooltip aos polígonos geográficos.

Nomes de cidades/bairros são rótulos permanentes no mapa, com controle de colisões.
A tabela de pizzas fica separada no fim da página; acompanha as pizzas realmente desenhadas
na vista atual. Ao expandir, consultar todos os candidatos com votos no local sob demanda,
apenas os selecionados quando houver filtro de candidatos. Percentual nos detalhes da tabela é nominal local,
explicitamente identificado; hover continua nacional. Não limitar detalhes a cinco candidatos.

Correção: detalhes da tabela respeitam candidatos selecionados; sem seleção exibem todos
com votos. Não limitar a cinco nem recalcular o denominador percentual ao filtrar.

Estilo adicional autorizado: vencedor presidencial por cidade/bairro. Preencher polígonos
pela cor do vencedor real, margem em pontos percentuais sobre votos válidos locais.
Não substituir a visão de pizzas: ela continua proporcional aos votos. Só presidente oferece
o estilo de vencedor; empates neutros. Filtro de candidatos é limpo ao entrar nessa visão.

Publicação autorizada em 20/10/2026: frontend no GitHub Pages em
ViniciusGabrielOliveira/eleicoes-sp; backend nesta máquina via ngrok, isolado em Docker.
Leia docs/publicacao.md. Não expor a API de desenvolvimento, abrir portas, montar pasta
pessoal/socket Docker ou incluir credenciais/dados brutos no Git. Runtime é ignorado.
