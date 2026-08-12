"""DTOs do painel administrativo."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminOverviewResponse(BaseModel):
    usersTotal: int = 0
    usersNewInPeriod: int = 0
    usersWithActiveSubscription: int = 0
    usersWithoutSubscription: int = 0
    subscriptionsByStatus: Dict[str, int] = Field(default_factory=dict)
    subscriptionsNewInPeriod: int = 0
    estimatedMrr: float = 0.0
    sitesTotal: int = 0
    unprocessedWebhooks: int = 0
    series: List[Dict[str, Any]] = Field(default_factory=list)
    periodDays: int = 30


class AdminUserListItem(BaseModel):
    id: str
    email: Optional[str] = None
    createdAt: Optional[str] = None
    lastSignInAt: Optional[str] = None
    emailConfirmedAt: Optional[str] = None
    banned: bool = False
    subscriptionStatus: str = "none"
    planId: Optional[str] = None
    asaasCustomerId: Optional[str] = None
    asaasSubscriptionId: Optional[str] = None


class AdminUserListResponse(BaseModel):
    items: List[AdminUserListItem]
    page: int
    perPage: int
    total: int


class AdminUserDetailResponse(BaseModel):
    id: str
    email: Optional[str] = None
    createdAt: Optional[str] = None
    lastSignInAt: Optional[str] = None
    emailConfirmedAt: Optional[str] = None
    banned: bool = False
    subscriptions: List[Dict[str, Any]] = Field(default_factory=list)
    checkouts: List[Dict[str, Any]] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)


class AdminSubscriptionListResponse(BaseModel):
    items: List[Dict[str, Any]]
    page: int
    perPage: int


class AdminHealthResponse(BaseModel):
    app: str = "ok"
    database: str = "unknown"
    asaasConfigured: bool = False
    asaasBaseUrl: Optional[str] = None
    webhookTokenConfigured: bool = False
    adminAllowlistConfigured: bool = False
    unprocessedWebhooks: int = 0
    recentWebhooks: List[Dict[str, Any]] = Field(default_factory=list)
    docsExposed: bool = False


class AdminAuditListResponse(BaseModel):
    items: List[Dict[str, Any]]
