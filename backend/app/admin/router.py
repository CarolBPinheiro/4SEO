"""Rotas do painel administrativo (/admin API)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.admin.deps import require_platform_admin
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminAuditListResponse,
    AdminHealthResponse,
    AdminOverviewResponse,
    AdminSubscriptionListResponse,
    AdminUserDetailResponse,
    AdminUserListResponse,
)
from app.admin.service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": True, "detail": message, "message": message},
    )


@router.get("/me")
async def admin_me(admin: dict = Depends(require_platform_admin)):
    return {
        "ok": True,
        "userId": admin.get("user_id"),
        "email": admin.get("email"),
    }


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    period: str = Query("30d", pattern="^(7d|30d|90d|12m)$"),
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        overview = await service.overview(period)
        await AdminRepository().insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.overview.view",
            meta={"period": period},
        )
        return overview
    except Exception:
        logger.exception("admin overview failed")
        return _error("Falha ao carregar visão geral.", 500)


@router.get("/users", response_model=AdminUserListResponse)
async def admin_users(
    page: int = Query(1, ge=1),
    perPage: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None, max_length=200),
    subscription: Optional[str] = Query("all"),
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        result = await service.list_users(
            page=page,
            per_page=perPage,
            q=q,
            subscription_filter=subscription,
        )
        await AdminRepository().insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.users.list",
            meta={"page": page, "q": q},
        )
        return result
    except Exception:
        logger.exception("admin users list failed")
        return _error("Falha ao listar usuários.", 500)


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def admin_user_detail(
    user_id: str,
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        detail = await service.user_detail(user_id)
        if not detail:
            return _error("Usuário não encontrado.", 404)
        await AdminRepository().insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.user.view",
            target_type="user",
            target_id=user_id,
        )
        return detail
    except Exception:
        logger.exception("admin user detail failed")
        return _error("Falha ao carregar usuário.", 500)


@router.get("/subscriptions", response_model=AdminSubscriptionListResponse)
async def admin_subscriptions(
    status: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    perPage: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_platform_admin),
):
    repo = AdminRepository()
    try:
        offset = (page - 1) * perPage
        st = None if not status or status == "all" else status
        items = await repo.list_subscriptions(status=st, limit=perPage, offset=offset)
        await repo.insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.subscriptions.list",
            meta={"status": status, "page": page},
        )
        return AdminSubscriptionListResponse(items=items, page=page, perPage=perPage)
    except Exception:
        logger.exception("admin subscriptions list failed")
        return _error("Falha ao listar assinaturas.", 500)


@router.get("/health", response_model=AdminHealthResponse)
async def admin_health(admin: dict = Depends(require_platform_admin)):
    service = AdminService()
    try:
        return await service.health()
    except Exception:
        logger.exception("admin health failed")
        return _error("Falha ao carregar saúde da plataforma.", 500)


@router.get("/audit", response_model=AdminAuditListResponse)
async def admin_audit(
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_platform_admin),
):
    repo = AdminRepository()
    try:
        items = await repo.list_audit(limit=limit)
        return AdminAuditListResponse(items=items)
    except Exception:
        logger.exception("admin audit list failed")
        return _error("Falha ao carregar audit log.", 500)
