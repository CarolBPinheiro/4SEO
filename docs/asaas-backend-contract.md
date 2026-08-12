# Contrato Asaas — Serviço de billing

Este frontend (Next.js) **não** integra a API Asaas. Toda comunicação com o Asaas ocorre no **backend FastAPI** (`backend/app/billing/`), com a API Key apenas em variáveis de ambiente do servidor (`backend/.env`).

**Status:** implementado em FastAPI (não NestJS). Endpoints:

- `POST /billing/checkout`
- `GET /billing/subscription` (JWT)
- `POST /webhooks/asaas`

Schema SQL: `supabase/billing.sql` (aplicar no Supabase SQL Editor).

Configure no frontend: `NEXT_PUBLIC_API_URL=http://localhost:8000` (`.env.local`).

Documentação oficial: [https://docs.asaas.com/](https://docs.asaas.com/)

## Fluxo

1. Usuário escolhe plano/ciclo na landing e acessa `/checkout?plan={id}&cycle={cycle}`.
2. Frontend chama `POST {NEXT_PUBLIC_API_URL}/billing/checkout`.
3. NestJS cria (ou reutiliza) o customer no Asaas e cria um **Asaas Checkout** com `chargeTypes: ["RECURRENT"]`.
4. NestJS responde com a URL do checkout; o frontend redireciona o usuário.
5. Asaas redireciona para as URLs de callback deste site.
6. NestJS recebe webhooks, valida o token, aplica idempotência e ativa/atualiza a assinatura no banco.

## Variáveis de ambiente (backend FastAPI)

| Variável | Descrição |
| --- | --- |
| `ASAAS_API_KEY` | Chave de API (Sandbox ou Produção). Nunca expor ao frontend. |
| `ASAAS_BASE_URL` | `https://api-sandbox.asaas.com/v3` ou `https://api.asaas.com/v3` |
| `ASAAS_WEBHOOK_TOKEN` | Token de autenticação do webhook (`asaas-access-token`) |
| `APP_PUBLIC_URL` | URL pública do marketing (ex.: `http://localhost:3000`) para callbacks |

Frontend:

| Variável | Descrição |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Base do FastAPI (ex.: `http://localhost:8000`) |

## Catálogo de planos (fonte no frontend)

Arquivo: `lib/billing/plans.ts`

| `planId` | Nome | Ciclos |
| --- | --- | --- |
| `start` | Start | monthly, quarterly, semiannual, annual |
| `pro` | Pro | idem |
| `scale` | Scale | idem |

Mapeamento de ciclo → Asaas (`subscription.cycle`):

| Frontend | Asaas |
| --- | --- |
| `monthly` | `MONTHLY` |
| `quarterly` | `QUARTERLY` |
| `semiannual` | `SEMIANNUALLY` |
| `annual` | `YEARLY` |

O valor cobrado deve ser o `pricing[cycle].total` do catálogo (ou o preço canônico persistido no NestJS, desde que coincida com a landing).

## Endpoints NestJS

### `POST /billing/checkout`

Cria a sessão de checkout Asaas e devolve a URL.

**Request**

```json
{
  "planId": "pro",
  "billingCycle": "monthly"
}
```

**Response `201`**

```json
{
  "checkoutUrl": "https://...",
  "checkoutId": "chk_...",
  "expiresAt": "2026-08-04T18:00:00.000Z"
}
```

**Erros**

| Status | Quando |
| --- | --- |
| `400` | `planId` / `billingCycle` inválidos |
| `401` | Autenticação exigida e ausente (se aplicável) |
| `429` | Rate limit |
| `502` / `503` | Falha ao falar com o Asaas |

Validações obrigatórias:

- Aceitar somente `planId` e `billingCycle` do catálogo.
- Timeout e retry com backoff para falhas transitórias do Asaas.
- Não registrar API Key, tokens ou dados sensíveis de cartão em logs.
- Não confiar em preço enviado pelo cliente; calcular no servidor a partir do catálogo.

### `GET /billing/subscription`

Retorna a assinatura ativa do usuário autenticado (para o app logado). Formato interno do NestJS; o frontend da landing ainda não consome este endpoint.

### `POST /webhooks/asaas`

Endpoint público para eventos Asaas.

Requisitos:

- Validar `ASAAS_WEBHOOK_TOKEN` (header/config conforme painel Asaas).
- Idempotência por `event` + `id` do recurso (ver guia oficial de idempotência).
- Responder `200` rapidamente; processar de forma segura (fila/transação).
- Nunca expor stack traces ao Asaas.

Eventos relevantes (assinaturas / cobranças / checkout): consultar [Eventos de Webhooks](https://docs.asaas.com/docs/eventos-de-webhooks.md) e [Eventos para Checkout](https://docs.asaas.com/docs/eventos-para-checkout.md).

## Criação do Asaas Checkout (recorrente)

Referência: [Checkout com Assinatura (recorrente)](https://docs.asaas.com/docs/checkout-com-assinatura-recorrente.md)

Payload mínimo esperado no NestJS ao chamar o Asaas:

```json
{
  "billingTypes": ["CREDIT_CARD", "PIX"],
  "chargeTypes": ["RECURRENT"],
  "minutesToExpire": 60,
  "callback": {
    "successUrl": "{APP_PUBLIC_URL}/checkout/sucesso",
    "cancelUrl": "{APP_PUBLIC_URL}/checkout/cancelado",
    "expiredUrl": "{APP_PUBLIC_URL}/checkout/expirado"
  },
  "items": [
    {
      "name": "4SEO Pro",
      "description": "Assinatura mensal 4SEO Pro",
      "quantity": 1,
      "value": 199.0
    }
  ],
  "subscription": {
    "cycle": "MONTHLY",
    "nextDueDate": "YYYY-MM-DD"
  }
}
```

Ajustar `billingTypes`, datas e `customerData` conforme regras de negócio e documentação atual do Asaas. Prefira preencher `customerData` no NestJS a partir do usuário autenticado ou de um formulário validado — nunca aceite payloads arbitrários do browser para a API Asaas.

## Callbacks do frontend

| Situação | URL |
| --- | --- |
| Sucesso | `/checkout/sucesso` |
| Cancelado | `/checkout/cancelado` |
| Expirado | `/checkout/expirado` |

A ativação definitiva do plano deve depender do **webhook** (fonte da verdade), não apenas do redirect de sucesso.

## Segurança

- API Key Asaas somente no NestJS.
- Webhook com token + idempotência.
- Validação de entrada (DTO + `ValidationPipe`).
- CORS permitindo apenas a origem do frontend.
- Rate limiting em `/billing/checkout` e `/webhooks/asaas`.
- Princípio do menor privilégio na conta Asaas / chaves.
- Sandbox para homologação; produção só com chaves de produção.

## Checklist de go-live

1. Conta Sandbox Asaas + chave configurada no NestJS.
2. Implementar `POST /billing/checkout` conforme este contrato.
3. Configurar webhook apontando para o NestJS público (túnel em dev).
4. Definir `NEXT_PUBLIC_API_URL` no frontend.
5. Homologar: criar checkout → pagar no sandbox → receber webhook → ativar plano.
6. Trocar para `ASAAS_BASE_URL` / chave de produção.
