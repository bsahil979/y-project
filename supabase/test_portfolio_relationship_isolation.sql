-- Run with psql against a fresh, disposable PostgreSQL database only.
-- Emulate the Supabase role and auth.uid() contract without real accounts.
\set ON_ERROR_STOP on
create schema auth;
create role authenticated;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$;
grant usage on schema auth, public to authenticated;

\ir portfolio_schema.sql
\ir multi_asset_schema.sql
\ir portfolio_relationship_isolation.sql
\ir portfolio_relationship_isolation.sql

grant select, insert, update, delete on all tables in schema public to authenticated;
insert into auth.users values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', true);
insert into portfolios (id, user_id) values
  ('aaaaaaaa-0000-4000-8000-000000000001', auth.uid());
insert into accounts (id, user_id, name) values
  ('aaaaaaaa-0000-4000-8000-000000000002', auth.uid(), 'Fixture broker');
insert into holdings (user_id, portfolio_id, account_id, ticker, quantity, average_cost)
values (auth.uid(), 'aaaaaaaa-0000-4000-8000-000000000001',
  'aaaaaaaa-0000-4000-8000-000000000002', 'MSFT', 1, 100);
insert into transactions (user_id, portfolio_id, ticker, transaction_type, quantity, price)
values (auth.uid(), 'aaaaaaaa-0000-4000-8000-000000000001', 'MSFT', 'buy', 1, 100);

select set_config('request.jwt.claim.sub', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', true);
insert into portfolios (id, user_id) values
  ('bbbbbbbb-0000-4000-8000-000000000001', auth.uid());
insert into holdings (user_id, portfolio_id, ticker, quantity, average_cost)
values (auth.uid(), 'bbbbbbbb-0000-4000-8000-000000000001', 'AAPL', 1, 100);

do $$
begin
  if (select array_agg(ticker) from holdings) is distinct from array['AAPL'] then
    raise exception 'Second account should see only its own holding';
  end if;
  if exists (select 1 from transactions) or exists (select 1 from accounts) then
    raise exception 'Second account should not see the first account’s broker or transaction';
  end if;
  update holdings set quantity = 10 where ticker = 'MSFT';
  if found then raise exception 'Second account updated the first account’s holding'; end if;

  begin
    insert into holdings (user_id, portfolio_id, ticker, quantity, average_cost)
    values (auth.uid(), 'aaaaaaaa-0000-4000-8000-000000000001', 'AAPL', 1, 100);
    raise exception 'Expected foreign portfolio to be rejected on insert';
  exception when insufficient_privilege then null;
  end;

  begin
    update holdings set account_id = 'aaaaaaaa-0000-4000-8000-000000000002' where ticker = 'AAPL';
    raise exception 'Expected foreign account to be rejected on update';
  exception when insufficient_privilege then null;
  end;

  begin
    insert into transactions (user_id, portfolio_id, account_id, ticker, transaction_type)
    values (auth.uid(), 'bbbbbbbb-0000-4000-8000-000000000001',
      'aaaaaaaa-0000-4000-8000-000000000002', 'AAPL', 'buy');
    raise exception 'Expected foreign account to be rejected on transaction insert';
  exception when insufficient_privilege then null;
  end;
end;
$$;

select set_config('request.jwt.claim.sub', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', true);
do $$
begin
  if (select quantity from holdings where ticker = 'MSFT') is distinct from 1::numeric then
    raise exception 'First account’s fixture should remain visible and unchanged';
  end if;
end;
$$;
rollback;
