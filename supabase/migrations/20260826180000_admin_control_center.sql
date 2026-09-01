-- Painel admin: chamados Typebot + histórico de mudanças de plano.
-- Somente service_role (backend). Sem policies para authenticated.

create table if not exists public.admin_support_tickets (
  id uuid primary key default gen_random_uuid(),
  typebot_result_id text unique,
  user_id uuid references auth.users(id) on delete set null,
  user_email text,
  user_name text,
  plan_id text,
  subject text not null default 'Chamado Typebot',
  message text,
  priority text not null default 'medium',
  status text not null default 'new',
  opened_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  resolved_at timestamptz,
  payload jsonb not null default '{}'::jsonb
);

create index if not exists admin_support_tickets_status_idx
  on public.admin_support_tickets (status);

create index if not exists admin_support_tickets_opened_at_idx
  on public.admin_support_tickets (opened_at desc);

create index if not exists admin_support_tickets_user_email_idx
  on public.admin_support_tickets (user_email);

alter table public.admin_support_tickets enable row level security;

create table if not exists public.admin_subscription_events (
  id uuid primary key default gen_random_uuid(),
  subscription_id uuid references public.subscriptions(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  action text not null,
  from_plan text,
  to_plan text,
  from_cycle text,
  to_cycle text,
  reason text,
  actor_user_id uuid references auth.users(id) on delete set null,
  actor_email text,
  created_at timestamptz not null default now()
);

create index if not exists admin_subscription_events_sub_idx
  on public.admin_subscription_events (subscription_id, created_at desc);

create index if not exists admin_subscription_events_created_at_idx
  on public.admin_subscription_events (created_at desc);

alter table public.admin_subscription_events enable row level security;
