"""Guardas e clients do sandbox DEMO_MODE."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.demo.catalog import fresh_state
from app.demo.clients import DemoShopifyClient, create_demo_nuvemshop_client
from app.demo.config import DemoModeError, assert_demo_safe, is_demo_mode, is_demo_token
from app.demo.connect import connect_demo_platform, require_demo_mode
from app.demo import store as demo_store
from app.demo.scan import crawl_demo_site
from app.integrations.shopify import create_shopify_client


def test_demo_mode_off_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert is_demo_mode() is False
    assert_demo_safe()


def test_demo_mode_refuses_production(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:8080")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
    with pytest.raises(DemoModeError, match="production"):
        assert_demo_safe()


def test_demo_mode_refuses_non_localhost(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("FRONTEND_URL", "https://4seo.app")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
    with pytest.raises(DemoModeError, match="FRONTEND_URL"):
        assert_demo_safe()


def test_demo_mode_allows_localhost(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:8080")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
    assert_demo_safe()
    assert is_demo_token("demo_shopify_token") is True
    assert is_demo_token("shpat_live") is False


@pytest.mark.asyncio
async def test_demo_shopify_list_apply_rollback():
    demo_store.reset_state()
    client = DemoShopifyClient("demo-4seo.myshopify.com", "demo_shopify_token")
    products = await client.get_products()
    assert len(products) >= 8
    target = next(p for p in products if p.id == 1)
    original = target.title
    result = await client.apply_proposals_direct(
        [
            {
                "id": "p1",
                "product_id": 1,
                "optimization_type": "title",
                "field_name": "title",
                "original_value": original,
                "proposed_value": "Tênis running feminino DemoSport",
                "content_type": "product",
            }
        ]
    )
    assert result["applied"] >= 1
    updated = await client.get_product(1)
    assert updated.title == "Tênis running feminino DemoSport"
    rolled = await client.rollback_all()
    assert rolled["rolled_back"] >= 1
    restored = await client.get_product(1)
    assert restored.title == original


@pytest.mark.asyncio
async def test_demo_nuvemshop_list_products():
    demo_store.reset_state()
    client = create_demo_nuvemshop_client()
    store = await client.get_store()
    assert store.name
    products = await client.get_products()
    assert len(products) >= 8


def test_demo_scan_fixture():
    result = crawl_demo_site("https://demo-4seo.lojavirtualnuvem.com.br", max_pages=20)
    assert result["pages_analyzed"] >= 10
    assert result["average_score"] > 0
    assert result["issues_summary"]
    first = result["pages"][0]
    assert first["url"].startswith("https://")
    assert "issues" in first


def test_fresh_catalog_has_seo_issues():
    state = fresh_state()
    broken = [p for p in state["products"] if not p.get("seo_title")]
    assert len(broken) >= 4


def test_create_shopify_client_uses_demo_token():
    client = create_shopify_client(
        shop_url="demo-4seo.myshopify.com",
        access_token="demo_shopify_token",
    )
    assert isinstance(client, DemoShopifyClient)


def test_require_demo_mode_404_when_off(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_demo_mode()
    assert exc.value.status_code == 404


def _connect_hooks() -> dict:
    return {
        "delete_url_only_sites": AsyncMock(),
        "set_shopify_client": MagicMock(),
        "set_nuvemshop_client": MagicMock(),
        "set_vtex_client": MagicMock(),
        "set_li_client": MagicMock(),
    }


@pytest.mark.asyncio
async def test_connect_demo_shopify(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(return_value=[])
    db.create_site = AsyncMock(return_value={"id": "site-1"})
    db.save_integration = AsyncMock()
    hooks = _connect_hooks()

    result = await connect_demo_platform(
        db=db,
        user={"user_id": "u1"},
        platform="shopify",
        cache_hooks=hooks,
    )

    assert result["success"] is True
    assert result["demo"] is True
    assert result["platform"] == "shopify"
    db.save_integration.assert_awaited()
    token = db.save_integration.await_args.kwargs["access_token"]
    assert token.startswith("demo_")
    hooks["set_shopify_client"].assert_called_once()


@pytest.mark.asyncio
async def test_connect_demo_conflict_when_store_exists(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(
        return_value=[{"id": "n1", "platform": "nuvemshop"}]
    )
    db.create_site = AsyncMock()
    db.save_integration = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await connect_demo_platform(
            db=db,
            user={"user_id": "u1"},
            platform="shopify",
            cache_hooks=_connect_hooks(),
        )
    assert exc.value.status_code == 409
    db.create_site.assert_not_awaited()


@pytest.mark.asyncio
async def test_connect_demo_gsc(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    db = MagicMock()
    with patch("app.demo.connect.store_gsc_tokens", new_callable=AsyncMock) as store_tokens:
        result = await connect_demo_platform(
            db=db,
            user={"user_id": "u1"},
            platform="gsc",
            cache_hooks=_connect_hooks(),
        )
    assert result["success"] is True
    assert result["platform"] == "gsc"
    store_tokens.assert_awaited()
    token = store_tokens.await_args.kwargs["tokens"]["access_token"]
    assert token.startswith("demo_")
