# Go-live — Virada Asaas Produção

Só execute após o Sandbox E2E verde ([ASAAS_SANDBOX.md](./ASAAS_SANDBOX.md)).

## Cutover

1. No Asaas **Produção**, gerar nova API Key
2. Render:
   - `ASAAS_API_KEY` = key de produção
   - `ASAAS_BASE_URL=https://api.asaas.com/v3`
   - `ASAAS_WEBHOOK_TOKEN` = authToken do webhook de **produção**
3. Criar webhook de produção: `https://api.4seo.app/webhooks/asaas` (mesmos eventos)
4. Confirmar `APP_PUBLIC_URL=https://4seo.app`
5. **Save and deploy** (não só Restart)
6. 1 compra real (plano Start) → sucesso → webhook → claim → `subscriptions` active
7. Conferir `billing_webhook_events` (idempotência) e logs Render

## Rollback

Se falhar: reverter `ASAAS_BASE_URL` + `ASAAS_API_KEY` para sandbox e redeploy.
