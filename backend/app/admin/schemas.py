"""DTOs do painel administrativo."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=1, max_length=200)


class AdminLoginResponse(BaseModel):
    ok: bool = True
    token: str
    email: str


class AdminOverviewResponse(BaseModel):
    usersTotal: int = 0
    usersNewInPeriod: int = 0
    usersWithActiveSubscription: int = 0
    usersWithoutSubscription: int = 0
    subscribersTotal: int = 0
    subscribersActive: int = 0
    subscribersInactive: int = 0
    subscribersCanceled: int = 0
    subscriptionsByStatus: Dict[str, int] = Field(default_factory=dict)
    subscriptionsNewInPeriod: int = 0
    subscriptionsCanceledInPeriod: int = 0
    netNewInPeriod: int = 0
    estimatedMrr: float = 0.0
    mrrByPlan: Dict[str, float] = Field(default_factory=dict)
    usersByPlan: Dict[str, int] = Field(default_factory=dict)
    plans: List[Dict[str, Any]] = Field(default_factory=list)
    arpu: float = 0.0
    churnRate: float = 0.0
    growthRate: float = 0.0
    sitesTotal: int = 0
    unprocessedWebhooks: int = 0
    expiringSoon: List[Dict[str, Any]] = Field(default_factory=list)
    ticketsByStatus: Dict[str, int] = Field(default_factory=dict)
    ticketsOpen: int = 0
    series: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[Dict[str, str]] = Field(default_factory=list)
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
    billingCycle: Optional[str] = None
    amount: Optional[float] = None
    currentPeriodEnd: Optional[str] = None
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
    planEvents: List[Dict[str, Any]] = Field(default_factory=list)
    tickets: List[Dict[str, Any]] = Field(default_factory=list)


class AdminSubscriptionListResponse(BaseModel):
    items: List[Dict[str, Any]]
    page: int
    perPage: int
    total: int = 0


class AdminChangePlanRequest(BaseModel):
    planId: str = Field(..., min_length=1, max_length=32)
    billingCycle: Optional[str] = Field(None, max_length=32)
    reason: Optional[str] = Field(None, max_length=500)


class AdminCancelSubscriptionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class AdminTicketListResponse(BaseModel):
    items: List[Dict[str, Any]]
    counts: Dict[str, int] = Field(default_factory=dict)


class AdminTicketPatchRequest(BaseModel):
    status: Optional[str] = Field(None, max_length=32)
    priority: Optional[str] = Field(None, max_length=16)


class AdminHealthResponse(BaseModel):
    app: str = "ok"
    database: str = "unknown"
    asaasConfigured: bool = False
    asaasBaseUrl: Optional[str] = None
    webhookTokenConfigured: bool = False
    typebotWebhookConfigured: bool = False
    adminAllowlistConfigured: bool = False
    unprocessedWebhooks: int = 0
    recentWebhooks: List[Dict[str, Any]] = Field(default_factory=list)
    docsExposed: bool = False
    sitesTotal: int = 0
    pastDueSubscriptions: int = 0
    ticketsOpen: int = 0


class AdminAuditListResponse(BaseModel):
    items: List[Dict[str, Any]]
