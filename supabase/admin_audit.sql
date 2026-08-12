-- Espelho da migration 20260812180000_admin_audit_log.sql (aplicar via SQL Editor se necessário)

create table if not exists public.admin_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references auth.users(id) on delete set null,
  actor_email text,
  action text not null,
  target_type text,
  target_id text,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists admin_audit_log_created_at_idx
  on public.admin_audit_log (created_at desc);

create index if not exists admin_audit_log_actor_user_id_idx
  on public.admin_audit_log (actor_user_id);

create index if not exists admin_audit_log_action_idx
  on public.admin_audit_log (action);

alter table public.admin_audit_log enable row level security;
