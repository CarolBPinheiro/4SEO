-- Trial gratuito 7 dias (sem cartão) — aditivo
-- Aplicar no Supabase: SQL Editor → Run

alter table public.subscriptions
  add column if not exists trial_ends_at timestamptz;

alter table public.subscriptions
  add column if not exists trial_started_at timestamptz;

create index if not exists subscriptions_trial_ends_at_idx
  on public.subscriptions (trial_ends_at)
  where trial_ends_at is not null;
