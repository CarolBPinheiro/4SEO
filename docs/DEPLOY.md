# Deploy em Produção

Este documento descreve como o 4SEO é publicado em produção e como reproduzir o ambiente do zero.

> **Go-live operacional (integrações + billing):** use a pasta [docs/go-live/](./go-live/) — [domínios](./go-live/DOMAINS.md), inventário de env, OAuth, Asaas Sandbox→Prod e checklist final.

> **Nunca** versione ou compartilhe valores reais de chaves. Todos os segredos abaixo aparecem como marcadores (`<...>`). O arquivo `.gitignore` do projeto já exclui `.env` e `.env.*` (exceto `.env.example` e `.env.production.example`).

---

## 1. Topologia de produção

A aplicação em produção é composta por **três serviços**. O usuário vê só `https://4seo.app`; a API fica em `https://api.4seo.app`:

| Camada | Serviço | Conteúdo | Origem |
|---|---|---|---|
| Frontend | **Netlify** | Marketing (Next export) + App autenticado (Vite SPA), mesclados em `deploy-out/` via `npm run build:go-live` | [netlify.toml](../netlify.toml) |
| Backend | **Render** | API FastAPI (Web Service Python) | [backend/render.yaml](../backend/render.yaml) |
| Dados e autenticação | **Supabase** | Postgres + Auth + RLS | `schema.sql` + `billing.sql` |

Build Netlify: `command = npm run build:go-live`, `publish = deploy-out`.  
Rotas de marketing (`/`, `/checkout/*`, `/sobre`) vêm do Next; rotas do produto (`/login`, `/dashboard`, `/analise`, …) caem no `spa.html` do Vite (`_redirects`).

### Fluxo de comunicação

```
                       Navegador (https://4seo.app)
                                  |
        +-------------------------+--------------------------+
        |                         |                          |
        v                         v                          v
  Netlify (CDN)         Supabase Auth (SDK)      api.4seo.app → Render
  Next + Vite SPA       login, cadastro,            FastAPI /api/*
  (deploy-out/)         refresh de sessão           Authorization: Bearer <JWT>
                                  ^                           |
                                  |                           v
                                  |                  Supabase REST (PostgREST)
                                  +---- JWKS/JWT ----  + APIs externas:
                                                       OpenAI, SearchAPI.io,
                                                       Google Search Console,
                                                       Shopify / Nuvemshop /
                                                       VTEX / Loja Integrada / Asaas
```

Pontos importantes dessa topologia:
- **Frontend** `https://4seo.app` (Netlify). **API** `https://api.4seo.app` (Render). Runbook: [docs/go-live/DOMAINS.md](./go-live/DOMAINS.md).
- Runbook completo: [docs/go-live/](./go-live/).
- Billing schema: [supabase/BILLING_APPLY.md](../supabase/BILLING_APPLY.md).

- **O navegador fala com o Supabase Auth diretamente.** O SDK `@supabase/supabase-js` (`src/lib/supabase.ts`) roda no browser e mantém a sessão; o backend nunca emite tokens próprios.
- **O navegador fala com o backend diretamente** (chamada cross-origin para o domínio do Render), usando o `access_token` do Supabase no header `Authorization`. Não há proxy do Netlify para a API — por isso a URL do backend precisa estar embutida no bundle (`VITE_API_BASE_URL`) e o domínio do frontend precisa estar liberado no CORS do backend.
- **O backend valida o JWT** em `backend/app/auth.py`: tokens `ES256` são verificados contra o JWKS público do projeto (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`) e tokens `HS256` contra `SUPABASE_JWT_SECRET`. Um `SUPABASE_URL` ausente ou incorreto derruba **toda** a autenticação da API.
- **O backend acessa o banco pela API REST do Supabase** (`backend/app/supabase_client.py`), em dois modos: com a *service key* (operações administrativas, ignora RLS) e em nome do usuário, repassando o token dele para que a RLS seja aplicada.
- **Os callbacks de OAuth (Nuvemshop e Google Search Console) apontam para o backend**, não para o frontend. Depois de trocar o código por token, o backend redireciona o navegador de volta para o frontend.

### Ordem recomendada de execução

1. **Supabase** (seção 4): criar o projeto, aplicar `supabase/schema.sql` e configurar as URLs de autenticação. As chaves geradas aqui alimentam os outros dois serviços.
2. **Backend no Render** (seção 2): precisa das chaves do Supabase e produz a URL pública da API.
3. **Frontend no Netlify** (seção 3): precisa da URL da API e das chaves públicas do Supabase.
4. **Checklist pós-deploy** (seção 5).

---

## 2. Backend — Render (Web Service Python)

### 2.1 Configuração do serviço

O arquivo `backend/render.yaml` é a fonte de verdade da configuração:

```yaml
services:
  - type: web
    name: sitecan-backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
```

Ao criar o serviço no painel do Render (**New → Web Service → conectar o repositório GitHub**), use:

| Campo | Valor |
|---|---|
| Runtime / Language | Python 3 |
| **Root Directory** | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |
| Branch | `main` (ou a branch de release adotada) |
| Auto-Deploy | habilitado (deploy a cada push na branch) |

O **Root Directory precisa ser `backend`**: tanto o `requirements.txt` quanto o pacote `app/` (referenciado como `app.main:app`) estão nessa pasta.

A versão do Python está fixada em dois lugares consistentes entre si: `PYTHON_VERSION=3.11` no `render.yaml` e `python-3.11.0` em `backend/runtime.txt`.

O serviço publicado chama-se `4seo-backend`. URL nativa: `https://fourseo-backend.onrender.com`. URL canônica: `https://api.4seo.app` (Custom Domain + CNAME). Use a canônica em `VITE_API_BASE_URL`, `BACKEND_URL`, `NEXT_PUBLIC_API_URL` e redirects OAuth assim que o TLS estiver verde.

### 2.2 Variáveis de ambiente

Configure em **Environment → Environment Variables**.

#### Obrigatórias

| Variável | Onde é usada | Observações |
|---|---|---|
| `SUPABASE_URL` | `supabase_client.py`, `auth.py`, `integrations/gsc.py` | `https://<projeto>.supabase.co`. Base do endpoint REST **e** do JWKS usado na validação dos tokens. |
| `SUPABASE_SERVICE_KEY` | `supabase_client.py`, `integrations/gsc.py` | Chave `service_role`. É a chave do cliente administrativo (ignora RLS) e a que o backend utiliza para gravar `gsc_tokens`. **Nunca** deve chegar ao frontend. |
| `SUPABASE_ANON_KEY` | `supabase_client.py` | Usada como `apikey` nas chamadas feitas em nome do usuário (`get_supabase_for_user`), o que mantém a RLS ativa. |
| `SUPABASE_JWT_SECRET` | `auth.py` | **Condicional.** Segredo JWT legado, usado apenas na verificação de tokens `HS256`. Projetos Supabase atuais assinam com `ES256` e são validados via JWKS, dispensando esta variável — deixe-a vazia nesse caso. |
| `OPENAI_API_KEY` | `llm_optimizer.py` e os otimizadores de cada plataforma | Sem ela, `GET /api/info` retorna `ai.enabled: false` e as propostas de otimização não são geradas. |
| `FRONTEND_URL` | `main.py` (callbacks OAuth) | `https://4seo.app`. Destino do redirect após o OAuth do GSC (`/integracoes?gsc=connected`) e da Nuvemshop (`/analise`). O padrão do código é `localhost`, então **é obrigatória em produção**. |
| `BACKEND_URL` | `main.py` (`/api/nuvemshop/auth`) | `https://api.4seo.app`. Compõe o `redirect_uri` `https://api.4seo.app/api/nuvemshop/oauth-redirect`. A Nuvemshop só aceita HTTPS (ou `localhost`). |

#### Condicionais — por integração

| Variável | Necessária para | Comportamento sem ela |
|---|---|---|
| `NUVEMSHOP_APP_ID` | OAuth da Nuvemshop | O código traz um valor embutido como fallback; em produção **defina explicitamente** com os dados do painel de parceiro. |
| `NUVEMSHOP_CLIENT_SECRET` | OAuth da Nuvemshop | Idem acima. Recomenda-se manter apenas no ambiente, nunca no código. |
| `GSC_CLIENT_ID` | Google Search Console | `GET /api/gsc/auth-url` responde `400`. |
| `GSC_CLIENT_SECRET` | Google Search Console | A troca do código por token falha. |
| `GSC_REDIRECT_URI` | Google Search Console | `https://api.4seo.app/api/gsc/callback`, idêntica à URI no Google Cloud Console. O padrão do código aponta para `localhost`. |
| `SEARCHAPI_KEY` | Enriquecimento com dados de SERP (SearchAPI.io) | As consultas de SERP são puladas e os recursos que dependem delas retornam vazio com aviso em log. |
| `LOJAINTEGRADA_APP_KEY` | Loja Integrada | `POST /api/lojaintegrada/connect` responde `503` ("não configurada no servidor"). |
| `SHOPIFY_API_KEY` / `SHOPIFY_API_SECRET` | OAuth Shopify | Sem elas, o fluxo OAuth do app 4SEO não inicia. |

**VTEX** não exige variáveis de ambiente (conta + App Key + App Token na UI).  
**Loja Integrada** exige `LOJAINTEGRADA_APP_KEY` no servidor; o lojista cola só a Chave de API da loja na UI.  
**Shopify OAuth** exige `SHOPIFY_API_KEY` e `SHOPIFY_API_SECRET` no backend (app no Partners); o lojista só informa o nome da loja. Cadastre `https://api.4seo.app/api/shopify/oauth-redirect` como Allowed redirection URL.

#### Opcionais — ajuste fino

| Variável | Padrão no código | Efeito |
|---|---|---|
| `AI_MODEL` | `gpt-5-mini` | Modelo usado nas gerações de SEO. |
| `AI_REASONING_EFFORT` | `minimal` | Esforço de raciocínio para modelos da família GPT-5 (custo/latência). |
| `VISION_MODEL` | `gpt-4o` | Modelo com visão usado na análise de imagens da integração Shopify. |
| `MAX_PAGES_PER_SCAN` | `20` | Teto de páginas por varredura. |
| `CORS_ORIGINS` | vazio | Origens **adicionais**, separadas por vírgula. O valor `*` é ignorado propositalmente. |
| `PYTHON_VERSION` | `3.11` (via `render.yaml`) | Versão do runtime. |

#### CORS

`backend/app/main.py` já embute as origens de produção e de desenvolvimento:

```
https://4seo.app
https://www.4seo.app
http://localhost:5173
http://localhost:3000
```

`CORS_ORIGINS` apenas acrescenta itens a essa lista. Se o frontend for servido em outro domínio (por exemplo, um deploy de preview do Netlify ou um domínio de cliente), essa origem precisa entrar em `CORS_ORIGINS`, senão o navegador bloqueia as chamadas.

### 2.3 Atenção: variável de ambiente nova exige *deploy*, não *restart*

No Render, **alterar uma variável de ambiente e depois clicar em "Restart service" NÃO aplica a variável nova**. Um restart reaproveita o build e a configuração do deploy anterior — o processo sobe novamente com os mesmos valores de antes, e o sintoma típico é "configurei a chave e o sistema continua dizendo que não está configurada".

O procedimento correto é:

1. Editar/adicionar a variável em **Environment**.
2. Ao salvar, escolher **"Save and deploy"** (e não apenas salvar).
3. Alternativa equivalente: **Manual Deploy → Deploy latest commit** depois de salvar.

Só um novo deploy materializa o ambiente atualizado. Vale a mesma regra para remoção de variáveis.

### 2.4 Considerações operacionais

- **Instância única.** O backend mantém caches em memória do processo (clientes de Shopify, Nuvemshop, VTEX e Loja Integrada, além de `states` de OAuth). Rode o serviço com **uma única instância**; escalar horizontalmente exigiria externalizar esses caches. Os `states` de OAuth da Nuvemshop são persistidos na tabela `oauth_states`, o que faz o fluxo sobreviver a reinícios do processo.
- **Varreduras em segundo plano.** Scans disparados após conectar uma loja rodam como tarefas assíncronas dentro do processo. Se a instância hibernar ou reiniciar no meio de um scan, ele fica com status `running` no banco; um novo scan pode ser disparado com `force`. Em planos que hibernam por inatividade, a primeira requisição após o período ocioso sofre atraso de "cold start".
- **Logs.** Erros não tratados são registrados com stack trace e devolvidos como `{"error": true, "detail": "..."}` — use **Logs** no painel do Render para diagnóstico.
- **Rollback.** Em **Deploys**, selecione um deploy anterior bem-sucedido e use "Redeploy".

---

## 3. Frontend — Netlify

Frontend em `https://4seo.app`: marketing (Next export) + app autenticado (Vite SPA), mesclados por `npm run build:go-live` em `deploy-out/`.

Configuração versionada em [netlify.toml](../netlify.toml). No painel, confirme que o site usa o arquivo do repositório (ou espelhe os valores abaixo).

### 3.1 Configuração de build

| Campo | Valor |
|---|---|
| Repositório | o repositório do projeto no GitHub |
| Branch de produção | `main` |
| Base directory | *(vazio — raiz do repositório)* |
| **Build command** | `npm run build:go-live` |
| **Publish directory** | `deploy-out` |
| Package manager | npm |
| `NODE_VERSION` | `20` (já no `netlify.toml`) |

O comando gera `out/` (Next), `dist/` (Vite) e mescla em `deploy-out/` (`spa.html` + páginas de marketing + `_redirects`).

Variáveis: ver [`.env.production.example`](../.env.production.example) e [docs/go-live/ENV_INVENTORY.md](./go-live/ENV_INVENTORY.md). Após mudar `VITE_*` / `NEXT_PUBLIC_*`, faça **Clear cache and deploy**.

### 3.2 Roteamento (marketing + SPA)

Arquivos estáticos do Next (`/`, `/checkout/*`, `/sobre`) têm precedência. Rotas do app caem em `spa.html` via `_redirects` gerado pelo merge. Evite regras manuais no painel Netlify que conflitem com o `_redirects` publicado.

### 3.3 Variáveis de ambiente (`VITE_*` / `NEXT_PUBLIC_*`)

Configure em **Site configuration → Environment variables** (ver também `.env.production.example`).

| Variável | Obrigatória | Valor de produção | Uso no código |
|---|---|---|---|
| `NEXT_PUBLIC_APP_URL` | Sim | `https://4seo.app` | Landing → login |
| `NEXT_PUBLIC_API_URL` | Sim | `https://api.4seo.app` | Checkout Asaas (`/billing/checkout`). **Sem** `/api`. |
| `VITE_API_BASE_URL` | Sim | `https://api.4seo.app/api` | `src/lib/apiClient.ts`. **O sufixo `/api` é obrigatório**. |
| `VITE_SUPABASE_URL` | Sim | `https://<projeto>.supabase.co` | `src/lib/supabase.ts` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Sim | chave `anon`/`publishable` do projeto | `src/lib/supabase.ts` |
| `VITE_MARKETING_URL` | Sim | `https://4seo.app` | Redirect `/` do Vite |
| `VITE_AUTH_REDIRECT_URL` | Não | `https://4seo.app/login` | `src/contexts/AuthContext.tsx` |

> **Importante:** `src/lib/supabase.ts` possui valores de fallback embutidos apontando para um projeto Supabase específico. Se `VITE_SUPABASE_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY` não estiverem definidas no ambiente de build, o site compilado se conecta silenciosamente a esse projeto de fallback em vez do seu. **Defina sempre as duas variáveis explicitamente.**

### 3.4 Atenção: variáveis `VITE_*` são embutidas em tempo de *build*

O Vite substitui cada referência a `import.meta.env.VITE_*` pelo valor literal **durante o build**. O bundle publicado é um arquivo estático com a string já dentro dele — não há leitura de variáveis em tempo de execução.

Consequência prática: **salvar uma variável no painel do Netlify não muda nada no site que já está no ar.** É preciso gerar um novo build:

1. Ajuste a variável em **Environment variables**.
2. Vá em **Deploys → Trigger deploy → "Clear cache and deploy site"**.

Use a opção com limpeza de cache: um deploy que reaproveita artefatos em cache pode republicar assets antigos, contendo os valores anteriores. O mesmo vale para *remover* uma variável (o valor antigo continua no bundle publicado até o próximo build).

Para conferir que o valor certo foi embutido, procure a URL do backend dentro dos arquivos gerados em `dist/assets/*.js` após o build.

### 3.5 Domínio e HTTPS

- Domínio de produção: **4seo.app** (e `www.4seo.app`), configurado em **Domain management**, com certificado HTTPS emitido pelo Netlify.
- Ambos os hosts já constam da lista de origens permitidas do CORS do backend.
- Qualquer domínio adicional precisa ser refletido em três lugares: CORS do backend (`CORS_ORIGINS`), **Redirect URLs** do Supabase Auth e, se aplicável, `VITE_AUTH_REDIRECT_URL`.

### 3.6 Rollback

Em **Deploys**, abra um deploy anterior e use "Publish deploy" para voltar instantaneamente à versão anterior do site.

---

## 4. Supabase — banco de dados e autenticação

### 4.1 Criar o projeto e aplicar o schema

1. Crie um projeto no Supabase (escolha a região mais próxima dos usuários; para o Brasil, `sa-east-1` reduz latência).
2. Abra **SQL Editor → New query**, cole o conteúdo **inteiro** de `supabase/schema.sql` e execute (**Run**).

O arquivo cria a extensão `pgcrypto` e as dez tabelas do sistema, todas com **Row Level Security habilitada** e políticas de acesso restritas ao usuário dono do registro:

| Tabela | Conteúdo | Regra de propriedade |
|---|---|---|
| `sites` | Lojas/sites do usuário | `auth.uid() = user_id` |
| `pages` | Páginas coletadas nos scans | via `sites.user_id` |
| `seo_tasks` | Problemas e sugestões de SEO | via `sites.user_id` |
| `scan_runs` | Execuções de varredura | via `sites.user_id` |
| `user_integrations` | Credenciais da loja conectada (1 linha por usuário) | `auth.uid() = user_id` |
| `oauth_states` | `state` de OAuth (sobrevive a reinícios do backend) | `auth.uid() = user_id` |
| `user_search_terms` | Termos monitorados | `auth.uid() = user_id` |
| `term_snapshots` | Histórico por termo | `auth.uid() = user_id` |
| `daily_snapshots` | Métricas diárias (1 por usuário/dia) | `auth.uid() = user_id` |
| `gsc_tokens` | Tokens do Google Search Console | `auth.uid() = user_id` |

Observações:

- A tabela `auth.users` é gerenciada pelo próprio Supabase Auth e **não** é criada pelo script.
- **O script não é idempotente** (usa `create table` sem `if not exists`). Execute-o uma única vez, em um projeto vazio. Reexecutar em um banco já provisionado gera erro de objeto duplicado.
- A RLS é o mecanismo de isolamento entre clientes: o frontend acessa o banco com a chave `anon` em nome do usuário autenticado, e o backend só ignora a RLS quando usa deliberadamente a `service_role`.

### 4.2 Coletar as chaves

Em **Project Settings → API** e **Project Settings → API → JWT Settings**:

| Item no painel | Destino |
|---|---|
| Project URL | `SUPABASE_URL` (Render) e `VITE_SUPABASE_URL` (Netlify) |
| Chave `anon` / `publishable` | `SUPABASE_ANON_KEY` (Render) e `VITE_SUPABASE_PUBLISHABLE_KEY` (Netlify) |
| Chave `service_role` | `SUPABASE_SERVICE_KEY` (**somente** no Render) |
| JWT Secret | `SUPABASE_JWT_SECRET` (**somente** no Render) |

A chave `service_role` e o JWT Secret ignoram a RLS e assinam tokens — jamais devem aparecer em variáveis `VITE_*`, no repositório ou em qualquer arquivo servido ao navegador.

### 4.3 Authentication → URL Configuration

Esta é a configuração que mais gera falhas silenciosas em produção. Em **Authentication → URL Configuration**:

| Campo | Valor de produção |
|---|---|
| **Site URL** | `https://4seo.app` |
| **Redirect URLs** | `https://4seo.app/login`<br>`https://www.4seo.app/login`<br>`http://localhost:8080/login` *(desenvolvimento local)* |

**Por que exatamente `/login`:** em `src/contexts/AuthContext.tsx`, a função `getAuthRedirectUrl()` monta a URL de retorno assim:

```ts
function getAuthRedirectUrl() {
  const configuredUrl = import.meta.env.VITE_AUTH_REDIRECT_URL;
  if (configuredUrl) {
    return configuredUrl;
  }
  return `${window.location.origin}/login`;
}
```

Ou seja: se `VITE_AUTH_REDIRECT_URL` estiver definida, ela é usada literalmente; caso contrário, o destino é a **origem atual + `/login`**. Essa mesma função alimenta os dois fluxos de e-mail:

- **Confirmação de cadastro** — `supabase.auth.signUp({ ..., options: { emailRedirectTo: .../login } })`
- **Recuperação de senha** — `supabase.auth.resetPasswordForEmail(email, { redirectTo: .../login?type=recovery })`

O query `type=recovery` faz o app abrir o formulário de nova senha em vez de tratar a sessão como login normal (antes o `/login` encerrava a sessão de recovery ou redirecionava ao dashboard sem permitir trocar a senha).

Portanto, a lista de **Redirect URLs** precisa conter exatamente as URLs terminadas em `/login` para cada origem em que o app é servido (produção, `www`, e a porta local `8080` definida em `vite.config.ts`). Query strings como `?type=recovery` não precisam estar na allowlist — o Supabase valida origem + path. Se a URL enviada não estiver na lista, o Supabase descarta o destino e envia o usuário para a **Site URL**, o que aparece para o usuário final como "cliquei no link do e-mail e caí na página errada" (ou em `localhost`). A rota `/login` existe no roteador do app (`src/App.tsx`), e o SDK do Supabase consome automaticamente os parâmetros de sessão presentes na URL ao carregar essa página.

### 4.4 Demais ajustes de autenticação

- **Authentication → Providers → Email**: mantenha o provedor de e-mail/senha habilitado (é o único fluxo implementado no app). Decida se "Confirm email" fica ligado — com ele ativo, o usuário precisa clicar no link antes do primeiro login.
- **Authentication → Emails**: personalize os templates (remetente e identidade visual) se desejar. Para volume de produção, configure um SMTP próprio; o serviço de e-mail padrão do Supabase tem limites de envio pensados para desenvolvimento.
- **Database → Backups**: confirme a política de backup do plano contratado antes de colocar clientes reais no ar.

---

## 5. Checklist de verificação pós-deploy

Execute na ordem. Cada bloco valida um elo diferente entre os três serviços.

### 5.1 Backend isolado

- [ ] `GET https://api.4seo.app/api/health` retorna `{"status":"ok","mode":"supabase","timestamp":"..."}`.
- [ ] `GET https://api.4seo.app/api/info` retorna `ai.enabled: true` e o `model` esperado. Se vier `false`, `OPENAI_API_KEY` não chegou ao processo — reveja a seção 2.3 (*Save and deploy*, não *Restart*).
- [ ] Nos **Logs** do Render, o deploy terminou com o Uvicorn ouvindo na porta e sem stack traces na inicialização.

### 5.2 Frontend isolado

- [ ] `https://4seo.app` carrega a landing page com HTTPS válido.
- [ ] Acessar uma rota profunda diretamente (ex.: `https://4seo.app/login`, com F5) devolve a aplicação, e não um 404 — valida o `_redirects` publicado.
- [ ] No DevTools → **Network**, as chamadas de API saem para `api.4seo.app` (e não para `4seo.app/api`). Se estiverem indo para `4seo.app/api`, `VITE_API_BASE_URL` não foi embutida — refaça o deploy com limpeza de cache (seção 3.4).
- [ ] Nenhuma requisição retorna erro de CORS no console.

### 5.3 Cadastro e login (Netlify ↔ Supabase)

- [ ] Cadastre um usuário novo em `https://4seo.app/login`.
- [ ] O e-mail de confirmação chega e o link leva de volta para `https://4seo.app/login` (não para `localhost` nem para a home). Se cair no lugar errado, revise **Site URL** e **Redirect URLs** (seção 4.3).
- [ ] O usuário aparece em **Authentication → Users** no painel do Supabase.
- [ ] O login redireciona para o Dashboard e a sessão persiste após recarregar a página.
- [ ] Teste também "esqueci minha senha": o e-mail de reset deve retornar para `/login` no domínio de produção.

### 5.4 Frontend ↔ Backend ↔ Supabase (usuário autenticado)

- [ ] Já logado, no DevTools → **Network**, a chamada `GET .../api/dashboard/summary` retorna **200** e envia o header `Authorization: Bearer ...`.
- [ ] Se retornar **401 "Token inválido"** ou **401 "Token expirado"** logo após o login, o problema está na validação do JWT no backend: confira `SUPABASE_URL` (usado para buscar o JWKS) e `SUPABASE_JWT_SECRET` no Render — e lembre-se de que ajustes nessas variáveis exigem um novo deploy.
- [ ] Se retornar **500** citando erro do Supabase, confira `SUPABASE_SERVICE_KEY` / `SUPABASE_ANON_KEY` e se o `supabase/schema.sql` foi aplicado por completo.

### 5.5 Conectar uma loja

Escolha ao menos uma plataforma e conclua o fluxo em **Integrações**:

- [ ] **Shopify / VTEX / Loja Integrada** (credenciais na UI, exceto OAuth Shopify/Nuvemshop): a conexão retorna sucesso e o nome da loja.
- [ ] **Nuvemshop** (OAuth): o botão leva ao consentimento na Nuvemshop e, ao autorizar, o navegador volta para `https://4seo.app/analise` com a loja conectada. Esse fluxo valida `BACKEND_URL` (a Nuvemshop redireciona para `https://api.4seo.app/api/nuvemshop/oauth-redirect`) e `FRONTEND_URL` (destino final). Um retorno para `localhost` significa que uma dessas variáveis ficou com o valor padrão.
- [ ] No Supabase (**Table Editor**), confirme que foram criadas: uma linha em `user_integrations` e uma em `sites`, ambas com o `user_id` correto.

### 5.6 Executar um scan e aplicar uma otimização

- [ ] Dispare uma varredura pelo Dashboard.
- [ ] Em `scan_runs`, a linha nasce com `status = 'running'` e termina em `completed`, com `pages_scanned`, `tasks_created` e `avg_score` preenchidos.
- [ ] As tabelas `pages` e `seo_tasks` recebem registros, e o Dashboard exibe score e oportunidades.
- [ ] Gere uma proposta de otimização com IA para um produto e **aplique** — valida `OPENAI_API_KEY` e as credenciais de escrita da plataforma.
- [ ] Execute o **rollback** da otimização aplicada e confirme que o conteúdo original volta na loja.

### 5.7 Google Search Console (se configurado)

- [ ] Em **Integrações**, "Conectar GSC" abre o consentimento do Google e retorna para `https://4seo.app/integracoes?gsc=connected`.
- [ ] A tabela `gsc_tokens` recebe uma linha para o usuário.
- [ ] Um erro `redirect_uri_mismatch` do Google indica divergência entre `GSC_REDIRECT_URI` e a URI cadastrada no Google Cloud Console — as duas precisam ser idênticas, incluindo o caminho `/api/gsc/callback`.

### 5.8 Isolamento entre contas (RLS)

- [ ] Crie um segundo usuário e confirme que ele **não** enxerga sites, páginas, tarefas nem integrações do primeiro. Uma falha aqui indica que as políticas de RLS do `schema.sql` não foram aplicadas ou que alguma rota está usando indevidamente a `service_role`.
- [ ] Faça logout e confirme que as rotas protegidas voltam a exigir login.

---

## 6. Resumo de erros comuns

| Sintoma | Causa provável | Correção |
|---|---|---|
| Variável nova configurada no Render "não faz efeito" | Foi usado **Restart service**, que reaproveita o build anterior | Salvar com **Save and deploy** ou disparar **Manual Deploy** |
| Variável nova no Netlify "não faz efeito" | `VITE_*` é embutida no build; o site publicado ainda tem o valor antigo | **Clear cache and deploy site** |
| Chamadas de API retornam HTML / erro de parse | `VITE_API_BASE_URL` ausente → o padrão `/api` bate no Netlify e cai no fallback do SPA | Definir `VITE_API_BASE_URL` com o sufixo `/api` e refazer o build |
| Erro de CORS no console | Origem do frontend fora da lista permitida do backend | Acrescentar o domínio em `CORS_ORIGINS` e redeployar o backend |
| 401 em todas as rotas logo após login | `SUPABASE_URL` / `SUPABASE_JWT_SECRET` incorretos no backend | Corrigir as variáveis e redeployar |
| Link do e-mail leva a `localhost` ou à home | **Redirect URLs** do Supabase sem a entrada `.../login` | Cadastrar as URLs terminadas em `/login` (seção 4.3) |
| 404 ao recarregar uma rota interna | Regra de redirect do SPA sobrescrita no painel do Netlify | Remover a regra conflitante; `public/_redirects` já resolve |
| OAuth da Nuvemshop volta para `localhost` | `BACKEND_URL` / `FRONTEND_URL` com os valores padrão | Definir ambas com as URLs públicas e redeployar |
| Propostas de IA não são geradas | `OPENAI_API_KEY` ausente (`/api/info` mostra `ai.enabled: false`) | Definir a chave e redeployar |