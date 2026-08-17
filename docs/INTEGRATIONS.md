# Integrações de E-commerce

Referência técnica das quatro plataformas de e-commerce suportadas pelo 4SEO. Documenta o
comportamento real de cada API — autenticação, paginação, limites de requisição e as
peculiaridades que condicionam a forma como o código está escrito.

Cada cliente de plataforma vive em `backend/app/integrations/` e expõe a mesma interface
lógica (listar produtos e categorias, analisar, aplicar otimização, reverter), o que permite
que o frontend trate todas de forma uniforme.

| Plataforma | Cliente | Autenticação | Obtida do lojista |
| --- | --- | --- | --- |
| Shopify | `shopify.py` | OAuth do app 4SEO (ou token legado) | Nome da loja (OAuth) |
| Nuvemshop | `nuvemshop.py` | OAuth 2.0 | Não, via consentimento OAuth |
| VTEX | `vtex.py` | App Key + App Token | Sim, colados pelo lojista |
| Loja Integrada | `lojaintegrada.py` | Chave API loja + chave aplicação | Sim (só chave da loja) |

---

## Padrões comuns a todos os clientes

**Read-modify-write.** Nenhuma das APIs de catálogo aceita atualização parcial de forma
confiável em todos os recursos. Antes de aplicar qualquer otimização, o cliente busca o
objeto completo, mescla apenas os campos de SEO alterados e reenvia o objeto inteiro. Isso
evita apagar dados não relacionados (preço, estoque, imagens, descrição).

**Whitelist de campos.** Apenas campos de SEO podem ser alterados. Os clientes mantêm um
mapeamento explícito de quais campos cada tipo de otimização pode tocar; qualquer campo fora
dessa lista é ignorado, mesmo que a IA sugira alteração.

**Rollback.** Toda aplicação registra o valor original antes de sobrescrevê-lo. O registro de
rollback permite reverter a alteração posteriormente, individualmente ou em lote.

**Retry com backoff.** Respostas HTTP 429 (limite de requisições) são reprocessadas com
espera exponencial, respeitando o cabeçalho `Retry-After` quando a plataforma o envia.

---

## Shopify

- **Base URL:** `https://{loja}.myshopify.com/admin/api/{versão}` — versão da API definida em
  `SHOPIFY_API_VERSION` (`shopify.py`).
- **Autenticação (fluxo principal):** OAuth 2.0 do app 4SEO no Shopify Partners / Dev Dashboard.
  Variáveis de servidor: `SHOPIFY_API_KEY` (Client ID) e `SHOPIFY_API_SECRET` (Client secret).
  Redirect URI: `https://api.4seo.app/api/shopify/oauth-redirect`. O lojista informa só o nome da loja
  na UI; o backend redireciona para a autorização e recebe um *offline access token*.
- **Autenticação (legado):** `POST /api/shopify/connect` com access token de app customizado
  na loja (`shpat_...`) — mantido como fallback.
- **Escopos:** `write_products,write_content` (configurável via `SHOPIFY_OAUTH_SCOPES`).
- **Tipos de conteúdo suportados:** produtos, coleções, páginas e artigos de blog — é a
  integração com a maior cobertura de tipos.
- **Campos de SEO:** título e descrição de SEO ficam em metafields (`title_tag` e
  `description_tag` no namespace `global`), não no objeto principal do produto.
- **Texto alternativo de imagens:** o 4SEO consegue gerar `alt` de imagens de produto usando
  um modelo com visão computacional (configurável por `VISION_MODEL`).

## Nuvemshop

- **Base URL:** `https://api.nuvemshop.com.br/2025-03/{store_id}`.
- **Autenticação:** cabeçalho `Authentication: bearer {access_token}` — atenção ao nome do
  cabeçalho, que é `Authentication` e não o convencional `Authorization`. O token é obtido
  por OAuth 2.0: o lojista autoriza o aplicativo e a Nuvemshop redireciona de volta com um
  código, que o backend troca por um token permanente.
- **Cabeçalho obrigatório:** a Nuvemshop exige um `User-Agent` identificando a aplicação e um
  meio de contato.
- **Paginação:** por página, com limites distintos conforme o recurso (produtos e categorias
  aceitam até 50 itens por página; conteúdos de blog, até 20).
- **Tipos de conteúdo suportados:** produtos, categorias, páginas e posts de blog.
- **Blog:** nem toda loja tem o módulo de blog habilitado; a API responde de forma diferente
  nesse caso, e o app trata isso exibindo um aviso em vez de erro.

## VTEX

- **Base URL:** `https://{accountName}.vtexcommercestable.com.br`. O ambiente
  `vtexcommercestable` é o único válido para essas APIs. O host `api.vtex.com` não é uma
  alternativa equivalente.
- **Autenticação:** cabeçalhos `X-VTEX-API-AppKey` e `X-VTEX-API-AppToken`.
- **Permissões:** não existe função (*role*) predefinida de catálogo — é preciso criar uma
  função customizada no License Manager contendo os recursos **Product and SKU Management**
  (leitura e escrita de produto), **Product management** (listagem de IDs) e
  **Categories Management** (leitura e escrita de categoria). Credenciais sem esses recursos
  autenticam mas retornam 403 nas operações de catálogo.
- **Validação de credenciais:** o app testa a conexão contra um endpoint privado de catálogo.
  Endpoints públicos (`/pub/`) não servem para validar, pois respondem sem autenticação.
- **Atualização de produto:** a documentação oficial é explícita — campos ausentes, vazios ou
  nulos são apagados, e booleanos viram `false`. O read-modify-write é obrigatório.
- **Campos de SEO do produto:** `Title` (title tag), `MetaTagDescription`, `KeyWords`
  (separadas por vírgula) e `LinkId` (slug).
- **Categoria:** não possui `MetaTagDescription`. Na categoria, o campo `Description` é o que
  alimenta a meta description, e `Title` é o title tag. A atualização exige remover os campos
  somente-leitura que o GET retorna (`Id`, `LinkId`, `HasChildren`, `TreePath`,
  `TreePathIds`, `TreePathLinkIds`).
- **Paginação:** a listagem de IDs de produto retorna no máximo 250 por página; a busca
  pública com dados completos usa janelas de até 50 itens e retorna apenas produtos ativos e
  visíveis.
- **Limites:** na ordem de dezenas de milhares de requisições por minuto por conta. Respostas
  429 acompanham `Retry-After`.

## Loja Integrada

- **Base URL:** `https://api.awsli.com.br/v1/`. Atenção: os campos `resource_uri` presentes
  nas respostas vêm no formato interno `/api/v1/...`, que **não** deve ser usado para montar
  chamadas.
- **Autenticação:** cabeçalho `Authorization: chave_api {CHAVE_API} aplicacao {CHAVE_APLICACAO}`
  — separado por espaço simples, sem a palavra `Bearer`. A chave da loja é fornecida pelo
  lojista; a chave da aplicação identifica o 4SEO e é configurada no backend via
  `LOJAINTEGRADA_APP_KEY`, nunca vindo do lojista nem sendo persistida no banco.
- **Plano gratuito:** o recurso de chave de API está disponível apenas em planos pagos da
  Loja Integrada. A tela de conexão do app informa isso ao lojista.
- **Descrição do produto:** `GET /v1/produto/{id}/` só retorna `descricao_completa` quando a
  requisição inclui `?descricao_completa=1`. Omitir esse parâmetro antes de um PUT apagaria a
  descrição do produto.
- **SEO como recurso separado:** o campo `seo` do produto é um *resource URI* apontando para
  um recurso independente (`/v1/seo/{id}`), com os campos `title`, `keyword` e `description`.
  Produtos sem SEO cadastrado podem retornar um URI terminando em `None` — nesse caso é
  preciso criar o registro de SEO antes de atualizá-lo. O mesmo recurso atende produtos e
  categorias. A atualização aceita corpo parcial e responde HTTP 202.
- **Atualização de produto:** exige o objeto completo. Categoria e SEO aceitam corpo parcial.
  `PATCH` não é suportado.
- **Listagem de categoria:** não traz o campo `seo` — apenas o detalhe individual traz.
- **Paginação:** formato TastyPie, com envelope `{"meta": {...}, "objects": [...]}`.
- **Limites:** 3.000 requisições/minuto por aplicação, 100/minuto por loja e 1.200/minuto por
  IP. Ao exceder, retorna HTTP 429 com um código de erro próprio no corpo.

### Webhooks (não utilizados atualmente)

A Loja Integrada oferece webhooks de produto e de pedido
(`PUT https://api.awsli.com.br/webhooks/v1/produto`), que permitiriam disparar uma nova
varredura automaticamente quando o catálogo mudasse. A versão atual do 4SEO não os utiliza —
a atualização é feita por varredura sob demanda. É a evolução natural caso se queira
sincronização automática.

---


---

## Fontes oficiais

- VTEX — schemas OpenAPI oficiais: `github.com/vtex/openapi-schemas` (Catalog API)
- VTEX — recursos do License Manager: `help.vtex.com/en/tutorial/license-manager-resources`
- Loja Integrada — API: `api-docs.lojaintegrada.com.br`
- Nuvemshop — autenticação: `tiendanube.github.io/api-documentation/authentication`
- Shopify — Admin API REST: `shopify.dev/docs/api/admin-rest`
