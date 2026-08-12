"""
Tests for Services Layer
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services import (
    SiteService, ScanService, TaskService, PageService, KeywordService
)


class TestSiteService:
    """Tests for SiteService"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.list_sites = AsyncMock(return_value=[
            {"id": "1", "base_url": "https://example.com", "platform": "shopify"}
        ])
        db.get_site = AsyncMock(return_value={
            "id": "1", "base_url": "https://example.com", "platform": "shopify"
        })
        db.create_site = AsyncMock(return_value={
            "id": "2", "base_url": "https://new.com", "platform": None
        })
        db.update_site = AsyncMock(return_value={
            "id": "1", "base_url": "https://updated.com", "platform": "vtex"
        })
        db.delete_site = AsyncMock(return_value=True)
        return db
    
    @pytest.mark.asyncio
    async def test_list_sites(self, mock_db):
        service = SiteService(mock_db)
        result = await service.list_sites()
        
        assert len(result) == 1
        assert result[0]["base_url"] == "https://example.com"
        mock_db.list_sites.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_site(self, mock_db):
        service = SiteService(mock_db)
        result = await service.get_site("1")
        
        assert result["id"] == "1"
        mock_db.get_site.assert_called_once_with("1")
    
    @pytest.mark.asyncio
    async def test_create_site_auto_detect_shopify(self, mock_db):
        service = SiteService(mock_db)
        await service.create_site("https://mystore.myshopify.com")
        
        # Should auto-detect shopify platform
        mock_db.create_site.assert_called_once()
        call_args = mock_db.create_site.call_args
        assert call_args[0][1] == "shopify"
    
    @pytest.mark.asyncio
    async def test_create_site_auto_detect_nuvemshop(self, mock_db):
        service = SiteService(mock_db)
        await service.create_site("https://loja.nuvemshop.com.br")
        
        call_args = mock_db.create_site.call_args
        assert call_args[0][1] == "nuvemshop"
    
    @pytest.mark.asyncio
    async def test_create_site_with_explicit_platform(self, mock_db):
        service = SiteService(mock_db)
        await service.create_site("https://example.com", "vtex")
        
        call_args = mock_db.create_site.call_args
        assert call_args[0][1] == "vtex"
    
    @pytest.mark.asyncio
    async def test_delete_site(self, mock_db):
        service = SiteService(mock_db)
        result = await service.delete_site("1")
        
        assert result is True
        mock_db.delete_site.assert_called_once_with("1")


class TestTaskService:
    """Tests for TaskService"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.list_tasks = AsyncMock(return_value=[
            {"id": "t1", "page_id": "p1", "issue_type": "missing_title", "status": "pending"}
        ])
        db.list_pages = AsyncMock(return_value=[
            {"id": "p1", "url": "https://example.com/page1"}
        ])
        db.get_task = AsyncMock(return_value={
            "id": "t1", "page_id": "p1", "issue_type": "missing_title"
        })
        db.get_page = AsyncMock(return_value={
            "id": "p1", "url": "https://example.com/page1", "title": "Test"
        })
        db.update_task_status = AsyncMock(return_value={"id": "t1", "status": "approved"})
        db.delete_task = AsyncMock(return_value=True)
        db.update_task = AsyncMock(return_value={"id": "t1"})
        return db
    
    @pytest.mark.asyncio
    async def test_list_tasks_enriched(self, mock_db):
        service = TaskService(mock_db)
        result = await service.list_tasks("site1", status="pending")
        
        assert len(result) == 1
        assert result[0]["page_url"] == "https://example.com/page1"
        assert "message" in result[0]
    
    @pytest.mark.asyncio
    async def test_approve_task(self, mock_db):
        service = TaskService(mock_db)
        result = await service.approve_task("t1")
        
        mock_db.update_task_status.assert_called_once_with("t1", "approved")
    
    @pytest.mark.asyncio
    async def test_delete_task(self, mock_db):
        service = TaskService(mock_db)
        result = await service.delete_task("t1")
        
        assert result is True
        mock_db.delete_task.assert_called_once_with("t1")


class TestKeywordService:
    """Tests for KeywordService"""
    
    def test_extract_keywords_basic(self):
        service = KeywordService()
        text = "Python programming is great. Python is easy to learn. Programming is fun."
        
        result = service.extract_keywords(text, limit=5)
        
        assert len(result) <= 5
        # Python and programming should be in top results
        keywords = [kw["keyword"] for kw in result]
        assert "python" in keywords
        assert "programming" in keywords
    
    def test_extract_keywords_removes_stopwords(self):
        service = KeywordService()
        text = "the and or is are a an the of to in"
        
        result = service.extract_keywords(text, limit=10)
        
        # All stopwords, should return empty or very few
        assert len(result) == 0
    
    def test_extract_keywords_returns_metrics(self):
        service = KeywordService()
        text = "ecommerce store online shopping cart checkout"
        
        result = service.extract_keywords(text, limit=3)
        
        for kw in result:
            assert "keyword" in kw
            assert "volume" in kw
            assert "cpc" in kw
            assert "intent" in kw
            assert "difficulty" in kw
            assert "opportunity" in kw
    
    def test_extract_keywords_respects_limit(self):
        service = KeywordService()
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        
        result = service.extract_keywords(text, limit=3)
        
        assert len(result) == 3
    
    def test_extract_keywords_handles_empty_text(self):
        service = KeywordService()
        result = service.extract_keywords("", limit=10)
        
        assert len(result) == 0


class TestScanService:
    """Tests for ScanService"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.get_site = AsyncMock(return_value={
            "id": "1", "base_url": "https://example.com"
        })
        db.create_scan_run = AsyncMock(return_value={"id": "scan1"})
        db.upsert_page = AsyncMock(return_value={"id": "page1"})
        db.create_task = AsyncMock(return_value={"id": "task1"})
        db.list_tasks = AsyncMock(return_value=[])
        db.get_running_scan_run = AsyncMock(return_value=None)
        db.complete_scan_run = AsyncMock(return_value={"id": "scan1", "status": "completed"})
        return db

    @pytest.mark.asyncio
    async def test_run_scan_site_not_found(self, mock_db):
        mock_db.get_site = AsyncMock(return_value=None)
        service = ScanService(mock_db)

        with pytest.raises(ValueError, match="Site não encontrado"):
            await service.run_scan("nonexistent")

    # ==================== REGRESSÃO: dedup de seo_tasks entre rescans ====================
    # Bug: cada rescan reinseria uma task por issue ainda presente, sem checar se já
    # existia uma pendente para a mesma página+issue — "Oportunidades Encontradas"
    # crescia sem limite a cada clique em "Atualizar panorama".

    @pytest.mark.asyncio
    async def test_create_tasks_skips_issue_with_existing_pending_task(self, mock_db):
        service = ScanService(mock_db)
        existing_keys = {("page1", "missing_title")}

        count = await service._create_tasks_for_issues(
            site_id="site1", page_id="page1", page_url="https://x.com",
            issues={"missing_title": True, "missing_h1": True},
            existing_task_keys=existing_keys,
        )

        assert count == 1
        mock_db.create_task.assert_called_once()
        assert mock_db.create_task.call_args.kwargs["task_type"] == "missing_h1"

    @pytest.mark.asyncio
    async def test_create_tasks_first_scan_has_no_existing_keys(self, mock_db):
        service = ScanService(mock_db)

        count = await service._create_tasks_for_issues(
            site_id="site1", page_id="page1", page_url="https://x.com",
            issues={"missing_title": True, "missing_h1": True, "missing_h2": False},
        )

        # missing_h2 está False (ausente) — não gera task
        assert count == 2

    @pytest.mark.asyncio
    async def test_run_scan_rescan_does_not_duplicate_pending_tasks(self, mock_db, monkeypatch):
        """Simula um rescan real: a issue com task pendente existente não deve duplicar."""
        mock_db.list_tasks = AsyncMock(return_value=[
            {"page_id": "page1", "issue_type": "missing_title", "status": "pending"},
        ])

        async def fake_crawl_site(base_url, max_pages=30):
            return {
                "pages": [{
                    "url": "https://x.com", "status_code": 200, "title": None,
                    "meta_description": None, "h1": None,
                    "issues": {"missing_title": True, "missing_h1": True}, "score": 50,
                }],
                "pages_analyzed": 1, "pages_found": 1, "pages_failed": 0,
                "average_score": 50, "duration_seconds": 1, "issues_summary": {},
            }
        monkeypatch.setattr("app.services.crawl_site", fake_crawl_site)

        service = ScanService(mock_db)
        result = await service.run_scan("site1")

        # missing_title já tinha task pendente (não duplica); só missing_h1 é nova
        assert result["tasks_created"] == 1
        mock_db.create_task.assert_called_once()
        assert mock_db.create_task.call_args.kwargs["task_type"] == "missing_h1"

    # ==================== REGRESSÃO: lock entre scans concorrentes ====================
    # nada impedia dois run_scan simultâneos do mesmo site (ex.: o
    # auto-scan de onboarding ainda rodando quando o usuário clica "Analisar
    # meu site agora" logo em seguida) — cada execução concorrente duplicava
    # seo_tasks e criava dois scan_runs quase simultâneos.

    @pytest.mark.asyncio
    async def test_run_scan_raises_when_another_scan_is_running(self, mock_db):
        from app.services import ScanInProgressError
        from datetime import datetime, timezone

        mock_db.get_running_scan_run = AsyncMock(return_value={
            "id": "running1",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        service = ScanService(mock_db)

        with pytest.raises(ScanInProgressError):
            await service.run_scan("site1")

        # Não deve nem tentar criar um novo scan_run
        mock_db.create_scan_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_scan_ignores_stale_running_scan(self, mock_db, monkeypatch):
        """Um scan_run 'running' iniciado há mais de 10min é tratado como
        abandonado (processo derrubado antes de completar) — não bloqueia."""
        from datetime import datetime, timezone, timedelta

        old_start = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        mock_db.get_running_scan_run = AsyncMock(return_value={"id": "stale1", "started_at": old_start})

        async def fake_crawl_site(base_url, max_pages=30):
            return {
                "pages": [], "pages_analyzed": 0, "pages_found": 0, "pages_failed": 0,
                "average_score": 0, "duration_seconds": 1, "issues_summary": {},
            }
        monkeypatch.setattr("app.services.crawl_site", fake_crawl_site)

        service = ScanService(mock_db)
        result = await service.run_scan("site1")  # não deve levantar

        assert result["pages_scanned"] == 0
        mock_db.create_scan_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scan_proceeds_when_no_running_scan(self, mock_db, monkeypatch):
        mock_db.get_running_scan_run = AsyncMock(return_value=None)

        async def fake_crawl_site(base_url, max_pages=30):
            return {
                "pages": [], "pages_analyzed": 0, "pages_found": 0, "pages_failed": 0,
                "average_score": 0, "duration_seconds": 1, "issues_summary": {},
            }
        monkeypatch.setattr("app.services.crawl_site", fake_crawl_site)

        service = ScanService(mock_db)
        result = await service.run_scan("site1")

        assert result["pages_scanned"] == 0
        mock_db.create_scan_run.assert_called_once()
