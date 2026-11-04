# Supabase setup for Noble POS Cloud

This app is an internet-connected Flet client. Supabase holds the shared shop data and authenticates every device. Use a separate Supabase project for development and production.

## 1. Create or upgrade the database schema

1. Open the exact Supabase project configured in `src/config.py`.
2. Open **SQL Editor** in the Supabase dashboard and choose a new query.
3. Copy the complete current `src/core/schema.sql` from this app into the SQL editor and click **Run**. It includes additive upgrades for the earlier Noble POS MVP schema, including `inventory.barcode`, while preserving existing shops and sales. Do not delete the tables or create a new project to fix a missing-column error.
4. If this is a brand-new Supabase project, the same full schema file creates the tables as well.

Back up the project before changing a database that contains valuable live business data.
4. In **Authentication → URL Configuration**, set the production redirect/site URL for the web client. Configure email confirmation and SMTP before inviting real customers.

The SQL enables row-level security on every tenant data table. Do not disable these policies and never put a `service_role` secret in the Flet app.

## 2. Connect the Flet client

Copy the project's URL and public/publishable anon key from the Supabase API settings into `src/config.py`:

- `SUPABASE_URL`: the project URL, for example `https://your-project.supabase.co`
- `SUPABASE_ANON_KEY`: the public anon/publishable key

The anon key is not an authorization boundary; the database RLS policies are. Treat a missing or incorrect policy as a release blocker.

## 3. Admin-managed subscriptions

New shops start in `trial`. For manual activation or suspension, an authorized service administrator can update `shops.subscription_status` to `active`, `past_due`, or `suspended` in the Supabase dashboard. Automatic billing and an admin portal are not part of this initial implementation. Keep any administrator credentials out of this client app.

## Current first-release scope

Included in the current implementation: owner/staff sign-up and sign-in, shop invites and roles, tenant-isolated inventory, barcode field/search, TZS checkout with cash/mobile-money/card/credit recording, atomic stock validation, configurable tax and discounts, customer balances and debt payments, expenses, receipts, sale voiding with stock restoration, basic recent-sales reporting, audit/stock movement records, and manual subscription status.

Not included yet: offline operation, automatic payment processing or subscription billing, printer/EFD integration, audited tax/accounting exports, or a hosted service-admin portal. Before commercial launch in Tanzania, verify fiscal receipt/EFD, tax, privacy, and retention requirements with the relevant official sources and qualified local advisers; this starter does not assert TRA compliance.

## Release checks

Before accepting paying shops, use separate staging and production Supabase projects; test RLS with two unrelated shop accounts; test simultaneous checkout for the last unit; configure backups and recovery; configure email delivery, monitoring, and support; and complete platform-specific signing/deployment. Never test tenant isolation only with the project owner/service role, because that bypasses normal client restrictions.
