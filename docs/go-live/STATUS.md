# Status da execução do plano Go-live

Atualizado automaticamente pelo agente durante a implementação.

## Feito no repositório

| Item | Status |
|---|---|
| Inventário env (`scripts/inventory_env.py`) | OK — Nuvemshop/Shopify/Asaas SET; LI EMPTY; Asaas **Sandbox** |
| `billing.sql` + apply/verify scripts | OK (apply exige `SUPABASE_ACCESS_TOKEN`) |
| Deploy unificado Next+Vite (`build:go-live`, `netlify.toml`, `deploy-out`) | OK — build local validado |
| `backend/render.yaml` com env de prod/sandbox | OK |
| `.env.production.example` (backend + root) | OK |
| Docs `docs/go-live/*` | OK |
| `docs/DEPLOY.md` atualizado p/ domínio único | OK |
| Frontend `https://4seo.app` responde 200 (Netlify) | OK |
| Serviço Render `4seo-backend` | OK — `https://fourseo-backend.onrender.com` |
| Custom domain `api.4seo.app` | Pendente — painel Render + DNS ([DOMAINS.md](./DOMAINS.md)) |

## Bloqueios externos (ação humana)

| Item | Motivo |
|---|---|
| Aplicar `billing.sql` no projeto `emnwonpdziqhtcfpuxxp` | MCP Supabase sem permissão neste projeto; falta `SUPABASE_ACCESS_TOKEN` |
| Custom domain `api.4seo.app` no Render | DNS CNAME + TLS; plano Free pode exigir upgrade Starter |
| Env Netlify/Render apontando para `api.4seo.app` | Só depois do health check no custom domain |
| Registrar OAuth nos portais | Usar `https://api.4seo.app/api/...` ([OAUTH_REDIRECTS.md](./OAUTH_REDIRECTS.md)) |
| Webhook Asaas Sandbox/Prod | `https://api.4seo.app/webhooks/asaas` |
| Pagamento E2E / cutover prod | Depende do custom domain + schema billing |

## Próximos comandos (você)

```powershell
# 1) Token: https://supabase.com/dashboard/account/tokens
$env:SUPABASE_ACCESS_TOKEN = "sbp_..."
npm run apply:billing-schema
npm run verify:billing-schema

# 2) Seguir docs/go-live/DOMAINS.md (Render domain → DNS → env → Netlify rebuild)
# 3) Seguir docs/go-live/OAUTH_REDIRECTS.md e ASAAS_SANDBOX.md
# 4) Smoke:
powershell -ExecutionPolicy Bypass -File .\scripts\go-live-smoke.ps1 -BackendUrl https://api.4seo.app
```
