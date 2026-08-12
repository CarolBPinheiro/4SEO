# Referência da API

Referência completa dos endpoints HTTP expostos pelo backend do 4SEO (FastAPI). Todas as rotas são declaradas em `backend/app/main.py`.

## Visão geral

**URL base**

Todos os caminhos são absolutos e já incluem o prefixo `/api`. A URL base é o host onde o backend está publicado:

```
https://<host-do-backend>/api/...
```

O frontend resolve a base pela variável `VITE_API_BASE_URL`; quando ela não está definida, usa o caminho relativo `/api` (backend servido atrás do mesmo domínio/proxy do frontend).

**Autenticação**

A autenticação é feita com o JWT emitido pelo Supabase Auth, enviado no cabeçalho HTTP:

```
Authorization: Bearer <token JWT do Supabase>
```

O backend valida a assinatura do token (ES256 via JWKS do projeto Supabase, ou HS256 com o segredo do projeto), exige a audiência `authenticated` e extrai o `sub` como identificador do usuário. O mesmo token é repassado ao Supabase nas consultas ao banco, de forma que as políticas de RLS garantem o isolamento entre contas.

Na coluna **Auth** das tabelas:

- **Sim** — endpoint protegido; sem cabeçalho `Authorization` válido a resposta é `401`.
- **Não** — endpoint público (health check, informações da API e os callbacks de OAuth, que são chamados pelos provedores externos e não pelo navegador autenticado).

Não há endpoints com autenticação opcional.

**Formato padrão de erro**

Toda falha (erro de negócio, `HTTPException` ou exceção não tratada) é serializada em JSON no mesmo formato:

```json
{
  "error": true,
  "detail": "Descrição do erro",
  "context": { "campo": "valor" }
}
```

- `error`: sempre `true` em respostas de erro.
- `detail`: mensagem legível. Em erros não tratados, vem no formato `"<TipoDaExcecao>: <mensagem>"`.
- `context`: objeto opcional, presente apenas quando o endpoint fornece dados adicionais de diagnóstico.

Códigos usados com mais frequência: `400` (requisição inválida, loja não conectada, integração ausente), `401` (token ausente, inválido ou expirado — inclusive quando a plataforma de e-commerce rejeita as credenciais), `404` (recurso inexistente ou de outro usuário), `409` (conflito, por exemplo já existir uma loja conectada), `503` (integração externa indisponível) e `500` (erro interno).

O backend não emite `429`. Os controles de intervalo entre varreduras respondem `200` com um corpo indicando o estado (`{"status": "cooldown", "seconds_until_next": N}` ou `{"status": "already_running"}`), cabendo ao frontend interpretá-lo.

Todas as respostas de sucesso são JSON, exceto os callbacks de OAuth, que respondem com redirecionamento HTTP para o frontend.

---

## Sistema

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/health` | Não | Health check do serviço (status, modo e timestamp UTC). |
| GET | `/api/info` | Não | Versão da API, se a geração por IA está habilitada, modelo em uso e modelos suportados. |

---

## Sites

Cadastro dos sites analisados. Cada usuário opera com uma loja/site principal; sites criados apenas para análise por URL não ocupam a vaga de integração.

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/sites` | Sim | Lista os sites do usuário autenticado. |
| POST | `/api/sites` | Sim | Cadastra um novo site a partir da URL base. |
| DELETE | `/api/sites/{site_id}` | Sim | Remove um site do usuário (propriedade validada via RLS). |

**Corpo de `POST /api/sites`**

```json
{
  "base_url": "https://minhaloja.com.br",
  "platform": "shopify"
}
```

`platform` é opcional (`shopify`, `nuvemshop`, `vtex`, `lojaintegrada` ou nulo para análise por URL).

---

## Dashboard e panorama

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/panorama` | Sim | Visão consolidada de performance orgânica do usuário. |
| GET | `/api/dashboard/summary` | Sim | Resumo do Dashboard (score, contagens, status do scan e da integração). |
| GET | `/api/dashboard/oportunidades` | Sim | Lista as oportunidades de otimização com classificação de impacto, contagens e filtros disponíveis. |

**Parâmetros de query**

- `GET /api/dashboard/summary`
  - `refresh` (bool, padrão `false`) — força o recálculo do resumo, ignorando o cache.
- `GET /api/dashboard/oportunidades`
  - `impactos` (string) — níveis separados por vírgula: `alto,medio,baixo`.
  - `tipos` (string) — códigos de problema separados por vírgula, ex.: `missing_title,missing_meta_description`.
  - `otimizados` (string) — `sim` (apenas já otimizados) ou `nao` (apenas pendentes); ausente retorna todos.

---

## Scan e páginas

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/scan` | Sim | Dispara em segundo plano o scan do site principal do usuário (ação "Atualizar" do Dashboard). |
| GET | `/api/scan/diagnose` | Sim | Diagnóstico síncrono do crawler (páginas descobertas, falhas, duração) sem gravar no banco. |
| POST | `/api/site-scan/{site_id}` | Sim | Executa o scan completo de um site específico (sitemap + crawl recursivo) e retorna o resultado. |
| GET | `/api/site-pages/{site_id}` | Sim | Lista as páginas analisadas do site, com título, meta description, H1, problemas e score. |
| GET | `/api/site-review/{site_id}` | Sim | Lista as tarefas de SEO pendentes do site. |

**Parâmetros de query**

- `POST /api/scan`
  - `force` (bool, padrão `false`) — ignora o intervalo mínimo entre scans.
- `POST /api/site-scan/{site_id}`
  - `max_pages` (int) — limite de páginas do scan; quando omitido usa o padrão do servidor (`MAX_PAGES_PER_SCAN`, padrão 20).

---

## Tarefas SEO e geração por IA

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/site-analyze/{site_id}` | Sim | Gera sugestões de otimização para as tarefas pendentes do site. |
| POST | `/api/task-approve/{task_id}` | Sim | Aprova uma tarefa de SEO. |
| DELETE | `/api/task-approve/{task_id}` | Sim | Remove uma tarefa de SEO. |
| POST | `/api/task-fix/{task_id}` | Sim | Gera a correção de conteúdo para uma tarefa específica. |
| POST | `/api/optimize` | Sim | Gera título, descrição e demais campos de SEO otimizados para um produto informado manualmente. |
| POST | `/api/generate-fix` | Sim | Gera a correção de um problema específico de uma página (por tipo de issue). |
| POST | `/api/generate-all-fixes` | Sim | Gera de uma vez as correções de todos os problemas informados para uma página. |
| POST | `/api/validate-proposal` | Sim | Valida uma proposta e retorna métricas de transparência (atributos preservados e cobertura semântica). |
| POST | `/api/keywords` | Sim | Extrai palavras-chave a partir do conteúdo de uma URL. |

**Parâmetros de query**

- `POST /api/site-analyze/{site_id}`
  - `max_tasks` (int, padrão `10`) — número máximo de tarefas processadas na chamada.

**Corpo de `POST /api/optimize`**

```json
{
  "product_name": "Tênis de corrida masculino",
  "product_description": "Descrição atual do produto",
  "category": "Calçados",
  "brand": "Marca"
}
```

**Corpo de `POST /api/generate-fix`**

```json
{
  "issue_type": "missing_meta_description",
  "page_url": "https://minhaloja.com.br/produto/x",
  "page_title": "Título atual",
  "page_description": "Meta description atual",
  "page_h1": "H1 atual"
}
```

**Corpo de `POST /api/generate-all-fixes`**

```json
{
  "page_url": "https://minhaloja.com.br/produto/x",
  "issues": ["missing_title", "missing_meta_description"],
  "page_title": "Título atual",
  "page_description": "Meta description atual",
  "page_h1": "H1 atual"
}
```

**Corpo de `POST /api/validate-proposal`**

```json
{
  "titulo_original": "Tênis masculino",
  "titulo_sugerido": "Tênis de corrida masculino leve",
  "atributos_produto": ["corrida", "masculino", "leve"],
  "keywords_mercado": ["tênis de corrida", "tênis leve"]
}
```

**Corpo de `POST /api/keywords`**

```json
{
  "url": "https://minhaloja.com.br/pagina"
}
```

---

## Integrações (geral)

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/integrations/status` | Sim | Retorna a integração ativa do usuário (plataforma, loja e estado da conexão); considera conectadas apenas integrações reais de e-commerce. |
| DELETE | `/api/integrations/disconnect` | Sim | Desconecta a loja do usuário, removendo credenciais e limpando o cache de clientes. |

---

## Shopify

O identificador da loja é o parâmetro de query `shop_url` (domínio da loja conectada). Os endpoints exigem uma loja Shopify previamente conectada; caso contrário respondem `400 Loja não conectada`.

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/shopify/connect` | Sim | Conecta uma loja Shopify, testa as credenciais e agenda o scan inicial (limite de 1 loja por usuário). |
| GET | `/api/shopify/products` | Sim | Lista os produtos da loja (paginado até o limite informado). |
| GET | `/api/shopify/product/{product_id}/analyze` | Sim | Analisa um produto e retorna os problemas de SEO detectados. |
| POST | `/api/shopify/product/{product_id}/optimize` | Sim | Gera propostas de otimização para um produto (não aplica nada automaticamente). |
| GET | `/api/shopify/collections` | Sim | Lista as coleções da loja. |
| GET | `/api/shopify/collection/{collection_id}/analyze` | Sim | Analisa uma coleção e retorna os problemas de SEO. |
| POST | `/api/shopify/collection/{collection_id}/optimize` | Sim | Gera propostas de otimização para uma coleção. |
| GET | `/api/shopify/pages` | Sim | Lista as páginas institucionais da loja. |
| GET | `/api/shopify/page/{page_id}/analyze` | Sim | Analisa uma página institucional. |
| POST | `/api/shopify/page/{page_id}/optimize` | Sim | Gera propostas de otimização para uma página institucional. |
| GET | `/api/shopify/blogs` | Sim | Lista os blogs da loja. |
| GET | `/api/shopify/articles` | Sim | Lista os artigos de blog (opcionalmente de um blog específico). |
| GET | `/api/shopify/article/{blog_id}/{article_id}/analyze` | Sim | Analisa um artigo de blog. |
| POST | `/api/shopify/article/{blog_id}/{article_id}/optimize` | Sim | Gera propostas de otimização para um artigo de blog. |
| POST | `/api/shopify/optimize-all` | Sim | Gera propostas de otimização para todos os produtos da loja, até o limite informado. |
| GET | `/api/shopify/proposals` | Sim | Lista as propostas de otimização, com filtro por produto e por status. |
| POST | `/api/shopify/proposals/approve` | Sim | Aprova propostas (as alterações ainda não são enviadas à loja). |
| POST | `/api/shopify/proposals/reject` | Sim | Rejeita propostas. |
| POST | `/api/shopify/proposals/apply` | Sim | Aplica na loja as propostas aprovadas e cria os registros de rollback. |
| GET | `/api/shopify/rollback` | Sim | Lista as alterações aplicadas que podem ser revertidas. |
| POST | `/api/shopify/rollback/direct` | Sim | Reverte uma alteração a partir do registro enviado pelo cliente (sem depender de estado em memória). |
| POST | `/api/shopify/rollback/all` | Sim | Reverte todas as alterações aplicadas na loja. |
| POST | `/api/shopify/rollback/product/{product_id}` | Sim | Reverte todas as alterações de um produto específico. |
| POST | `/api/shopify/rollback/{rollback_id}` | Sim | Reverte uma alteração específica. |

**Parâmetros de query**

- `shop_url` (string, obrigatório em todos os endpoints exceto `POST /api/shopify/connect`).
- `limit` (int) — `products`: padrão `500`; `collections`, `pages` e `articles`: padrão `50`; `optimize-all`: padrão `50`.
- `collection_type` (string, padrão `custom`) — em analyze/optimize de coleção (`custom` ou `smart`).
- `blog_id` (int, opcional) — em `GET /api/shopify/articles`.
- `product_id` (int, opcional) — em `GET /api/shopify/proposals`, `POST /api/shopify/proposals/apply` e `GET /api/shopify/rollback`.
- `status` (string, opcional) — em `GET /api/shopify/proposals`: `pending`, `approved`, `applied`, `rejected` ou `rolled_back`.
- `proposal_ids` (lista de strings, obrigatório) — em approve/reject, repetido na query: `?proposal_ids=a&proposal_ids=b`.
- `rollback_id` (path) — identificador do registro de rollback.

**Corpo de `POST /api/shopify/connect`**

```json
{
  "shop_url": "minhaloja.myshopify.com",
  "api_key": "<api_key>",
  "api_secret": "<api_secret>",
  "access_token": "<access_token>"
}
```

Apenas `shop_url` é obrigatório; informe `access_token` (aplicativo privado/custom app) ou o par `api_key`/`api_secret`.

**Corpo de `POST /api/shopify/product/{product_id}/optimize` e `POST /api/shopify/optimize-all`**

```json
{
  "optimize_title": true,
  "optimize_description": true,
  "optimize_seo_title": true,
  "optimize_seo_description": true,
  "optimize_image_alts": true,
  "generate_faq": true,
  "generate_rich_description": false,
  "generate_tags": true,
  "target_keyword": "tênis de corrida"
}
```

Todos os campos têm valor padrão; em `optimize-all` o corpo é opcional.

**Corpo de `POST /api/shopify/proposals/apply`** (opcional — quando enviado, aplica exatamente as propostas informadas)

```json
{
  "proposals": [
    { "id": "...", "content_type": "product", "product_id": 123, "field": "seo_title", "new_value": "..." }
  ]
}
```

**Corpo de `POST /api/shopify/rollback/direct`**

```json
{
  "record": {
    "id": "...",
    "content_type": "product",
    "product_id": 123,
    "field": "seo_title",
    "old_value": "Valor anterior"
  }
}
```

---

## Nuvemshop

O identificador da loja é o parâmetro de query `store_id` (ID numérico da loja na Nuvemshop, retornado na conexão).

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/nuvemshop/auth` | Sim | Inicia o fluxo OAuth e retorna a URL de autorização e o `state` gerado. |
| GET | `/api/nuvemshop/oauth-redirect` | Não | Callback OAuth: troca o código por token, salva a integração e redireciona ao frontend. |
| POST | `/api/nuvemshop/exchange-code` | Sim | Troca manualmente um authorization code por access token e vincula a loja ao usuário. |
| POST | `/api/nuvemshop/connect-token` | Sim | Conecta a loja diretamente com `access_token` e `store_id` (limite de 1 loja por usuário). |
| GET | `/api/nuvemshop/products` | Sim | Lista os produtos da loja (paginado até o limite informado). |
| GET | `/api/nuvemshop/product/{product_id}/analyze` | Sim | Analisa um produto e retorna métricas de SEO. |
| POST | `/api/nuvemshop/product/{product_id}/optimize` | Sim | Gera propostas de otimização para um produto. |
| GET | `/api/nuvemshop/categories` | Sim | Lista as categorias da loja. |
| GET | `/api/nuvemshop/category/{category_id}/analyze` | Sim | Analisa uma categoria e retorna métricas de SEO. |
| POST | `/api/nuvemshop/category/{category_id}/optimize` | Sim | Gera propostas de otimização para uma categoria. |
| GET | `/api/nuvemshop/pages` | Sim | Lista as páginas da loja. |
| GET | `/api/nuvemshop/page/{page_id}/analyze` | Sim | Analisa uma página e retorna métricas de SEO. |
| POST | `/api/nuvemshop/page/{page_id}/optimize` | Sim | Gera propostas de otimização para uma página. |
| GET | `/api/nuvemshop/blog` | Sim | Lista os posts do blog da loja. |
| GET | `/api/nuvemshop/blog/debug` | Sim | Endpoint de diagnóstico da API de blogs da loja (verifica disponibilidade e formato dos dados). |
| GET | `/api/nuvemshop/blog/{blog_id}/{post_id}/analyze` | Sim | Analisa um post do blog e retorna métricas de SEO. |
| POST | `/api/nuvemshop/blog/{blog_id}/{post_id}/optimize` | Sim | Gera propostas de otimização para um post do blog. |
| GET | `/api/nuvemshop/proposals` | Sim | Lista as propostas de otimização, com filtro por status e tipo de conteúdo. |
| POST | `/api/nuvemshop/proposals/approve` | Sim | Aprova as propostas informadas. |
| POST | `/api/nuvemshop/proposals/reject` | Sim | Rejeita as propostas informadas. |
| POST | `/api/nuvemshop/proposals/apply` | Sim | Aplica na loja as propostas aprovadas e cria os registros de rollback. |
| GET | `/api/nuvemshop/rollback` | Sim | Lista os registros de rollback disponíveis. |
| POST | `/api/nuvemshop/rollback/direct` | Sim | Reverte uma alteração a partir do registro enviado pelo cliente. |
| POST | `/api/nuvemshop/rollback/all` | Sim | Reverte todas as alterações aplicadas na loja. |
| POST | `/api/nuvemshop/rollback/{rollback_id}` | Sim | Reverte uma alteração específica. |

**Parâmetros de query**

- `store_id` (string, obrigatório) — em todos os endpoints, exceto `auth`, `oauth-redirect`, `exchange-code` e `connect-token`.
- `GET /api/nuvemshop/oauth-redirect`: `code`, `state` e `error` (enviados pela Nuvemshop; a resposta é um redirecionamento para o frontend com o resultado).
- `limit` (int) — `products`: padrão `500`; `categories`, `pages` e `blog`: padrão `50`.
- `target_keyword` (string, opcional) — nos endpoints de otimização.
- `status` e `content_type` (string, opcionais) — em `GET /api/nuvemshop/proposals`.
- `content_type` (string, opcional) — em `GET /api/nuvemshop/rollback`.
- `item_id` (int, opcional) — em `POST /api/nuvemshop/proposals/apply`, para aplicar apenas as propostas de um item.

**Corpo de `POST /api/nuvemshop/connect-token`**

```json
{
  "access_token": "<access_token>",
  "store_id": "1234567"
}
```

**Corpo de `POST /api/nuvemshop/exchange-code`**

```json
{
  "code": "<authorization_code>"
}
```

**Corpo de `POST /api/nuvemshop/proposals/approve` e `/reject`**

```json
{
  "proposal_ids": ["id-1", "id-2"]
}
```

**Corpo de `POST /api/nuvemshop/proposals/apply`** (opcional)

```json
{
  "proposals": [
    { "id": "...", "content_type": "product", "product_id": 123, "field": "seo_title", "new_value": "..." }
  ]
}
```

**Corpo de `POST /api/nuvemshop/rollback/direct`**

```json
{
  "record": {
    "id": "...",
    "content_type": "product",
    "product_id": 123,
    "field": "seo_title",
    "old_value": "Valor anterior"
  }
}
```

---

## VTEX

O identificador da loja é o parâmetro de query `store_id`, que corresponde ao **account name** da conta VTEX (devolvido no campo `store_id` da resposta de conexão).

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/vtex/connect` | Sim | Conecta uma conta VTEX via App Key/App Token, testa o acesso ao catálogo e agenda o scan inicial. |
| GET | `/api/vtex/products` | Sim | Lista os produtos da loja (paginado até o limite informado). |
| GET | `/api/vtex/product/{product_id}/analyze` | Sim | Analisa um produto e retorna métricas de SEO. |
| POST | `/api/vtex/product/{product_id}/optimize` | Sim | Gera propostas de otimização para um produto. |
| GET | `/api/vtex/categories` | Sim | Lista as categorias da loja (árvore de categorias achatada). |
| GET | `/api/vtex/category/{category_id}/analyze` | Sim | Analisa uma categoria e retorna métricas de SEO. |
| POST | `/api/vtex/category/{category_id}/optimize` | Sim | Gera propostas de otimização para uma categoria. |
| GET | `/api/vtex/proposals` | Sim | Lista as propostas de otimização, com filtro por status e tipo de conteúdo. |
| POST | `/api/vtex/proposals/approve` | Sim | Aprova as propostas informadas. |
| POST | `/api/vtex/proposals/reject` | Sim | Rejeita as propostas informadas. |
| POST | `/api/vtex/proposals/apply` | Sim | Aplica na loja as propostas aprovadas (leitura, alteração e gravação do registro completo). |
| GET | `/api/vtex/rollback` | Sim | Lista os registros de rollback disponíveis. |
| POST | `/api/vtex/rollback/direct` | Sim | Reverte uma alteração a partir do registro enviado pelo cliente. |
| POST | `/api/vtex/rollback/all` | Sim | Reverte todas as alterações aplicadas na loja. |
| POST | `/api/vtex/rollback/{rollback_id}` | Sim | Reverte uma alteração específica. |

**Parâmetros de query**

- `store_id` (string, obrigatório) — em todos os endpoints, exceto `POST /api/vtex/connect`.
- `limit` (int) — `products`: padrão `500`; `categories`: padrão `100`.
- `target_keyword` (string, opcional) — nos endpoints de otimização.
- `status` e `content_type` (string, opcionais) — em `GET /api/vtex/proposals`.
- `content_type` (string, opcional) — em `GET /api/vtex/rollback`.
- `item_id` (int, opcional) — em `POST /api/vtex/proposals/apply`.

**Corpo de `POST /api/vtex/connect`**

```json
{
  "account_name": "minhaconta",
  "app_key": "<app_key>",
  "app_token": "<app_token>"
}
```

A App Key precisa de um perfil de acesso com os recursos de Catálogo (Product and SKU Management e Categories Management).

**Corpo de `POST /api/vtex/proposals/approve` e `/reject`**

```json
{
  "proposal_ids": ["id-1", "id-2"]
}
```

**Corpo de `POST /api/vtex/proposals/apply`** (opcional)

```json
{
  "proposals": [
    { "id": "...", "content_type": "product", "product_id": 123, "field": "seo_title", "new_value": "..." }
  ]
}
```

**Corpo de `POST /api/vtex/rollback/direct`**

```json
{
  "record": {
    "id": "...",
    "content_type": "product",
    "product_id": 123,
    "field": "seo_title",
    "old_value": "Valor anterior"
  }
}
```

---

## Loja Integrada

O identificador da loja é o parâmetro de query `store_id`, que corresponde à chave interna da loja devolvida no campo `store_id` da resposta de conexão (derivada da chave de API, que nunca trafega de volta).

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/lojaintegrada/connect` | Sim | Conecta via Chave de API da loja, testa o acesso e agenda o scan inicial. |
| GET | `/api/lojaintegrada/products` | Sim | Lista os produtos da loja (paginado até o limite informado). |
| GET | `/api/lojaintegrada/product/{product_id}/analyze` | Sim | Analisa um produto e retorna métricas de SEO. |
| POST | `/api/lojaintegrada/product/{product_id}/optimize` | Sim | Gera propostas de otimização para um produto. |
| GET | `/api/lojaintegrada/categories` | Sim | Lista as categorias da loja. |
| GET | `/api/lojaintegrada/category/{category_id}/analyze` | Sim | Analisa uma categoria e retorna métricas de SEO. |
| POST | `/api/lojaintegrada/category/{category_id}/optimize` | Sim | Gera propostas de otimização para uma categoria. |
| GET | `/api/lojaintegrada/proposals` | Sim | Lista as propostas de otimização, com filtro por status e tipo de conteúdo. |
| POST | `/api/lojaintegrada/proposals/approve` | Sim | Aprova as propostas informadas. |
| POST | `/api/lojaintegrada/proposals/reject` | Sim | Rejeita as propostas informadas. |
| POST | `/api/lojaintegrada/proposals/apply` | Sim | Aplica na loja as propostas aprovadas (campos de SEO pelo recurso próprio; produto por atualização completa). |
| GET | `/api/lojaintegrada/rollback` | Sim | Lista os registros de rollback disponíveis. |
| POST | `/api/lojaintegrada/rollback/direct` | Sim | Reverte uma alteração a partir do registro enviado pelo cliente. |
| POST | `/api/lojaintegrada/rollback/all` | Sim | Reverte todas as alterações aplicadas na loja. |
| POST | `/api/lojaintegrada/rollback/{rollback_id}` | Sim | Reverte uma alteração específica. |

**Parâmetros de query**

- `store_id` (string, obrigatório) — em todos os endpoints, exceto `POST /api/lojaintegrada/connect`.
- `limit` (int) — `products`: padrão `500`; `categories`: padrão `100`.
- `target_keyword` (string, opcional) — nos endpoints de otimização.
- `status` e `content_type` (string, opcionais) — em `GET /api/lojaintegrada/proposals`.
- `content_type` (string, opcional) — em `GET /api/lojaintegrada/rollback`.
- `item_id` (int, opcional) — em `POST /api/lojaintegrada/proposals/apply`.

**Corpo de `POST /api/lojaintegrada/connect`**

```json
{
  "chave_api": "<chave_de_api_da_loja>"
}
```

A chave de aplicação (integrador) é configurada no ambiente do backend (`LOJAINTEGRADA_APP_KEY`); o cliente informa apenas a chave da própria loja. A API da plataforma está disponível somente em planos pagos.

**Corpo de `POST /api/lojaintegrada/proposals/approve` e `/reject`**

```json
{
  "proposal_ids": ["id-1", "id-2"]
}
```

**Corpo de `POST /api/lojaintegrada/proposals/apply`** (opcional)

```json
{
  "proposals": [
    { "id": "...", "content_type": "product", "product_id": 123, "field": "seo_title", "new_value": "..." }
  ]
}
```

**Corpo de `POST /api/lojaintegrada/rollback/direct`**

```json
{
  "record": {
    "id": "...",
    "content_type": "product",
    "product_id": 123,
    "field": "seo_title",
    "old_value": "Valor anterior"
  }
}
```

---

## Google Search Console

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/gsc/auth-url` | Sim | Retorna a URL de autorização do Google para conectar o Search Console. |
| GET | `/api/gsc/callback` | Não | Callback OAuth do Google: troca o código por tokens, seleciona a primeira propriedade disponível e redireciona ao frontend. |
| GET | `/api/gsc/status` | Sim | Informa se o usuário tem o Search Console conectado e qual propriedade está selecionada. |
| GET | `/api/gsc/sites` | Sim | Lista as propriedades do Search Console às quais o usuário tem acesso. |
| PUT | `/api/gsc/site` | Sim | Define qual propriedade do Search Console será usada pelo usuário. |
| DELETE | `/api/gsc/disconnect` | Sim | Desconecta o Search Console e remove os tokens armazenados. |
| GET | `/api/gsc/overview` | Sim | Retorna a visão geral de desempenho da propriedade conectada. |
| GET | `/api/gsc/performance` | Sim | Retorna as métricas de desempenho (cliques, impressões, CTR, posição) no período solicitado. |

**Parâmetros de query**

- `GET /api/gsc/callback`: `code` (obrigatório) e `state` (obrigatório na prática — carrega o identificador do usuário). A resposta é um redirecionamento para a página de integrações do frontend.
- `PUT /api/gsc/site`: `site_url` (string, obrigatório) — propriedade a ser usada, no formato retornado por `GET /api/gsc/sites`.
- `GET /api/gsc/performance`: `start_date` e `end_date` (string, opcionais, formato `AAAA-MM-DD`).

---

## Termos de pesquisa

Cada usuário acompanha até 5 termos monitorados.

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/api/termos` | Sim | Lista os termos monitorados do usuário, já enriquecidos com os dados do último snapshot. |
| POST | `/api/termos` | Sim | Adiciona um termo de pesquisa ao monitoramento (máximo de 5). |
| DELETE | `/api/termos/{term_id}` | Sim | Remove um termo monitorado. |
| POST | `/api/termos/refresh` | Sim | Atualiza os snapshots de todos os termos monitorados do usuário. |
| POST | `/api/termos/trends` | Sim | Consulta dados de tendência de busca para até 5 palavras-chave informadas. |

**Corpo de `POST /api/termos`**

```json
{
  "term": "tênis de corrida"
}
```

**Corpo de `POST /api/termos/trends`**

```json
{
  "keywords": ["tênis de corrida", "tênis leve"],
  "geo": "BR",
  "timeframe": "today 3-m"
}
```

`geo` (padrão `BR`) e `timeframe` (padrão `today 3-m`) são opcionais; `keywords` aceita de 1 a 5 termos.

---

## Histórico

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/historico/snapshot` | Sim | Coleta os dados atuais do Search Console e grava o snapshot do dia. |
| GET | `/api/historico` | Sim | Retorna os snapshots do usuário nos últimos N dias. |

**Parâmetros de query**

- `GET /api/historico`
  - `days` (int, padrão `30`) — janela de dias retornada.