"""
Tests for the enriched AI optimization pipeline:
- fetch_serp (SearchAPI SERP)
- fetch_gsc_page_performance
- Proposal models (priority/impact/effort/target_keyword/pre_metrics)
- Optimizer helper methods (_build_enriched_prompt_blocks, _extract_priority_fields)
- API endpoint signatures (target_keyword param)
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestFetchSerp:
    """Tests for searchapi_client.fetch_serp"""

    @pytest.mark.asyncio
    async def test_serp_returns_empty_without_api_key(self):
        """Should return empty results when SEARCHAPI_KEY is not set"""
        with patch("app.integrations.searchapi_client.SEARCHAPI_KEY", ""):
            from app.integrations.searchapi_client import fetch_serp
            result = await fetch_serp("test keyword")
            assert result["keyword"] == "test keyword"
            assert result["results"] == []
            assert "error" in result

    @pytest.mark.asyncio
    async def test_serp_parses_organic_results(self):
        """Should correctly parse SearchAPI response into structured results"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {
                    "position": 1,
                    "title": "Best Product 2024",
                    "link": "https://example.com/product",
                    "snippet": "Great product for testing",
                    "displayed_link": "example.com › product",
                },
                {
                    "position": 2,
                    "title": "Second Result",
                    "link": "https://other.com/page",
                    "snippet": "Another result",
                    "displayed_link": "other.com › page",
                },
            ],
            "search_information": {"total_results": 1500000},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.integrations.searchapi_client.SEARCHAPI_KEY", "test-key"):
            with patch("app.integrations.searchapi_client.httpx.AsyncClient", return_value=mock_client):
                from app.integrations.searchapi_client import fetch_serp
                result = await fetch_serp("test keyword", geo="BR", num_results=5)

        assert result["keyword"] == "test keyword"
        assert len(result["results"]) == 2
        assert result["results"][0]["position"] == 1
        assert result["results"][0]["title"] == "Best Product 2024"
        assert result["results"][0]["link"] == "https://example.com/product"
        assert result["results"][0]["snippet"] == "Great product for testing"
        assert result["total_results"] == 1500000

    @pytest.mark.asyncio
    async def test_serp_limits_results(self):
        """Should respect num_results limit"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {"position": i, "title": f"Result {i}", "link": f"https://ex.com/{i}", "snippet": f"Snippet {i}", "displayed_link": f"ex.com/{i}"}
                for i in range(1, 11)
            ],
            "search_information": {"total_results": 100},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.integrations.searchapi_client.SEARCHAPI_KEY", "test-key"):
            with patch("app.integrations.searchapi_client.httpx.AsyncClient", return_value=mock_client):
                from app.integrations.searchapi_client import fetch_serp
                result = await fetch_serp("keyword", num_results=3)

        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_serp_handles_exception_gracefully(self):
        """Should return error dict on exception, not crash"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.integrations.searchapi_client.SEARCHAPI_KEY", "test-key"):
            with patch("app.integrations.searchapi_client.httpx.AsyncClient", return_value=mock_client):
                from app.integrations.searchapi_client import fetch_serp
                result = await fetch_serp("keyword")

        assert result["keyword"] == "keyword"
        assert result["results"] == []
        assert "error" in result


class TestFetchGscPagePerformance:
    """Tests for gsc.fetch_gsc_page_performance"""

    @pytest.mark.asyncio
    async def test_returns_not_found_when_page_missing(self):
        """Should return found=False when page not in GSC data"""
        with patch("app.integrations.gsc.fetch_gsc_performance", new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "rows": [
                    {"keys": ["https://other-page.com"], "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 5.0}
                ]
            }
            from app.integrations.gsc import fetch_gsc_page_performance
            result = await fetch_gsc_page_performance("token", "https://site.com", "https://site.com/missing")

        assert result["page_url"] == "https://site.com/missing"
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_returns_metrics_when_page_found(self):
        """Should return metrics and top queries when page exists in GSC"""
        page_url = "https://site.com/product-1"

        with patch("app.integrations.gsc.fetch_gsc_performance", new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "rows": [
                    {"keys": [page_url], "clicks": 50, "impressions": 1000, "ctr": 0.05, "position": 8.3}
                ]
            }

            # Mock the httpx call for queries
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "rows": [
                    {"keys": ["buy product"], "clicks": 20, "impressions": 500, "ctr": 0.04, "position": 6.1},
                    {"keys": ["best product"], "clicks": 10, "impressions": 300, "ctr": 0.033, "position": 10.2},
                ]
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch("app.integrations.gsc.httpx.AsyncClient", return_value=mock_client):
                from app.integrations.gsc import fetch_gsc_page_performance
                result = await fetch_gsc_page_performance("token", "https://site.com", page_url)

        assert result["found"] is True
        assert result["clicks"] == 50
        assert result["impressions"] == 1000
        assert result["ctr"] == 5.0  # 0.05 * 100
        assert result["position"] == 8.3
        assert len(result["top_queries"]) == 2
        assert result["top_queries"][0]["query"] == "buy product"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Should return found=False on any exception"""
        with patch("app.integrations.gsc.fetch_gsc_performance", new_callable=AsyncMock, side_effect=Exception("Auth error")):
            from app.integrations.gsc import fetch_gsc_page_performance
            result = await fetch_gsc_page_performance("bad-token", "https://site.com", "https://site.com/page")

        assert result["found"] is False
        assert "error" in result


class TestShopifyProposalModel:
    """Tests for the extended Shopify OptimizationProposal model"""

    def test_proposal_has_priority_fields(self):
        """OptimizationProposal should accept priority/impact/effort/target_keyword/pre_metrics"""
        from app.integrations.shopify import OptimizationProposal

        proposal = OptimizationProposal(
            id="test-1",
            product_id=123,
            optimization_type="product_title",
            field_name="title",
            original_value="Old Title",
            proposed_value="New SEO Title",
            reasoning="Better ranking",
            status="pending",
            priority="high",
            impact="ranking",
            effort="low",
            target_keyword="sapato masculino",
            pre_metrics={"clicks": 50, "impressions": 1000, "ctr": 5.0, "position": 8.3},
        )

        assert proposal.priority == "high"
        assert proposal.impact == "ranking"
        assert proposal.effort == "low"
        assert proposal.target_keyword == "sapato masculino"
        assert proposal.pre_metrics["clicks"] == 50

    def test_proposal_fields_are_optional(self):
        """New fields should default to None"""
        from app.integrations.shopify import OptimizationProposal

        proposal = OptimizationProposal(
            id="test-2",
            product_id=456,
            optimization_type="product_description",
            field_name="description",
            original_value="Old desc",
            proposed_value="New desc",
            reasoning="More keywords",
            status="pending",
        )

        assert proposal.priority is None
        assert proposal.impact is None
        assert proposal.effort is None
        assert proposal.target_keyword is None
        assert proposal.pre_metrics is None

    def test_proposal_serializes_correctly(self):
        """model_dump should include all new fields"""
        from app.integrations.shopify import OptimizationProposal

        proposal = OptimizationProposal(
            id="test-3",
            product_id=789,
            optimization_type="product_seo_title",
            field_name="seo_title",
            original_value="",
            proposed_value="New Meta Title",
            reasoning="SEO improvement",
            status="pending",
            priority="medium",
            impact="ctr",
            effort="low",
        )

        data = proposal.model_dump()
        assert "priority" in data
        assert "impact" in data
        assert "effort" in data
        assert "target_keyword" in data
        assert "pre_metrics" in data
        assert data["priority"] == "medium"
        assert data["impact"] == "ctr"


class TestNuvemshopProposalModel:
    """Tests for the extended Nuvemshop OptimizationProposal model"""

    def test_proposal_has_priority_fields(self):
        """Nuvemshop OptimizationProposal should also have all extended fields"""
        from app.integrations.nuvemshop import OptimizationProposal

        proposal = OptimizationProposal(
            id="ns-1",
            product_id=100,
            optimization_type="product_name",
            field_name="name",
            original_value="Old Name",
            proposed_value="New SEO Name",
            reasoning="Better keyword density",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
            priority="high",
            impact="ranking",
            effort="medium",
            target_keyword="camiseta esportiva",
            pre_metrics={"clicks": 10, "impressions": 200, "ctr": 5.0, "position": 12.5},
        )

        assert proposal.priority == "high"
        assert proposal.target_keyword == "camiseta esportiva"
        assert proposal.pre_metrics["position"] == 12.5

    def test_proposal_fields_default_none(self):
        """New fields should not break existing code that doesn't set them"""
        from app.integrations.nuvemshop import OptimizationProposal

        proposal = OptimizationProposal(
            id="ns-2",
            product_id=200,
            optimization_type="product_description",
            field_name="description",
            original_value="Short desc",
            proposed_value="Longer optimized description",
            reasoning="More content",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )

        assert proposal.priority is None
        assert proposal.pre_metrics is None


class TestNuvemshopOptimizerHelpers:
    """Tests for NuvemshopOptimizer helper methods"""

    def _make_optimizer(self):
        """Create a NuvemshopOptimizer with mocked dependencies"""
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
        mock_client = MagicMock()
        mock_client._generate_proposal_id = MagicMock(return_value="prop-test-id")
        optimizer = NuvemshopOptimizer(mock_client)
        return optimizer

    def test_build_enriched_prompt_empty(self):
        """Should return empty string when no context provided"""
        optimizer = self._make_optimizer()
        result = optimizer._build_enriched_prompt_blocks()
        assert result == ""

    def test_build_enriched_prompt_keyword_only(self):
        """Should include keyword directive"""
        optimizer = self._make_optimizer()
        result = optimizer._build_enriched_prompt_blocks(target_keyword="sapato masculino")
        assert "KEYWORD ALVO: sapato masculino" in result
        assert "centradas nesta keyword" in result
        assert "LEMBRETE" in result  # preservation reminder

    def test_build_enriched_prompt_serp_context(self):
        """Should include SERP context and competitive instruction"""
        optimizer = self._make_optimizer()
        serp = "=== CONCORRENTES NO GOOGLE para 'sapato' ===\n#1: Best Shoes"
        result = optimizer._build_enriched_prompt_blocks(serp_context=serp)
        assert "CONCORRENTES NO GOOGLE" in result
        assert "SUPERAR" in result

    def test_build_enriched_prompt_gsc_context(self):
        """Should include GSC data"""
        optimizer = self._make_optimizer()
        gsc = "=== PERFORMANCE ATUAL ===\nCliques: 50\nCTR: 5%"
        result = optimizer._build_enriched_prompt_blocks(gsc_context=gsc)
        assert "PERFORMANCE ATUAL" in result
        assert "direcionar as otimizações" in result

    def test_build_enriched_prompt_all_contexts(self):
        """Should combine all contexts with preservation reminder"""
        optimizer = self._make_optimizer()
        result = optimizer._build_enriched_prompt_blocks(
            target_keyword="tênis running",
            serp_context="CONCORRENTES...",
            gsc_context="PERFORMANCE...",
        )
        assert "KEYWORD ALVO: tênis running" in result
        assert "CONCORRENTES" in result
        assert "PERFORMANCE" in result
        assert "Preserve medidas" in result

    def test_extract_priority_fields_full(self):
        """Should extract priority/impact/effort from AI response"""
        optimizer = self._make_optimizer()
        field_data = {
            "value": "New Title",
            "reasoning": "Better SEO",
            "priority": "high",
            "impact": "ranking",
            "effort": "low",
        }
        result = optimizer._extract_priority_fields(field_data)
        assert result == {"priority": "high", "impact": "ranking", "effort": "low"}

    def test_extract_priority_fields_missing(self):
        """Should return None for missing fields"""
        optimizer = self._make_optimizer()
        field_data = {"value": "Title", "reasoning": "reason"}
        result = optimizer._extract_priority_fields(field_data)
        assert result == {"priority": None, "impact": None, "effort": None}

    def test_extract_priority_fields_partial(self):
        """Should handle partial data"""
        optimizer = self._make_optimizer()
        field_data = {"value": "X", "reasoning": "Y", "priority": "medium"}
        result = optimizer._extract_priority_fields(field_data)
        assert result["priority"] == "medium"
        assert result["impact"] is None
        assert result["effort"] is None


class TestShopifyOptimizerHelpers:
    """Tests for ShopifySEOOptimizer helper methods"""

    def _make_optimizer(self):
        from app.integrations.shopify_optimizer import ShopifySEOOptimizer
        mock_client = MagicMock()
        optimizer = ShopifySEOOptimizer(mock_client)
        return optimizer

    @pytest.mark.asyncio
    async def test_fetch_serp_context_returns_formatted_text(self):
        """Should format SERP results as readable prompt text"""
        optimizer = self._make_optimizer()

        mock_serp = {
            "keyword": "camiseta dry fit",
            "results": [
                {"position": 1, "title": "Top Result", "displayed_link": "example.com", "snippet": "Best product"},
                {"position": 2, "title": "Second", "displayed_link": "other.com", "snippet": "Good too"},
            ],
        }

        with patch("app.integrations.searchapi_client.fetch_serp", new_callable=AsyncMock, return_value=mock_serp):
            result = await optimizer._fetch_serp_context("camiseta dry fit")

        assert "CONCORRENTES NO GOOGLE" in result
        assert "camiseta dry fit" in result
        assert "#1: Top Result" in result
        assert "#2: Second" in result

    @pytest.mark.asyncio
    async def test_fetch_serp_context_empty_on_no_results(self):
        """Should return empty string when SERP has no results"""
        optimizer = self._make_optimizer()

        mock_serp = {"keyword": "nonexistent", "results": []}

        with patch("app.integrations.searchapi_client.fetch_serp", new_callable=AsyncMock, return_value=mock_serp):
            result = await optimizer._fetch_serp_context("nonexistent")

        assert result == ""

    @pytest.mark.asyncio
    async def test_fetch_serp_context_handles_error(self):
        """Should return empty string on exception"""
        optimizer = self._make_optimizer()

        with patch("app.integrations.searchapi_client.fetch_serp", new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await optimizer._fetch_serp_context("test")

        assert result == ""


class TestSystemPrompts:
    """Verify system prompts contain content preservation rules"""

    def test_shopify_system_prompt_has_preservation_rules(self):
        from app.integrations.shopify_optimizer import SYSTEM_PROMPT_ECOMMERCE as shopify_prompt
        # Must contain preservation instructions
        assert "PRESERVAÇÃO" in shopify_prompt or "preserv" in shopify_prompt.lower()
        assert "medidas" in shopify_prompt.lower() or "dimensões" in shopify_prompt.lower()

    def test_nuvemshop_system_prompt_has_preservation_rules(self):
        from app.integrations.nuvemshop_optimizer import SYSTEM_PROMPT_ECOMMERCE as nuvemshop_prompt
        assert "PRESERVAÇÃO" in nuvemshop_prompt or "preserv" in nuvemshop_prompt.lower()

    def test_shopify_system_prompt_has_prioritization(self):
        from app.integrations.shopify_optimizer import SYSTEM_PROMPT_ECOMMERCE as shopify_prompt
        assert "priority" in shopify_prompt.lower() or "prioriz" in shopify_prompt.lower()

    def test_nuvemshop_system_prompt_has_prioritization(self):
        from app.integrations.nuvemshop_optimizer import SYSTEM_PROMPT_ECOMMERCE as nuvemshop_prompt
        assert "priority" in nuvemshop_prompt.lower() or "prioriz" in nuvemshop_prompt.lower()


class TestApiEndpointSignatures:
    """Verify that API endpoints accept the new target_keyword parameter"""

    def test_shopify_optimize_request_has_target_keyword(self):
        """ShopifyOptimizeRequest should have target_keyword field"""
        import sys
        sys.path.insert(0, ".")
        # Import the model directly
        from pydantic import BaseModel
        
        # We can check by importing main and verifying the model
        from app.main import ShopifyOptimizeRequest
        
        fields = ShopifyOptimizeRequest.model_fields
        assert "target_keyword" in fields
        # Should be Optional (default None)
        assert fields["target_keyword"].default is None

    def test_shopify_optimize_request_backward_compatible(self):
        """Existing requests without target_keyword should still work"""
        from app.main import ShopifyOptimizeRequest

        # Old-style request without target_keyword
        req = ShopifyOptimizeRequest(
            optimize_title=True,
            optimize_description=True,
        )
        assert req.target_keyword is None
        assert req.optimize_title is True

    def test_shopify_optimize_request_with_keyword(self):
        """New requests with target_keyword should work"""
        from app.main import ShopifyOptimizeRequest

        req = ShopifyOptimizeRequest(
            optimize_title=True,
            target_keyword="sapato social masculino",
        )
        assert req.target_keyword == "sapato social masculino"


class TestOptimizerSignatures:
    """Verify that optimizer methods accept the new parameters"""

    def test_shopify_generate_optimizations_accepts_keyword(self):
        """generate_optimizations should accept target_keyword, user, page_url"""
        import inspect
        from app.integrations.shopify_optimizer import ShopifySEOOptimizer
        sig = inspect.signature(ShopifySEOOptimizer.generate_optimizations)
        params = list(sig.parameters.keys())
        assert "target_keyword" in params
        assert "user" in params
        assert "page_url" in params

    def test_nuvemshop_optimize_product_accepts_keyword(self):
        """optimize_product should accept target_keyword, user, page_url"""
        import inspect
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
        sig = inspect.signature(NuvemshopOptimizer.optimize_product)
        params = list(sig.parameters.keys())
        assert "target_keyword" in params
        assert "user" in params
        assert "page_url" in params

    def test_nuvemshop_optimize_category_accepts_keyword(self):
        import inspect
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
        sig = inspect.signature(NuvemshopOptimizer.optimize_category)
        params = list(sig.parameters.keys())
        assert "target_keyword" in params
        assert "user" in params
        assert "page_url" in params

    def test_nuvemshop_optimize_page_accepts_keyword(self):
        import inspect
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
        sig = inspect.signature(NuvemshopOptimizer.optimize_page)
        params = list(sig.parameters.keys())
        assert "target_keyword" in params
        assert "user" in params

    def test_nuvemshop_optimize_blog_post_accepts_keyword(self):
        import inspect
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
        sig = inspect.signature(NuvemshopOptimizer.optimize_blog_post)
        params = list(sig.parameters.keys())
        assert "target_keyword" in params
        assert "user" in params


class TestClassifySearchChance:
    """Existing function tests to confirm no regressions"""

    def test_alta_chance(self):
        from app.integrations.searchapi_client import classify_search_chance
        assert classify_search_chance(80, 5) == "alta"

    def test_moderada_chance(self):
        from app.integrations.searchapi_client import classify_search_chance
        assert classify_search_chance(50, 2) == "moderada"

    def test_baixa_chance(self):
        from app.integrations.searchapi_client import classify_search_chance
        assert classify_search_chance(20, 1) == "baixa"
