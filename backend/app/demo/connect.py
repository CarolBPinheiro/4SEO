"""Conecta uma loja (ou GSC) demo ao usuário autenticado."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException

from app.demo.clients import (
    create_demo_lojaintegrada_client,
    create_demo_nuvemshop_client,
    create_demo_shopify_client,
    create_demo_vtex_client,
)
from app.demo.config import (
    DEMO_GSC_REFRESH,
    DEMO_GSC_SITE,
    DEMO_GSC_TOKEN,
    DEMO_STORES,
    is_demo_mode,
)
from app.integrations.gsc import store_gsc_tokens

PLATFORMS = ("shopify", "nuvemshop", "vtex", "lojaintegrada")


def require_demo_mode() -> None:
    if not is_demo_mode():
        raise HTTPException(status_code=404, detail="Sandbox de demonstração desligado.")


async def connect_demo_platform(
    *,
    db: Any,
    user: Dict[str, Any],
    platform: str,
    cache_hooks: Dict[str, Any],
) -> Dict[str, Any]:
    require_demo_mode()
    platform = (platform or "").strip().lower()
    if platform == "gsc":
        return await connect_demo_gsc(user_id=user["user_id"])
    if platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail="Plataforma inválida.")

    existing = await db.list_sites_for_user(user["user_id"], limit=10)
    integration_sites = [
        s for s in existing if s.get("platform") in PLATFORMS
    ]
    if integration_sites:
        raise HTTPException(
            status_code=409,
            detail="Você já possui uma loja conectada. Desconecte a atual antes de conectar outra.",
        )
    delete_url_only = cache_hooks.get("delete_url_only_sites")
    if delete_url_only:
        await delete_url_only(db, user["user_id"])

    cfg = DEMO_STORES[platform]
    created = await db.create_site(
        base_url=cfg["base_url"],
        platform=platform,
        user_id=user["user_id"],
    )
    metadata: Dict[str, Any] = {"demo": True}
    store_url = cfg.get("store_url") or cfg["base_url"]
    token = cfg["token"]
    if platform == "vtex":
        metadata["account_name"] = cfg["account_name"]
        metadata["app_key"] = cfg["app_key"]
        store_url = cfg["account_name"]
    elif platform == "nuvemshop":
        metadata["store_id"] = cfg["store_id"]
        store_url = cfg["store_url"]

    await db.save_integration(
        user_id=user["user_id"],
        platform=platform,
        store_url=store_url,
        access_token=token,
        store_name=cfg["store_name"],
        metadata=metadata,
    )

    if platform == "shopify":
        from app.integrations.shopify_optimizer import ShopifySEOOptimizer

        client = create_demo_shopify_client(cfg["store_url"])
        optimizer = ShopifySEOOptimizer(client)
        cache_hooks["set_shopify_client"](cfg["base_url"], client, optimizer, user["user_id"])
        store_id = cfg["store_url"]
    elif platform == "nuvemshop":
        from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer

        client = create_demo_nuvemshop_client(cfg["store_id"])
        optimizer = NuvemshopOptimizer(client)
        cache_hooks["set_nuvemshop_client"](cfg["store_id"], client, optimizer, user["user_id"])
        store_id = cfg["store_id"]
    elif platform == "vtex":
        from app.integrations.vtex_optimizer import VtexSEOOptimizer

        client = create_demo_vtex_client(cfg["account_name"])
        optimizer = VtexSEOOptimizer(client)
        cache_hooks["set_vtex_client"](client.account_name, client, optimizer, user["user_id"])
        store_id = client.account_name
    else:
        from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer

        client = create_demo_lojaintegrada_client(cfg["token"])
        optimizer = LojaIntegradaSEOOptimizer(client)
        cache_hooks["set_li_client"](client.store_key, client, optimizer, user["user_id"])
        store_id = client.store_key

    return {
        "success": True,
        "demo": True,
        "platform": platform,
        "store_id": store_id,
        "site_id": str(created.get("id")) if created else None,
        "store": {
            "name": cfg["store_name"],
            "url": cfg["base_url"],
            "platform": platform,
        },
        "message": f"Loja demo {platform} conectada.",
    }


async def connect_demo_gsc(*, user_id: str) -> Dict[str, Any]:
    require_demo_mode()
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    await store_gsc_tokens(
        user_id=user_id,
        tokens={
            "access_token": DEMO_GSC_TOKEN,
            "refresh_token": DEMO_GSC_REFRESH,
            "expires_in": int(30 * 24 * 3600),
            "expires_at": expires.isoformat(),
        },
        site_url=DEMO_GSC_SITE,
    )
    return {
        "success": True,
        "demo": True,
        "platform": "gsc",
        "connected": True,
        "site_url": DEMO_GSC_SITE,
        "message": "Google Search Console demo conectado.",
    }
