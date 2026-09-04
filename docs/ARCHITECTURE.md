# Arquitetura

Documento de arquitetura do **4SEO** — plataforma SaaS de SEO para lojas online. O conteúdo abaixo descreve o sistema como ele está implementado no código-fonte entregue: componentes, fronteiras, fluxos de execução e modelo de dados.

---

## 1. Visão geral

O 4SEO é composto por três blocos executáveis e um conjunto de serviços externos:

| Bloco | Tecnologia | Papel |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite 5 + Tailwind CSS | SPA que roda no navegador; toda a interface do produto |
| **Backend** | Python 3.11 + FastAPI (`uvicorn`) | API REST `/api/*`; regra de negócio, crawler, camada de IA e integrações |
| **Banco / Autenticação** | Supabase (PostgreSQL + Supabase Auth + Row Level Security) | Persistência e identidade; o isolamento entre clientes é garantido pelo RLS |
| **Serviços externos** | OpenAI, Shopify, Nuvemshop, VTEX, Loja Integrada, Google Search Console, SearchAPI.io | Geração de conteúdo, leitura/escrita nos catálogos, dados de desempenho e de SERP |

### 1.1 Topologia

```
                         ┌───────────────────────────────────────────┐
                         │              NAVEGADOR                    │
                         │  SPA React (react-router-dom, Tailwind)   │
                         └───────────────┬───────────────────────────┘
                                         │
              ┌──────────────────────────┼───────────────────────────────┐
              │                          │                               │
   (1) login / refresh de sessão   (2) chamadas de API            (browser → CDN)
   supabase-js  ──────────────┐    fetch em /api/*                 assets estáticos
                              │    Authorization: Bearer <JWT>
                              ▼                    │
                  ┌───────────────────────┐        │
                  │   SUPABASE AUTH       │        │
                  │  emite JWT (ES256)    │        │
                  └───────────┬───────────┘        │
                              │ JWKS                ▼
                              │        ┌──────────────────────────────────────┐
                              └───────▶│        BACKEND — FastAPI             │
                                       │                                      │
                                       │  app/main.py      rotas HTTP         │
                                       │  app/auth.py      validação do JWT   │
                                       │  app/services.py  regras de negócio  │
                                       │  app/crawler.py   varredura do site  │
                                       │  app/seo_analysis.py  score/issues   │
                                       │  app/llm_optimizer.py + ai_config.py │
                                       │  app/integrations/*  clients         │
                                       └───┬──────────┬──────────┬────────────┘
                                           │          │          │
                    ┌──────────────────────┘          │          └───────────────────┐
                    │                                 │                              │
                    ▼                                 ▼                              ▼
     ┌───────────────────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
     │ SUPABASE / PostgreSQL     │   │ PLATAFORMAS DE E-COMMERCE │   │ SERVIÇOS DE APOIO        │
     │ REST (PostgREST) + RLS    │   │ Shopify   (Admin REST)    │   │ OpenAI (Chat Completions)│
     │ 10 tabelas de aplicação   │   │ Nuvemshop (API 2025-03)   │   │ Google Search Console    │
     │ auth.users (Supabase Auth)│   │ VTEX      (Catalog API)   │   │ SearchAPI.io (SERP/Trends)│
     └───────────────────────────┘   │ Loja Integrada (v1)       │   └──────────────────────────┘
                                     └───────────────────────────┘
                                                 ▲
                                                 │ leitura de catálogo e escrita de SEO
                                                 │ (com registro de rollback)
                                                 └── site público da loja ◀── crawler HTTP
```

### 1.2 Como as peças se conectam

1. **Navegador → Supabase Auth.** O login/cadastro é feito diretamente pelo SDK `@supabase/supabase-js` no frontend. O backend não emite nem armazena senhas; ele apenas valida o JWT recebido.
2. **Navegador → Frontend.** A SPA é servida como conteúdo estático (build Vite em `dist/`).
3. **Frontend → Backend.** Todas as chamadas passam pelo cliente HTTP central `src/lib/apiClient.ts`, que injeta `Authorization: Bearer <access_token>` em cada requisição para `${VITE_API_BASE_URL || "/api"}`.
4. **Backend → Supabase.** O backend fala com o PostgreSQL pela **API REST do Supabase** (PostgREST), e não por conexão SQL direta. Nas rotas de usuário ele usa a *anon key* somada ao JWT do usuário, o que faz o RLS valer (seção 4).
5. **Backend → Plataformas de e-commerce.** Um client por plataforma em `backend/app/integrations/` lê catálogo (produtos, categorias, páginas, blog) e escreve os campos de SEO aprovados.
6. **Backend → OpenAI.** A camada de IA monta o prompt com o contexto enriquecido e recebe um JSON estruturado com as propostas.
7. **Backend → Crawler.** Para a análise genérica por URL, o backend acessa o site público da loja por HTTP (sitemap + páginas).

---

## 2. Frontend

### 2.1 Organização de pastas

```
src/
├── main.tsx                 Bootstrap: createRoot(...).render(<App />)
├── App.tsx                  Providers globais + tabela de rotas
├── index.css / App.css      Estilos base (Tailwind)
├── pages/                   Uma página por rota
│   ├── MarketingRedirect.tsx Redireciona "/" para o site Next (UX atual)
│   ├── Login.tsx            Autenticação
│   ├── Dashboard.tsx        Panorama consolidado + oportunidades
│   ├── Analise.tsx          Fluxo de análise/otimização (roteia por plataforma)
│   ├── Integracoes.tsx      Conectar/desconectar loja e GSC
│   ├── PanoramaSEO.tsx      Relatório de SEO do site
│   ├── TermosPesquisa.tsx   Termos monitorados (tendências)
│   ├── Historico.tsx        Série histórica de desempenho
│   └── NotFound.tsx
├── components/
│   ├── layout/              AppLayout (sidebar + shell), ProtectedRoute
│   ├── seo/                 Componentes de domínio: ShopifyAnalise, NuvemshopAnalise,
│   │                        VtexAnalise, LojaIntegradaAnalise, IntegrationAnalise,
│   │                        PagesTable, ReviewCard, ScanSummary, RollbackHistory,
│   │                        SiteForm/SiteList/SiteEditDialog, PageDetailDialog, Toast...
│   └── ui/                  Biblioteca de componentes base (Radix UI + Tailwind)
├── contexts/                AuthContext, StoreContext
├── hooks/                   Hooks de dados e utilitários (seção 2.4)
├── lib/                     apiClient.ts, supabase.ts, utils.ts, validation.ts
└── test/                    Setup e suítes de teste (Vitest)
```

Componentes de teste (`*.test.ts` / `*.test.tsx`) ficam ao lado do arquivo testado; a execução é feita por Vitest (`npm test`).

### 2.2 Roteamento

`App.tsx` monta, de fora para dentro: `ErrorBoundary` → `QueryClientProvider` → `TooltipProvider` (+ toasters) → `AuthProvider` → `BrowserRouter` → `Routes`.

As rotas privadas usam o wrapper `ProtectedApp`, que combina três camadas:

```tsx
<ProtectedRoute>      // exige sessão; redireciona para /login quando não há usuário
  <StoreProvider>     // carrega e mantém a loja conectada do usuário
    <AppLayout>       // sidebar de navegação + cabeçalho
      {children}
    </AppLayout>
  </StoreProvider>
</ProtectedRoute>
```

| Rota | Acesso | Página |
|---|---|---|
| `/` | pública | `MarketingRedirect` → site Next.js |
| `/login` | pública | `Login` |
| `/dashboard` | protegida | `Dashboard` |
| `/termos` | protegida | `TermosPesquisa` |
| `/historico` | protegida | `Historico` |
| `/integracoes` | protegida | `Integracoes` |
| `/analise` | protegida | `Analise` |
| `/panorama` | protegida | `PanoramaSEO` |
| `/app`, `/keywords`, `/shopify`, `/nuvemshop` | — | redirecionamentos de compatibilidade para `/analise`, `/termos`, `/integracoes` e `/analise` |
| `*` | — | `NotFound` |

`ProtectedRoute` exibe um indicador de carregamento enquanto a sessão está sendo resolvida, evitando o "flash" de redirecionamento para `/login` em um recarregamento de página.

### 2.3 Contextos

**`AuthContext` (`src/contexts/AuthContext.tsx`)** — fonte única da identidade no frontend.

- Ao montar, chama `supabase.auth.getSession()` e assina `supabase.auth.onAuthStateChange`. Em ambos os casos, propaga o `access_token` para o cliente HTTP via `setToken()`.
- Expõe `user`, `session`, `loading`, `passwordRecovery`, `signIn`, `signUp`, `signOut`, `resetPassword`, `updatePassword`.
- No fluxo de recuperação de senha (`PASSWORD_RECOVERY` / `?type=recovery`), o Login exibe o formulário de nova senha e **não** encerra a sessão.
- `signOut` encerra a sessão no Supabase, limpa o token e chama `clearAppLocalStorage()`, que remove as chaves gravadas pela aplicação (`4seo_store`, `shopify_rollbacks_*`, `nuvemshop_rollbacks_*`, `vtex_rollbacks_*`, `lojaintegrada_rollbacks_*`). Isso impede que dados de uma conta permaneçam visíveis para o próximo usuário no mesmo navegador.
- A URL de retorno de cadastro/recuperação de senha vem de `VITE_AUTH_REDIRECT_URL`, com fallback para `${window.location.origin}/login`.

**`StoreContext` (`src/contexts/StoreContext.tsx`)** — estado da loja conectada (o produto trabalha com **uma loja por usuário**).

- Formato: `{ platform: "shopify" | "nuvemshop" | "vtex" | "lojaintegrada" | null, name, url, storeId }`.
- Na montagem, restaura o último valor conhecido de `localStorage["4seo_store"]` (resposta instantânea da UI) e, em seguida, sincroniza com a verdade do servidor via `GET /api/integrations/status`.
- `disconnect()` só limpa o estado local **depois** que `DELETE /api/integrations/disconnect` retorna sucesso; se a API falhar, o erro é propagado e a UI continua refletindo o estado real do backend.
- Expõe `store`, `connected`, `loading`, `setStore`, `refreshStatus`, `disconnect`.

### 2.4 Cliente HTTP central e injeção do token

Todo tráfego com o backend passa por `src/lib/apiClient.ts`:

- **Base URL:** `import.meta.env.VITE_API_BASE_URL || "/api"`. Em desenvolvimento, o proxy do Vite encaminha `/api` para `http://localhost:8000`; em produção, a variável aponta para a URL pública do backend, pois a hospedagem estática não faz proxy de `/api`.
- **Token sempre fresco:** antes de cada requisição, `getFreshToken()` chama `supabase.auth.getSession()`. O SDK do Supabase renova o `access_token` automaticamente quando ele está perto de expirar; o valor retornado é espelhado em `localStorage["auth_token"]` e enviado no header `Authorization: Bearer <token>`.
- **Tratamento de 401 em duas etapas:** ao receber 401, o cliente força `supabase.auth.refreshSession()` e **repete a requisição uma vez**. Se ainda assim retornar 401, a sessão é considerada irrecuperável: executa `signOut`, limpa o token e redireciona para `/login?expired=1`.
- **Erros normalizados:** respostas não-OK viram `Error` com a mensagem de `detail` ou `message` do corpo (o backend responde sempre `{ "error": true, "detail": "..." }`), com fallback `Erro HTTP <status>`.
- **Superfície tipada:** o objeto `api` agrupa as chamadas por domínio — `sites`, `tasks`, `keywords`, `integrations`, `dashboard`, `gsc`, `termos`, `historico`, `panorama`, `shopify`, `nuvemshop`, `vtex`, `lojaintegrada`. Os namespaces `vtex` e `lojaintegrada` são tipados com as interfaces exportadas por `useIntegrationSeo`, o que garante em tempo de compilação que ambos implementam o mesmo contrato.

### 2.5 Hooks de integração

Existem **dois desenhos distintos** de hook de integração, e isso é intencional:

| Hook | Implementação | Conteúdo suportado |
|---|---|---|
| `useShopify` | **Independente** — motor próprio, ~750 linhas | produtos, coleções (custom/smart), páginas, blogs e artigos; conexão por *access token*; propostas, aplicação e rollback (inclusive `rollbackProduct`) |
| `useNuvemshop` | **Independente** — motor próprio, ~775 linhas | produtos, categorias, páginas e posts de blog; fluxo OAuth (`getAuthUrl`, `handleOAuthCallback`, `exchangeCodeManually`, `connectWithToken`); propostas, aplicação e rollback |
| `useVtex` | **Wrapper fino** — `useIntegrationSeo(api.vtex, "vtex")` | produtos e categorias |
| `useLoja Integrada` | **Wrapper fino** — `useIntegrationSeo(api.lojaintegrada, "lojaintegrada")` | produtos e categorias |

`useShopify` e `useNuvemshop` são independentes porque cada uma dessas plataformas expõe um conjunto de conteúdos e um fluxo de conexão próprios (coleções e artigos na Shopify; OAuth de três etapas na Nuvemshop). VTEX e Loja Integrada expõem o mesmo contrato no backend (produtos + categorias, propostas, aplicação, rollback), então compartilham o motor genérico:

**`useIntegrationSeo(platformApi, storagePrefix)`** (`src/hooks/useIntegrationSeo.ts`) concentra:

- **Tipos comuns** — `IntegrationProduct`, `IntegrationCategory`, `IntegrationProposal`, `IntegrationRollback`, `IntegrationSEOAnalysis` e os *shapes* de resposta (`ProductsResponse`, `ProposalsResponse`, `ApplyResponse`, `RollbacksResponse`).
- **Contrato `IntegrationApi`** — a interface que `api.vtex` e `api.lojaintegrada` implementam.
- **Estado e operações** — `fetchProducts`, `selectProduct`, `generateProductProposals`, `fetchCategories`, `selectCategory`, `generateCategoryProposals`, `approveProposals`, `rejectProposals`, `applyProposals`, `fetchRollbacks`, `rollback`, além de `loading`/`toast`.
- **Persistência local de rollbacks** — a lista de reversões pendentes é gravada em `localStorage` sob a chave `${storagePrefix}_rollbacks_${store_id}` e, ao carregar, é mesclada por `id` com o que o backend devolve. Isso mantém o histórico de reversão disponível na interface mesmo depois de o processo do backend ser reciclado.

Na camada visual o mesmo padrão se repete: `VtexAnalise` e `LojaIntegradaAnalise` são wrappers finos sobre `IntegrationAnalise` (painel compartilhado de produtos + categorias, propostas e selos de transparência), enquanto `ShopifyAnalise` e `NuvemshopAnalise` são painéis próprios.

### 2.6 Demais hooks

- **`useSeoScanner`** — CRUD de sites, disparo de varredura, listagem de páginas e de revisões, aprovação/descarte de tarefas.
- **`useCommon`** (`useAsyncOperation`) — utilitário que encapsula `loading` + *toast* + tratamento de erro em torno de uma operação assíncrona.
- **`useApiError`** — traduz erros técnicos (falhas de rede, códigos HTTP, erros de OAuth) para mensagens em português voltadas ao usuário final.
- **`use-toast`, `use-mobile`** — utilitários de UI.

---

## 3. Backend

### 3.1 Camadas

```
backend/app/
├── main.py               Camada HTTP: aplicação FastAPI, ~118 rotas, CORS,
│                         middleware e handlers de erro, validação de payload (Pydantic)
├── auth.py               Validação do JWT do Supabase (dependências FastAPI)
├── services.py           Regras de negócio: SiteService, ScanService, TaskService,
│                         PageService, KeywordService
├── supabase_client.py    Persistência: cliente REST do Supabase (service role e por usuário)
├── crawler.py            Descoberta e coleta de páginas do site
├── seo_analysis.py       Catálogo de problemas de SEO, pesos e cálculo de score
├── ai_config.py          Modelo de IA, compatibilidade de parâmetros e parse de JSON
├── llm_optimizer.py      Geração de correções/otimizações genéricas com IA
├── ai_validation.py      Validação pós-geração (transparência das propostas)
├── data_enrichment.py    Enriquecimento do contexto antes da chamada de IA
└── integrations/
    ├── shopify.py          + shopify_optimizer.py
    ├── nuvemshop.py        + nuvemshop_optimizer.py
    ├── vtex.py             + vtex_optimizer.py
    ├── lojaintegrada.py     + lojaintegrada_optimizer.py
    ├── gsc.py              Google Search Console (OAuth + métricas)
    └── searchapi_client.py SearchAPI.io (tendências e SERP)
```

**Responsabilidade de cada camada:**

- **`main.py` (rotas).** Define a aplicação (`FastAPI(title="SiteCan SEO - MVP")`), o CORS, os handlers globais e cada endpoint. Um endpoint típico: (1) recebe `user` via `Depends(get_current_user)`; (2) monta um cliente Supabase no contexto do usuário; (3) valida propriedade do recurso; (4) delega para um *service* ou para o client da plataforma; (5) devolve JSON. As rotas estão agrupadas por assunto: saúde/informação, sites, panorama, dashboard, varredura, tarefas, integrações, IA, GSC, termos, histórico e um bloco por plataforma de e-commerce.
- **`services.py` (regras).** Isola a lógica de negócio da camada HTTP e da persistência. `ScanService.run_scan` é o coração do fluxo de varredura (seção 5); `TaskService` cuida do ciclo de vida das tarefas de SEO, inclusive da geração de sugestão com IA; `KeywordService` extrai palavras-chave por frequência a partir do texto de uma página.
- **`supabase_client.py` (persistência).** Encapsula todas as chamadas PostgREST em métodos de domínio (`list_sites_for_user`, `upsert_page`, `create_task`, `create_scan_run`, `complete_scan_run`, `save_integration`, `save_oauth_state`, `save_daily_snapshot`, ...). Nenhuma outra camada monta URLs do Supabase.
- **`integrations/*` (clients por plataforma).** Cada plataforma tem um par: o **client** (protocolo HTTP, modelos de dados, aplicação e rollback) e o **optimizer** (análise de SEO do item e geração de propostas com IA).

### 3.2 Aplicação HTTP e políticas transversais

- **CORS.** `ALLOWED_ORIGINS` = origens fixas (`https://4seo.app`, `https://www.4seo.app`, `http://localhost:5173`, `http://localhost:3000`) unidas às origens extras de `CORS_ORIGINS` (lista separada por vírgula; o coringa `*` é descartado).
- **Middleware `ensure_cors_on_errors`.** Garante os cabeçalhos CORS também em respostas de erro, para que o frontend consiga ler a mensagem em vez de receber uma falha opaca de rede.
- **Handlers globais.** `HTTPException` e `Exception` são convertidos no formato uniforme `{"error": true, "detail": "..."}` (helper `format_error`), com log completo do *stack trace* no caso genérico.
- **Endpoints de serviço.** `GET /api/health` (verificação de disponibilidade) e `GET /api/info` (versão, modelo de IA ativo e se a chave da OpenAI está configurada).

### 3.3 Padrão comum dos clients de plataforma

Os quatro clients (`ShopifyClient`, `NuvemshopClient`, `VtexClient`, `LojaIntegradaClient`) seguem a mesma estrutura:

**a) Autenticação por cabeçalho, definida no construtor**

| Plataforma | Base URL | Autenticação |
|---|---|---|
| Shopify | `https://{loja}/admin/api/2024-01` | `X-Shopify-Access-Token: <token>` (ou Basic auth com *api key* + *secret*) |
| Nuvemshop | `https://api.nuvemshop.com.br/2025-03/{store_id}` | `Authentication: bearer <token>` + `User-Agent` identificando a aplicação |
| VTEX | `https://{conta}.vtexcommercestable.com.br` | `X-VTEX-API-AppKey` + `X-VTEX-API-AppToken` |
| Loja Integrada | `https://api.awsli.com.br/v1` | `Authorization: chave_api {chave da loja} aplicacao {chave do integrador}` |

**b) Um único método `_request` como ponto de entrada.** Todas as chamadas passam por ele, o que centraliza *timeout* (30s), serialização JSON, log e tradução de erro. Os erros são mapeados para exceções de domínio: `401/403` → erro de autenticação (`VtexAuthError`, `LojaIntegradaAuthError`, `NuvemshopAuthError`) com mensagem acionável; `404` → erro de recurso não encontrado; demais `>= 400` → exceção com o corpo truncado.

**c) Retry com backoff em 429 (limite de taxa).**

- **VTEX:** respeita o cabeçalho `Retry-After` quando presente; caso contrário, aplica backoff exponencial `2^tentativa`, limitado a 30s, com até 3 tentativas.
- **Loja Integrada:** backoff `5 × 2^tentativa`, limitado a 60s, com até 3 tentativas — calibrado para o limite da plataforma (100 requisições/minuto por loja).
- **Shopify e Nuvemshop:** o erro HTTP é propagado ao chamador, que o converte em mensagem de usuário (a interface trata `429` com orientação de aguardar).

**d) Paginação encapsulada em métodos `get_all_*`.** Cada plataforma tem seu esquema, e o client esconde essa diferença atrás de uma assinatura única `get_all_x(max_items=N)`:

| Plataforma | Estratégia | Página |
|---|---|---|
| Shopify | cursor por `since_id` (usa o último `id` do lote como âncora) | 250 |
| Nuvemshop | `page` + `per_page` | 50 (20 para páginas institucionais) |
| VTEX | janela `_from` / `_to` sobre a busca de catálogo | 50 |
| Loja Integrada | TastyPie: `limit`/`offset`, seguindo `meta.next` | 50 |

Em todos os casos o laço encerra ao atingir `max_items`, ao receber um lote vazio ou ao receber um lote menor que o tamanho da página.

**e) Escrita com preservação do estado anterior.** VTEX exige *read-modify-write* (o `PUT` substitui o objeto inteiro), então `update_product_fields` faz `GET` → *merge* → `PUT`, e devolve os valores originais. Na Loja Integrada, o SEO é um recurso separado (`/v1/seo/{id}`): a aplicação é feita em duas fases (campos da entidade e campos de SEO), cada uma registrando seu rollback assim que conclui. Na Shopify, título/descrição/tags vão no recurso do produto e `seo_title`/`seo_description` viram *metafields* `global.title_tag` e `global.description_tag`.

**f) Estado em memória por client.** Cada client mantém `_proposals` e `_rollback_records` (dicionários indexados por id). Para não depender desse estado entre requisições, todos expõem variantes *stateless* — `apply_proposals_direct(proposals_data)` e `rollback_direct(record)` — que recebem os dados vindos do frontend. Esse é o caminho usado pela interface em produção.

**g) Cache de clients por usuário no `main.py`.** `_shopify_clients`, `_nuvemshop_clients`, `_vtex_clients_cache` e `_li_clients_cache` guardam `{client, optimizer, user_id}`. As funções `get_or_restore_*_client(...)`:

1. verificam se há entrada em cache e se o `user_id` da entrada é o do usuário autenticado — caso contrário devolvem `None`;
2. se não houver, reconstroem o client a partir de `user_integrations` (lido com o token do usuário, portanto sob RLS);
3. só então instanciam também o *optimizer* correspondente.

---

## 4. Autenticação e multi-tenancy

### 4.1 Emissão do token

A autenticação é do Supabase Auth. O frontend faz login/cadastro/recuperação de senha pelo SDK e recebe uma sessão com `access_token` (JWT) e `refresh_token`. O backend nunca vê a senha do usuário.

### 4.2 Validação do JWT no backend (`app/auth.py`)

O esquema de segurança é `HTTPBearer(auto_error=False)` — a ausência do cabeçalho não gera erro automático, permitindo endpoints opcionalmente autenticados.

`_decode_token(token)` funciona assim:

1. Lê o cabeçalho **não verificado** do JWT apenas para descobrir o algoritmo (`alg`).
2. **`ES256` (padrão atual do Supabase para tokens de usuário):** obtém a chave pública correspondente ao `kid` via `PyJWKClient` apontado para `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` e valida a assinatura com essa chave.
3. **`HS256` (modo legado):** valida a assinatura com o segredo simétrico `SUPABASE_JWT_SECRET`.
4. Em ambos os casos exige `audience="authenticated"`.
5. Erros são traduzidos para HTTP 401: `Token expirado` (assinatura expirada) e `Token inválido: <motivo>` (token malformado ou assinatura inválida).

O suporte duplo permite operar durante a migração de chaves de assinatura do projeto Supabase sem invalidar sessões existentes.

Duas dependências FastAPI consomem essa função:

- **`get_current_user`** — obrigatória. Exige o cabeçalho, decodifica, valida a presença de `sub` e devolve `{"user_id", "email", "role", "token"}`. O campo `token` é repassado adiante justamente para permitir chamadas ao Supabase **no contexto do usuário**.
- **`get_optional_user`** — devolve `None` quando não há token ou quando ele é inválido, para endpoints públicos.

### 4.3 Isolamento entre clientes: o RLS é a camada de isolamento

Todas as tabelas de aplicação têm `row level security` habilitado e políticas que amarram cada linha ao seu dono. A aplicação dessas políticas depende de **qual credencial o backend usa** ao falar com o Supabase — e é isso que `app/supabase_client.py` controla:

```python
class SupabaseClient:
    def __init__(self, url=None, key=None, user_token=None):
        auth_key = user_token or self.key          # JWT do usuário quando fornecido
        self.headers = {
            "apikey": self.key,                    # identifica o projeto/role da chave
            "Authorization": f"Bearer {auth_key}", # identidade efetiva da requisição
            ...
        }

def get_supabase() -> SupabaseClient:
    """Instância service role — BYPASSA o RLS."""

def get_supabase_for_user(user_token: str) -> SupabaseClient:
    """anon key como apikey + JWT do usuário no Authorization — o RLS É APLICADO."""
    return SupabaseClient(key=SUPABASE_ANON_KEY, user_token=user_token)
```

**Consequência prática, e o ponto central do modelo de segurança:**

- **`get_supabase_for_user(user["token"])`** é o caminho usado por praticamente todas as rotas de usuário. Como a `apikey` é a *anon key* e o `Authorization` carrega o JWT, o PostgreSQL resolve `auth.uid()` para o `sub` daquele usuário e **as políticas de RLS filtram as linhas no próprio banco**. Mesmo que um identificador de recurso fosse adivinhado ou vazasse, a consulta simplesmente não retorna linhas de outro usuário — o isolamento não depende de o código lembrar de filtrar por `user_id`.
- **`get_supabase()`** usa a *service key* (`SUPABASE_SERVICE_KEY`), que **ignora o RLS**. Esse caminho existe para operações de servidor que não têm um usuário no contexto — por exemplo, a recuperação de um `state` de OAuth durante o *callback* da Nuvemshop (a requisição vem da plataforma, não do navegador do usuário) e o armazenamento/renovação de tokens do Google Search Console em `gsc_tokens`. **A service key nunca é exposta ao frontend e nunca deve ser usada para servir dados diretamente a uma requisição autenticada de usuário.**

### 4.4 Defesas complementares na aplicação

O RLS é a fronteira principal; sobre ela há verificações adicionais na camada de aplicação:

- **`_ensure_site_owner(db, site_id, user_id)`** — confirma que o site pertence ao usuário antes de operar sobre ele; caso contrário, responde 404 (sem revelar a existência do recurso).
- **Verificação de dono no cache de clients** — uma entrada de cache cujo `user_id` não coincide com o do usuário autenticado nunca é devolvida, mesmo que o identificador da loja seja conhecido.
- **Uma loja por usuário** — as rotas de conexão (`/api/{plataforma}/connect`) respondem **409** se o usuário já tem uma integração ativa. Sites criados apenas para análise por URL (plataforma fora de `("shopify", "nuvemshop", "vtex", "lojaintegrada")`) não ocupam esse espaço e são removidos ao conectar uma loja real.
- **`state` de OAuth persistido** — o `state` é gravado em `oauth_states` com validade de 10 minutos, junto do `user_id` e do token do usuário, de modo que o *callback* consiga reassociar a loja ao usuário correto. Se o contexto do usuário não puder ser recuperado, o client **não é colocado em cache** — a conexão precisa ser refeita, em vez de ficar acessível sem dono definido.
- **Higiene no navegador** — `signOut` limpa o token e todas as chaves de aplicação do `localStorage` (loja conectada e caches de rollback por plataforma).

---

## 5. Fluxo de varredura (scan) e análise

Este fluxo cobre a análise **por URL** do site público: descobre páginas, calcula score e gera tarefas de SEO.

### 5.1 Sequência completa

```
POST /api/scan?force=…              (Dashboard)          POST /api/site-scan/{site_id}   (execução direta)
        │                                                          │
        ├── 1. site do usuário (RLS)                                ├── _ensure_site_owner
        ├── 2. guarda de concorrência: scan "running"?              │
        ├── 3. cooldown de 5 min (a menos que force=true)           │
        └── 4. asyncio.create_task(...)  ──────────────┐            └── execução síncrona ──┐
                                                       ▼                                    ▼
                                        ┌───────────────────────────────────────────────────────┐
                                        │              ScanService.run_scan                     │
                                        │  a) lê o site                                         │
                                        │  b) trava contra scan concorrente (600s)              │
                                        │  c) INSERT scan_runs (status = running)               │
                                        │  d) crawl_site(base_url, max_pages)                   │
                                        │  e) por página: upsert em `pages`                     │
                                        │  f) por problema: INSERT em `seo_tasks` (sem duplicar)│
                                        │  g) UPDATE scan_runs (status = completed + métricas)  │
                                        └───────────────────────────────────────────────────────┘
                                                       │
                                                       ▼
                              GET /api/dashboard/summary   (somente leitura do banco;
                              o frontend faz polling até completed_at avançar)
```

### 5.2 Controle de concorrência e cooldown

Dois mecanismos independentes evitam varreduras redundantes e resultados duplicados:

**Trava de concorrência (`ScanService.run_scan`)**

```python
SCAN_LOCK_TIMEOUT_SECONDS = 600  # 10 minutos
```

Antes de iniciar, o serviço consulta o `scan_run` mais recente com `status = 'running'` para aquele site. Se existir e tiver começado há **menos de 600 segundos**, levanta `ScanInProgressError` e nada é executado. Se o registro for mais antigo que isso, ele é considerado abandonado (processo encerrado antes de concluir) e a nova varredura prossegue — assim uma falha travada não bloqueia o site permanentemente. A rota `POST /api/scan` faz a mesma verificação antes de agendar a tarefa e devolve `{"status": "already_running"}` para que a interface informe o usuário.

**Cooldown (`POST /api/scan`)**

Se já existe um scan concluído **e** o site já tem páginas registradas, uma nova varredura só é aceita **300 segundos (5 minutos)** após o `completed_at` do último scan. Dentro da janela, a resposta é `{"status": "cooldown", "seconds_until_next": N}`. O parâmetro `?force=true` ignora o cooldown (a trava de concorrência continua valendo). A interface usa `force=true` automaticamente quando ainda não há nenhuma página analisada.

**Limites de páginas por origem da chamada:** `POST /api/scan` usa 100; `POST /api/site-scan/{site_id}` usa `max_pages` ou o padrão `MAX_PAGES_PER_SCAN` (20); a varredura inicial disparada logo após conectar uma loja usa 30.

### 5.3 Crawler (`app/crawler.py`)

`crawl_site(url, max_pages)` executa:

1. **Normalização e sondagem de redirecionamento.** Garante o esquema `https://`, remove a barra final e segue o redirecionamento do domínio-base (por exemplo `http → https` ou inclusão de `www.`), atualizando `base_url` e `domain` para o destino final.
2. **Descoberta por sitemap.** Lê `/robots.txt` (diretivas `Sitemap:`) e tenta `/sitemap.xml`, `/sitemap_index.xml` e `/sitemap-index.xml`. Índices de sitemap são percorridos recursivamente até 3 níveis; cada arquivo é limitado a 5 MB. As URLs são normalizadas (sem fragmento, sem barra final, mesmo domínio) e filtradas.
3. **Filtros de URL.** Descarta extensões de mídia/estáticos (`.jpg`, `.pdf`, `.css`, `.js`, `.woff`, ...) e caminhos que não interessam ao SEO de catálogo (`/cart`, `/checkout`, `/account`, `/login`, `/admin`, `/api/`, `/wp-admin`, `/search`, `/busca`, `/wishlist`, `/order`, ...).
4. **Coleta.** O motor preferencial é o `BeautifulSoupCrawler` do Crawlee, usado quando a biblioteca está disponível no ambiente (concorrência 5, *timeout* de 15s por página). O motor padrão de produção é o **fallback próprio em `httpx` + BeautifulSoup**, que faz busca em largura a partir das URLs semente, com semáforo de 5 requisições simultâneas, ondas de 20 URLs por lote e enfileiramento dos links internos descobertos. Identificação: `User-Agent: SiteCan-SEO-Crawler/1.0`.
5. **Análise de cada página** via `analyze_seo_html`.
6. **Consolidação.** Devolve `pages_found`, `pages_crawled`, `pages_failed`, `pages_analyzed`, `average_score`, `total_issues`, `issues_summary` (contagem por tipo de problema), `duration_seconds` e a lista de páginas.

### 5.4 Análise de SEO (`app/seo_analysis.py`)

`analyze_seo_html(html, base_url, domain)` parte de **score 100** e subtrai a penalidade de cada problema detectado (piso 0). O catálogo `ISSUE_CONFIG` tem 18 códigos: 16 emitidos pelo analisador atual e 2 mantidos para leitura de dados históricos (`title_length` e `meta_description_length`, anteriores à separação entre "curto" e "longo").

| Código | Critério | Penalidade | Impacto |
|---|---|---|---|
| `noindex_detected` | `<meta name="robots">` contém `noindex` | 25 | alto |
| `missing_title` | sem `<title>` | 20 | alto |
| `missing_meta_description` | sem `<meta name="description">` | 15 | alto |
| `missing_h1` | nenhum `<h1>` | 15 | médio |
| `title_too_short` / `title_too_long` | título < 30 / > 60 caracteres | 8 | alto / médio |
| `missing_img_alt` | há `<img>` sem `alt` | 8 | baixo |
| `meta_description_short` / `meta_description_long` | descrição < 70 / > 160 caracteres | 5 | alto / médio |
| `multiple_h1` | mais de um `<h1>` | 5 | médio |
| `missing_canonical` | sem `<link rel="canonical">` | 5 | médio |
| `few_internal_links` | menos de 3 links internos | 5 | baixo |
| `missing_og_tags` | sem `og:title` **e** `og:description` | 5 | médio |
| `missing_schema` | sem `<script type="application/ld+json">` | 5 | médio |
| `missing_h2` | nenhum `<h2>` | 3 | baixo |
| `missing_og_image` | sem `og:image` | 3 | baixo |

Além das penalidades, o módulo publica `ISSUE_IMPACT` (alto/médio/baixo, usado nos filtros do Dashboard), `ISSUE_LABEL` (rótulo amigável) e a mensagem explicativa em português de cada problema. O retorno inclui os metadados extraídos (`title`, `meta_description`, `h1`, contagens de H2/imagens/links) e dois mapas de problemas: `issues` (apenas os presentes) e `all_issues` (todos os códigos avaliados).

### 5.5 Persistência do resultado

- **`pages`** — `upsert_page` grava/atualiza a linha por `(site_id, url)` com título, meta description, H1, o mapa `issues`, o `score` e `last_scanned_at`.
- **`seo_tasks`** — para cada problema presente, cria uma tarefa com `issue_type`, a mensagem padrão de `ISSUE_CONFIG` como `suggestion` inicial, `priority = "medium"` e `status = "pending"`. Antes do laço, o serviço carrega **uma vez** todas as tarefas pendentes do site e monta o conjunto de chaves `(page_id, issue_type)`; problemas que já têm tarefa pendente são ignorados, e as chaves recém-criadas entram no mesmo conjunto. Assim, re-executar a varredura não multiplica as oportunidades listadas.
- **`scan_runs`** — `complete_scan_run` fecha o registro com `pages_scanned`, `tasks_created`, `avg_score` e `issues_summary`. Se a coleta falhar, o registro é encerrado com zeros e `issues_summary = {"crawl_error": 1}`, para que o site nunca fique com uma execução pendurada.

### 5.6 Leitura pelo Dashboard

`GET /api/dashboard/summary` é **estritamente leitura do banco** — nunca dispara varredura. Ele combina o último `scan_run`, as páginas, as tarefas pendentes e (quando conectado) os dados do Google Search Console, produzindo: score médio, percentuais derivados (segurança, velocidade, visibilidade), potencial de crescimento, *checklist* de SEO com variação em relação ao scan anterior e a lista de oportunidades. O frontend dispara `POST /api/scan` e então faz *polling* de `summary` a cada 5 segundos (até ~2 minutos), detectando o término pela mudança de `last_scan.completed_at`.

---

## 6. Fluxo de otimização por IA

Existem dois caminhos de IA no produto, com propósitos distintos:

- **(A) Propostas de catálogo** — para itens de uma loja conectada (produto, categoria, página, artigo). São geradas, aprovadas, **aplicadas na plataforma** e podem ser revertidas.
- **(B) Sugestões de correção de página** — para as tarefas geradas pela varredura por URL. Produzem texto/HTML pronto para o usuário aplicar manualmente no seu tema/CMS (`POST /api/site-analyze/{site_id}`, `POST /api/generate-fix`, `POST /api/task-fix/{task_id}`, `POST /api/generate-all-fixes`), gravados em `seo_tasks.suggestion` com `ai_generated = true`.

O restante desta seção detalha o caminho (A), que é o fluxo principal do produto.

### 6.1 Etapas

```
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 1. ANÁLISE                                                                 │
 │    GET /api/{plataforma}/product/{id}/analyze                              │
 │    optimizer.analyze_product(...) → score, issues[], recommendations[]     │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 2. ENRIQUECIMENTO (antes de chamar a IA)                                   │
 │    • data_enrichment.enrich_product_context → atributos + segmento         │
 │    • SearchAPI.io  → palavras-chave de mercado + top 5 resultados da SERP  │
 │    • Google Search Console → cliques/impressões/CTR/posição da URL         │
 │      (guardados como `pre_metrics` na proposta)                            │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 3. GERAÇÃO                                                                 │
 │    POST /api/{plataforma}/product/{id}/optimize?target_keyword=…           │
 │    system prompt "Engenheiro de SEO Sênior" + payload de contexto          │
 │    → OpenAI Chat Completions (ai_config.completion_params)                 │
 │    → parse_ai_json → uma OptimizationProposal por campo                    │
 │    → ai_validation → bloco `transparencia` anexado a cada proposta         │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 4. REVISÃO DO USUÁRIO                                                      │
 │    POST …/proposals/approve   |   POST …/proposals/reject                  │
 │    Nada é escrito na loja enquanto não houver aprovação explícita.         │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 5. APLICAÇÃO                                                               │
 │    POST …/proposals/apply  (corpo: as propostas aprovadas)                 │
 │    agrupa por (content_type, id) → escreve na plataforma                   │
 │    → devolve rollback_records com o valor ORIGINAL de cada campo           │
 │    → incrementa metadata.applied_count em user_integrations                │
 │    → marca como `approved` as seo_tasks pendentes da página correspondente │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 6. ROLLBACK                                                                │
 │    GET …/rollback  |  POST …/rollback/direct  |  POST …/rollback/all       │
 │    reescreve o valor original na plataforma e marca o registro revertido   │
 └────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Análise do item

Cada optimizer implementa `analyze_product` / `analyze_category` (e, na Shopify e na Nuvemshop, também `analyze_page`, `analyze_collection`, `analyze_article`, `analyze_blog_post`). A análise é determinística — não usa IA — e devolve `score` (100 menos penalidades), `issues` (com `type`, `message` e `severity`) e `recommendations`. Os critérios respeitam as particularidades de cada plataforma; por exemplo, na VTEX o `Title` do produto é a *title tag*, `MetaTagDescription` é a meta description e a `Description` da categoria é o que a plataforma usa como meta description da página de categoria.

### 6.3 Enriquecimento do contexto (`app/data_enrichment.py`)

`enrich_product_context(product_data, user_id)` monta o payload que será entregue à IA:

- **`atributos_extraidos`** — atributos descritivos extraídos de tags, variantes, `product_type`/marca/material/cor/tamanho e categorias (com suporte a campos multilíngues), sem duplicatas, limitados a 15.
- **`segmento`** — segmento de mercado inferido por dicionário de termos (moda, casa, eletrônicos, esportes, beleza, alimentício, pet, infantil, móveis, joias; padrão `ecommerce`).
- **`keywords_mercado` e `serp_data`** — quando `SEARCHAPI_KEY` está configurada, consulta a SERP do Google via SearchAPI.io e extrai as palavras relevantes dos títulos dos concorrentes melhor posicionados.

Os optimizers ainda acrescentam, quando disponível, o bloco de desempenho atual da URL no Google Search Console; esses números são congelados na proposta em `pre_metrics`, permitindo comparar o antes e o depois.

### 6.4 Chamada de IA

- **Prompt de sistema.** Um único prompt "Engenheiro de SEO Sênior" (`SYSTEM_PROMPT_ECOMMERCE` / `SYSTEM_PROMPT_V2`) é compartilhado pelos otimizadores. Ele restringe o modelo a **reestruturar os dados recebidos** (proibindo inventar informação), define a estrutura de título de cauda longa (`[Categoria] + [Público] + [Produto] + [Atributos]`), impõe faixas de tamanho (título 50–60 caracteres; meta description 120–155 com CTA), veta clichês comerciais e **proíbe remover medidas, dimensões, links, telefones, especificações técnicas e informações de garantia/troca**. A resposta é sempre um JSON.
- **Compatibilidade de parâmetros (`app/ai_config.py`).** `AI_MODEL` (padrão `gpt-5-mini`) e `completion_params(...)` resolvem as diferenças entre famílias de modelos: modelos de raciocínio (`gpt-5*`, `o1`, `o3`, `o4`) recebem `max_completion_tokens` (com piso de 1024 tokens, para que os tokens de raciocínio não consumam todo o orçamento de saída) e `reasoning_effort` (padrão `minimal`), com `temperature` omitida; os demais modelos recebem `max_tokens` + `temperature`.
- **Parse tolerante (`parse_ai_json`).** Extrai o primeiro objeto JSON da resposta; em caso de resposta vazia, sem JSON ou com JSON malformado, registra aviso com um rótulo de contexto (por exemplo `"produto VTEX"`) e devolve `{}` — o endpoint responde uma lista vazia de propostas em vez de propagar uma falha opaca.
- **Ausência de chave da OpenAI.** Os otimizadores de plataforma retornam lista vazia com aviso em log; o caminho genérico (`llm_optimizer`) possui geradores de fallback sem IA, que produzem sugestões básicas a partir dos próprios dados da página.

### 6.5 A proposta

Cada campo sugerido vira uma `OptimizationProposal`:

| Campo | Descrição |
|---|---|
| `id`, `product_id`, `content_type` | Identificação da proposta e do item (`product`, `category`, `page`, `article`) |
| `optimization_type`, `field_name` | Campo alvo no vocabulário do produto (`name`, `seo_title`, `seo_description`, `tags`, `category_*`, ...) |
| `original_value`, `proposed_value` | Valor atual e valor sugerido |
| `reasoning` | Justificativa técnica da mudança |
| `status` | `pending` → `approved` → `applied` (ou `rejected`) |
| `priority`, `impact`, `effort` | Priorização devolvida pelo modelo |
| `target_keyword` | Palavra-chave alvo, quando informada |
| `pre_metrics` | Fotografia das métricas do GSC no momento da geração |
| `transparencia` | Resultado da validação pós-geração (abaixo) |

**Transparência (`app/ai_validation.py`).** Duas verificações determinísticas, sem chamada de IA, comparam título original e título sugerido: `validar_atributos_descritivos` identifica atributos que passaram a constar no título, e `calcular_cobertura_semantica` conta quantas palavras-chave estratégicas foram incorporadas (2 ou mais rendem o selo de melhor cobertura semântica). O resultado acompanha a proposta até a interface, para que o usuário entenda **o que** mudou e **por quê** antes de aprovar.

### 6.6 Aprovação e aplicação

A interface envia as propostas aprovadas **no corpo** da chamada de aplicação (`apply_proposals_direct`), tornando a operação independente do estado em memória do servidor. O client agrupa as propostas por `(content_type, id)` e executa **uma escrita por item**, o que reduz chamadas à plataforma e mantém a consistência do objeto:

| Plataforma | Escrita |
|---|---|
| Shopify | `PUT /products/{id}.json` (título, `body_html`, tags) + *metafields* `global.title_tag` / `global.description_tag`; `alt` de imagem por `PUT /products/{id}/images/{id}.json`; mesma mecânica para coleções, páginas e artigos |
| Nuvemshop | `PUT` do produto/categoria/página/post, com os campos de SEO próprios da plataforma |
| VTEX | *read-modify-write*: `GET` do objeto → merge dos campos mapeados (`Name`, `Title`, `Description`, `MetaTagDescription`, `KeyWords`, `LinkId`) → `PUT` do objeto completo |
| Loja Integrada | Fase 1: `PUT` da entidade (produto exige objeto completo; categoria aceita parcial). Fase 2: recurso de SEO (`/v1/seo/{id}`), criado sob demanda |

Para **cada campo efetivamente escrito** é criado um `RollbackRecord` contendo `original_value` (lido do estado anterior real, quando a plataforma o devolve), `new_value`, `applied_at`, `content_type` e `optimization_type`. Os registros voltam na resposta e são persistidos no `localStorage` pelo hook.

Depois de aplicar, o backend ainda:

- incrementa `metadata.applied_count` em `user_integrations` (contador de otimizações aplicadas que sobrevive a reinícios);
- executa `_mark_pages_optimized`: resolve a URL pública de cada item otimizado, localiza a página correspondente em `pages` (comparação normalizada, ignorando protocolo, `www.` e barra final) e marca as `seo_tasks` pendentes dessa página como `approved`, de forma que o Dashboard passe a exibi-la como otimizada. A operação é *best-effort*: qualquer falha é apenas registrada em log e não interrompe a aplicação.

### 6.7 Rollback

Três granularidades, disponíveis nas quatro plataformas:

- **`POST …/rollback/direct`** — recebe o registro de rollback vindo do frontend e reescreve o valor original no campo correspondente. É o caminho usado pela interface e não depende de estado em memória do servidor.
- **`POST …/rollback/{rollback_id}`** — reverte um registro mantido em memória pelo client.
- **`POST …/rollback/all`** — percorre todos os registros ainda não revertidos. (Na Shopify há também `POST …/rollback/product/{product_id}`.)

Ao reverter, o registro é marcado com `rolled_back = true` e `rolled_back_at`; o hook remove o item da lista local e regrava a lista persistida.

---

## 7. Modelo de dados

Fonte de verdade: **`supabase/schema.sql`**. São **10 tabelas** no schema `public`, todas com `row level security` habilitado. A tabela `auth.users` é gerenciada pelo próprio Supabase Auth e é referenciada por chave estrangeira com `on delete cascade` — excluir um usuário remove todos os seus dados.

Há dois padrões de propriedade (*ownership*):

- **Direto** — a tabela tem `user_id`, e as políticas comparam `auth.uid() = user_id`.
- **Indireto** — a tabela pertence a um site, e as políticas verificam a existência do site do usuário: `exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid())`.

| # | Tabela | Propósito | Colunas principais | Ownership / RLS |
|---|---|---|---|---|
| 1 | **`sites`** | Site/loja analisado. É a raiz do grafo de dados de análise: um usuário tem um site de integração (loja conectada) e, eventualmente, sites criados apenas para análise por URL. | `user_id`, `base_url`, `platform`, `store_id`, `store_name`, `created_at`, `updated_at` | **Direto.** Quatro políticas (`select`/`insert`/`update`/`delete`) sobre `auth.uid() = user_id`. `user_id → auth.users(id) on delete cascade`. |
| 2 | **`pages`** | Página descoberta e analisada pela varredura: metadados extraídos, mapa de problemas e score. Unicidade por `(site_id, url)` — a varredura faz *upsert*. | `site_id`, `url`, `title`, `meta_description`, `h1`, `issues` (jsonb), `score`, `last_scanned_at` | **Indireto por `sites.user_id`.** As quatro políticas usam o `exists` sobre `sites`. `site_id` em cascata a partir de `sites`. |
| 3 | **`seo_tasks`** | Oportunidade de SEO detectada em uma página (uma por problema). Guarda o tipo do problema, a sugestão (padrão ou gerada por IA) e o estado do fluxo de aprovação. | `site_id`, `page_id`, `issue_type`, `description`, `suggestion`, `priority`, `status` (`pending`/`approved`), `ai_generated`, `updated_at` | **Indireto por `sites.user_id`** (mesmo `exists` de `pages`). `page_id → pages(id) on delete cascade`. |
| 4 | **`scan_runs`** | Registro de execução de varredura: serve tanto de histórico (métricas por execução, comparação entre scans) quanto de **trava de concorrência** — um registro `running` recente bloqueia nova varredura do mesmo site. | `site_id`, `status` (`running`/`completed`), `started_at`, `completed_at`, `pages_scanned`, `tasks_created`, `avg_score`, `issues_summary` (jsonb) | **Indireto por `sites.user_id`.** Políticas de `select`, `insert` e `update` (não há política de `delete`: o histórico não é apagado pela aplicação). |
| 5 | **`user_integrations`** | Credenciais e metadados da loja conectada — **uma linha por usuário** (`user_id` com restrição `unique`, gravação por *upsert* com `on_conflict=user_id`). Permite reconstruir o client da plataforma após reinício do servidor e sobrevive a novos logins. | `user_id` (unique), `platform`, `store_url`, `access_token`, `store_name`, `metadata` (jsonb: `site_url`, `account_name`, `app_key`, `applied_count`, ...) | **Direto** (`auth.uid() = user_id`), com as quatro operações. Lida sempre pelo cliente autenticado como o usuário; a exclusão faz parte do *disconnect*. |
| 6 | **`oauth_states`** | `state` de OAuth persistido para sobreviver a reinícios do servidor entre o início da autorização e o *callback* da plataforma. Guarda o `user_id` e o token do usuário para reassociar a loja ao dono correto, com expiração de 10 minutos. | `state` (unique), `user_id`, `user_token`, `expires_at` | **Direto** (`auth.uid() = user_id`) para `select`, `insert` e `delete`. O *callback* chega sem sessão de navegador, então essa leitura específica é feita pelo backend com a chave de serviço; a expiração é verificada em código. |
| 7 | **`user_search_terms`** | Termos de pesquisa que o usuário acompanha na tela "Termos de Pesquisa". | `user_id`, `term`, `created_at` | **Direto** (`auth.uid() = user_id`) para `select`, `insert` e `delete`. |
| 8 | **`term_snapshots`** | Fotografia diária dos dados de um termo (interesse ao longo do tempo e consultas relacionadas), preservando a série histórica. | `term_id`, `user_id`, `interest_over_time` (jsonb), `related_queries` (jsonb), `date` | **Direto** (`auth.uid() = user_id`) para `select` e `insert`; além disso `term_id → user_search_terms(id) on delete cascade`, o que remove os *snapshots* junto com o termo. |
| 9 | **`daily_snapshots`** | Consolidação diária de desempenho orgânico (dados do Google Search Console) usada na tela "Histórico". Uma linha por usuário/dia — restrição `unique (user_id, date)` com gravação por *upsert*. | `user_id`, `date`, `impressions`, `clicks`, `ctr`, `position_avg`, `pages_count` | **Direto** (`auth.uid() = user_id`) para `select`, `insert` e `update`. |
| 10 | **`gsc_tokens`** | Tokens OAuth do Google Search Console por usuário (uma linha por usuário, `user_id` com `unique`), incluindo o `refresh_token` e a propriedade selecionada. | `user_id` (unique), `access_token`, `refresh_token`, `expires_at`, `site_url`, `updated_at` | **Direto** (`auth.uid() = user_id`) nas quatro operações. Na prática é acessada pelo backend com a chave de serviço (a renovação de token acontece fora do contexto de uma requisição do usuário); o RLS permanece habilitado como defesa em profundidade. |

### 7.1 Relações

```
auth.users (Supabase Auth)
   │ 1
   ├──── N  sites ───┬── N  pages ──── N  seo_tasks
   │                 ├── N  seo_tasks  (também ligadas diretamente ao site)
   │                 └── N  scan_runs
   ├──── 1  user_integrations      (unique user_id)
   ├──── 1  gsc_tokens             (unique user_id)
   ├──── N  oauth_states           (temporárias, expiram em 10 min)
   ├──── N  user_search_terms ──── N  term_snapshots
   └──── N  daily_snapshots        (unique user_id + date)
```

Todas as chaves estrangeiras para `auth.users` e para `sites` usam `on delete cascade`: remover um usuário elimina sites, páginas, tarefas, execuções de varredura, integrações, termos, *snapshots* e tokens; remover um site elimina suas páginas, tarefas e execuções.

### 7.2 Aplicação do schema

O arquivo `supabase/schema.sql` é aplicado uma única vez em um projeto Supabase vazio (Dashboard → SQL Editor → colar o arquivo → *Run*). Ele usa `create table` sem `if not exists`, ou seja, **não é idempotente**. A extensão `pgcrypto` é habilitada no início para o `gen_random_uuid()` usado como padrão das chaves primárias.

---

## 8. Configuração e implantação

### 8.1 Variáveis de ambiente

**Backend** (`backend/.env` ou variáveis do serviço):

| Variável | Função |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase (também usada para montar o endpoint JWKS) |
| `SUPABASE_SERVICE_KEY` | Chave de serviço — **ignora o RLS**; uso restrito a operações sem usuário no contexto |
| `SUPABASE_ANON_KEY` (ou `SUPABASE_KEY`) | Chave anônima usada em conjunto com o JWT do usuário para que o RLS seja aplicado |
| `SUPABASE_JWT_SECRET` | Segredo para validação de tokens `HS256` (modo legado) |
| `OPENAI_API_KEY` | Habilita a camada de IA; ausente, o produto opera com os fallbacks descritos na seção 6.4 |
| `AI_MODEL` | Modelo de geração (padrão `gpt-5-mini`) |
| `AI_REASONING_EFFORT` | Esforço de raciocínio para modelos da família GPT-5 (padrão `minimal`) |
| `VISION_MODEL` | Modelo com visão para geração de texto alternativo de imagens (padrão `gpt-4o`) |
| `SEARCHAPI_KEY` | SearchAPI.io — tendências de busca e resultados de SERP |
| `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`, `GSC_REDIRECT_URI` | Credenciais OAuth do Google Search Console |
| `NUVEMSHOP_APP_ID`, `NUVEMSHOP_CLIENT_SECRET` | Credenciais da aplicação na Nuvemshop |
| `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET` | Credenciais OAuth do app 4SEO no Shopify Partners |
| `LOJAINTEGRADA_APP_KEY` | Chave de aplicação (integrador) da Loja Integrada |
| `CORS_ORIGINS` | Origens extras permitidas, separadas por vírgula |
| `MAX_PAGES_PER_SCAN` | Limite padrão de páginas por varredura (padrão `20`) |
| `BACKEND_URL`, `FRONTEND_URL` | URLs públicas usadas para montar *callbacks* e redirecionamentos de OAuth |

**Frontend** (prefixo `VITE_`, embutidas no build):

| Variável | Função |
|---|---|
| `VITE_SUPABASE_URL` | URL do projeto Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Chave pública (anon) usada pelo SDK no navegador |
| `VITE_API_BASE_URL` | Base das chamadas de API (padrão `/api`) |
| `VITE_AUTH_REDIRECT_URL` | URL de retorno de confirmação de cadastro e recuperação de senha |

> **Credenciais.** Todos os valores acima devem ser fornecidos por variável de ambiente no serviço de hospedagem, e não versionados no repositório. Atenção: o código ainda mantém alguns valores embutidos como padrão de fallback — notadamente o segredo de aplicação da Nuvemshop em `backend/app/integrations/nuvemshop.py`. Recomenda-se rotacioná-lo e passar a lê-lo exclusivamente de variável de ambiente. As chaves de serviço (`SUPABASE_SERVICE_KEY`) e os segredos de aplicação (`NUVEMSHOP_CLIENT_SECRET`, `GSC_CLIENT_SECRET`, `LOJAINTEGRADA_APP_KEY`, `OPENAI_API_KEY`) são exclusivamente do servidor — apenas as variáveis com prefixo `VITE_` chegam ao navegador.

### 8.2 Execução e build

- **Desenvolvimento.** Backend: `uvicorn app.main:app --reload` na porta 8000. Frontend: `npm run dev` na porta 8080, com proxy de `/api` para `http://localhost:8000` (`vite.config.ts`).
- **Build do frontend.** `npm run build` → `dist/`. A hospedagem estática (Netlify) serve o conteúdo de `dist/` e reescreve todas as rotas para `index.html`, conforme `public/_redirects`, permitindo que o roteamento do SPA funcione em links diretos. Não há reescrita de `/api`: as chamadas à API vão direto para a URL definida em `VITE_API_BASE_URL`, e por isso o backend precisa liberar o domínio do frontend em `CORS_ORIGINS`.
- **Backend em produção.** Serviço web Python 3.11 com `pip install -r requirements.txt` e `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (`backend/render.yaml`, `backend/runtime.txt`).
- **Dependências principais do backend.** `fastapi`, `uvicorn`, `httpx`, `beautifulsoup4`, `lxml`, `pydantic`, `openai`, `PyJWT`, `python-dotenv`, `google-api-python-client`, `google-auth-oauthlib`.
- **Testes.** Backend: `pytest` (suítes em `backend/tests/`, cobrindo serviços, análise de SEO, rollback, integrações e desconexão). Frontend: `npm test` (Vitest).

### 8.3 Notas operacionais

- O backend é **sem estado no que diz respeito a dados do usuário**: propostas e registros de rollback mantidos em memória são apenas cache; os caminhos usados pela interface (`apply_proposals_direct`, `rollback_direct`) transportam os dados necessários na requisição, e os hooks persistem os registros de rollback no navegador. Um reinício do processo não perde dados de negócio, que vivem no Supabase e nas próprias plataformas.
- Varreduras disparadas pelo Dashboard rodam em segundo plano (`asyncio.create_task`) e são observadas por *polling* — o cliente nunca fica bloqueado esperando a coleta terminar.
- Os limites de taxa das plataformas são absorvidos pelos clients (backoff em 429) e, no caso de estouro, transformados em mensagens acionáveis pela camada `useApiError` do frontend.