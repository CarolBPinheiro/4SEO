"""
Regressão: loja recém-conectada (0 páginas escaneadas
ainda) mostrava Potencial SEO "ALTO"/verde — uma afirmação de oportunidade
sem nenhum dado real por trás — simultaneamente ao banner "site ainda não
foi analisado" e ao card Saúde SEO "0/100" em vermelho.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_mock_db(pages=None, last_scan=None):
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(return_value=[{"id": "site1", "platform": "shopify"}])
    db.get_latest_scan_run = AsyncMock(return_value=last_scan)
    db.list_pages = AsyncMock(return_value=pages or [])
    db.list_tasks = AsyncMock(return_value=[])
    db.list_recent_scan_runs = AsyncMock(return_value=[last_scan] if last_scan else [])
    db.count_search_terms = AsyncMock(return_value=0)
    db.get_integration = AsyncMock(return_value=None)
    return db


class TestPotencialSeoNoData:

    @pytest.mark.asyncio
    async def test_zero_pages_scanned_returns_neutral_potencial(self):
        """Sem nenhuma página escaneada, o Potencial SEO deve ser neutro
        (não pode afirmar 'ALTO/verde' sem dado real)."""
        from app.main import dashboard_summary

        db = _base_mock_db(pages=[], last_scan=None)
        with patch("app.supabase_client.get_supabase_for_user", return_value=db):
            result = await dashboard_summary(refresh=False, user={"user_id": "u1", "token": "t"})

        assert result["connected"] is True
        assert result["total_pages_scanned"] == 0
        assert result["potencial_seo_label"] == "—"
        assert result["potencial_seo_color"] == "cinza"

    @pytest.mark.asyncio
    async def test_low_score_with_pages_still_returns_alto_verde(self):
        """Com páginas de verdade escaneadas e score baixo, o comportamento
        original (ALTO/verde = muito a ganhar) continua valendo."""
        from app.main import dashboard_summary

        pages = [{"id": "p1", "url": "https://x.com/a", "score": 30, "issues": {"missing_title": True}}]
        db = _base_mock_db(pages=pages, last_scan={"avg_score": 30, "completed_at": "2026-01-01"})
        with patch("app.supabase_client.get_supabase_for_user", return_value=db):
            result = await dashboard_summary(refresh=False, user={"user_id": "u1", "token": "t"})

        assert result["total_pages_scanned"] == 1
        assert result["potencial_seo_label"] == "ALTO"
        assert result["potencial_seo_color"] == "verde"

    @pytest.mark.asyncio
    async def test_high_score_with_pages_returns_baixo_cinza(self):
        from app.main import dashboard_summary

        pages = [{"id": "p1", "url": "https://x.com/a", "score": 90, "issues": {}}]
        db = _base_mock_db(pages=pages, last_scan={"avg_score": 90, "completed_at": "2026-01-01"})
        with patch("app.supabase_client.get_supabase_for_user", return_value=db):
            result = await dashboard_summary(refresh=False, user={"user_id": "u1", "token": "t"})

        assert result["potencial_seo_label"] == "BAIXO"
        assert result["potencial_seo_color"] == "cinza"
