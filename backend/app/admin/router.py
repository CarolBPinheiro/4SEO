"""Rotas do painel administrativo (/admin API)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.admin.deps import require_platform_admin
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminAuditListResponse,
    AdminCancelSubscriptionRequest,
    AdminChangePlanRequest,
    AdminHealthResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminOverviewResponse,
    AdminSubscriptionListResponse,
    AdminTicketListResponse,
    AdminTicketPatchRequest,
    AdminUserDetailResponse,
    AdminUserListResponse,
)
from app.admin.service import AdminActionError, AdminService, is_uuid
from app.admin.session import (
    admin_login_configured,
    is_admin_login_email,
    issue_admin_token,
    password_matches,
)
from app.billing.rate_limit import admin_login_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": True, "detail": message, "message": message},
    )


def _action_error(exc: AdminActionError) -> JSONResponse:
    return _error(exc.message, exc.status_code)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest, request: Request):
    if not admin_login_limiter.allow(f"admin-login:{_client_ip(request)}"):
        return _error("Muitas tentativas. Aguarde um minuto.", 429)
    if not admin_login_configured():
        logger.warning("ADMIN_LOGIN_EMAIL/ADMIN_PASSWORD ausentes — login admin bloqueado")
        return _error("Painel administrativo não configurado.", 503)
    email = body.email.strip().lower()
    if not is_admin_login_email(email) or not password_matches(body.password):
        return _error("E-mail ou senha inválidos.", 401)
    token = issue_admin_token(email)
    await AdminRepository().insert_audit(
        actor_user_id=None,
        actor_email=email,
        action="admin.login",
        meta={"source": "admin_password"},
    )
    return AdminLoginResponse(ok=True, token=token, email=email)


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
    if not is_uuid(user_id):
        return _error("Usuário inválido.", 400)
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
    plan: Optional[str] = Query(None, max_length=32),
    expiringDays: Optional[int] = Query(None, ge=1, le=90),
    page: int = Query(1, ge=1),
    perPage: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        result = await service.list_subscriptions_page(
            status=status,
            plan_id=plan,
            expiring_days=expiringDays,
            page=page,
            per_page=perPage,
        )
        await AdminRepository().insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.subscriptions.list",
            meta={"status": status, "plan": plan, "page": page},
        )
        return AdminSubscriptionListResponse(**result)
    except Exception:
        logger.exception("admin subscriptions list failed")
        return _error("Falha ao listar assinaturas.", 500)


@router.post("/subscriptions/{subscription_id}/change-plan")
async def admin_change_plan(
    subscription_id: str,
    body: AdminChangePlanRequest,
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        updated = await service.change_plan(
            subscription_id,
            plan_id=body.planId,
            billing_cycle=body.billingCycle,
            reason=body.reason,
            admin=admin,
        )
        return {"ok": True, "subscription": updated}
    except AdminActionError as exc:
        return _action_error(exc)
    except Exception:
        logger.exception("admin change plan failed")
        return _error("Falha ao alterar o plano.", 500)


@router.post("/subscriptions/{subscription_id}/cancel")
async def admin_cancel_subscription(
    subscription_id: str,
    body: AdminCancelSubscriptionRequest,
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        updated = await service.cancel_subscription(
            subscription_id,
            reason=body.reason,
            admin=admin,
        )
        return {"ok": True, "subscription": updated}
    except AdminActionError as exc:
        return _action_error(exc)
    except Exception:
        logger.exception("admin cancel subscription failed")
        return _error("Falha ao cancelar a assinatura.", 500)


@router.get("/tickets", response_model=AdminTicketListResponse)
async def admin_tickets(admin: dict = Depends(require_platform_admin)):
    service = AdminService()
    try:
        result = await service.list_tickets()
        await AdminRepository().insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.tickets.list",
        )
        return result
    except Exception:
        logger.exception("admin tickets list failed")
        return _error("Falha ao listar chamados.", 500)


@router.patch("/tickets/{ticket_id}")
async def admin_patch_ticket(
    ticket_id: str,
    body: AdminTicketPatchRequest,
    admin: dict = Depends(require_platform_admin),
):
    service = AdminService()
    try:
        updated = await service.patch_ticket(
            ticket_id,
            status=body.status,
            priority=body.priority,
            admin=admin,
        )
        return {"ok": True, "ticket": updated}
    except AdminActionError as exc:
        return _action_error(exc)
    except Exception:
        logger.exception("admin ticket patch failed")
        return _error("Falha ao atualizar o chamado.", 500)


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
