"""
Regressão: conectar uma loja Loja Integrada sem
nenhum produto no catálogo gravava permanentemente uma base_url FAKE
("https://lojaintegrada-{key}.pendente") no site — como esse domínio nunca
existe (não resolve DNS), TODO scan futuro (manual ou automático) falhava
para sempre, sem nenhuma tela de correção.

Cobre:
- POST /api/lojaintegrada/connect: catálogo vazio não cria mais o site com
  URL fake (só salva a integração; site fica pendente de auto-cura).
- GET /api/integrations/status: tenta re-derivar a URL a cada checagem
  (self-healing) e só cria o site quando uma URL real é encontrada.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_db(sites=None, integration=None):
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(return_value=sites or [])
    db.get_integration = AsyncMock(return_value=integration)
    db.create_site = AsyncMock(side_effect=lambda base_url, platform, user_id: {
        "id": "site1", "base_url": base_url, "platform": platform,
    })
    db.save_integration = AsyncMock(return_value={})
    return db


class TestLojaIntegradaConnectEmptyCatalog:

    @pytest.mark.asyncio
    async def test_connect_with_no_products_does_not_create_fake_url_site(self):
        from app.main import lojaintegrada_connect, LojaIntegradaConnectRequest

        db = _mock_db(sites=[])
        fake_client = MagicMock()
        fake_client.store_key = "abc123"
        fake_client.store_url = ""
        fake_client.test_connection = AsyncMock(return_value={"connected": True})
        fake_client.get_all_products = AsyncMock(return_value=[])  # catálogo vazio

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch("app.integrations.lojaintegrada.create_lojaintegrada_client", return_value=fake_client), \
             patch("app.integrations.lojaintegrada.LOJAINTEGRADA_APP_KEY", "app-key-fake"):
            result = await lojaintegrada_connect(
                LojaIntegradaConnectRequest(chave_api="chave-teste"),
                user={"user_id": "u1", "token": "t"},
            )

        assert result["success"] is True
        # Nenhum site deve ter sido criado com domínio fake
        db.create_site.assert_not_called()
        # A integração (credenciais) ainda deve ser salva — conexão "lembrada"
        db.save_integration.assert_awaited_once()
        saved_metadata = db.save_integration.call_args.kwargs.get("metadata", {})
        assert saved_metadata.get("site_url") == ""


class TestIntegrationsStatusSelfHeals:

    @pytest.mark.asyncio
    async def test_self_heals_when_products_now_exist(self):
        """Na conexão a loja não tinha produtos; agora tem — o status deve
        re-derivar a URL e criar o site (em vez de reportar desconectado ou
        usar um domínio fake)."""
        from app.main import integrations_status

        integration = {
            "platform": "lojaintegrada",
            "access_token": "chave-teste",
            "store_url": "abc123",  # store_key
            "store_name": "Loja Integrada",
            "metadata": {"site_url": ""},
        }
        db = _mock_db(sites=[], integration=integration)

        fake_product = MagicMock()
        fake_product.url = "https://minha-loja.com.br/produto-1"
        fake_client = MagicMock()
        fake_client.store_url = "https://minha-loja.com.br"
        fake_client.get_all_products = AsyncMock(return_value=[fake_product])
        cached = {"client": fake_client, "optimizer": MagicMock(), "user_id": "u1"}

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch("app.main.get_or_restore_lojaintegrada_client", AsyncMock(return_value=cached)):
            result = await integrations_status(user={"user_id": "u1", "token": "t"})

        assert result["connected"] is True
        db.create_site.assert_called_once()
        assert db.create_site.call_args.kwargs.get("base_url") == "https://minha-loja.com.br" \
            or db.create_site.call_args.args[0] == "https://minha-loja.com.br"
        # metadata.site_url deve ter sido persistido para não precisar re-derivar de novo
        db.save_integration.assert_awaited_once()
        assert db.save_integration.call_args.kwargs["metadata"]["site_url"] == "https://minha-loja.com.br"

    @pytest.mark.asyncio
    async def test_still_no_products_reports_connected_without_fake_site(self):
        """Loja continua sem produtos — deve reportar conectado, SEM criar
        site com domínio inválido."""
        from app.main import integrations_status

        integration = {
            "platform": "lojaintegrada",
            "access_token": "chave-teste",
            "store_url": "abc123",
            "store_name": "Loja Integrada",
            "metadata": {"site_url": ""},
        }
        db = _mock_db(sites=[], integration=integration)

        fake_client = MagicMock()
        fake_client.store_url = ""
        fake_client.get_all_products = AsyncMock(return_value=[])
        cached = {"client": fake_client, "optimizer": MagicMock(), "user_id": "u1"}

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch("app.main.get_or_restore_lojaintegrada_client", AsyncMock(return_value=cached)):
            result = await integrations_status(user={"user_id": "u1", "token": "t"})

        assert result["connected"] is True
        assert result["platform"] == "lojaintegrada"
        assert result["site_id"] is None
        db.create_site.assert_not_called()
        # Nenhum domínio ".pendente" ou fake em lugar nenhum da resposta
        assert ".pendente" not in str(result)
