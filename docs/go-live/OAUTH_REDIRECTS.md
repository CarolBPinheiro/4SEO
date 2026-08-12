# Go-live — Redirects OAuth (produção)

`BACKEND_URL` = URL pública do FastAPI no Render (HTTPS).  
`FRONTEND_URL` = `https://4seo.app`

## Nuvemshop (Partner portal)

1. Redirect URI: `{BACKEND_URL}/api/nuvemshop/oauth-redirect`
2. Scopes no app: `read_products`, `write_products`, `read_content`, `write_content`, `read_categories`, `write_categories`
3. Env Render: `NUVEMSHOP_APP_ID`, `NUVEMSHOP_CLIENT_SECRET`
4. Aceite: Integrações → Nuvemshop → autorizar → volta para `https://4seo.app/analise`

## Shopify (Partners / Dev Dashboard)

1. Allowed redirection URL: `{BACKEND_URL}/api/shopify/oauth-redirect`
2. Scopes: `write_products,write_content`
3. Env: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`
4. Aceite: Integrações → Shopify → autorizar → `https://4seo.app/analise`

## Loja Integrada

- Sem OAuth. Preencher `LOJAINTEGRADA_APP_KEY` no Render quando a chave de aplicação chegar.
- Lojista cola Chave de API da loja na UI (plano pago LI).

## VTEX

- Sem redirect. App Key/Token com permissões de Catálogo na UI.

## Checklist rápido

- [ ] `FRONTEND_URL=https://4seo.app` no Render (Save and deploy)
- [ ] `BACKEND_URL` HTTPS correto no Render e nos portais
- [ ] Redirects cadastrados idênticos (incluindo `/api/...`)
- [ ] Teste Nuvemshop e/ou Shopify com loja de teste
- [ ] Aplicar 1 proposta + rollback
