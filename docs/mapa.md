# Atlas de pixels — 20/10/2026

## Interação

Um único cargo e turno por vez; cidades, bairros, regiões intermediárias e imediatas
aceitam seleção múltipla. Dentro de cada lista, seleções se somam; entre filtros,
aplica-se interseção. Bairros têm chave composta pelo município TSE e nome de origem.
Alterar região limpa cidades e bairros; alterar cidades limpa bairros; trocar cargo limpa
candidatos. As cores usam uma paleta contrastante, escolhendo tons perceptualmente distantes
dos demais candidatos visíveis e de Outros. PT e PL presidenciais mantêm vermelho e azul;
cores personalizadas são preservadas. Reordenar o mesmo grupo não altera as cores, mas
mudar o conjunto de candidatos pode redistribuir os tons automáticos. A legenda permite editá-los.

A visão automática passa para bairros a partir do zoom 9,5. Selecionar bairros sempre
ativa essa visão. Os filtros territoriais reenquadram o mapa; zoom e arraste permanecem
livres. É possível forçar a visão municipal ou de bairros. O mapa funciona sem serviço
de tiles externo: os limites IBGE estão salvos localmente.

O CSV contém o recorte integral recebido pelo mapa e as categorias exibidas, inclusive votos
sem área geográfica. "Outros" aparece somente sem filtro de candidatos. Não se limita aos
símbolos visíveis na tela.

## Geografia e proveniência

Fontes oficiais:

- [Localidades IBGE](https://servicodados.ibge.gov.br/api/docs/localidades): 645 municípios,
  11 regiões geográficas intermediárias e 53 imediatas nesta carga.
- [Malhas IBGE, API v3](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3): limites municipais.
- [Bairros Censo 2022 — SP](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/bairros/shp/UF/SP/):
  2.170 registros de polígonos de bairros no arquivo fonte; não é cadastro de todos os bairros TSE.
- [TRE-SP, zonas eleitorais](https://www.tre-sp.jus.br/servicos-eleitorais/consulta-a-zonas-eleitorais):
  divisão eleitoral distinta da regionalização IBGE. Não atribuir ao TRE a divisão adotada aqui.

O código municipal TSE não é o código IBGE. A ponte exige nome normalizado único;
"São Luís do Paraitinga" (TSE) foi relacionado a "São Luiz do Paraitinga" (IBGE), grafia
conferida na API baixada. Nenhuma associação por distância ou nome parecido de municípios.

Um bairro usa limite IBGE somente quando o nome normalizado é inequívoco dentro do município
e ao menos metade dos locais TSE com coordenadas válidas daquele bairro cai no polígono,
com tolerância de aproximadamente 0,0001 grau. Polígonos homônimos no cadastro IBGE são
dissolvidos. Isso produziu 481 bairros com limite oficial compatível.

Para as 6.380 áreas aproximadas, os locais com coordenadas plausíveis e dentro do município
(tolerância de 0,002 grau para validação da malha simplificada) geram células de Voronoi em
Web Mercator. Elas são recortadas pelo município, subtraindo as áreas oficiais aceitas,
e dissolvidas por bairro TSE. Coordenadas idênticas atribuídas a bairros diferentes não
geram sementes. Nomes de bairro não são fundidos por semelhança. São áreas de referência
dos locais de votação: não representam divisas oficiais, áreas de residência ou distribuição
espacial real dos votos dentro do bairro. A distorção do Web Mercator também impede interpretar
suas fronteiras como limites de distância geodésica exata.

O cadastro usado para as sementes é do primeiro turno. Para novos turnos e alterações de
local, revisar a fonte e regenerar a geografia; não assumir que áreas estimadas são históricas
ou permanentes. Os limites oficiais de bairros são do Censo 2022, não uma malha de 2026.

As áreas estimadas têm limites tracejados e essa origem aparece no tooltip e no detalhe
ao clicar. O controle "Incluir áreas aproximadas" pode ocultá-las. Áreas sem geometria
ou ocultadas não desaparecem dos totais: a interface mostra a cobertura e o número de
votos sem área exibida. Municípios têm cobertura completa; bairros não.

As entradas fonte, horários e SHA-256 são registrados em `reports/geography.json`.

## Área proporcional ao número absoluto de votos

Conforme a correção solicitada em 20/10/2026, o preenchimento dos polígonos foi substituído
por símbolos ancorados em um ponto interno de cada território. Por ajuste estético solicitado
depois, cidades e bairros usam círculos. O contorno fica como
referência: seu tamanho não determina a quantidade de cor mostrada.

Uma única escala `s` (votos por pixel quadrado de tela) é usada em todos os blocos da vista.
Para um território com `T` votos, o lado do bloco é `sqrt(T/s)`. A faixa de um candidato
com `v` votos tem largura `lado × v/T` e altura `lado`; sua área é exatamente `v/s`.
Portanto, 2.000 votos ocupam o dobro da área de 1.000 votos, mesmo em bairros geograficamente
distintos. O candidato continua agrupado em uma faixa, seguindo a ordem da legenda.
Nas cidades, o raio é `sqrt(T/(πs))` e cada candidato ocupa uma fatia de ângulo `2π × v/T`.
A área da fatia também é `v/s`: o formato redondo preserva a comparação com os bairros.
Não há arredondamento para um número inteiro de células nem tamanho mínimo que infle
territórios com poucos votos: as faixas e quadrículas podem ser parciais.

A escala cresce com o zoom de forma uniforme para todos os blocos. Se o maior bloco
ultrapassaria 38% da menor dimensão da tela, a escala comum é ajustada para cabê-lo.
A unidade corrente é indicada em "1 quadrícula ≈ N votos". Comparar votos entre territórios
na mesma vista/escala; ao mudar zoom, a equivalência muda. O controle de quadrícula muda
a grade visual, não normaliza votos individualmente por bairro.

Blocos próximos são deslocados para evitar sobreposição, preservando seus tamanhos.
Linhas ligam blocos deslocados ao seu ponto de origem. Se a tela não comportar todos,
o algoritmo preserva área e origem, podendo haver sobreposição residual; aproximar ou
reduzir o recorte permite separar os blocos. Blocos de âncoras fora da tela são omitidos
do desenho, mas permanecem nos totais do recorte. A cobertura exibida refere-se à disponibilidade
de área geográfica, não à contagem de símbolos atualmente dentro da janela.

Sem seleção, os seis candidatos mais votados no recorte são representados e os demais
ficam em "Outros". Com filtro, apenas os candidatos escolhidos são desenhados; "Outros"
é removido do símbolo e da legenda. O total do painel e a cobertura consideram os votos
selecionados. O tamanho do símbolo usa a soma desses votos, preservando a área por voto
e a escala de referência original, sem inflar os candidatos escolhidos. Os percentuais da
legenda principal continuam relativos a todos os votos nominais do cargo no recorte;
o hover mostra os cinco mais votados entre os selecionados e mantém os denominadores nacionais.
As cores não indicam localização dos votos dentro do bairro nem residência de eleitores.

## Hover: cinco mais votados e participação nacional

O hover do bairro ou do bloco lista os cinco candidatos mais votados naquele território,
considerando apenas os candidatos selecionados quando há filtro de candidatura. Sem esse filtro,
considera todos os candidatos; com menos de cinco selecionados, mostra somente esses candidatos. Empates
são desfeitos pelo ID da candidatura; no máximo cinco linhas.

Cada linha mostra `nome — votos locais — percentual do total nacional do candidato`.
A fórmula é `100 × votos do candidato no território / total nacional da mesma candidatura,
eleição, cargo e turno`. O denominador não muda com cidades, bairros, regiões ou candidatos
selecionados. São até seis casas decimais para não mostrar contribuições pequenas como 0%.

A referência está em `data/warehouse/candidate_totals.parquet`, gerada por
`.venv/bin/eleicoes national-totals`. Para presidente, soma o arquivo por seção BR integral,
incluindo exterior quando aplicável. Para governador, senador e deputados de SP, o total
da candidatura no país corresponde ao total de seus votos em SP. Nunca somar candidaturas
de mesmo nome ou mesmo número em UFs diferentes.

Os denominadores usam a mesma geração dos votos por seção do mapa. O arquivo posterior
de votação nominal por município/zona também foi baixado e comparado: omite 29 candidaturas
presentes na versão das seções (1 presidente, 1 governador, 2 senadores, 21 deputados federais,
4 estaduais), enquanto os totais dos candidatos presentes coincidem. Para evitar misturar
versões, a referência das seções foi mantida para todos. Não atribuir a omissão a uma causa
judicial sem verificação. Proveniência e conferência em `reports/national_totals.json`.
Atualizar os denominadores após cada nova carga de seções; a publicação da referência
é interrompida se faltar candidato ou se os totais de SP não coincidirem com o snapshot.

## Implementação e validação

Angular 22 e Leaflet; uma camada canvas para os blocos e um alvo SVG por bloco visível
para hover e clique, sem criar um elemento DOM por pixel. Mudanças rápidas de filtro são agrupadas por 150 ms, consultas antigas
são canceladas no cliente e HTTP 429 recebe tentativas com espera curta. A API usa as
tabelas analíticas já auditadas, agrega sem truncar territórios e comprime o JSON.

Testes: `npm test -- --watch=false` no frontend; `.venv/bin/pytest -q` na raiz;
`npx playwright test` com a API local em execução. Quando necessário, informar o caminho
do navegador instalado em `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Capturas e análise automatizada
de acessibilidade ficam em `reports/`. Não há hospedagem externa configurada.

Cidades e bairros usam símbolos circulares, inclusive quando o filtro de cidade aproxima
o mapa e o detalhamento automático passa a bairros. A área de cada fatia permanece proporcional
aos votos, com escala comum na vista.

O tooltip de votos aparece somente sobre as pizzas, nunca sobre os polígonos
de bairros ou cidades. Os contornos permanecem como referência geográfica.

## Nomes no mapa e tabela ao fim da página

Os nomes são desenhados diretamente no mapa, com halo claro e redução de sobreposições;
no detalhamento municipal aparecem cidades, no detalhamento de bairros aparecem bairros.
Não dependem do hover. Em vistas densas, alguns rótulos são omitidos para manter a leitura.

A tabela separada abaixo do explorador acompanha exatamente as pizzas desenhadas, inclusive
zoom, navegação e filtro de candidatos. Mostra votos da pizza e total nominal do local.
Expandir uma linha consulta `/map/area-candidates` sob demanda e mostra todos os candidatos
com votos, em ordem decrescente, aplicando o filtro de candidatos do mapa quando houver seleção. Os percentuais
da tabela detalhada usam o total nominal local, explicitado na interface; o hover mantém
seu denominador nacional. Filtros de bairros são preservados ao agregar uma pizza municipal.

Correção: detalhes da tabela respeitam candidatos selecionados; sem seleção exibem todos
com votos. Não limitar a cinco nem recalcular o denominador percentual ao filtrar.

## Visão do vencedor presidencial

O seletor de estilo permite trocar pizzas por territórios preenchidos, somente para presidente.
O detalhamento municipal/bairro continua independente. A cor representa o candidato mais votado
no território, considerando todas as candidaturas; a margem é
`100 × (votos do primeiro − votos do segundo) / votos nominais locais`, em pontos percentuais.
Empates recebem cinza e rótulo de empate. Não calcular a vantagem sobre o total nacional nem
sobre apenas as duas candidaturas. A área geográfica nesta visão não representa votos.
Ao entrar, limpar a seleção de candidatos; nesta visão não há filtro de candidatos que possa
substituir o vencedor real. Ao mudar para outro cargo, retornar ao estilo de pizzas.
A tabela inferior acompanha os territórios visíveis e mantém seus detalhes completos.
