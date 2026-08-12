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

## Bloqueios externos (ação humana)

| Item | Motivo |
|---|---|
| Aplicar `billing.sql` no projeto `emnwonpdziqhtcfpuxxp` | MCP Supabase sem permissão neste projeto; falta `SUPABASE_ACCESS_TOKEN` |
| Serviço Render do 4SEO | Workspace Render ligado só tem outro serviço; repo local sem `git remote` |
| Registrar OAuth nos portais | Requer `BACKEND_URL` público definitivo |
| Webhook Asaas Sandbox/Prod | Requer `BACKEND_URL` público |
| Pagamento E2E / cutover prod | Depende do backend publicado + schema billing |

## Próximos comandos (você)

```powershell
# 1) Token: https://supabase.com/dashboard/account/tokens
$env:SUPABASE_ACCESS_TOKEN = "sbp_..."
npm run apply:billing-schema
npm run verify:billing-schema

# 2) Publicar backend no Render (Blueprint backend/render.yaml) e preencher secrets
# 3) Netlify: build command = npm run build:go-live, publish = deploy-out
#    Env: ver .env.production.example
# 4) Seguir docs/go-live/OAUTH_REDIRECTS.md e ASAAS_SANDBOX.md
# 5) Smoke:
powershell -ExecutionPolicy Bypass -File .\scripts\go-live-smoke.ps1 -BackendUrl https://SEU.onrender.com
```
