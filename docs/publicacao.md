# Publicação do Atlas

Front: GitHub Pages, no repositório `ViniciusGabrielOliveira/eleicoes-sp`.
Backend: máquina local, API isolada em Docker e túnel HTTPS ngrok. Não há portas
publicadas por estes containers nem alteração no roteador. A API local de desenvolvimento
em 127.0.0.1:8026 é independente e não é o destino do túnel.

## Limites do isolamento

A API executa como usuário 10001, filesystem somente leitura, sem capabilities, sem
novos privilégios e com limites de CPU, memória, processos e requisições. Está somente
na rede Docker interna. A imagem contém código Python e dependências; o único volume
é uma cópia dos cinco arquivos permitidos de dados públicos, montada somente leitura.
Não montar `/home`, `.ssh`, `.aws`, o socket Docker, a raiz do projeto ou outros serviços.
Não usar `privileged`, `network_mode: host` nem mapeamento `ports`.

O proxy encaminha somente para essa API. A superfície pública limita-se a `/health`,
`/candidates` e rotas específicas do mapa. Não há upload, SQL livre, shell, download do
banco, listagem de arquivos nem endpoints de administração. CORS restringe navegadores
à origem configurada, mas NÃO autentica clientes: as consultas públicas podem ser
feitas por qualquer pessoa. Credencial secreta no front não é usada como segurança.

O agente ngrok conecta-se ao proxy na rede interna e à internet em outra rede; não recebe
pasta pessoal nem socket Docker. Seu inspetor HTTP está desligado. O token existente foi
copiado para `deploy/runtime/ngrok.env`, arquivo local 0600, ignorado pelo Git, nunca na
imagem nem no frontend. Dados pessoais de credenciais não devem aparecer em logs.

Containers compartilham o kernel do computador; isso reduz exposição, mas não garante
risco zero. O site depende de o computador e a internet permanecerem ligados. Os limites
da conta ngrok também se aplicam. A URL pública atual fica em `deploy/public-config.json`;
se mudar, atualizar esse arquivo e enviar um commit para republicar o frontend.

## Operação

- `scripts/public-api.sh status`: estado dos três containers.
- `scripts/public-api.sh stop`: interrompe o acesso público do projeto.
- `scripts/public-api.sh start`: inicia novamente, sem reconstruir dados.
- `scripts/public-api.sh logs`: logs da API/proxy, sem configuração de credenciais.

Para preparar uma nova máquina ou atualização: `python3 scripts/prepare-public-data.py`
copia somente banco auditado, referência nacional, catálogo e duas malhas. Também cria
um contexto Docker separado com apenas código e dependências. Execute antes do build.
O token ngrok deve ser configurado localmente em `deploy/runtime/ngrok.env` como
`NGROK_AUTHTOKEN=...`, com permissão 0600; nunca enviar ao GitHub. Defina
`ELEICOES_ORIGINS` com a origem HTTPS do Pages, sem caminho, antes de executar Compose.
Faça build e validação com o túnel parado antes de publicar uma atualização.

## Deploy do front

O workflow `.github/workflows/pages.yml` compila Angular com o caminho do GitHub Pages
e envia apenas `frontend/dist/frontend/browser`. O endpoint HTTPS vem da variável
opcional do repositório `API_BASE_URL`, ou de `deploy/public-config.json`.
O JSON público não contém segredos. No desenvolvimento local, `frontend/public/api-config.json`
usa a mesma origem; o workflow o substitui apenas durante o build para publicação.
Configurar Settings → Pages → Source → GitHub Actions. O workflow usa permissões de
leitura no build e somente Pages/id-token no job de deploy. Não há runner auto-hospedado.

## Verificações realizadas em 20/10/2026

- API executando sem root; dados e filesystem somente leitura; nenhuma porta publicada.
- Pasta pessoal e socket Docker ausentes no container da API.
- Saída da API para a internet bloqueada pela rede interna.
- Consultas públicas do mapa e preflight CORS funcionando por HTTPS ngrok.
- `/docs`, `/.env`, relatórios não utilizados e download do arquivo do banco retornam 404.
- Testes cobrem allowlist pública, métodos, CORS e limite de query string.
