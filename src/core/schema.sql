-- Noble POS Cloud schema for a fresh or upgraded Supabase project.
-- Existing records are preserved; additive ALTER statements below upgrade older installs.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.shops (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) between 2 and 120),
    currency text not null default 'TZS' check (length(currency) between 3 and 5),
    tax_rate numeric(6,3) not null default 0 check (tax_rate >= 0 and tax_rate <= 100),
    subscription_status text not null default 'trial' check (subscription_status in ('trial', 'active', 'past_due', 'suspended')),
    created_by uuid not null references auth.users(id) on delete restrict,
    created_at timestamptz not null default now()
);

create table if not exists public.shop_members (
    shop_id uuid not null references public.shops(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null default 'owner' check (role in ('owner', 'manager', 'cashier')),
    created_at timestamptz not null default now(),
    primary key (shop_id, user_id)
);

create table if not exists public.shop_invites (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    code_hash text not null unique,
    role text not null check (role in ('manager', 'cashier')),
    created_by uuid not null references auth.users(id),
    expires_at timestamptz not null default now() + interval '7 days',
    redeemed_by uuid references auth.users(id),
    redeemed_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists public.inventory (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    name text not null check (length(trim(name)) between 1 and 160),
    barcode text,
    category text not null default 'General',
    cost_price bigint not null default 0 check (cost_price >= 0),
    price bigint not null check (price > 0),
    stock_qty bigint not null default 0 check (stock_qty >= 0),
    reorder_level bigint not null default 0 check (reorder_level >= 0),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (shop_id, name)
);
create table if not exists public.customers (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    name text not null check (length(trim(name)) between 1 and 160),
    phone text not null default '',
    balance bigint not null default 0 check (balance >= 0),
    credit_limit bigint not null default 50000 check (credit_limit >= 0),
    due_date date,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (shop_id, name)
);

create table if not exists public.sales (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete restrict,
    customer_id uuid references public.customers(id) on delete set null,
    receipt_no text not null,
    subtotal bigint not null check (subtotal >= 0),
    discount bigint not null default 0 check (discount >= 0),
    tax bigint not null default 0 check (tax >= 0),
    total bigint not null check (total >= 0),
    paid_amount bigint not null default 0 check (paid_amount >= 0),
    cash bigint not null default 0,
    change_due bigint not null default 0 check (change_due >= 0),
    payment_type text not null check (payment_type in ('CASH', 'MOBILE_MONEY', 'CARD', 'CREDIT')),
    payment_reference text not null default '',
    cost_total bigint not null default 0,
    profit bigint not null default 0,
    status text not null default 'completed' check (status in ('completed', 'voided')),
    void_reason text not null default '',
    voided_by uuid references auth.users(id),
    voided_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists public.sale_items (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    sale_id uuid not null references public.sales(id) on delete cascade,
    inventory_id uuid references public.inventory(id) on delete set null,
    item_name text not null,
    quantity bigint not null check (quantity > 0),
    unit_price bigint not null check (unit_price >= 0),
    unit_cost bigint not null check (unit_cost >= 0),
    line_total bigint not null check (line_total >= 0),
    created_at timestamptz not null default now()
);

create table if not exists public.debt_payments (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    customer_id uuid not null references public.customers(id) on delete restrict,
    user_id uuid not null references auth.users(id) on delete restrict,
    amount bigint not null check (amount > 0),
    payment_type text not null default 'CASH' check (payment_type in ('CASH', 'MOBILE_MONEY', 'CARD')),
    reference text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists public.expenses (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete restrict,
    title text not null check (length(trim(title)) between 1 and 160),
    category text not null default 'Other',
    amount bigint not null check (amount > 0),
    description text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists public.stock_movements (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.shops(id) on delete cascade,
    inventory_id uuid references public.inventory(id) on delete set null,
    user_id uuid references auth.users(id) on delete set null,
    movement_type text not null,
    quantity_delta bigint not null,
    note text not null default '',
    sale_id uuid references public.sales(id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists public.audit_events (
    id bigint generated always as identity primary key,
    shop_id uuid not null references public.shops(id) on delete cascade,
    user_id uuid references auth.users(id) on delete set null,
    action text not null,
    entity_type text not null,
    entity_id text not null default '',
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Additive upgrades for projects created with the earlier MVP schema.
alter table public.inventory add column if not exists barcode text;
alter table public.inventory add column if not exists category text not null default 'General';
alter table public.inventory add column if not exists reorder_level bigint not null default 0;
alter table public.inventory add column if not exists active boolean not null default true;
alter table public.inventory add column if not exists updated_at timestamptz not null default now();
create unique index if not exists inventory_shop_barcode_unique on public.inventory(shop_id, barcode) where barcode is not null and barcode <> '';
alter table public.customers add column if not exists active boolean not null default true;
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
do $$
begin
    if exists (select 1 from information_schema.columns where table_schema='public' and table_name='sales' and column_name='cash') then
        execute 'update public.sales set paid_amount=coalesce(cash,0) where paid_amount=0';
    end if;
end $$;
update public.sales set receipt_no='OLD-' || upper(replace(id::text,'-','')) where receipt_no is null or trim(receipt_no)='';
alter table public.sales alter column receipt_no set not null;
do $$
declare c record;
begin
    for c in select conname from pg_constraint where conrelid='public.sales'::regclass and contype='c' and pg_get_constraintdef(oid) ilike '%payment_type%'
    loop execute format('alter table public.sales drop constraint %I',c.conname); end loop;
end $$;
alter table public.sales add constraint sales_payment_type_check check (payment_type in ('CASH','MOBILE_MONEY','CARD','CREDIT'));
do $$
declare c record;
begin
    for c in select conname from pg_constraint where conrelid='public.shop_members'::regclass and contype='c' and pg_get_constraintdef(oid) ilike '%role%'
    loop execute format('alter table public.shop_members drop constraint %I',c.conname); end loop;
end $$;
alter table public.shop_members add constraint shop_members_role_check check (role in ('owner','manager','cashier'));

create index if not exists inventory_shop_name_idx on public.inventory(shop_id, name);
create index if not exists inventory_shop_barcode_idx on public.inventory(shop_id, barcode);
create index if not exists sales_shop_created_idx on public.sales(shop_id, created_at desc);
create unique index if not exists sales_shop_receipt_unique on public.sales(shop_id, receipt_no);
create index if not exists sales_shop_status_idx on public.sales(shop_id, status);
create index if not exists expenses_shop_created_idx on public.expenses(shop_id, created_at desc);
create index if not exists customers_shop_name_idx on public.customers(shop_id, name);
create index if not exists debt_payments_customer_idx on public.debt_payments(shop_id, customer_id, created_at desc);
create index if not exists sale_items_sale_idx on public.sale_items(sale_id);

create or replace function public.has_shop_access(target_shop uuid)
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.shop_members m where m.shop_id = target_shop and m.user_id = auth.uid()); $$;
create or replace function public.has_shop_role(target_shop uuid, allowed_roles text[])
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.shop_members m where m.shop_id = target_shop and m.user_id = auth.uid() and m.role = any(allowed_roles)); $$;
grant execute on function public.has_shop_access(uuid) to authenticated;
grant execute on function public.has_shop_role(uuid, text[]) to authenticated;

alter table public.shops enable row level security;
alter table public.shop_members enable row level security;
alter table public.shop_invites enable row level security;
alter table public.inventory enable row level security;
alter table public.customers enable row level security;
alter table public.sales enable row level security;
alter table public.sale_items enable row level security;
alter table public.debt_payments enable row level security;
alter table public.expenses enable row level security;
alter table public.stock_movements enable row level security;
alter table public.audit_events enable row level security;

grant usage on schema public to authenticated;
grant select on public.shops to authenticated;
grant insert (name, created_by, tax_rate) on public.shops to authenticated;
grant update (name, tax_rate) on public.shops to authenticated;
grant select, insert on public.shop_members to authenticated;
grant select on public.inventory to authenticated;
grant insert (shop_id,name,barcode,category,cost_price,price,stock_qty,reorder_level,active) on public.inventory to authenticated;
grant update (name,barcode,category,cost_price,price,reorder_level,active) on public.inventory to authenticated;
grant select on public.customers to authenticated;
grant insert (shop_id,name,phone,credit_limit,due_date,active) on public.customers to authenticated;
grant update (name,phone,credit_limit,due_date,active) on public.customers to authenticated;
grant select on public.sales to authenticated;
grant select on public.sale_items to authenticated;
grant select on public.debt_payments to authenticated;
grant select, insert on public.expenses to authenticated;
grant select on public.stock_movements to authenticated;
grant select on public.audit_events to authenticated;
grant select, insert on public.shop_invites to authenticated;

-- Keep subscription status server-admin managed, not editable by shop clients.
revoke update on public.shops from authenticated;
grant update (name, tax_rate) on public.shops to authenticated;

-- Shop and membership policies.
drop policy if exists shops_select_member on public.shops;
create policy shops_select_member on public.shops for select to authenticated using (created_by = auth.uid() or public.has_shop_access(id));
drop policy if exists shops_create_owner on public.shops;
create policy shops_create_owner on public.shops for insert to authenticated with check (created_by = auth.uid());
drop policy if exists shops_update_owner on public.shops;
create policy shops_update_owner on public.shops for update to authenticated using (public.has_shop_role(id, array['owner'])) with check (public.has_shop_role(id, array['owner']));
drop policy if exists members_select_shop on public.shop_members;
create policy members_select_shop on public.shop_members for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists members_create_first_owner on public.shop_members;
create policy members_create_first_owner on public.shop_members for insert to authenticated with check (
    user_id = auth.uid() and role = 'owner' and exists (
        select 1 from public.shops s where s.id = shop_members.shop_id and s.created_by = auth.uid()
    )
);
drop policy if exists invites_select_manager on public.shop_invites;
create policy invites_select_manager on public.shop_invites for select to authenticated using (public.has_shop_role(shop_id, array['owner','manager']));

-- Tenant isolation and role-aware data access.
drop policy if exists inventory_select_member on public.inventory;
create policy inventory_select_member on public.inventory for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists inventory_write_manager on public.inventory;
create policy inventory_write_manager on public.inventory for all to authenticated using (public.has_shop_role(shop_id, array['owner','manager'])) with check (public.has_shop_role(shop_id, array['owner','manager']));
drop policy if exists customers_select_member on public.customers;
create policy customers_select_member on public.customers for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists customers_write_manager on public.customers;
create policy customers_write_manager on public.customers for all to authenticated using (public.has_shop_role(shop_id, array['owner','manager'])) with check (public.has_shop_role(shop_id, array['owner','manager']));
drop policy if exists sales_select_member on public.sales;
create policy sales_select_member on public.sales for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists sales_insert_member on public.sales;
create policy sales_insert_member on public.sales for insert to authenticated with check (public.has_shop_access(shop_id) and user_id = auth.uid());
drop policy if exists sale_items_select_member on public.sale_items;
create policy sale_items_select_member on public.sale_items for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists sale_items_insert_member on public.sale_items;
create policy sale_items_insert_member on public.sale_items for insert to authenticated with check (public.has_shop_access(shop_id) and exists (select 1 from public.sales s where s.id = sale_items.sale_id and s.shop_id = sale_items.shop_id));
drop policy if exists debt_payments_select_member on public.debt_payments;
create policy debt_payments_select_member on public.debt_payments for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists expenses_select_member on public.expenses;
create policy expenses_select_member on public.expenses for select to authenticated using (public.has_shop_access(shop_id));
drop policy if exists expenses_insert_manager on public.expenses;
create policy expenses_insert_manager on public.expenses for insert to authenticated with check (public.has_shop_role(shop_id, array['owner','manager']) and user_id = auth.uid());
drop policy if exists expenses_delete_owner on public.expenses;
create policy expenses_delete_owner on public.expenses for delete to authenticated using (public.has_shop_role(shop_id, array['owner']));
drop policy if exists stock_select_manager on public.stock_movements;
create policy stock_select_manager on public.stock_movements for select to authenticated using (public.has_shop_role(shop_id, array['owner','manager']));
drop policy if exists audit_select_manager on public.audit_events;
create policy audit_select_manager on public.audit_events for select to authenticated using (public.has_shop_role(shop_id, array['owner','manager']));

create or replace function public.create_shop_invite(p_shop_id uuid, p_role text)
returns text language plpgsql security definer set search_path = extensions, public
as $$
declare v_code text;
begin
    if not public.has_shop_role(p_shop_id, array['owner','manager']) then raise exception 'Not authorized to invite staff'; end if;
    if p_role not in ('manager','cashier') or (p_role = 'manager' and not public.has_shop_role(p_shop_id, array['owner'])) then raise exception 'Not authorized to invite this role'; end if;
    v_code := upper(encode(gen_random_bytes(9), 'hex'));
    insert into public.shop_invites(shop_id,code_hash,role,created_by,expires_at) values(p_shop_id,encode(digest(v_code,'sha256'),'hex'),p_role,auth.uid(),now()+interval '7 days');
    return v_code;
end;
$$;
grant execute on function public.create_shop_invite(uuid,text) to authenticated;

create or replace function public.redeem_shop_invite(p_code text)
returns jsonb language plpgsql security definer set search_path = extensions, public
as $$
declare v_invite public.shop_invites%rowtype;
begin
    if auth.uid() is null or length(trim(coalesce(p_code,''))) < 8 then raise exception 'Enter a valid staff invitation code'; end if;
    select * into v_invite from public.shop_invites where code_hash=encode(digest(upper(trim(p_code)),'sha256'),'hex') and redeemed_at is null and expires_at>now() for update;
    if not found then raise exception 'Invitation is invalid, expired, or already used'; end if;
    insert into public.shop_members(shop_id,user_id,role) values(v_invite.shop_id,auth.uid(),v_invite.role) on conflict (shop_id,user_id) do nothing;
    update public.shop_invites set redeemed_by=auth.uid(),redeemed_at=now() where id=v_invite.id;
    insert into public.audit_events(shop_id,user_id,action,entity_type,entity_id) values(v_invite.shop_id,auth.uid(),'staff_joined','membership',auth.uid()::text);
    return jsonb_build_object('shop_id',v_invite.shop_id,'role',v_invite.role);
end;
$$;
grant execute on function public.redeem_shop_invite(text) to authenticated;

drop function if exists public.checkout_sale(uuid,jsonb,bigint);
create or replace function public.checkout_sale(p_shop_id uuid,p_items jsonb,p_payment_type text,p_paid_amount bigint,p_customer_id uuid default null,p_discount bigint default 0,p_payment_reference text default '')
returns jsonb language plpgsql security definer set search_path = public
as $$
declare
    line record; v_product public.inventory%rowtype; v_customer public.customers%rowtype;
    v_subtotal bigint:=0; v_cost_total bigint:=0; v_tax bigint:=0; v_total bigint:=0;
    v_paid bigint:=coalesce(p_paid_amount,0); v_discount bigint:=coalesce(p_discount,0);
    v_tax_rate numeric(6,3); v_sale_id uuid; v_receipt text;
begin
    if auth.uid() is null or not public.has_shop_access(p_shop_id) then raise exception 'Not authorized for this shop'; end if;
    if jsonb_typeof(p_items)<>'array' or jsonb_array_length(p_items)=0 then raise exception 'Cart is empty'; end if;
    if p_payment_type not in ('CASH','MOBILE_MONEY','CARD','CREDIT') then raise exception 'Unsupported payment method'; end if;
    if v_paid<0 or v_discount<0 then raise exception 'Payment and discount cannot be negative'; end if;
    select tax_rate into v_tax_rate from public.shops where id=p_shop_id and subscription_status in ('trial','active');
    if not found then raise exception 'Shop subscription is not active'; end if;
    for line in select (value->>'id')::uuid as product_id,sum((value->>'quantity')::bigint)::bigint as qty from jsonb_array_elements(p_items) group by (value->>'id')::uuid order by (value->>'id')::uuid loop
        if line.qty<=0 then raise exception 'Quantity must be positive'; end if;
        select * into v_product from public.inventory where id=line.product_id and shop_id=p_shop_id and active for update;
        if not found then raise exception 'A cart item is missing or inactive'; end if;
        if v_product.stock_qty<line.qty then raise exception 'Insufficient stock for % (available: %)',v_product.name,v_product.stock_qty; end if;
        v_subtotal:=v_subtotal+v_product.price*line.qty; v_cost_total:=v_cost_total+v_product.cost_price*line.qty;
    end loop;
    if v_discount>v_subtotal then raise exception 'Discount cannot exceed subtotal'; end if;
    v_tax:=round((v_subtotal-v_discount)*v_tax_rate/100.0)::bigint; v_total:=v_subtotal-v_discount+v_tax;
    if p_payment_type='CREDIT' then
        if p_customer_id is null then raise exception 'Select a customer for a credit sale'; end if;
        if v_paid<>0 then raise exception 'Use a separate debt payment to collect credit'; end if;
        select * into v_customer from public.customers where id=p_customer_id and shop_id=p_shop_id and active for update;
        if not found then raise exception 'Customer not found'; end if;
        if v_customer.balance+v_total>v_customer.credit_limit then raise exception 'Sale exceeds customer credit limit'; end if;
    elsif p_payment_type='CASH' then
        if v_paid<v_total then raise exception 'Cash tendered is less than the total'; end if;
    elsif v_paid<>v_total then raise exception 'Mobile money and card payments must match the sale total'; end if;
    v_receipt:='R-'||to_char(now(),'YYMMDD-HH24MISS')||'-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,6));
    insert into public.sales(shop_id,user_id,customer_id,receipt_no,subtotal,discount,tax,total,paid_amount,cash,change_due,payment_type,payment_reference,cost_total,profit)
    values(p_shop_id,auth.uid(),p_customer_id,v_receipt,v_subtotal,v_discount,v_tax,v_total,v_paid,v_paid,case when p_payment_type='CASH' then v_paid-v_total else 0 end,p_payment_type,coalesce(p_payment_reference,''),v_cost_total,v_total-v_cost_total)
    returning id into v_sale_id;
    for line in select (value->>'id')::uuid as product_id,sum((value->>'quantity')::bigint)::bigint as qty from jsonb_array_elements(p_items) group by (value->>'id')::uuid order by (value->>'id')::uuid loop
        select * into v_product from public.inventory where id=line.product_id and shop_id=p_shop_id for update;
        update public.inventory set stock_qty=stock_qty-line.qty,updated_at=now() where id=v_product.id;
        insert into public.sale_items(shop_id,sale_id,inventory_id,item_name,quantity,unit_price,unit_cost,line_total) values(p_shop_id,v_sale_id,v_product.id,v_product.name,line.qty,v_product.price,v_product.cost_price,v_product.price*line.qty);
        insert into public.stock_movements(shop_id,inventory_id,user_id,movement_type,quantity_delta,note,sale_id) values(p_shop_id,v_product.id,auth.uid(),'sale',-line.qty,v_receipt,v_sale_id);
    end loop;
    if p_payment_type='CREDIT' then update public.customers set balance=balance+v_total where id=p_customer_id; end if;
    insert into public.audit_events(shop_id,user_id,action,entity_type,entity_id,details) values(p_shop_id,auth.uid(),'sale_completed','sale',v_sale_id::text,jsonb_build_object('receipt_no',v_receipt,'total',v_total,'payment_type',p_payment_type));
    return jsonb_build_object('sale_id',v_sale_id,'receipt_no',v_receipt,'subtotal',v_subtotal,'discount',v_discount,'tax',v_tax,'total',v_total,'paid_amount',v_paid,'change_due',case when p_payment_type='CASH' then v_paid-v_total else 0 end);
end;
$$;
grant execute on function public.checkout_sale(uuid,jsonb,text,bigint,uuid,bigint,text) to authenticated;

create or replace function public.record_debt_payment(p_shop_id uuid,p_customer_id uuid,p_amount bigint,p_payment_type text default 'CASH',p_reference text default '')
returns jsonb language plpgsql security definer set search_path = public
as $$
declare v_customer public.customers%rowtype;
begin
    if not public.has_shop_role(p_shop_id,array['owner','manager']) then raise exception 'Not authorized to record debt payments'; end if;
    if p_amount<=0 or p_payment_type not in ('CASH','MOBILE_MONEY','CARD') then raise exception 'Invalid payment'; end if;
    select * into v_customer from public.customers where id=p_customer_id and shop_id=p_shop_id for update;
    if not found or v_customer.balance<p_amount then raise exception 'Payment exceeds customer balance'; end if;
    update public.customers set balance=balance-p_amount where id=p_customer_id;
    insert into public.debt_payments(shop_id,customer_id,user_id,amount,payment_type,reference) values(p_shop_id,p_customer_id,auth.uid(),p_amount,p_payment_type,coalesce(p_reference,''));
    insert into public.audit_events(shop_id,user_id,action,entity_type,entity_id,details) values(p_shop_id,auth.uid(),'debt_payment','customer',p_customer_id::text,jsonb_build_object('amount',p_amount));
    return jsonb_build_object('balance',v_customer.balance-p_amount);
end;
$$;
grant execute on function public.record_debt_payment(uuid,uuid,bigint,text,text) to authenticated;

create or replace function public.void_sale(p_shop_id uuid,p_sale_id uuid,p_reason text)
returns jsonb language plpgsql security definer set search_path = public
as $$
declare v_sale public.sales%rowtype; line record;
begin
    if not public.has_shop_role(p_shop_id,array['owner','manager']) then raise exception 'Only an owner or manager can void a sale'; end if;
    if length(trim(coalesce(p_reason,'')))<3 then raise exception 'Provide a reason for the void'; end if;
    select * into v_sale from public.sales where id=p_sale_id and shop_id=p_shop_id for update;
    if not found or v_sale.status<>'completed' then raise exception 'Sale is not available to void'; end if;
    for line in select inventory_id,quantity from public.sale_items where sale_id=p_sale_id and shop_id=p_shop_id loop
        if line.inventory_id is not null then
            update public.inventory set stock_qty=stock_qty+line.quantity,updated_at=now() where id=line.inventory_id and shop_id=p_shop_id;
            insert into public.stock_movements(shop_id,inventory_id,user_id,movement_type,quantity_delta,note,sale_id) values(p_shop_id,line.inventory_id,auth.uid(),'sale_void',line.quantity,trim(p_reason),p_sale_id);
        end if;
    end loop;
    if v_sale.payment_type='CREDIT' and v_sale.customer_id is not null then update public.customers set balance=greatest(0,balance-v_sale.total) where id=v_sale.customer_id and shop_id=p_shop_id; end if;
    update public.sales set status='voided',void_reason=trim(p_reason),voided_by=auth.uid(),voided_at=now() where id=p_sale_id;
    insert into public.audit_events(shop_id,user_id,action,entity_type,entity_id,details) values(p_shop_id,auth.uid(),'sale_voided','sale',p_sale_id::text,jsonb_build_object('reason',trim(p_reason)));
    return jsonb_build_object('sale_id',p_sale_id,'status','voided');
end;
$$;
grant execute on function public.void_sale(uuid,uuid,text) to authenticated;

create or replace function public.adjust_inventory_stock(p_shop_id uuid,p_inventory_id uuid,p_delta bigint,p_note text)
returns jsonb language plpgsql security definer set search_path = public
as $$
declare v_item public.inventory%rowtype;
begin
    if not public.has_shop_role(p_shop_id,array['owner','manager']) then raise exception 'Only an owner or manager can adjust stock'; end if;
    if p_delta=0 or length(trim(coalesce(p_note,'')))<2 then raise exception 'Enter a non-zero adjustment and a reason'; end if;
    select * into v_item from public.inventory where id=p_inventory_id and shop_id=p_shop_id for update;
    if not found then raise exception 'Product not found'; end if;
    if v_item.stock_qty+p_delta<0 then raise exception 'Stock cannot become negative'; end if;
    update public.inventory set stock_qty=stock_qty+p_delta,updated_at=now() where id=p_inventory_id;
    insert into public.stock_movements(shop_id,inventory_id,user_id,movement_type,quantity_delta,note) values(p_shop_id,p_inventory_id,auth.uid(),'manual_adjustment',p_delta,trim(p_note));
    insert into public.audit_events(shop_id,user_id,action,entity_type,entity_id,details) values(p_shop_id,auth.uid(),'stock_adjustment','inventory',p_inventory_id::text,jsonb_build_object('delta',p_delta,'note',trim(p_note)));
    return jsonb_build_object('stock_qty',v_item.stock_qty+p_delta);
end;
$$;
grant execute on function public.adjust_inventory_stock(uuid,uuid,bigint,text) to authenticated;

-- SECURITY DEFINER functions must not inherit PostgreSQL's default PUBLIC execute grant.
-- Keep application RPCs callable only by signed-in users; each function also checks shop roles.
revoke all on function public.has_shop_access(uuid) from public, anon;
revoke all on function public.has_shop_role(uuid,text[]) from public, anon;
revoke all on function public.create_shop_invite(uuid,text) from public, anon;
revoke all on function public.redeem_shop_invite(text) from public, anon;
revoke all on function public.checkout_sale(uuid,jsonb,text,bigint,uuid,bigint,text) from public, anon;
revoke all on function public.record_debt_payment(uuid,uuid,bigint,text,text) from public, anon;
revoke all on function public.void_sale(uuid,uuid,text) from public, anon;
revoke all on function public.adjust_inventory_stock(uuid,uuid,bigint,text) from public, anon;

grant execute on function public.has_shop_access(uuid) to authenticated;
grant execute on function public.has_shop_role(uuid,text[]) to authenticated;
grant execute on function public.create_shop_invite(uuid,text) to authenticated;
grant execute on function public.redeem_shop_invite(text) to authenticated;
grant execute on function public.checkout_sale(uuid,jsonb,text,bigint,uuid,bigint,text) to authenticated;
grant execute on function public.record_debt_payment(uuid,uuid,bigint,text,text) to authenticated;
grant execute on function public.void_sale(uuid,uuid,text) to authenticated;
grant execute on function public.adjust_inventory_stock(uuid,uuid,bigint,text) to authenticated;

notify pgrst, 'reload schema';
