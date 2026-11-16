-- SmartAdvisor portfolio data foundation
-- Apply this migration in Supabase before relying on remote workspace sync.
-- RLS policies ensure each authenticated user can access only their own rows.

create extension if not exists pgcrypto;

create table if not exists portfolios (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'My Portfolio',
  base_currency text not null default 'USD',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  institution text,
  account_type text not null default 'brokerage',
  currency text not null default 'USD',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  portfolio_id uuid not null references portfolios(id) on delete cascade,
  account_id uuid references accounts(id) on delete set null,
  ticker text not null,
  asset_name text,
  asset_type text not null default 'stock',
  quantity numeric not null check (quantity >= 0),
  average_cost numeric not null check (average_cost >= 0),
  currency text not null default 'USD',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  portfolio_id uuid not null references portfolios(id) on delete cascade,
  account_id uuid references accounts(id) on delete set null,
  -- Nullable for cash-only dividend and fee records.
  ticker text,
  transaction_type text not null check (transaction_type in ('buy', 'sell', 'dividend', 'fee', 'transfer')),
  quantity numeric not null default 0,
  price numeric not null default 0,
  fees numeric not null default 0,
  currency text not null default 'USD',
  transaction_date date not null default current_date,
  created_at timestamptz not null default now()
);

-- Safe for databases where the table was created before currency support.
alter table transactions add column if not exists currency text not null default 'USD';
-- Safe for databases created from the original required-ticker definition.
alter table transactions alter column ticker drop not null;
-- Safe for databases created before holdings became currency-aware.
alter table holdings add column if not exists currency text not null default 'USD';

create table if not exists financial_goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  target_amount numeric not null check (target_amount > 0),
  current_amount numeric not null default 0 check (current_amount >= 0),
  target_date date,
  currency text not null default 'USD',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'Main Watchlist',
  tickers text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table portfolios enable row level security;
alter table accounts enable row level security;
alter table holdings enable row level security;
alter table transactions enable row level security;
alter table watchlists enable row level security;
alter table financial_goals enable row level security;

drop policy if exists "Users manage their own portfolios" on portfolios;
create policy "Users manage their own portfolios" on portfolios for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage their own accounts" on accounts;
create policy "Users manage their own accounts" on accounts for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage their own holdings" on holdings;
create policy "Users manage their own holdings" on holdings for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage their own transactions" on transactions;
create policy "Users manage their own transactions" on transactions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage their own watchlists" on watchlists;
create policy "Users manage their own watchlists" on watchlists for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage their own financial goals" on financial_goals;
create policy "Users manage their own financial goals" on financial_goals for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Keep updated_at reliable for edits made through the dashboard or Supabase API.
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists portfolios_set_updated_at on portfolios;
create trigger portfolios_set_updated_at before update on portfolios for each row execute function set_updated_at();
drop trigger if exists accounts_set_updated_at on accounts;
create trigger accounts_set_updated_at before update on accounts for each row execute function set_updated_at();
drop trigger if exists holdings_set_updated_at on holdings;
create trigger holdings_set_updated_at before update on holdings for each row execute function set_updated_at();
drop trigger if exists goals_set_updated_at on financial_goals;
create trigger goals_set_updated_at before update on financial_goals for each row execute function set_updated_at();
drop trigger if exists watchlists_set_updated_at on watchlists;
create trigger watchlists_set_updated_at before update on watchlists for each row execute function set_updated_at();

create index if not exists holdings_user_id_idx on holdings(user_id);
create index if not exists transactions_user_id_idx on transactions(user_id);
create index if not exists accounts_user_id_idx on accounts(user_id);
