# Go-live — Domínios (Netlify + Render)

Topologia canônica. **Não** recrie o site Netlify nem o serviço Render se já existirem.

```text
                         4seo.app
                            │
                            ▼
                       ┌─────────┐
                       │ Netlify │  marketing Next + SPA Vite
                       └────┬────┘
                            │  VITE_API_BASE_URL / NEXT_PUBLIC_API_URL
                            ▼
                      api.4seo.app
                            │
                            ▼
                       ┌─────────┐
                       │ Render  │  FastAPI (4seo-backend)
                       └────┬────┘
                            ▼
                        Supabase
```

| Domínio | Serviço | Função |
| --- | --- | --- |
| `4seo.app` | Netlify | Landing + app autenticado |
| `www.4seo.app` | Netlify | Redirect para `4seo.app` |
| `api.4seo.app` | Render | FastAPI |
| `fourseo-backend.onrender.com` | Render | URL nativa (manter até o custom domain verificar) |

Serviço Render já publicado:

- Nome: `4seo-backend`
- URL nativa: `https://fourseo-backend.onrender.com`
- Painel: [dashboard.render.com/web/srv-d9ub2eu417fc73851v50](https://dashboard.render.com/web/srv-d9ub2eu417fc73851v50)
- Repo: `https://github.com/CarolBPinheiro/4SEO`

**Não** transforme FastAPI em Netlify Functions. **Não** faça proxy `/api` no Netlify.

---

## Ordem (não pule)

1. Render: plano pago (se Free bloquear custom domain) + domínio `api.4seo.app` + DNS
2. Render: env `BACKEND_URL` / `GSC_REDIRECT_URI` + **Save and deploy**
3. Conferir `https://api.4seo.app/api/health`
4. Netlify: env de produção + **Clear cache and deploy**
5. Portais: OAuth + webhook Asaas nas URLs de `api.4seo.app`
6. Só então, se quiser, desligar o subdomínio `onrender.com`

Enquanto o certificado de `api.4seo.app` não estiver verde, continue usando `https://fourseo-backend.onrender.com` nas env e nos portais.

---

## 1. Render — custom domain

1. Abra o serviço **4seo-backend** (link acima).
2. Se o plano for **Free** e o painel recusar domínio customizado: **Settings → Instance type** → **Starter** (o Blueprint já declara `plan: starter`). Custom domain em Web Service exige instância paga.
3. **Settings → Custom Domains → Add Custom Domain** → `api.4seo.app` → Save.
4. Copie o alvo CNAME que o Render mostrar. Em geral:

   | Tipo | Nome | Alvo |
   | --- | --- | --- |
   | CNAME | `api` | `fourseo-backend.onrender.com` |

   Use **exatamente** o valor do painel. Remova registros `AAAA` (IPv6) nesse hostname.
5. No DNS do registrador de `4seo.app` (onde já aponta o apex para o Netlify), crie só o registro `api`. **Não** mude `4seo.app` / `www` — continuam no Netlify.
6. Volte ao Render e clique **Verify**. Espere o TLS (Let's Encrypt) ficar ativo (2–15 min).
7. Teste: `https://api.4seo.app/api/health` deve devolver JSON `status: ok`.

Health check: em **Settings** defina **Health Check Path** = `/api/health` se estiver vazio.

---

## 2. Render — variáveis (depois do TLS verde)

**Environment → Environment Variables** → editar → **Save and deploy** (não Restart).

| Variável | Valor |
| --- | --- |
| `FRONTEND_URL` | `https://4seo.app` |
| `BACKEND_URL` | `https://api.4seo.app` |
| `CORS_ORIGINS` | `https://4seo.app,https://www.4seo.app` |
| `APP_PUBLIC_URL` | `https://4seo.app` |
| `GSC_REDIRECT_URI` | `https://api.4seo.app/api/gsc/callback` |

Lista completa: [backend/.env.production.example](../../backend/.env.production.example).

`CORS_ORIGINS` são origens do **browser** (`4seo.app`). Não inclua `api.4seo.app`.

---

## 3. Netlify — não recrie o site

Confirme **Site configuration → Build & deploy**:

| Campo | Valor |
| --- | --- |
| Build command | `npm run build:go-live` |
| Publish directory | `deploy-out` |
| Base directory | *(vazio)* |
| Node | `20` (já no `netlify.toml`) |

**Domain management:** `4seo.app` + `www.4seo.app` (redirect www → apex). Não adicione `api.4seo.app` no Netlify.

**Environment variables** (Production):

| Variável | Valor |
| --- | --- |
| `NEXT_PUBLIC_APP_URL` | `https://4seo.app` |
| `NEXT_PUBLIC_API_URL` | `https://api.4seo.app` |
| `VITE_API_BASE_URL` | `https://api.4seo.app/api` |
| `VITE_MARKETING_URL` | `https://4seo.app` |
| `VITE_AUTH_REDIRECT_URL` | `https://4seo.app/login` |
| `VITE_SUPABASE_URL` | URL do projeto |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | chave anon |

Não existe `VITE_API_URL`.

Depois: **Deploys → Trigger deploy → Clear cache and deploy site**.

No DevTools → Network, as calls da API devem ir para `api.4seo.app`, **não** para `4seo.app/api` nem `onrender.com`.

---

## 4. Supabase Auth

**Authentication → URL Configuration**

- Site URL: `https://4seo.app`
- Redirect URLs: `https://4seo.app/login`, `https://www.4seo.app/login`

Não cadastre callbacks OAuth de loja no Supabase — eles vão para o FastAPI.

---

## 5. Portais (só com `api.4seo.app` no ar)

Cadastre **exatamente** (incluindo `/api/...`):

| Portal | URL |
| --- | --- |
| Shopify — Allowed redirection URL | `https://api.4seo.app/api/shopify/oauth-redirect` |
| Nuvemshop — Redirect URI | `https://api.4seo.app/api/nuvemshop/oauth-redirect` |
| Google Cloud — Authorized redirect URI | `https://api.4seo.app/api/gsc/callback` |
| Asaas — Webhook | `https://api.4seo.app/webhooks/asaas` |

Detalhes: [OAUTH_REDIRECTS.md](./OAUTH_REDIRECTS.md), [ASAAS_SANDBOX.md](./ASAAS_SANDBOX.md).

Se o portal já tinha `https://fourseo-backend.onrender.com/...`, **substitua** (não deixe os dois a menos que o provedor aceite múltiplos).

---

## 6. Smoke

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\go-live-smoke.ps1 -BackendUrl https://api.4seo.app
```

Checklist: [CHECKLIST.md](./CHECKLIST.md).
