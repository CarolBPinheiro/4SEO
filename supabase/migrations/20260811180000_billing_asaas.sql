-- Billing / Asaas — tabelas aditivas (idempotente)
-- Aplicar no Supabase: SQL Editor → Run
-- Fonte: docs/asaas-backend-contract.md

-- ==================== billing_checkouts ====================
create table if not exists public.billing_checkouts (
  id uuid primary key default gen_random_uuid(),
  external_reference text not null unique,
  asaas_checkout_id text not null unique,
  checkout_url text,
  plan_id text not null,
  billing_cycle text not null,
  amount numeric(12, 2) not null,
  currency text not null default 'BRL',
  status text not null default 'pending',
  user_id uuid references auth.users(id) on delete set null,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists billing_checkouts_user_id_idx
  on public.billing_checkouts (user_id);
create index if not exists billing_checkouts_status_idx
  on public.billing_checkouts (status);

alter table public.billing_checkouts enable row level security;

drop policy if exists "billing_checkouts_select_own" on public.billing_checkouts;
create policy "billing_checkouts_select_own" on public.billing_checkouts
  for select using (auth.uid() = user_id);

-- Escrita apenas via service_role (backend). Sem policies de insert/update para authenticated.

-- ==================== subscriptions ====================
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  plan_id text not null,
  billing_cycle text not null,
  status text not null default 'pending',
  asaas_checkout_id text,
  asaas_subscription_id text unique,
  asaas_customer_id text,
  amount numeric(12, 2),
  currency text not null default 'BRL',
  current_period_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists subscriptions_user_id_idx
  on public.subscriptions (user_id);
create index if not exists subscriptions_status_idx
  on public.subscriptions (status);
create index if not exists subscriptions_asaas_checkout_id_idx
  on public.subscriptions (asaas_checkout_id);

alter table public.subscriptions enable row level security;

drop policy if exists "subscriptions_select_own" on public.subscriptions;
create policy "subscriptions_select_own" on public.subscriptions
  for select using (auth.uid() = user_id);

-- ==================== billing_webhook_events (idempotência) ====================
create table if not exists public.billing_webhook_events (
  id uuid primary key default gen_random_uuid(),
  event_id text not null unique,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  received_at timestamptz not null default now(),
  processed_at timestamptz
);

create index if not exists billing_webhook_events_event_type_idx
  on public.billing_webhook_events (event_type);

alter table public.billing_webhook_events enable row level security;
-- Sem policies para authenticated: somente service_role acessa.
