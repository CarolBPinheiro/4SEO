-- SiteCan PRO — schema completo do banco de dados
--
-- Reconstruído em 2026-07-19 a partir do uso real do código (não existia
-- schema versionado neste repo até então — ver backend/app/supabase_client.py
-- e backend/app/integrations/gsc.py como fonte de verdade). Verificado por
-- uma segunda leitura independente do código antes de ser aplicado.
--
-- Como aplicar num projeto Supabase novo: Dashboard → SQL Editor → cole este
-- arquivo inteiro → Run. Idempotência: NÃO é idempotente (usa `create table`
-- sem `if not exists`) — rode uma única vez num projeto vazio.
--
-- auth.users é gerenciada pela própria Supabase Auth, não precisa ser criada.

create extension if not exists pgcrypto;

-- ==================== sites ====================
create table public.sites (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  base_url text not null,
  platform text,
  store_id text,
  store_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.sites enable row level security;

create policy "sites_select_own" on public.sites
  for select using (auth.uid() = user_id);
create policy "sites_insert_own" on public.sites
  for insert with check (auth.uid() = user_id);
create policy "sites_update_own" on public.sites
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "sites_delete_own" on public.sites
  for delete using (auth.uid() = user_id);

-- ==================== pages (ownership via sites.user_id) ====================
create table public.pages (
  id uuid primary key default gen_random_uuid(),
  site_id uuid not null references public.sites(id) on delete cascade,
  url text not null,
  title text,
  meta_description text,
  h1 text,
  issues jsonb not null default '{}'::jsonb,
  score integer not null default 0,
  last_scanned_at timestamptz,
  created_at timestamptz not null default now(),
  unique (site_id, url)
);

alter table public.pages enable row level security;

create policy "pages_select_own" on public.pages
  for select using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "pages_insert_own" on public.pages
  for insert with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "pages_update_own" on public.pages
  for update using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "pages_delete_own" on public.pages
  for delete using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));

-- ==================== seo_tasks (ownership via sites.user_id) ====================
create table public.seo_tasks (
  id uuid primary key default gen_random_uuid(),
  site_id uuid not null references public.sites(id) on delete cascade,
  page_id uuid references public.pages(id) on delete cascade,
  issue_type text not null,
  description text,
  suggestion text,
  priority text default 'medium',
  status text not null default 'pending',
  ai_generated boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

alter table public.seo_tasks enable row level security;

create policy "seo_tasks_select_own" on public.seo_tasks
  for select using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "seo_tasks_insert_own" on public.seo_tasks
  for insert with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "seo_tasks_update_own" on public.seo_tasks
  for update using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "seo_tasks_delete_own" on public.seo_tasks
  for delete using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));

-- ==================== scan_runs (ownership via sites.user_id) ====================
create table public.scan_runs (
  id uuid primary key default gen_random_uuid(),
  site_id uuid not null references public.sites(id) on delete cascade,
  status text not null default 'running',
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  pages_scanned integer,
  tasks_created integer,
  avg_score integer,
  issues_summary jsonb
);

alter table public.scan_runs enable row level security;

create policy "scan_runs_select_own" on public.scan_runs
  for select using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "scan_runs_insert_own" on public.scan_runs
  for insert with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));
create policy "scan_runs_update_own" on public.scan_runs
  for update using (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.sites s where s.id = site_id and s.user_id = auth.uid()));

-- ==================== user_integrations (1 linha por usuário, upsert por user_id) ====================
create table public.user_integrations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  platform text not null,
  store_url text,
  access_token text,
  store_name text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_integrations enable row level security;

create policy "user_integrations_select_own" on public.user_integrations
  for select using (auth.uid() = user_id);
create policy "user_integrations_insert_own" on public.user_integrations
  for insert with check (auth.uid() = user_id);
create policy "user_integrations_update_own" on public.user_integrations
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "user_integrations_delete_own" on public.user_integrations
  for delete using (auth.uid() = user_id);

-- ==================== oauth_states (persistência de state OAuth entre restarts) ====================
create table public.oauth_states (
  id uuid primary key default gen_random_uuid(),
  state text not null unique,
  user_id uuid not null references auth.users(id) on delete cascade,
  user_token text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

alter table public.oauth_states enable row level security;

create policy "oauth_states_select_own" on public.oauth_states
  for select using (auth.uid() = user_id);
create policy "oauth_states_insert_own" on public.oauth_states
  for insert with check (auth.uid() = user_id);
create policy "oauth_states_delete_own" on public.oauth_states
  for delete using (auth.uid() = user_id);

-- ==================== user_search_terms ====================
create table public.user_search_terms (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  term text not null,
  created_at timestamptz not null default now()
);

alter table public.user_search_terms enable row level security;

create policy "user_search_terms_select_own" on public.user_search_terms
  for select using (auth.uid() = user_id);
create policy "user_search_terms_insert_own" on public.user_search_terms
  for insert with check (auth.uid() = user_id);
create policy "user_search_terms_delete_own" on public.user_search_terms
  for delete using (auth.uid() = user_id);

-- ==================== term_snapshots ====================
create table public.term_snapshots (
  id uuid primary key default gen_random_uuid(),
  term_id uuid not null references public.user_search_terms(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  interest_over_time jsonb,
  related_queries jsonb,
  date date not null,
  created_at timestamptz not null default now()
);

alter table public.term_snapshots enable row level security;

create policy "term_snapshots_select_own" on public.term_snapshots
  for select using (auth.uid() = user_id);
create policy "term_snapshots_insert_own" on public.term_snapshots
  for insert with check (auth.uid() = user_id);

-- ==================== daily_snapshots (1 por usuário/dia) ====================
create table public.daily_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null,
  impressions integer default 0,
  clicks integer default 0,
  ctr numeric default 0,
  position_avg numeric default 0,
  pages_count integer default 0,
  unique (user_id, date)
);

alter table public.daily_snapshots enable row level security;

create policy "daily_snapshots_select_own" on public.daily_snapshots
  for select using (auth.uid() = user_id);
create policy "daily_snapshots_insert_own" on public.daily_snapshots
  for insert with check (auth.uid() = user_id);
create policy "daily_snapshots_update_own" on public.daily_snapshots
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ==================== gsc_tokens (acessada só via service_role no backend, RLS por precaução) ====================
create table public.gsc_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  site_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.gsc_tokens enable row level security;

create policy "gsc_tokens_select_own" on public.gsc_tokens
  for select using (auth.uid() = user_id);
create policy "gsc_tokens_insert_own" on public.gsc_tokens
  for insert with check (auth.uid() = user_id);
create policy "gsc_tokens_update_own" on public.gsc_tokens
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "gsc_tokens_delete_own" on public.gsc_tokens
  for delete using (auth.uid() = user_id);

-- Billing / Asaas: ver supabase/billing.sql (billing_checkouts, subscriptions, billing_webhook_events)

