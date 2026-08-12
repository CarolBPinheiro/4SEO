# Go-live — Asaas Sandbox

## 1. Painel Asaas (Sandbox)

1. API Key sandbox → `ASAAS_API_KEY` no Render
2. `ASAAS_BASE_URL=https://api-sandbox.asaas.com/v3`
3. Webhook:
   - URL: `{BACKEND_URL}/webhooks/asaas` (também funciona `{BACKEND_URL}/api/webhooks/asaas`)
   - authToken: mesmo valor de `ASAAS_WEBHOOK_TOKEN` (mín. 32 chars)
   - Eventos: `CHECKOUT_CREATED`, `CHECKOUT_PAID`, `CHECKOUT_CANCELED`, `CHECKOUT_EXPIRED`
     (+ `SUBSCRIPTION_*` / `PAYMENT_*` se disponíveis)
4. `APP_PUBLIC_URL=https://4seo.app`
5. **Save and deploy** no Render

## 2. Pré-requisito schema

```powershell
npm run verify:billing-schema
```

Se falhar: aplique `supabase/billing.sql` ([BILLING_APPLY.md](../../supabase/BILLING_APPLY.md)).

## 3. Fluxo E2E

1. `https://4seo.app` → Pricing → escolher plano → Checkout
2. `POST {BACKEND}/billing/checkout` retorna `checkoutUrl`
3. Pagar no Sandbox Asaas
4. Redirect → `https://4seo.app/checkout/sucesso/`
5. Webhook cria/ativa linha em `subscriptions`
6. Login no app → claim associa assinatura ao `user_id`
7. `GET {BACKEND}/billing/subscription` (JWT) → plano ativo

## 4. Cancelado / expirado

- `https://4seo.app/checkout/cancelado/`
- `https://4seo.app/checkout/expirado/`

## 5. Limitações aceitas no go-live

- Trial “7 dias” na landing ainda não está no billing code
- Limites de produtos/buscas ainda não são enforce no backend
