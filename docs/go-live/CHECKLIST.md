# Go-live — Checklist final

## Infra
- [ ] `https://4seo.app` HTTPS OK (landing Next)
- [ ] `https://api.4seo.app/api/health` 200 (custom domain Render)
- [ ] Deep links app (`/login`, `/dashboard`) com F5 → SPA Vite
- [ ] Netlify build = `npm run build:go-live` / publish `deploy-out`
- [ ] Backend Render 1 instância; `/api/info` com `ai.enabled: true`
- [ ] DevTools: calls da API vão para `api.4seo.app`, não `4seo.app/api`
- [ ] Env conforme [ENV_INVENTORY.md](./ENV_INVENTORY.md) e [DOMAINS.md](./DOMAINS.md)

## Auth
- [ ] Supabase Site URL + Redirect = `https://4seo.app/login`
- [ ] Signup / confirm / login / reset funcionando

## Schema billing
- [ ] `npm run verify:billing-schema` → OK
- [ ] Tabelas: `billing_checkouts`, `subscriptions`, `billing_webhook_events`

## Integrações ([OAUTH_REDIRECTS.md](./OAUTH_REDIRECTS.md))
- [ ] Nuvemshop OAuth (se `NUVEMSHOP_*` no Render)
- [ ] Shopify OAuth (se `SHOPIFY_*` no Render)
- [ ] VTEX UI (loja teste)
- [ ] Loja Integrada só se `LOJAINTEGRADA_APP_KEY` preenchida
- [ ] 1x optimize + apply + rollback por integração ativa

## Billing Sandbox ([ASAAS_SANDBOX.md](./ASAAS_SANDBOX.md))
- [ ] Webhook sandbox apontando para Render
- [ ] Checkout → pagamento sandbox → sucesso → subscription
- [ ] Claim após login

## Billing Produção ([ASAAS_PRODUCTION_CUTOVER.md](./ASAAS_PRODUCTION_CUTOVER.md))
- [ ] Cutover keys + BASE_URL produção
- [ ] 1 pagamento real validado

## Segurança
- [ ] Sem CORS errors
- [ ] Sem secrets em `VITE_` / `NEXT_PUBLIC_`
- [ ] RLS: usuário A não vê dados do B

## Follow-ups pós go-live
- [ ] Enforce limites do plano no backend
- [ ] Trial 7 dias real ou remover copy da landing
- [ ] `LOJAINTEGRADA_APP_KEY` quando chegar do parceiro
