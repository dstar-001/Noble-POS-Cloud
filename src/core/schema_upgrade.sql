-- Upgrade an existing Noble POS Supabase project to the current app schema.
-- Run this in Supabase SQL Editor. It preserves the shops and sales already created.
-- Do not run against a different Supabase project than the one configured in src/config.py.

begin;

-- Inventory columns used by current search, forms, and low-stock reporting.
alter table public.inventory add column if not exists barcode text;
alter table public.inventory add column if not exists category text not null default 'General';
alter table public.inventory add column if not exists reorder_level bigint not null default 0;
alter table public.inventory add column if not exists active boolean not null default true;
alter table public.inventory add column if not exists updated_at timestamptz not null default now();
create index if not exists inventory_shop_barcode_idx on public.inventory(shop_id, barcode);
create unique index if not exists inventory_shop_barcode_unique
    on public.inventory(shop_id, barcode) where barcode is not null and barcode <> '';

-- Customer table was not present in the first cloud schema.
create table if not exists public.customers (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    name text not null,
    phone text not null default '',
    balance bigint not null default 0 check (balance >= 0),
    credit_limit bigint not null default 50000 check (credit_limit >= 0),
    due_date date,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (shop_id, name)
);
alter table public.customers add column if not exists active boolean not null default true;
create index if not exists customers_shop_name_idx on public.customers(shop_id, name);

-- Columns required by checkout, receipts, reports, customer credit, and voids.
alter table public.sales add column if not exists customer_id uuid references public.customers(id) on delete set null;
alter table public.sales add column if not exists receipt_no text;
alter table public.sales add column if not exists discount bigint not null default 0;
alter table public.sales add column if not exists paid_amount bigint not null default 0;
alter table public.sales add column if not exists cash bigint not null default 0;
alter table public.sales add column if not exists payment_reference text not null default '';
alter table public.sales add column if not exists cost_total bigint not null default 0;
alter table public.sales add column if not exists profit bigint not null default 0;
alter table public.sales add column if not exists status text not null default 'completed';
alter table public.sales add column if not exists void_reason text not null default '';
alter table public.sales add column if not exists voided_by uuid references auth.users(id);
alter table public.sales add column if not exists voided_at timestamptz;

-- Preserve cash amounts in projects that used the earlier `cash` column.
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema='public' and table_name='sales' and column_name='cash'
    ) then
        execute 'update public.sales set paid_amount = coalesce(cash, 0) where paid_amount = 0';
    end if;
end $$;

-- Give historical sales stable visible receipt numbers before making the column required.
update public.sales
set receipt_no = 'OLD-' || upper(replace(id::text, '-', ''))
where receipt_no is null or trim(receipt_no) = '';
alter table public.sales alter column receipt_no set not null;
create unique index if not exists sales_shop_receipt_unique on public.sales(shop_id, receipt_no);
create index if not exists sales_shop_status_idx on public.sales(shop_id, status);

-- Earlier starter schemas allowed only CASH. Replace that check with all recorded tender types.
do $$
declare c record;
begin
    for c in
        select conname from pg_constraint
        where conrelid = 'public.sales'::regclass and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%payment_type%'
    loop
        execute format('alter table public.sales drop constraint %I', c.conname);
    end loop;
end $$;
alter table public.sales add constraint sales_payment_type_check
    check (payment_type in ('CASH','MOBILE_MONEY','CARD','CREDIT'));

-- Earlier starter schemas used only owner/cashier. Enable manager invitations too.
do $$
declare c record;
begin
    for c in
        select conname from pg_constraint
        where conrelid = 'public.shop_members'::regclass and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%role%'
    loop
        execute format('alter table public.shop_members drop constraint %I', c.conname);
    end loop;
end $$;
alter table public.shop_members add constraint shop_members_role_check
    check (role in ('owner','manager','cashier'));

-- Refresh PostgREST's cached database schema so the app sees the new columns.
notify pgrst, 'reload schema';

commit;
