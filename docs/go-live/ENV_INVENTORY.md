# Go-live 4SEO — Inventário de ambiente

Domínio único: `https://4seo.app`  
Backend: Render (`BACKEND_URL`)  
Billing: Sandbox primeiro → depois Produção

## Backend (Render) — ver [backend/.env.production.example](../backend/.env.production.example)

| Variável | Prod | Notas |
|---|---|---|
| `SUPABASE_URL` | obrigatório | Projeto `emnwonpdziqhtcfpuxxp` |
| `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` | obrigatório | |
| `OPENAI_API_KEY` | obrigatório p/ propostas | |
| `FRONTEND_URL` | `https://4seo.app` | OAuth return |
| `BACKEND_URL` | URL pública Render | OAuth + webhooks |
| `CORS_ORIGINS` | `https://4seo.app,https://www.4seo.app` | |
| `NUVEMSHOP_APP_ID` / `CLIENT_SECRET` | se integrar Nuvemshop | |
| `SHOPIFY_API_KEY` / `SECRET` | se integrar Shopify | |
| `LOJAINTEGRADA_APP_KEY` | se tiver chave de app LI | senão LI fora do go-live |
| `ASAAS_API_KEY` | Sandbox → depois Prod | |
| `ASAAS_BASE_URL` | sandbox v3 → depois `api.asaas.com/v3` | |
| `ASAAS_WEBHOOK_TOKEN` | = authToken do painel Asaas | |
| `APP_PUBLIC_URL` | `https://4seo.app` | callbacks checkout |

VTEX: sem env (credenciais na UI).

## Frontend (Netlify) — build `npm run build:go-live`

| Variável | Valor |
|---|---|
| `NEXT_PUBLIC_APP_URL` | `https://4seo.app` |
| `NEXT_PUBLIC_API_URL` | `https://<BACKEND_URL>` (sem `/api`) |
| `VITE_SUPABASE_URL` | mesmo projeto Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | anon |
| `VITE_API_BASE_URL` | `https://<BACKEND_URL>/api` |
| `VITE_MARKETING_URL` | `https://4seo.app` |
| `VITE_AUTH_REDIRECT_URL` | `https://4seo.app/login` |

## Supabase Auth

- Site URL: `https://4seo.app`
- Redirect URLs: `https://4seo.app/login`, `https://www.4seo.app/login`

## Schema billing

```powershell
# Verificar
npm run verify:billing-schema

# Aplicar (requer SUPABASE_ACCESS_TOKEN)
$env:SUPABASE_ACCESS_TOKEN = "sbp_..."
npm run apply:billing-schema
```

Manual: [supabase/BILLING_APPLY.md](../supabase/BILLING_APPLY.md)
