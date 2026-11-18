-- Apply after portfolio_schema.sql. Existing per-row owner policies still apply.
-- A holding or transaction must also reference parents belonging to its owner.
begin;

drop policy if exists "Holdings must reference owned parents" on public.holdings;
create policy "Holdings must reference owned parents" on public.holdings
as restrictive for all to authenticated
using (true)
with check (
  exists (
    select 1 from public.portfolios p
    where p.id = holdings.portfolio_id and p.user_id = holdings.user_id
  )
  and (
    holdings.account_id is null
    or exists (
      select 1 from public.accounts a
      where a.id = holdings.account_id and a.user_id = holdings.user_id
    )
  )
);

drop policy if exists "Transactions must reference owned parents" on public.transactions;
create policy "Transactions must reference owned parents" on public.transactions
as restrictive for all to authenticated
using (true)
with check (
  exists (
    select 1 from public.portfolios p
    where p.id = transactions.portfolio_id and p.user_id = transactions.user_id
  )
  and (
    transactions.account_id is null
    or exists (
      select 1 from public.accounts a
      where a.id = transactions.account_id and a.user_id = transactions.user_id
    )
  )
);

commit;
