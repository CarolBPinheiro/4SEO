# Sandbox de demonstração local

Ambiente temporário em `localhost` para apresentar o 4SEO com dados fictícios. Não é permanente e não deve ir para produção.

## Pré-requisitos

- Setup normal do [SETUP.md](SETUP.md) (Node, Python 3.11, projeto Supabase com `schema.sql` + `billing.sql`)
- `backend/.env` com `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
- Frontend `.env` apontando para o mesmo projeto Supabase

OpenAI, Asaas, GSC e apps de e-commerce são **opcionais**. Sem eles, o sandbox usa mocks.

## Ligar

No `backend/.env`:

```
ENVIRONMENT=development
DEMO_MODE=true
FRONTEND_URL=http://localhost:8080
BACKEND_URL=http://localhost:8000
ADMIN_EMAILS=admin@demo.4seo.local
```

`DEMO_MODE` recusa boot se `ENVIRONMENT=production` ou se `FRONTEND_URL` / `BACKEND_URL` não forem localhost.

Semeia contas e sobe os três processos:

```bash
npm run demo:seed
npm run demo
```

- Marketing: http://localhost:3000
- App: http://localhost:8080/login
- API: http://localhost:8000/docs

Reset (apaga só `*@demo.4seo.local` e semeia de novo): `npm run demo:reset`.

Senha padrão: `Demo4SEO!local` (sobrescreva com `DEMO_PASSWORD` no `backend/.env`).

## Contas

| E-mail | Papel |
| --- | --- |
| `demo@demo.4seo.local` | Plano Scale ativo — Dashboard, Análise, Termos, Histórico, Panorama |
| `trial@demo.4seo.local` | Trial 7 dias — menus pagos bloqueados |
| `admin@demo.4seo.local` | Scale + `/admin` (exige `ADMIN_EMAILS`) |

Na tela de login, com o backend em demo, use **Preencher conta demo**.

## O que é mock vs real (híbrido)

| Recurso | Sem credencial no `.env` | Com credencial |
| --- | --- | --- |
| Shopify / Nuvemshop / VTEX / Loja Integrada | Catálogo fixture + apply/rollback locais | OAuth / connect real continua disponível |
| Google Search Console | `Conectar Search Console demo` | OAuth Google |
| SearchAPI / Trends | Série fictícia | API real |
| OpenAI | Propostas canned | Modelo configurado |
| Asaas checkout | 503 claro — use a assinatura seedada | Sandbox Asaas |

Em Integrações, **Conectar loja demo** grava um token `demo_*` (uma loja por usuário; desconecte para trocar de plataforma).

## Roteiro de apresentação

1. Landing `:3000` → Login
2. `demo@` → Dashboard (score, oportunidades, GSC)
3. Integrações: desconectar e conectar outra plataforma demo
4. Análise: gerar propostas, aplicar, rollback
5. Termos, Histórico, Panorama
6. `trial@` → menus full bloqueados
7. `admin@` → `/admin`

## Segurança

- Flag default off; nada disso entra em `.env.production.example`
- Tokens fictícios prefixados com `demo_`
- Seed/reset só tocam e-mails `@demo.4seo.local`
- Estado mutável do catálogo fica em `backend/.demo-state/` (gitignored)
