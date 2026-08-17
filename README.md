# 4SEO

Workspace unificado:

| Pasta | Papel | Porta |
| --- | --- | --- |
| `app/`, `components/`, `lib/` | Marketing Next.js (UX/UI atual) | `3000` |
| `src/` | App autenticado (Vite + React Router) | `8080` |
| `backend/` | API FastAPI + Supabase | `8000` |
| `supabase/` | Schema SQL / RLS | — |

## Setup

```bash
# Frontend (marketing + app)
cp .env.example .env.local   # Next
cp .env.example .env         # Vite (mesmas VITE_*)
npm install

# Backend
cd backend
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env       # preencher Supabase e demais keys
```

## Desenvolvimento

```bash
# Terminal 1 — API
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — App autenticado
npm run dev:app

# Terminal 3 — Marketing
npm run dev:marketing
```

Fluxo: landing (`:3000`) → Login (`:8080/login`) → API (`:8000/api/*`).

## Scripts

- `npm run dev:marketing` / `build:marketing`
- `npm run dev:app` / `build:app`
- `npm test` — Vitest (app)
- `npm run test:backend` — Pytest (requer venv)

## Documentação

- `docs/go-live/DOMAINS.md` — `4seo.app` (Netlify) + `api.4seo.app` (Render)
- `docs/ecosystem.md` — visão do ecossistema
- `docs/asaas-backend-contract.md` — checkout Asaas (implementado em `backend/app/billing/`)
- `backend/.env.example` — secrets do servidor (local)
- `.env.production.example` / `backend/.env.production.example` — produção
- `docs/SETUP.md` — setup detalhado do produto
- `supabase/billing.sql` — tabelas de checkout/assinatura/webhooks
