# Como aplicar o schema de billing no Supabase do 4SEO
#
# Projeto: emnwonpdziqhtcfpuxxp
#
# Opção A — script (recomendado se você tiver Personal Access Token):
#   1. Crie um token em https://supabase.com/dashboard/account/tokens
#   2. No PowerShell:
#        $env:SUPABASE_ACCESS_TOKEN = "sbp_..."
#        npm run apply:billing-schema
#   3. Confirme:
#        npm run verify:billing-schema
#
# Opção B — SQL Editor (manual):
#   1. Abra https://supabase.com/dashboard/project/emnwonpdziqhtcfpuxxp/sql/new
#   2. Cole o conteúdo completo de `supabase/billing.sql` e clique em Run
#   3. Cole e rode também `supabase/migrations/20260812190000_subscription_trial.sql`
#      (colunas trial_ends_at / trial_started_at — necessárias para “Avaliação grátis”)
#   4. Confirme as tabelas: billing_checkouts, subscriptions, billing_webhook_events
#   5. npm run verify:billing-schema
#
# Depois configure no painel Asaas (Sandbox primeiro — ver docs/go-live/ASAAS_SANDBOX.md):
# - API Key → Render `ASAAS_API_KEY`
# - Webhook URL → `https://api.4seo.app/webhooks/asaas`
# - authToken → o mesmo valor de `ASAAS_WEBHOOK_TOKEN` no backend
# - Eventos: CHECKOUT_CREATED, CHECKOUT_PAID, CHECKOUT_CANCELED, CHECKOUT_EXPIRED
#   (+ SUBSCRIPTION_* / PAYMENT_* se desejar)
#
# Virada para produção: docs/go-live/ASAAS_PRODUCTION_CUTOVER.md
