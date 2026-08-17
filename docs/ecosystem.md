# Ecossistema 4SEO (workspace unificado)

Raiz: `C:\Users\Admin\Documents\Projetos 4Scale\4SEO`

| Pasta | Papel |
| --- | --- |
| `app/`, `components/`, `lib/` | Marketing Next.js — UX/UI público |
| `src/` | App autenticado Vite |
| `backend/` | FastAPI + integrações |
| `supabase/` | Schema / RLS |

## Portas locais

1. Backend `:8000` — `uvicorn app.main:app`
2. App `:8080` — `npm run dev:app`
3. Marketing `:3000` — `npm run dev:marketing`

## Pendências conhecidas

- Configurar `ASAAS_API_KEY` / `ASAAS_WEBHOOK_TOKEN` no `backend/.env` e aplicar `supabase/billing.sql`
- Configurar webhook Asaas → `POST https://api.4seo.app/webhooks/asaas`
- Rotacionar secrets Nuvemshop se já vazaram historicamente
- Typebot default em host de terceiros (configurável por env)
