"""
Testes das integrações VTEX e Loja Integrada (clients + optimizers).

Cobrem os comportamentos das APIs verificados nas fontes oficiais
(ver docs/INTEGRATIONS.md):
- VTEX: headers X-VTEX-API-AppKey/AppToken, base URL por conta, read-modify-write
  de produto/categoria (strip de campos read-only), retry em 429 com Retry-After.
- Loja Integrada: header Authorization exato, base https://api.awsli.com.br/v1,
  paginação TastyPie, GET produto sempre com descricao_completa=1, SEO como
  recurso separado (/v1/seo), PUT completo de produto.
- Optimizers: degradação graciosa sem OPENAI_API_KEY, propostas com transparência.
"""
import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.vtex import (
    VtexClient,
    VtexAuthError,
    VtexNotFoundError,
    VTEX_PRODUCT_FIELD_MAP,
    VTEX_CATEGORY_FIELD_MAP,
)
from app.integrations.lojaintegrada import (
    LojaIntegradaClient,
    LojaIntegradaAuthError,
    LojaIntegradaNotFoundError,
    _parse_resource_id,
)


# ==================== VTEX CLIENT ====================

class TestVtexClient:

    def test_base_url_and_headers(self):
        """Base URL por conta e headers de auth exatos (doc oficial)"""
        client = VtexClient("MinhaLoja", "key-123", "token-456")
        assert client.base_url == "https://minhaloja.vtexcommercestable.com.br"
        assert client.headers["X-VTEX-API-AppKey"] == "key-123"
        assert client.headers["X-VTEX-API-AppToken"] == "token-456"

    @pytest.mark.asyncio
    async def test_update_product_read_modify_write(self):
        """PUT de produto envia o objeto COMPLETO mesclado, sem o Id no body"""
        client = VtexClient("loja", "k", "t")
        raw = {
            "Id": 42, "Name": "Produto Antigo", "CategoryId": 7, "BrandId": 3,
            "Title": "Titulo Antigo", "Description": "Desc", "MetaTagDescription": "Meta antiga",
            "KeyWords": "a,b", "LinkId": "produto-antigo", "IsActive": True, "IsVisible": True,
        }
        calls = []

        async def fake_request(method, endpoint, data=None, params=None, **kw):
            calls.append((method, endpoint, data))
            if method == "GET":
                return dict(raw)
            return {}

        client._request = fake_request
        result = await client.update_product_fields(42, {"Title": "Novo Titulo", "MetaTagDescription": "Nova meta"})

        assert result["updated"] is True
        assert result["original"] == {"Title": "Titulo Antigo", "MetaTagDescription": "Meta antiga"}
        put = [c for c in calls if c[0] == "PUT"][0]
        assert put[1] == "/api/catalog/pvt/product/42"
        body = put[2]
        # Campos alterados aplicados
        assert body["Title"] == "Novo Titulo"
        assert body["MetaTagDescription"] == "Nova meta"
        # Campos não alterados preservados (read-modify-write)
        assert body["Name"] == "Produto Antigo"
        assert body["CategoryId"] == 7
        assert body["BrandId"] == 3
        # Id não vai no body (vai no path)
        assert "Id" not in body

    @pytest.mark.asyncio
    async def test_update_product_rejects_non_seo_fields(self):
        """Campos fora da whitelist de SEO não são aplicados"""
        client = VtexClient("loja", "k", "t")
        client._request = AsyncMock(return_value={"Id": 1, "Name": "X"})
        result = await client.update_product_fields(1, {"IsActive": False, "CategoryId": 999})
        assert result["updated"] is False
        # Nenhum PUT deve ter sido feito
        put_calls = [c for c in client._request.call_args_list if c.args and c.args[0] == "PUT"]
        assert not put_calls

    @pytest.mark.asyncio
    async def test_update_category_strips_readonly_fields(self):
        """PUT de categoria remove campos read-only do GET (confirmado no OpenAPI)"""
        client = VtexClient("loja", "k", "t")
        raw = {
            "Id": 9, "Name": "Acessorios", "Title": "Acessorios | Loja",
            "Description": "Meta da categoria", "Keywords": "acessorios",
            "FatherCategoryId": 1, "IsActive": True, "GlobalCategoryId": 166,
            "LinkId": "acessorios", "HasChildren": True,
            "TreePath": ["A"], "TreePathIds": [1], "TreePathLinkIds": ["a"],
        }
        calls = []

        async def fake_request(method, endpoint, data=None, params=None, **kw):
            calls.append((method, endpoint, data))
            if method == "GET":
                return dict(raw)
            return {}

        client._request = fake_request
        await client.update_category_fields(9, {"Title": "Novo Title"})

        body = [c for c in calls if c[0] == "PUT"][0][2]
        assert body["Title"] == "Novo Title"
        assert body["Name"] == "Acessorios"
        for readonly in ("Id", "LinkId", "HasChildren", "TreePath", "TreePathIds", "TreePathLinkIds"):
            assert readonly not in body

    @pytest.mark.asyncio
    async def test_429_retry_honors_retry_after(self):
        """429 -> aguarda Retry-After e tenta de novo"""
        resp_429 = MagicMock(status_code=429, headers={"Retry-After": "1"}, text="rate limited")
        resp_200 = MagicMock(status_code=200, text='{"ok": true}')
        resp_200.json.return_value = {"ok": True}

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=[resp_429, resp_200])
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        client = VtexClient("loja", "k", "t")
        with patch("app.integrations.vtex.httpx.AsyncClient", return_value=mock_http):
            with patch("app.integrations.vtex.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await client._request("GET", "/api/x")

        assert result == {"ok": True}
        mock_sleep.assert_awaited_once()
        assert mock_sleep.await_args.args[0] == 1.0

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        """401/403 viram VtexAuthError com mensagem em pt-BR"""
        resp_401 = MagicMock(status_code=401, headers={}, text="unauthorized")
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp_401)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        client = VtexClient("loja", "k", "t")
        with patch("app.integrations.vtex.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(VtexAuthError):
                await client._request("GET", "/api/x")

    @pytest.mark.asyncio
    async def test_404_raises_not_found_error(self):
        """404 vira VtexNotFoundError (não Exception genérica) para virar HTTP 404 na rota"""
        resp_404 = MagicMock(status_code=404, headers={}, text="not found")
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp_404)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        client = VtexClient("loja", "k", "t")
        with patch("app.integrations.vtex.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(VtexNotFoundError):
                await client._request("GET", "/api/catalog/pvt/product/999999")

    def test_field_maps_cover_optimizer_outputs(self):
        """Todos os optimization_types emitidos pelo optimizer têm mapeamento de campo"""
        for ot in ("name", "description", "seo_title", "seo_description", "tags"):
            assert ot in VTEX_PRODUCT_FIELD_MAP
        for ot in ("category_name", "category_seo_title", "category_seo_description", "category_keywords"):
            assert ot in VTEX_CATEGORY_FIELD_MAP
        # Categoria VTEX não tem MetaTagDescription: seo_description -> Description
        assert VTEX_CATEGORY_FIELD_MAP["category_seo_description"] == "Description"
        # KeyWords com K e W maiúsculos (case exato da API)
        assert VTEX_PRODUCT_FIELD_MAP["tags"] == "KeyWords"

    @pytest.mark.asyncio
    async def test_rollback_direct_routes_to_product(self):
        """rollback_direct de produto usa update_product_fields com o valor original"""
        client = VtexClient("loja", "k", "t")
        client.update_product_fields = AsyncMock(return_value={"original": {}, "updated": True})
        result = await client.rollback_direct({
            "content_type": "product", "product_id": 5,
            "optimization_type": "seo_title", "field_name": "seo_title",
            "original_value": "Titulo original",
        })
        client.update_product_fields.assert_awaited_once_with(5, {"Title": "Titulo original"})
        assert result["rolled_back"] == 1


# ==================== LOJA INTEGRADA CLIENT ====================

class TestLojaIntegradaClient:

    def test_auth_header_exact_format(self):
        """Header exato: 'Authorization: chave_api {X} aplicacao {Y}' (doc oficial)"""
        client = LojaIntegradaClient("minha-chave-api", "minha-chave-app")
        assert client.headers["Authorization"] == "chave_api minha-chave-api aplicacao minha-chave-app"
        assert client.base_url == "https://api.awsli.com.br/v1"

    def test_parse_resource_id(self):
        """Resource URIs TastyPie -> id; '/seo/None' -> None"""
        assert _parse_resource_id("/api/v1/seo/123") == 123
        assert _parse_resource_id("/api/v1/seo/123/") == 123
        assert _parse_resource_id("/api/v1/seo/None") is None
        assert _parse_resource_id(None) is None
        assert _parse_resource_id("") is None

    @pytest.mark.asyncio
    async def test_pagination_follows_meta_next(self):
        """Paginação TastyPie: segue meta.next até o fim"""
        client = LojaIntegradaClient("chave", "app")
        pages = [
            {"meta": {"limit": 2, "offset": 0, "next": "/v1/produto/?offset=2", "total_count": 3},
             "objects": [{"id": 1, "nome": "P1"}, {"id": 2, "nome": "P2"}]},
            {"meta": {"limit": 2, "offset": 2, "next": None, "total_count": 3},
             "objects": [{"id": 3, "nome": "P3"}]},
        ]
        client._request = AsyncMock(side_effect=pages)
        items = await client._list_paginated("/produto/", max_items=10)
        assert [i["id"] for i in items] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_produto_raw_always_requests_full_description(self):
        """GET de produto SEMPRE envia descricao_completa=1 (senão o PUT completo apagaria a descrição)"""
        client = LojaIntegradaClient("chave", "app")
        client._request = AsyncMock(return_value={"id": 1, "nome": "P"})
        await client.get_produto_raw(1)
        _, kwargs = client._request.call_args
        assert kwargs.get("params", {}).get("descricao_completa") == 1

    @pytest.mark.asyncio
    async def test_update_produto_full_put_strips_readonly(self):
        """PUT de produto envia objeto completo mesclado, sem campos read-only/computados"""
        client = LojaIntegradaClient("chave", "app")
        raw = {
            "id": 10, "nome": "Nome Antigo", "apelido": "nome-antigo",
            "descricao_completa": "Descricao antiga", "ativo": True,
            "categorias": ["/api/v1/categoria/1"], "marca": None, "pai": None,
            "resource_uri": "/api/v1/produto/10/", "url": "https://loja.com/p",
            "imagem_principal": {"id": 1}, "imagens": [], "filhos": [], "grades": [],
            "variacoes": [], "seo": "/api/v1/seo/5",
            "data_criacao": "2024-01-01", "data_modificacao": "2024-01-02",
        }
        calls = []

        async def fake_request(method, endpoint, data=None, params=None, **kw):
            calls.append((method, endpoint, data))
            if method == "GET":
                return dict(raw)
            return {}

        client._request = fake_request
        result = await client.update_produto_fields(10, {"nome": "Nome Novo"})

        assert result["original"] == {"nome": "Nome Antigo"}
        body = [c for c in calls if c[0] == "PUT"][0][2]
        assert body["nome"] == "Nome Novo"
        # Objeto completo: campos editáveis/relacionais preservados
        assert body["descricao_completa"] == "Descricao antiga"
        assert body["categorias"] == ["/api/v1/categoria/1"]
        # Read-only/computados removidos
        for readonly in ("resource_uri", "url", "imagem_principal", "imagens", "seo",
                         "data_criacao", "data_modificacao", "id"):
            assert readonly not in body

    @pytest.mark.asyncio
    async def test_update_seo_partial_put(self):
        """PUT /v1/seo aceita body parcial só com title/keyword/description"""
        client = LojaIntegradaClient("chave", "app")
        client._request = AsyncMock(return_value={})
        await client.update_seo(5, {"title": "Novo", "invalido": "x"})
        args, kwargs = client._request.call_args
        assert args[0] == "PUT"
        assert args[1] == "/seo/5/"
        assert kwargs["data"] == {"title": "Novo"}

    @pytest.mark.asyncio
    async def test_apply_group_seo_fields_via_seo_resource(self):
        """Propostas de seo_title/seo_description são aplicadas via recurso /v1/seo"""
        from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus
        client = LojaIntegradaClient("chave", "app")
        client.ensure_product_seo = AsyncMock(return_value=77)
        client.get_seo = AsyncMock(return_value={"title": "Antigo", "description": "Meta antiga", "keyword": ""})
        client.update_seo = AsyncMock(return_value={})

        proposal = OptimizationProposal(
            id="abc123", product_id=10, optimization_type="seo_title", field_name="seo_title",
            original_value="Antigo", proposed_value="Novo Titulo SEO", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="product",
        )
        result = await client._apply_group("product", 10, [proposal])

        client.update_seo.assert_awaited_once_with(77, {"title": "Novo Titulo SEO"})
        assert result["applied"] == 1
        assert len(result["rollback_records"]) == 1
        rec = result["rollback_records"][0]
        assert rec["original_value"] == "Antigo"
        assert rec["optimization_type"] == "seo_title"

    @pytest.mark.asyncio
    async def test_401_raises_auth_error_with_plan_hint(self):
        """401 vira LojaIntegradaAuthError citando a restrição de plano grátis"""
        resp_401 = MagicMock(status_code=401, headers={}, text="unauthorized")
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp_401)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        client = LojaIntegradaClient("chave", "app")
        with patch("app.integrations.lojaintegrada.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(LojaIntegradaAuthError) as exc:
                await client._request("GET", "/categoria/")
        assert "plano" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_404_raises_not_found_error(self):
        """404 vira LojaIntegradaNotFoundError (não Exception genérica) para virar HTTP 404 na rota"""
        resp_404 = MagicMock(status_code=404, headers={}, text="not found")
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp_404)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        client = LojaIntegradaClient("chave", "app")
        with patch("app.integrations.lojaintegrada.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(LojaIntegradaNotFoundError):
                await client._request("GET", "/produto/999999/")


# ==================== OPTIMIZERS ====================

def _mock_ai_response(payload: dict):
    """Monta resposta fake da OpenAI com JSON no content"""
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestVtexOptimizer:

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_api_key(self):
        """Sem OPENAI_API_KEY: retorna [] sem crash (regra de ouro)"""
        from app.integrations.vtex_optimizer import VtexSEOOptimizer
        client = VtexClient("loja", "k", "t")
        optimizer = VtexSEOOptimizer(client)
        optimizer.ai_client = None
        result = await optimizer.optimize_product(1)
        assert result == []
        result = await optimizer.optimize_category(1)
        assert result == []

    @pytest.mark.asyncio
    async def test_optimize_product_generates_proposals_with_transparencia(self):
        """Propostas geradas com transparencia e cacheadas no client"""
        from app.integrations.vtex_optimizer import VtexSEOOptimizer
        from app.integrations.vtex import VtexProduct

        client = VtexClient("loja", "k", "t")
        optimizer = VtexSEOOptimizer(client)

        product = VtexProduct(id=1, name="Sandalia Malu", title=None, description="Uma sandalia",
                              seo_description=None, keywords=None, url="https://loja/s/p")
        client.get_product = AsyncMock(return_value=product)
        optimizer._fetch_serp_context = AsyncMock(return_value="")

        ai_payload = {
            "seo_title": {"value": "Sandalia Feminina Malu em Couro Caramelo", "reasoning": "cauda longa",
                          "priority": "high", "impact": "ranking", "effort": "low"},
        }
        optimizer.ai_client = MagicMock()
        optimizer.ai_client.chat.completions.create = AsyncMock(return_value=_mock_ai_response(ai_payload))

        with patch("app.data_enrichment.enrich_product_context", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {
                "atributos_extraidos": ["Couro", "Caramelo", "Feminina"],
                "keywords_mercado": ["sandalia feminina", "couro caramelo"],
                "segmento": "Moda",
            }
            proposals = await optimizer.optimize_product(1)

        assert len(proposals) == 1
        p = proposals[0]
        assert p.optimization_type == "seo_title"
        assert p.content_type == "product"
        assert p.priority == "high"
        # Transparência populada pela validação pós-IA
        assert p.transparencia is not None
        assert p.transparencia["atributos"]["status"] == "atributos_identificados"
        assert p.transparencia["semantica"]["total"] >= 2
        # Proposta cacheada no client (padrão dos demais otimizadores)
        assert p.id in client._proposals


class TestLojaIntegradaOptimizer:

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_api_key(self):
        """Sem OPENAI_API_KEY: retorna [] sem crash (regra de ouro)"""
        from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer
        client = LojaIntegradaClient("chave", "app")
        optimizer = LojaIntegradaSEOOptimizer(client)
        optimizer.ai_client = None
        assert await optimizer.optimize_product(1) == []
        assert await optimizer.optimize_category(1) == []

    @pytest.mark.asyncio
    async def test_optimize_product_generates_proposals(self):
        """Propostas de produto LI com campos SEO do recurso /seo"""
        from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer
        from app.integrations.lojaintegrada import LojaIntegradaProduct

        client = LojaIntegradaClient("chave", "app")
        optimizer = LojaIntegradaSEOOptimizer(client)

        product = LojaIntegradaProduct(id=10, name="Tenis Runner", description="Tenis de corrida",
                                       seo_title=None, seo_description=None, seo_id=5,
                                       url="https://loja.com.br/tenis-runner")
        client.get_product = AsyncMock(return_value=product)
        optimizer._fetch_serp_context = AsyncMock(return_value="")

        ai_payload = {
            "seo_title": {"value": "Tenis de Corrida Masculino Runner Amortecimento", "reasoning": "r",
                          "priority": "high", "impact": "ctr", "effort": "low"},
            "seo_description": {"value": "Tenis de corrida com amortecimento. Compre online.", "reasoning": "r",
                                "priority": "medium", "impact": "ctr", "effort": "low"},
        }
        optimizer.ai_client = MagicMock()
        optimizer.ai_client.chat.completions.create = AsyncMock(return_value=_mock_ai_response(ai_payload))

        with patch("app.data_enrichment.enrich_product_context", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"atributos_extraidos": [], "keywords_mercado": [], "segmento": ""}
            proposals = await optimizer.optimize_product(10)

        assert len(proposals) == 2
        types = {p.optimization_type for p in proposals}
        assert types == {"seo_title", "seo_description"}
        for p in proposals:
            assert p.content_type == "product"
            assert p.id in client._proposals


# ==================== REGRESSÃO: rollback de categoria (VTEX / Loja Integrada) ====================
#
# Bug: RollbackRecord não carregava optimization_type — apenas field_name (bare,
# ex. "seo_title"). Para categorias, os mapas de campo só têm chaves PREFIXADAS
# (ex. "category_seo_title"), então rollback_single/rollback_direct caíam no
# fallback field_name bare, que não resolve, e o rollback sempre falhava
# (ValueError "Campo desconhecido") — a alteração ficava aplicada na loja real
# sem nenhuma forma de reverter pela UI.

class TestVtexCategoryRollbackRegression:

    @pytest.mark.asyncio
    async def test_apply_then_rollback_category_roundtrip(self):
        from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

        client = VtexClient("loja", "k", "t")
        client.update_category_fields = AsyncMock(
            return_value={"original": {"Title": "Titulo Antigo"}, "updated": True}
        )

        proposal = OptimizationProposal(
            id="p1", product_id=99, optimization_type="category_seo_title", field_name="seo_title",
            original_value="Titulo Antigo", proposed_value="Titulo Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="category",
        )
        result = await client._apply_group("category", 99, [proposal])

        assert result["applied"] == 1
        rollback_id = result["rollback_records"][0]["id"]
        # O registro persistido precisa carregar optimization_type (prefixado) —
        # sem isso, o rollback abaixo cai no fallback bare e falha.
        assert client._rollback_records[rollback_id].optimization_type == "category_seo_title"

        # Reverter não deve levantar ValueError ("Campo desconhecido para rollback")
        rollback_result = await client.rollback_single(rollback_id)
        assert rollback_result["rolled_back"] == 1
        client.update_category_fields.assert_awaited_with(99, {"Title": "Titulo Antigo"})


class TestLojaIntegradaCategoryRollbackRegression:

    @pytest.mark.asyncio
    async def test_apply_then_rollback_category_roundtrip(self):
        from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

        client = LojaIntegradaClient("chave", "app")
        client.ensure_category_seo = AsyncMock(return_value=42)
        client.get_seo = AsyncMock(return_value={"title": "Titulo Antigo", "description": "", "keyword": ""})
        client.update_seo = AsyncMock(return_value={})

        proposal = OptimizationProposal(
            id="p1", product_id=7, optimization_type="category_seo_title", field_name="seo_title",
            original_value="Titulo Antigo", proposed_value="Titulo Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="category",
        )
        result = await client._apply_group("category", 7, [proposal])

        assert result["applied"] == 1
        rollback_id = result["rollback_records"][0]["id"]
        assert client._rollback_records[rollback_id].optimization_type == "category_seo_title"

        rollback_result = await client.rollback_single(rollback_id)
        assert rollback_result["rolled_back"] == 1
        # update_seo deve ser chamado de novo, agora com o valor original
        assert client.update_seo.await_args_list[-1].args == (42, {"title": "Titulo Antigo"})


# ==================== REGRESSÃO: apply parcial não perde rollback (Loja Integrada) ====================
#
# Contexto: quando um grupo tinha proposta de ENTIDADE (nome/
# descrição) E de SEO para o MESMO produto/categoria, o PUT de entidade era
# aplicado de verdade na loja e só DEPOIS o código tentava resolver/criar o
# registro de SEO — se isso falhasse (ensure_*_seo pode legitimamente
# retornar None; a criação de SEO é best-effort/não documentada), a exceção
# subia ANTES do loop que cria RollbackRecord e marca status=APPLIED, então
# a mudança de entidade ficava aplicada na loja real sem NENHUMA forma de
# reverter pela UI e sem a proposta refletir que foi aplicada.

class TestLojaIntegradaPartialApplyRegression:

    @pytest.mark.asyncio
    async def test_entity_change_keeps_rollback_when_seo_step_fails_after(self):
        from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

        client = LojaIntegradaClient("chave", "app")
        client.update_produto_fields = AsyncMock(
            return_value={"original": {"nome": "Nome Antigo"}, "updated": True}
        )
        # Falha ao resolver/criar o registro de SEO (cenário real e plausível)
        client.ensure_product_seo = AsyncMock(return_value=None)

        entity_proposal = OptimizationProposal(
            id="p1", product_id=10, optimization_type="name", field_name="name",
            original_value="Nome Antigo", proposed_value="Nome Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="product",
        )
        seo_proposal = OptimizationProposal(
            id="p2", product_id=10, optimization_type="seo_title", field_name="seo_title",
            original_value="SEO Antigo", proposed_value="SEO Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="product",
        )

        with pytest.raises(ValueError, match="registro de SEO"):
            await client._apply_group("product", 10, [entity_proposal, seo_proposal])

        # A mudança de ENTIDADE (nome) já foi de fato aplicada (PUT real) —
        # ela precisa continuar rollback-ável e marcada como aplicada, mesmo
        # a etapa de SEO tendo falhado depois.
        client.update_produto_fields.assert_awaited_once()
        assert entity_proposal.status == OptimizationStatus.APPLIED
        assert len(client._rollback_records) == 1
        rollback = list(client._rollback_records.values())[0]
        assert rollback.field_name == "name"
        assert rollback.original_value == "Nome Antigo"

        # A proposta de SEO, essa sim, não foi aplicada (a etapa falhou antes
        # de qualquer PUT de SEO) — não deve ter status/registro de rollback.
        assert seo_proposal.status == OptimizationStatus.APPROVED

    @pytest.mark.asyncio
    async def test_both_phases_succeed_creates_two_rollback_records(self):
        from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

        client = LojaIntegradaClient("chave", "app")
        client.update_produto_fields = AsyncMock(
            return_value={"original": {"nome": "Nome Antigo"}, "updated": True}
        )
        client.ensure_product_seo = AsyncMock(return_value=42)
        client.get_seo = AsyncMock(return_value={"title": "SEO Antigo"})
        client.update_seo = AsyncMock(return_value={})

        entity_proposal = OptimizationProposal(
            id="p1", product_id=10, optimization_type="name", field_name="name",
            original_value="Nome Antigo", proposed_value="Nome Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="product",
        )
        seo_proposal = OptimizationProposal(
            id="p2", product_id=10, optimization_type="seo_title", field_name="seo_title",
            original_value="SEO Antigo", proposed_value="SEO Novo", reasoning="r",
            status=OptimizationStatus.APPROVED, created_at="2026-01-01T00:00:00",
            content_type="product",
        )

        result = await client._apply_group("product", 10, [entity_proposal, seo_proposal])

        assert result["applied"] == 2
        assert entity_proposal.status == OptimizationStatus.APPLIED
        assert seo_proposal.status == OptimizationStatus.APPLIED
        assert len(client._rollback_records) == 2


# ==================== REGRESSÃO: isolamento por usuário no cache Shopify ====================
#
# Bug: _shopify_clients (main.py) nunca guardava nem validava user_id — diferente
# de Nuvemshop/VTEX/Loja Integrada. Qualquer usuário autenticado que soubesse o
# shop_url (não é segredo) de OUTRO usuário conseguia reusar o client cacheado
# (com access_token real) e ler/escrever na loja alheia.

class TestShopifyClientIsolationRegression:

    def setup_method(self):
        # Isola o cache global entre testes (evita vazamento de estado entre casos)
        from app.main import _shopify_clients
        self._cache = _shopify_clients
        self._cache.clear()

    def teardown_method(self):
        self._cache.clear()

    @pytest.mark.asyncio
    async def test_cache_hit_denies_other_user(self):
        from app.main import get_or_restore_shopify_client, set_shopify_client

        fake_client = MagicMock()
        fake_optimizer = MagicMock()
        set_shopify_client("https://lojaa.myshopify.com", fake_client, fake_optimizer, "user-A")

        # Usuário B (autenticado, mas sem relação com essa loja) tenta acessar
        # o mesmo shop_url — não deve receber o client de A.
        result = await get_or_restore_shopify_client(
            "https://lojaa.myshopify.com", {"user_id": "user-B", "token": "tok-b"}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_allows_owner(self):
        from app.main import get_or_restore_shopify_client, set_shopify_client

        fake_client = MagicMock()
        fake_optimizer = MagicMock()
        set_shopify_client("https://lojaa.myshopify.com", fake_client, fake_optimizer, "user-A")

        result = await get_or_restore_shopify_client(
            "https://lojaa.myshopify.com", {"user_id": "user-A", "token": "tok-a"}
        )
        assert result is not None
        assert result["client"] is fake_client


# ==================== REGRESSÃO: race condition em ensure_*_seo (Loja Integrada) ====================
#
# Contexto: duas chamadas concorrentes de ensure_product_seo/
# ensure_category_seo para o MESMO produto/categoria (ex.: duplo clique em
# "Aplicar", ou duas abas) podiam ambas ver "sem SEO ainda" e criar um
# registro de SEO cada uma — uma das alterações aplicadas pelo usuário
# ficava gravada num registro órfão e era silenciosamente perdida.

class TestLojaIntegradaSeoLockRegression:

    @pytest.mark.asyncio
    async def test_concurrent_calls_for_same_product_are_serialized(self):
        client = LojaIntegradaClient("chave", "app")
        call_order = []

        async def fake_get_produto_raw(product_id):
            call_order.append(("get", product_id))
            await asyncio.sleep(0.01)  # simula I/O de rede
            return {"id": product_id, "seo": None}

        async def fake_create_seo(base_uri):
            call_order.append(("create", base_uri))
            await asyncio.sleep(0.01)
            return 999

        client.get_produto_raw = fake_get_produto_raw
        client._create_seo = fake_create_seo

        results = await asyncio.gather(
            client.ensure_product_seo(1),
            client.ensure_product_seo(1),
        )

        assert results == [999, 999]
        # Sem o lock, as duas chamadas "get" aconteceriam ANTES de qualquer
        # "create" (interleaved) — cada uma veria "sem SEO" e criaria um
        # registro. Com o lock, a 2ª chamada só começa depois que a 1ª
        # terminou (get -> create) por completo.
        assert call_order == [
            ("get", 1), ("create", "/api/v1/produto/1"),
            ("get", 1), ("create", "/api/v1/produto/1"),
        ]

    @pytest.mark.asyncio
    async def test_concurrent_calls_for_different_products_are_not_serialized(self):
        client = LojaIntegradaClient("chave", "app")
        order = []

        async def fake_get_produto_raw(product_id):
            order.append(f"start:{product_id}")
            await asyncio.sleep(0.02)
            order.append(f"end:{product_id}")
            return {"id": product_id, "seo": "/api/v1/seo/5"}

        client.get_produto_raw = fake_get_produto_raw

        await asyncio.gather(client.ensure_product_seo(1), client.ensure_product_seo(2))

        # Produtos diferentes usam locks independentes — a execução é
        # concorrente de verdade (ambos "start" antes de qualquer "end").
        assert order[0].startswith("start:") and order[1].startswith("start:")

    @pytest.mark.asyncio
    async def test_category_lock_is_independent_from_product_lock(self):
        client = LojaIntegradaClient("chave", "app")
        client.get_produto_raw = AsyncMock(return_value={"id": 1, "seo": "/api/v1/seo/1"})
        client._request = AsyncMock(return_value={"id": 1, "seo": "/api/v1/seo/2"})

        # Não deve haver deadlock nem interferência entre locks de produto e categoria
        results = await asyncio.gather(
            client.ensure_product_seo(1),
            client.ensure_category_seo(1),
        )
        assert results == [1, 2]


# ==================== REGRESSÃO: 404 da VTEX/LI virava HTTP 500 genérico ====================
#
# Contexto: um produto/categoria removido na loja (ou um ID
# digitado errado) fazia a API da VTEX/Loja Integrada responder 404, que o
# _request tratava como erro genérico (`response.status_code >= 400`) e
# virava uma Exception comum — as rotas de main.py mapeavam qualquer
# Exception para HTTP 500, escondendo do frontend que o recurso simplesmente
# não existe (mensagem/tratamento de "erro interno" em vez de "não encontrado").

class TestNotFoundBecomesHttp404Regression:

    @pytest.mark.asyncio
    async def test_vtex_analyze_product_404_becomes_http_404(self):
        from fastapi import HTTPException
        from app.main import vtex_analyze_product

        fake_optimizer = MagicMock()
        fake_optimizer.analyze_product = AsyncMock(
            side_effect=VtexNotFoundError("Recurso não encontrado na VTEX: /api/catalog/pvt/product/999")
        )
        cached = {"client": MagicMock(), "optimizer": fake_optimizer}

        with patch("app.main.get_or_restore_vtex_client", AsyncMock(return_value=cached)):
            with pytest.raises(HTTPException) as exc:
                await vtex_analyze_product(999, "store-1", user={"user_id": "u1", "token": "t"})
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_vtex_apply_proposals_404_becomes_http_404(self):
        from fastapi import HTTPException
        from app.main import vtex_apply_proposals

        fake_client = MagicMock()
        fake_client.apply_approved_proposals = AsyncMock(
            side_effect=VtexNotFoundError("Recurso não encontrado na VTEX: /api/catalog/pvt/product/999")
        )
        cached = {"client": fake_client, "optimizer": MagicMock()}

        with patch("app.main.get_or_restore_vtex_client", AsyncMock(return_value=cached)):
            with pytest.raises(HTTPException) as exc:
                await vtex_apply_proposals("store-1", item_id=999, body=None, user={"user_id": "u1", "token": "t"})
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_lojaintegrada_analyze_category_404_becomes_http_404(self):
        from fastapi import HTTPException
        from app.main import lojaintegrada_analyze_category

        fake_optimizer = MagicMock()
        fake_optimizer.analyze_category = AsyncMock(
            side_effect=LojaIntegradaNotFoundError("Recurso não encontrado na Loja Integrada: /categoria/999/")
        )
        cached = {"client": MagicMock(), "optimizer": fake_optimizer}

        with patch("app.main.get_or_restore_lojaintegrada_client", AsyncMock(return_value=cached)):
            with pytest.raises(HTTPException) as exc:
                await lojaintegrada_analyze_category(999, "store-1", user={"user_id": "u1", "token": "t"})
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_lojaintegrada_apply_proposals_404_becomes_http_404(self):
        from fastapi import HTTPException
        from app.main import lojaintegrada_apply_proposals

        fake_client = MagicMock()
        fake_client.apply_approved_proposals = AsyncMock(
            side_effect=LojaIntegradaNotFoundError("Recurso não encontrado na Loja Integrada: /produto/999/")
        )
        cached = {"client": fake_client, "optimizer": MagicMock()}

        with patch("app.main.get_or_restore_lojaintegrada_client", AsyncMock(return_value=cached)):
            with pytest.raises(HTTPException) as exc:
                await lojaintegrada_apply_proposals("store-1", item_id=999, body=None, user={"user_id": "u1", "token": "t"})
        assert exc.value.status_code == 404
