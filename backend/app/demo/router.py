"""Rotas HTTP do sandbox de demonstração."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.demo.config import is_demo_mode
from app.demo.connect import connect_demo_platform, require_demo_mode

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoConnectRequest(BaseModel):
    platform: str = Field(..., min_length=2, max_length=32)


def get_demo_cache_hooks() -> dict:
    from app import main as app_main

    return {
        "delete_url_only_sites": app_main._delete_url_only_sites,
        "set_shopify_client": app_main.set_shopify_client,
        "set_nuvemshop_client": app_main.set_nuvemshop_client,
        "set_vtex_client": lambda account, client, optimizer, user_id: app_main._vtex_clients_cache.__setitem__(
            account,
            {"client": client, "optimizer": optimizer, "user_id": user_id},
        ),
        "set_li_client": lambda key, client, optimizer, user_id: app_main._li_clients_cache.__setitem__(
            key,
            {"client": client, "optimizer": optimizer, "user_id": user_id},
        ),
    }


@router.get("/status")
async def demo_status():
    require_demo_mode()
    return {"enabled": is_demo_mode()}


@router.post("/connect")
async def demo_connect(
    payload: DemoConnectRequest,
    user: dict = Depends(get_current_user),
):
    from app.supabase_client import get_supabase_for_user

    require_demo_mode()
    db = get_supabase_for_user(user["token"])
    return await connect_demo_platform(
        db=db,
        user=user,
        platform=payload.platform,
        cache_hooks=get_demo_cache_hooks(),
    )


@router.post("/gsc")
async def demo_connect_gsc(user: dict = Depends(get_current_user)):
    from app.supabase_client import get_supabase_for_user

    require_demo_mode()
    db = get_supabase_for_user(user["token"])
    return await connect_demo_platform(
        db=db,
        user=user,
        platform="gsc",
        cache_hooks=get_demo_cache_hooks(),
    )
