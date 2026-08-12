"""Testes do OAuth Shopify (normalização de domínio, HMAC e início do fluxo)."""
import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def shopify_oauth_env(monkeypatch):
    monkeypatch.setenv("SHOPIFY_API_KEY", "test-client-id")
    monkeypatch.setenv("SHOPIFY_API_SECRET", "test-client-secret")
    # Recarrega constantes lidas no import do módulo
    import app.integrations.shopify as shopify_mod
    monkeypatch.setattr(shopify_mod, "SHOPIFY_API_KEY", "test-client-id")
    monkeypatch.setattr(shopify_mod, "SHOPIFY_API_SECRET", "test-client-secret")
    shopify_mod._shopify_oauth_states.clear()
    yield
    shopify_mod._shopify_oauth_states.clear()


class TestNormalizeShopDomain:
    def test_handle_only(self):
        from app.integrations.shopify import normalize_shop_domain
        assert normalize_shop_domain("teste-seo-2") == "teste-seo-2.myshopify.com"

    def test_full_domain(self):
        from app.integrations.shopify import normalize_shop_domain
        assert normalize_shop_domain("teste-seo-2.myshopify.com") == "teste-seo-2.myshopify.com"

    def test_with_https(self):
        from app.integrations.shopify import normalize_shop_domain
        assert normalize_shop_domain("https://teste-seo-2.myshopify.com/") == "teste-seo-2.myshopify.com"

    def test_rejects_invalid(self):
        from app.integrations.shopify import normalize_shop_domain
        with pytest.raises(ValueError):
            normalize_shop_domain("https://evil.com")


class TestShopifyHmac:
    def test_valid_hmac(self):
        from app.integrations.shopify import ShopifyOAuth

        params = {
            "code": "0907a61c0c8d55e99db179b68161bc00",
            "shop": "teste-seo-2.myshopify.com",
            "state": "nonce123",
            "timestamp": "1337178173",
        }
        message = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        digest = hmac.new(
            b"test-client-secret",
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["hmac"] = digest
        assert ShopifyOAuth.verify_hmac(params) is True

    def test_invalid_hmac(self):
        from app.integrations.shopify import ShopifyOAuth
        params = {
            "code": "abc",
            "shop": "loja.myshopify.com",
            "state": "x",
            "timestamp": "1",
            "hmac": "0" * 64,
        }
        assert ShopifyOAuth.verify_hmac(params) is False


class TestShopifyGenerateAuthUrl:
    def test_builds_authorize_url(self):
        from app.integrations.shopify import ShopifyOAuth, _shopify_oauth_states

        result = ShopifyOAuth.generate_auth_url(
            "teste-seo-2",
            "http://localhost:8000/api/shopify/oauth-redirect",
        )
        assert result["shop"] == "teste-seo-2.myshopify.com"
        assert result["state"] in _shopify_oauth_states
        assert "teste-seo-2.myshopify.com/admin/oauth/authorize" in result["auth_url"]
        assert "client_id=test-client-id" in result["auth_url"]
        assert "write_products" in result["auth_url"]


class TestShopifyOAuthRedirectDoesNotOverwrite:
    @pytest.mark.asyncio
    async def test_skips_save_when_nuvemshop_already_connected(self):
        from app.main import shopify_oauth_redirect
        from app.integrations.shopify import _shopify_oauth_states, ShopifyOAuth

        db = MagicMock()
        db.list_sites_for_user = AsyncMock(
            return_value=[{"id": "n1", "platform": "nuvemshop", "base_url": "https://x.com"}]
        )
        db.create_site = AsyncMock()
        db.save_integration = AsyncMock()

        _shopify_oauth_states["st-1"] = {
            "user_id": "u1",
            "token": "t",
            "shop": "loja.myshopify.com",
        }

        params = {
            "code": "auth-code",
            "shop": "loja.myshopify.com",
            "state": "st-1",
            "timestamp": "1",
        }
        message = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        params["hmac"] = hmac.new(
            b"test-client-secret", message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        request = MagicMock()
        request.query_params = params

        fake_client = MagicMock()
        fake_client.test_connection = AsyncMock(
            return_value={"success": True, "shop_name": "Loja"}
        )

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch.object(
                 ShopifyOAuth,
                 "exchange_code",
                 new_callable=AsyncMock,
                 return_value={
                     "success": True,
                     "shop": "loja.myshopify.com",
                     "access_token": "tok",
                     "scope": "write_products",
                 },
             ), \
             patch("app.integrations.shopify.create_shopify_client", return_value=fake_client):
            response = await shopify_oauth_redirect(
                request=request,
                code=params["code"],
                shop=params["shop"],
                state=params["state"],
                hmac=params["hmac"],
            )

        db.save_integration.assert_not_awaited()
        db.create_site.assert_not_awaited()
        assert "error=already_connected" in response.headers["location"]
