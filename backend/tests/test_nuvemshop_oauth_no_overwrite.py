"""
Regressão: o callback OAuth da Nuvemshop (tanto o
redirect quanto a troca manual de código) salvava a credencial Nuvemshop em
user_integrations INCONDICIONALMENTE, mesmo quando o usuário já tinha outra
plataforma conectada (ex.: Shopify). Como save_integration faz upsert por
user_id (1 linha por usuário), isso sobrescrevia silenciosamente as
credenciais da integração existente — a tabela `sites` continuava com o
site antigo (ex.: Shopify), mas `user_integrations` passava a apontar pra
Nuvemshop, quebrando a reconexão automática (login) e o disconnect (que lê
get_integration para saber o que apagar) da loja original.

Cobre:
- GET /nuvemshop/oauth/callback (nuvemshop_oauth_redirect): não salva nem
  cria site quando outra plataforma já está conectada.
- POST /api/nuvemshop/exchange-code (nuvemshop_exchange_code_manual): idem.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_db(sites=None):
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(return_value=sites or [])
    db.create_site = AsyncMock(return_value={"id": "new-site"})
    db.save_integration = AsyncMock(return_value={})
    db.delete_site = AsyncMock(return_value=True)
    return db


def _fake_nuvemshop_client():
    store_obj = MagicMock()
    store_obj.name = "Minha Loja Nuvemshop"
    store_obj.url = "https://minhaloja.nuvemshop.com.br"
    client = MagicMock()
    client.test_connection = AsyncMock(return_value={"store": store_obj})
    return client


SHOPIFY_SITE = {"id": "site-shopify", "platform": "shopify", "base_url": "https://loja.myshopify.com"}


class TestNuvemshopOAuthRedirectDoesNotOverwrite:

    @pytest.mark.asyncio
    async def test_skips_save_when_shopify_already_connected(self):
        from app.main import nuvemshop_oauth_redirect
        from app.integrations.nuvemshop import _oauth_states

        db = _mock_db(sites=[SHOPIFY_SITE])
        fake_client = _fake_nuvemshop_client()
        _oauth_states["state-test-1"] = {"user_id": "u1", "token": "t"}

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch(
                 "app.integrations.nuvemshop.NuvemshopOAuth.exchange_code",
                 new_callable=AsyncMock,
                 return_value={"success": True, "store_id": "999", "access_token": "tok-nuvem"},
             ), \
             patch("app.integrations.nuvemshop.create_nuvemshop_client", return_value=fake_client):
            response = await nuvemshop_oauth_redirect(code="auth-code", state="state-test-1")

        # Não sobrescreve a integração Shopify existente
        db.save_integration.assert_not_awaited()
        db.create_site.assert_not_awaited()
        assert "error=already_connected" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_saves_normally_when_no_other_integration(self):
        """Não regride o caso comum: sem outra integração, conecta normalmente."""
        from app.main import nuvemshop_oauth_redirect
        from app.integrations.nuvemshop import _oauth_states

        db = _mock_db(sites=[])
        fake_client = _fake_nuvemshop_client()
        _oauth_states["state-test-2"] = {"user_id": "u1", "token": "t"}

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch(
                 "app.integrations.nuvemshop.NuvemshopOAuth.exchange_code",
                 new_callable=AsyncMock,
                 return_value={"success": True, "store_id": "999", "access_token": "tok-nuvem"},
             ), \
             patch("app.integrations.nuvemshop.create_nuvemshop_client", return_value=fake_client):
            response = await nuvemshop_oauth_redirect(code="auth-code", state="state-test-2")

        db.save_integration.assert_awaited_once()
        assert db.save_integration.call_args.kwargs["platform"] == "nuvemshop"
        db.create_site.assert_awaited_once()
        assert "connected=true" in response.headers["location"]


class TestNuvemshopExchangeCodeManualDoesNotOverwrite:

    @pytest.mark.asyncio
    async def test_rejects_when_vtex_already_connected(self):
        from app.main import nuvemshop_exchange_code_manual, NuvemshopManualCodeRequest

        db = _mock_db(sites=[{"id": "site-vtex", "platform": "vtex", "base_url": "https://vtex.example.com"}])
        fake_client = _fake_nuvemshop_client()

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch(
                 "app.integrations.nuvemshop.NuvemshopOAuth.exchange_code",
                 new_callable=AsyncMock,
                 return_value={"success": True, "store_id": "999", "access_token": "tok-nuvem"},
             ), \
             patch("app.integrations.nuvemshop.create_nuvemshop_client", return_value=fake_client):
            response = await nuvemshop_exchange_code_manual(
                NuvemshopManualCodeRequest(code="auth-code"),
                user={"user_id": "u1", "token": "t"},
            )

        db.save_integration.assert_not_awaited()
        db.create_site.assert_not_awaited()
        assert response.status_code == 409
