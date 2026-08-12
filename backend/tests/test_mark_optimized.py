"""
Testes de regressão: o Dashboard nunca refletia
otimizações reais aplicadas via IA nas integrações (Shopify/Nuvemshop/VTEX/
Loja Integrada) — o filtro "Já Otimizados" ficava sempre vazio e o selo
"✓ Otimizado" nunca aparecia, porque nenhum dos 4 endpoints de apply tocava
seo_tasks (só TaskService.approve_task, exposto por um endpoint legado que o
frontend não usa mais, fazia isso).

Cobre:
- SupabaseClient.find_page_by_url (comparação de URL normalizada)
- SupabaseClient.approve_pending_tasks_for_page
- main._mark_pages_optimized (helper compartilhado pelos 4 endpoints de apply)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.supabase_client import SupabaseClient


class TestFindPageByUrl:

    @pytest.mark.asyncio
    async def test_matches_ignoring_protocol_and_trailing_slash(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db.list_pages = AsyncMock(return_value=[
            {"id": "p1", "url": "https://loja.com/produto-x/"},
            {"id": "p2", "url": "https://loja.com/produto-y"},
        ])
        page = await db.find_page_by_url("site1", "http://loja.com/produto-x")
        assert page["id"] == "p1"

    @pytest.mark.asyncio
    async def test_matches_ignoring_www(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db.list_pages = AsyncMock(return_value=[{"id": "p1", "url": "https://www.loja.com/x"}])
        page = await db.find_page_by_url("site1", "https://loja.com/x")
        assert page["id"] == "p1"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db.list_pages = AsyncMock(return_value=[{"id": "p1", "url": "https://loja.com/outro"}])
        page = await db.find_page_by_url("site1", "https://loja.com/produto-x")
        assert page is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_url(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db.list_pages = AsyncMock(return_value=[])
        assert await db.find_page_by_url("site1", "") is None
        assert await db.find_page_by_url("site1", None) is None


class TestApprovePendingTasksForPage:

    @pytest.mark.asyncio
    async def test_approves_all_pending_tasks_for_page(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db._request = AsyncMock(return_value=[{"id": "t1"}, {"id": "t2"}])
        db.update_task_status = AsyncMock(return_value={})

        count = await db.approve_pending_tasks_for_page("page1")

        assert count == 2
        assert db.update_task_status.await_count == 2
        db.update_task_status.assert_any_await("t1", "approved")
        db.update_task_status.assert_any_await("t2", "approved")

    @pytest.mark.asyncio
    async def test_no_pending_tasks_returns_zero(self):
        db = SupabaseClient(url="https://x.supabase.co", key="k")
        db._request = AsyncMock(return_value=[])
        db.update_task_status = AsyncMock()

        count = await db.approve_pending_tasks_for_page("page1")

        assert count == 0
        db.update_task_status.assert_not_awaited()


class TestMarkPagesOptimizedHelper:

    @pytest.mark.asyncio
    async def test_marks_product_page_as_optimized(self):
        from app.main import _mark_pages_optimized, INTEGRATION_PLATFORMS

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(return_value=[{"id": "site1", "platform": "vtex"}])
        db.find_page_by_url = AsyncMock(return_value={"id": "page1"})
        db.approve_pending_tasks_for_page = AsyncMock(return_value=1)

        async def resolve_url(content_type, product_id):
            assert content_type == "product"
            assert product_id == 42
            return "https://loja.com/produto-42"

        await _mark_pages_optimized(db, "user1", [
            {"content_type": "product", "product_id": 42, "field_name": "seo_title"},
        ], resolve_url)

        db.find_page_by_url.assert_awaited_once_with("site1", "https://loja.com/produto-42")
        db.approve_pending_tasks_for_page.assert_awaited_once_with("page1")

    @pytest.mark.asyncio
    async def test_dedupes_multiple_proposals_for_same_product(self):
        """3 propostas (seo_title, seo_description, name) do MESMO produto só
        devem resolver a URL e marcar a página UMA vez."""
        from app.main import _mark_pages_optimized

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(return_value=[{"id": "site1", "platform": "nuvemshop"}])
        db.find_page_by_url = AsyncMock(return_value={"id": "page1"})
        db.approve_pending_tasks_for_page = AsyncMock(return_value=1)

        resolve_url = AsyncMock(return_value="https://loja.com/p")
        await _mark_pages_optimized(db, "user1", [
            {"content_type": "product", "product_id": 42, "field_name": "seo_title"},
            {"content_type": "product", "product_id": 42, "field_name": "seo_description"},
            {"content_type": "product", "product_id": 42, "field_name": "name"},
        ], resolve_url)

        assert resolve_url.await_count == 1
        db.find_page_by_url.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_unsupported_content_types(self):
        """Shopify collection/page/article ficam fora do escopo (gap documentado) —
        não deve tentar resolver URL nem chamar find_page_by_url para eles."""
        from app.main import _mark_pages_optimized

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(return_value=[{"id": "site1", "platform": "shopify"}])
        db.find_page_by_url = AsyncMock()
        resolve_url = AsyncMock(return_value="https://loja.com/x")

        await _mark_pages_optimized(db, "user1", [
            {"content_type": "collection", "product_id": 1},
            {"content_type": "page", "product_id": 2},
            {"content_type": "blog", "product_id": 3},
        ], resolve_url)

        resolve_url.assert_not_awaited()
        db.find_page_by_url.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_site_connected_is_a_noop(self):
        from app.main import _mark_pages_optimized

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(return_value=[])
        resolve_url = AsyncMock()

        # Não deve lançar, apenas retornar silenciosamente
        await _mark_pages_optimized(db, "user1", [{"content_type": "product", "product_id": 1}], resolve_url)
        resolve_url.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resolve_url_failure_does_not_raise(self):
        """Falha ao buscar o produto (ex.: já foi removido da loja) não deve
        derrubar o apply — é best-effort."""
        from app.main import _mark_pages_optimized

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(return_value=[{"id": "site1", "platform": "vtex"}])

        async def resolve_url(content_type, product_id):
            raise Exception("produto não encontrado")

        # Não deve lançar
        await _mark_pages_optimized(db, "user1", [{"content_type": "product", "product_id": 1}], resolve_url)

    @pytest.mark.asyncio
    async def test_empty_proposals_is_a_noop(self):
        from app.main import _mark_pages_optimized

        db = MagicMock()
        db.list_sites_for_user = AsyncMock()

        await _mark_pages_optimized(db, "user1", [], AsyncMock())
        db.list_sites_for_user.assert_not_awaited()
