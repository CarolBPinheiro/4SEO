# Go-live — Asaas Sandbox

## 0. Ambiente × chave (erro comum)

O Asaas rejeita com `invalid_environment` se:

| ASAAS_BASE_URL | ASAAS_API_KEY deve ser |
|----------------|------------------------|
| `https://api-sandbox.asaas.com/v3` | chave do **Sandbox** |
| `https://api.asaas.com/v3` | chave de **Produção** |

Sintoma no checkout: “Não foi possível continuar” / falha ao criar checkout.

**Local:** se a chave no `backend/.env` for de produção, ou mude
`ASAAS_BASE_URL` para `https://api.asaas.com/v3`, ou troque a chave pela do sandbox.

> Pagamentos reais só com URL + chave de produção. Para validar cartão/PIX sem
> cobrar de verdade, use **sempre** sandbox (chave + URL).

## 1. Painel Asaas (Sandbox)

1. API Key sandbox → `ASAAS_API_KEY` no Render **e** no `backend/.env`
2. `ASAAS_BASE_URL=https://api-sandbox.asaas.com/v3`
3. Webhook:
   - URL: `https://api.4seo.app/webhooks/asaas` (também funciona `/api/webhooks/asaas`)
   - authToken: mesmo valor de `ASAAS_WEBHOOK_TOKEN` (mín. 32 chars)
   - Eventos: `CHECKOUT_CREATED`, `CHECKOUT_PAID`, `CHECKOUT_CANCELED`, `CHECKOUT_EXPIRED`
     (+ `SUBSCRIPTION_*` / `PAYMENT_*` se disponíveis)
4. `APP_PUBLIC_URL=https://4seo.app`
5. **Save and deploy** no Render

## 2. Métodos de pagamento no checkout

O backend cria checkout recorrente (`chargeTypes: RECURRENT`) com:

- `billingTypes`: `CREDIT_CARD` e `PIX`
- `subscription.cycle` + `nextDueDate`

O cadastro do cartão/PIX ocorre **na página hospedada do Asaas** (não no 4SEO).
Confirme no painel Asaas que cartão (e PIX, se desejado) estão habilitados e que
os **dados comerciais** da conta estão 100% preenchidos — sem isso o Asaas
pode recusar cobrança com cartão.

## 3. Pré-requisito schema

```powershell
npm run verify:billing-schema
```

Se falhar: aplique `supabase/billing.sql` + migration de trial
([BILLING_APPLY.md](../../supabase/BILLING_APPLY.md)).

## 4. Fluxo E2E (sandbox)

1. Landing → Pricing → plano → Checkout **ou** trial → “assine agora”
2. `POST {BACKEND}/billing/checkout` retorna `checkoutUrl`
3. Pagar no Sandbox Asaas (cartão de teste / PIX sandbox)
4. Redirect → `https://4seo.app/checkout/sucesso/`
5. Webhook cria/ativa linha em `subscriptions`
6. Login no app → claim associa assinatura ao `user_id`
7. `GET {BACKEND}/billing/subscription` (JWT) → `accessLevel: full`

## 5. Trial 7 dias corridos + bloqueio

1. Cadastro → `/trial` → “Avaliação grátis” → `status=trialing`, `trial_ends_at = agora+7d`
2. Enquanto `trial_ends_at` no futuro: Dashboard, Análise e Integrações liberados
3. Após 7 dias corridos: trial inválido → APIs 402; na consulta de assinatura o
   status vira `expired` e o FE pede upgrade

## 6. Cancelado / expirado

- `https://4seo.app/checkout/cancelado/`
- `https://4seo.app/checkout/expirado/`

## 7. Limitações aceitas

- Limites de produtos/buscas ainda não são enforce no backend
- Render free pode cold-start; webhook precisa da URL pública estável
