# Instalação e Configuração

Guia completo para preparar o ambiente de desenvolvimento do 4SEO, com a referência detalhada de cada variável de ambiente utilizada pela aplicação.

## Referência completa das variáveis de ambiente

O backend carrega as variáveis de `backend/.env` via `python-dotenv` (`load_dotenv()` em `app/main.py:14`, `app/auth.py:13`, `app/supabase_client.py:19`, `app/integrations/gsc.py:24`). O frontend carrega de `.env` na **raiz do projeto** (padrão do Vite): apenas variáveis com prefixo `VITE_` são expostas ao navegador, e elas são **embutidas no bundle em tempo de build** — nunca coloque segredos de servidor ali.

### A.1 - Backend (`backend/.env`)

| Variável | Onde é lida (arquivo:linha) | Valor padrão no código | Obrigatória? | O que acontece se faltar |
|---|---|---|---|---|
| `SUPABASE_URL` | `backend/app/supabase_client.py:21`; `backend/app/auth.py:16`; `backend/app/integrations/gsc.py:31` | Sim em `supabase_client.py` (URL de um projeto Supabase embutida no código); `""` em `auth.py` e `gsc.py` | **Sim** | O cliente de dados aponta para o projeto embutido no código em vez do seu. Em `auth.py`, sem URL o `PyJWKClient` não é instanciado (`auth.py:20-21`) e tokens ES256 — o padrão do Supabase Auth atual — não podem ser validados: toda rota autenticada responde `401`. O armazenamento de tokens do GSC (`gsc.py:96`) monta uma URL inválida. |
| `SUPABASE_SERVICE_KEY` | `backend/app/supabase_client.py:23` (1ª opção de `SUPABASE_KEY`); `backend/app/integrations/gsc.py:32` | Não em `supabase_client.py`; `""` em `gsc.py` | **Sim** | Chave `service_role`, ignora RLS. Sem ela, `SUPABASE_KEY` cai para `SUPABASE_ANON_KEY`; se as duas faltarem, o header `apikey` fica `None` e toda chamada do cliente service-role (`get_supabase()`, usado em `app/services.py:27,66,215,285`) falha. Sem ela, o GSC não consegue gravar/ler tokens (`gsc.py:88-89`). |
| `SUPABASE_ANON_KEY` | `backend/app/supabase_client.py:23` (fallback de `SUPABASE_KEY`); `backend/app/supabase_client.py:27` (1ª opção de `SUPABASE_ANON_KEY`) | Não | **Sim** | É a chave usada como `apikey` em todas as chamadas com RLS do usuário: `get_supabase_for_user()` (`supabase_client.py:609`), invocada 38 vezes em `app/main.py`. Vazia, o Supabase responde `401 No API key found` em praticamente todos os endpoints autenticados. |
| `SUPABASE_KEY` | `backend/app/supabase_client.py:27` (último fallback de `SUPABASE_ANON_KEY`) | `""` | Não (legado) | Nome alternativo aceito só como fallback da anon key. Se você já definiu `SUPABASE_ANON_KEY`, esta variável não tem efeito. **Não confundir com `SUPABASE_SERVICE_KEY`.** |
| `SUPABASE_JWT_SECRET` | `backend/app/auth.py:15` | `""` | Condicional | Usada apenas no ramo HS256 de `_decode_token()` (`auth.py:41-46`). Projetos Supabase que assinam com ES256 usam o JWKS e não dependem dela. Se o seu projeto emitir tokens HS256 e o segredo faltar, a validação falha com `401 Token inválido`. |
| `OPENAI_API_KEY` | `backend/app/llm_optimizer.py:14`; otimizadores de plataforma | Não (fica `None`) | **Sim**, para a geração de propostas | Sem ela, os otimizadores retornam lista vazia de propostas. |
| `AI_MODEL` | `backend/app/ai_config.py:23`; `backend/app/main.py:192` (só para exibição em `/api/info`) | `"gpt-5-mini"` | Não | Usa `gpt-5-mini`. `ai_config.completion_params()` detecta automaticamente família de raciocínio (gpt-5/o1/o3/o4) e troca `max_tokens` por `max_completion_tokens`. |
| `AI_REASONING_EFFORT` | `backend/app/ai_config.py:27` | `"minimal"` | Não | Usa `minimal` (mais rápido/barato). Só se aplica a modelos de raciocínio. |
| `VISION_MODEL` | `backend/app/integrations/shopify_optimizer.py:32` | `"gpt-4o"` | Não | Usa `gpt-4o` na análise de imagens para geração de texto alternativo (`shopify_optimizer.py:766`). |
| `CORS_ORIGINS` | `backend/app/main.py:49` | `""` | Não | Lista separada por vírgula, somada às origens fixas de `main.py:43-48` (`https://4seo.app`, `https://www.4seo.app`, `http://localhost:5173`, `http://localhost:3000`). **Atenção:** `http://localhost:8080` — a porta do Vite neste projeto — **não** está na lista fixa; só é necessário adicioná-la se o frontend chamar o backend direto, sem o proxy do Vite. |
| `MAX_PAGES_PER_SCAN` | `backend/app/main.py:52` | `"20"` | Não | Limite padrão de páginas por varredura = 20 (`main.py:1012`). Valor não numérico quebra o import do módulo (`int()`). |
| `FRONTEND_URL` | `backend/app/main.py:1475` (redirect após callback do GSC); `backend/app/main.py:2695` (redirect após OAuth Nuvemshop) | `"http://localhost:5173"` na linha 1475 e `"http://localhost:8080"` na linha 2695 | Não, mas **recomendada em dev** | Os dois padrões divergem. Como o Vite roda em **8080**, sem definir a variável o retorno do OAuth do GSC redireciona para `http://localhost:5173/integracoes?gsc=connected`, que não existe. Defina `FRONTEND_URL=http://localhost:8080`. |
| `BACKEND_URL` | `backend/app/main.py:2660` | `"http://localhost:8000"` | Não em dev | Monta o `redirect_uri` do OAuth Nuvemshop (`{BACKEND_URL}/api/nuvemshop/oauth-redirect`). O padrão já é correto em ambiente local; em produção é obrigatório (a Nuvemshop só aceita HTTPS ou localhost). |
| `GSC_CLIENT_ID` | `backend/app/integrations/gsc.py:26` | `""` | Não (só p/ Google Search Console) | `GET /api/gsc/auth-url` responde `400 "GSC not configured. Set GSC_CLIENT_ID in .env"` (`main.py:1448-1449`). O resto da aplicação funciona normalmente. |
| `GSC_CLIENT_SECRET` | `backend/app/integrations/gsc.py:27` | `""` | Não (só p/ GSC) | A troca do código de autorização por tokens falha (`gsc.py:50-65`). |
| `GSC_REDIRECT_URI` | `backend/app/integrations/gsc.py:28` | `"http://localhost:8000/api/gsc/callback"` | Não em dev | O padrão já corresponde à rota real (`main.py:1454`). Precisa ser idêntico ao URI cadastrado no Google Cloud Console. |
| `SEARCHAPI_KEY` | `backend/app/integrations/searchapi_client.py:14` | `""` | Não | Sem ela, `POST /api/termos/trends` retorna payload com `error: "SEARCHAPI_KEY não configurada no servidor"` (`searchapi_client.py:133-137`) e o enriquecimento com dados de SERP é silenciosamente pulado (`app/data_enrichment.py:38-39`; `searchapi_client.py:203-205`). As propostas continuam sendo geradas, apenas sem contexto competitivo. |
| `NUVEMSHOP_APP_ID` | `backend/app/integrations/nuvemshop.py:23` | Sim — ID embutido no código | Não, mas **recomendada** | Usa o ID de aplicação embutido. Para operar com a sua própria aplicação Nuvemshop, defina o ID dela. |
| `NUVEMSHOP_CLIENT_SECRET` | `backend/app/integrations/nuvemshop.py:24` | Sim — valor embutido no código | Não, mas **fortemente recomendada** | Usa o segredo embutido no código. Deve ser sobrescrito pelo segredo da sua própria aplicação Nuvemshop, mantido apenas em variável de ambiente. |
| `SHOPIFY_API_KEY` | `backend/app/integrations/shopify.py` | `""` | **Sim**, para OAuth Shopify | Client ID do app 4SEO no Shopify Partners. Sem ela, `POST /api/shopify/auth` responde erro de configuração. |
| `SHOPIFY_API_SECRET` | `backend/app/integrations/shopify.py` | `""` | **Sim**, para OAuth Shopify | Client secret do app. Usado na troca do code e na validação HMAC do callback `{BACKEND_URL}/api/shopify/oauth-redirect`. |
| `LOJAINTEGRADA_APP_KEY` | `backend/app/integrations/lojaintegrada.py` | `""` | **Sim**, para a integração Loja Integrada | Chave da aplicação integradora (não a chave da loja). Ausente, `POST /api/lojaintegrada/connect` responde `503`. |

**Credenciais que NÃO são variáveis de ambiente:** VTEX (`account_name` + `app_key` + `app_token`) e a **Chave de API da loja** na Loja Integrada são fornecidas pelo usuário na interface e persistidas por conta no banco. Shopify via OAuth obtém o token automaticamente; o fluxo legado com `shpat_` manual ainda existe como fallback na UI.

### A.2 - Frontend (`.env` na raiz do projeto)

| Variável | Onde é lida (arquivo:linha) | Valor padrão no código | Obrigatória? | O que acontece se faltar |
|---|---|---|---|---|
| `VITE_SUPABASE_URL` | `src/lib/supabase.ts:4` | Sim — URL de um projeto Supabase embutida como fallback (`supabase.ts:5`) | **Sim** | O app autentica contra o projeto Supabase embutido no código, e não contra o seu — o login funcionaria, mas os tokens não seriam aceitos pelo backend configurado com outro `SUPABASE_URL`. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `src/lib/supabase.ts:7` | Sim — chave anon embutida como fallback (`supabase.ts:8`) | **Sim** | **Este é o nome exato da variável — não existe `VITE_SUPABASE_ANON_KEY` no código.** Recebe a chave `anon` / `publishable` do seu projeto. Sem ela, vale o fallback embutido, com o mesmo problema acima. |
| `VITE_API_BASE_URL` | `src/lib/apiClient.ts:14` | `"/api"` | Não | Usa o caminho relativo `/api`, que em desenvolvimento é redirecionado pelo proxy do Vite para `http://localhost:8000` (`vite.config.ts:13-18`). É o comportamento desejado em dev. Só defina se for chamar o backend direto (nesse caso, veja a nota de CORS abaixo). |
| `VITE_AUTH_REDIRECT_URL` | `src/contexts/AuthContext.tsx:22` | Não; há fallback em código para `` `${window.location.origin}/login` `` (`AuthContext.tsx:26`) | Não | Os e-mails do Supabase (confirmação de cadastro e redefinição de senha) redirecionam para a origem atual + `/login`. Em desenvolvimento local isso já resolve; defina apenas se precisar forçar outra URL. |
| `VITE_SUPABASE_PROJECT_ID` | *(nenhum arquivo)* | — | **Não — sem efeito** | Aparece em arquivos `.env` por herança, mas **não é lida em nenhum ponto de `src/`**. Pode ser omitida com segurança. |

---

## Passo a passo de instalação

### B.1 Pré-requisitos

| Item | Versão mínima | Como foi determinada |
|---|---|---|
| **Node.js** | 18.x ou superior (recomendado 20 LTS+) | `package.json` não declara o campo `engines`; a exigência vem do Vite 5.4 (`^18.0.0 \|\| >=20.0.0`). Validado nesta base com Node 24.14.1 / npm 11.11.0. |
| **npm** | 9+ | Acompanha o Node. O repositório versiona `package-lock.json` (lockfile v3). |
| **Python** | 3.11 | `backend/runtime.txt` → `python-3.11.0`; `backend/render.yaml` → `PYTHON_VERSION: 3.11`. |
| **Conta Supabase** | — | Banco de dados, autenticação e RLS. Ver seção B.2. |
| **Chave da API OpenAI** | — | Necessária para gerar as propostas de otimização. |

Pilha instalada pelo `backend/requirements.txt` (versões fixas): FastAPI 0.115.6, Uvicorn 0.30.6, httpx 0.27.2, Pydantic 2.10.3, openai 1.58.1, PyJWT 2.9.0, beautifulsoup4 4.12.3, lxml 5.3.0, google-api-python-client 2.149.0, google-auth-oauthlib 1.2.1, python-dotenv 1.0.1, mais pytest 8.2+ e pytest-asyncio 1.3+ para testes.

Pilha do frontend: React 18.3, Vite 5.4, TypeScript 5.8, Tailwind CSS 3.4, Vitest 3.2, `@supabase/supabase-js` 2.90, TanStack Query 5.83, React Router 6.30, Radix UI e Recharts.

### B.2 Pré-requisito de banco de dados (Supabase)

O projeto não sobe banco local: ele fala com a API REST do Supabase. Antes de rodar a aplicação:

1. Crie um projeto em [supabase.com](https://supabase.com) (região mais próxima do público-alvo; guarde a senha do banco).
2. Aplique o schema: no painel do projeto, abra **SQL Editor**, cole o conteúdo **completo** de `supabase/schema.sql` e clique em **Run**.
   - O arquivo cria as 10 tabelas do produto — `sites`, `pages`, `seo_tasks`, `scan_runs`, `user_integrations`, `oauth_states`, `user_search_terms`, `term_snapshots`, `daily_snapshots`, `gsc_tokens` — habilita **Row Level Security** em todas e cria as políticas de isolamento por usuário (`auth.uid() = user_id`).
   - O script **não é idempotente** (usa `create table` sem `if not exists`): execute uma única vez, em um projeto vazio. A tabela `auth.users` é gerenciada pelo próprio Supabase Auth e não é criada pelo script.
3. Colete as credenciais em **Project Settings → API** (em projetos mais recentes, **Project Settings → API Keys**):
   - **Project URL** → `SUPABASE_URL` (backend) e `VITE_SUPABASE_URL` (frontend);
   - chave **`anon` / `public` / `publishable`** → `SUPABASE_ANON_KEY` (backend) e `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend);
   - chave **`service_role` / `secret`** → `SUPABASE_SERVICE_KEY` (**apenas no backend** — ela ignora as políticas de RLS e nunca deve ir para o frontend nem para o repositório);
   - **JWT Secret**, em **Project Settings → API → JWT Settings** (ou **Project Settings → JWT Keys**) → `SUPABASE_JWT_SECRET`. Necessário apenas se o projeto emitir tokens HS256; projetos que assinam com ES256 são validados automaticamente via JWKS.
4. Em **Authentication → URL Configuration**, defina a **Site URL** como `http://localhost:8080` para que os links de confirmação de cadastro e de redefinição de senha voltem para o ambiente local.

### B.3 Arquivos de ambiente

São **dois** arquivos `.env`, ambos ignorados pelo Git (`.gitignore`: `.env`, `.env.*`). O projeto traz modelos comentados — copie-os e preencha:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

No Windows (PowerShell), use `Copy-Item .env.example .env` e `Copy-Item backend\.env.example backend\.env`.

O conteúdo mínimo de cada um:

**Arquivo 1 — `.env` na raiz do projeto (frontend):**

```dotenv
VITE_SUPABASE_URL=https://SEU-PROJETO.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<sua-chave-anon-publishable>
# Deixe VITE_API_BASE_URL comentado em desenvolvimento: o proxy do Vite
# encaminha /api para http://localhost:8000 automaticamente.
# VITE_API_BASE_URL=/api
```

**Arquivo 2 — `backend/.env` (backend):**

```dotenv
# --- Supabase (obrigatório) ---
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=<sua-chave-anon-publishable>
SUPABASE_SERVICE_KEY=<sua-chave-service-role>
SUPABASE_JWT_SECRET=<seu-jwt-secret>

# --- IA (obrigatório para gerar propostas) ---
OPENAI_API_KEY=<sua-chave-openai>
# AI_MODEL=gpt-5-mini
# AI_REASONING_EFFORT=minimal

# --- URLs locais ---
FRONTEND_URL=http://localhost:8080
BACKEND_URL=http://localhost:8000
# CORS_ORIGINS=http://localhost:8080

# --- Varredura ---
# MAX_PAGES_PER_SCAN=20

# --- Google Search Console (opcional) ---
# GSC_CLIENT_ID=<client-id-do-google-cloud>
# GSC_CLIENT_SECRET=<client-secret-do-google-cloud>
# GSC_REDIRECT_URI=http://localhost:8000/api/gsc/callback

# --- Dados de SERP / Tendências (opcional) ---
# SEARCHAPI_KEY=<sua-chave-searchapi-io>

# --- Integrações de e-commerce (por integração) ---
# NUVEMSHOP_APP_ID=<id-da-sua-aplicacao-nuvemshop>
# NUVEMSHOP_CLIENT_SECRET=<segredo-da-sua-aplicacao-nuvemshop>
# SHOPIFY_API_KEY=<client-id-do-app-partners>
# SHOPIFY_API_SECRET=<client-secret-do-app-partners>
# LOJAINTEGRADA_APP_KEY=<chave-da-aplicacao-integradora>
```

As credenciais de VTEX e a chave de API da **loja** na Loja Integrada **não** vão no `.env` (só a chave da **aplicação** `LOJAINTEGRADA_APP_KEY`). O lojista informa a chave da loja na tela de Integrações. Shopify OAuth usa `SHOPIFY_API_KEY`/`SHOPIFY_API_SECRET` no servidor.

### B.4 Instalação e execução — Windows (PowerShell)

Execute a partir da pasta raiz do projeto, já descompactado.

**1. Dependências do frontend**

```powershell
npm install
```

**2. Ambiente virtual e dependências do backend**

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Se o PowerShell bloquear a ativação do ambiente virtual, libere a execução apenas para a sessão atual e repita o comando de ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**3. Criar os dois arquivos `.env`** conforme a seção B.3.

**4. Subir o backend** (deixe este terminal aberto):

```powershell
cd backend
..\backend\.venv\Scripts\Activate.ps1   # se abriu um terminal novo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

O comando precisa ser executado **de dentro de `backend/`**, pois o módulo é `app.main`. Verifique em `http://localhost:8000/api/health` — deve responder `{"status":"ok","mode":"supabase",...}`. A documentação interativa da API fica em `http://localhost:8000/docs`.

**5. Subir o frontend** (em um **segundo** terminal, na raiz do projeto):

```powershell
npm run dev
```

**6. Abrir a aplicação:** `http://localhost:8080`

### B.5 Instalação e execução — macOS / Linux

```bash
# 1. Dependências do frontend
npm install

# 2. Ambiente virtual e dependências do backend
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# 3. Criar os dois arquivos .env (seção B.3)

# 4. Backend — terminal 1
cd backend
source .venv/bin/activate      # se abriu um terminal novo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 5. Frontend — terminal 2, na raiz do projeto
npm run dev
```

Abra `http://localhost:8080`.

### B.6 Portas e comunicação entre frontend e backend

| Serviço | Porta | Origem da configuração |
|---|---|---|
| Frontend (Vite dev server) | **8080** | `vite.config.ts:9` (`server.port: 8080`, `host: "::"`) |
| Backend (FastAPI/Uvicorn) | **8000** | Alvo do proxy em `vite.config.ts:15`; padrão de `BACKEND_URL` e `GSC_REDIRECT_URI` |
| Preview do build de produção | 4173 | Padrão do `vite preview` |

O `vite.config.ts` declara um proxy: toda requisição a `/api` é encaminhada para `http://localhost:8000` com `changeOrigin: true` e **sem reescrita de caminho**. Como `src/lib/apiClient.ts:14` usa `API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"` e as rotas do backend já são prefixadas com `/api` (ex.: `/api/health`, `/api/sites`), os caminhos batem exatamente. Por isso, **em desenvolvimento não defina `VITE_API_BASE_URL`**: como o navegador chama a mesma origem, não há requisição cross-origin e o CORS não entra em jogo.

Se preferir apontar o frontend direto para o backend (`VITE_API_BASE_URL=http://localhost:8000/api`), aí passa a existir requisição cross-origin de `http://localhost:8080` — que **não** consta na lista fixa de origens permitidas (`backend/app/main.py:43-48`). Nesse caso é obrigatório definir no `backend/.env`:

```dotenv
CORS_ORIGINS=http://localhost:8080
```

### B.7 Rodando os testes

**Frontend (Vitest + Testing Library, ambiente jsdom):** na raiz do projeto.

```bash
npm test          # execução única (vitest run)
npm run test:watch # modo observador
```

A configuração está em `vitest.config.ts` (inclui `src/**/*.{test,spec}.{ts,tsx}`, setup em `src/test/setup.ts`). Suíte atual: 11 arquivos, 81 testes. Não requer `.env` nem backend no ar.

**Backend (pytest + pytest-asyncio):** de dentro de `backend/`, com o ambiente virtual ativo.

```bash
cd backend
pytest                                  # suíte completa (160 testes)
pytest tests/test_seo_analysis.py       # um arquivo
pytest -k rollback                      # filtro por nome
```

A configuração está em `backend/pytest.ini` (`testpaths = tests`, `asyncio_mode = auto`). Os testes usam mocks das APIs externas — não exigem chave da OpenAI nem acesso ao Supabase —, mas precisam ser executados a partir de `backend/` para que o pacote `app` seja resolvido.

**Análise estática do frontend:**

```bash
npm run lint      # ESLint 9 (flat config em eslint.config.js)
```

### B.8 Build de produção

```bash
npm run build       # gera dist/ (bundle otimizado)
npm run build:dev   # build com modo development (sourcemaps, sem minificação agressiva)
npm run preview     # serve dist/ localmente para conferência
```

O backend não tem etapa de build: é servido diretamente pelo Uvicorn. Em produção, use workers e sem `--reload`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Em produção, defina obrigatoriamente `FRONTEND_URL`, `BACKEND_URL` e `CORS_ORIGINS` com os domínios reais, e cadastre as URLs de callback correspondentes (`{BACKEND_URL}/api/gsc/callback` no Google Cloud Console e `{BACKEND_URL}/api/nuvemshop/oauth-redirect` no painel da Nuvemshop).

### B.9 Verificação rápida do ambiente

1. `http://localhost:8000/api/health` → `{"status":"ok","mode":"supabase",...}`
2. `http://localhost:8000/api/info` → confirme `ai.enabled: true` e o modelo em uso; se vier `false`, `OPENAI_API_KEY` não foi carregada de `backend/.env`.
3. `http://localhost:8080` → tela de login. Crie uma conta; se a confirmação por e-mail estiver ativa no Supabase, confirme pelo link recebido.
4. Após o login, o dashboard deve carregar sem erro `401`. Um `401` persistente indica divergência entre o projeto Supabase do frontend (`VITE_SUPABASE_URL`) e o do backend (`SUPABASE_URL`), ou `SUPABASE_URL` ausente no backend — sem ela o validador de JWT não consegue buscar as chaves públicas do projeto.