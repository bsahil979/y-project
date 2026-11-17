-- Run after portfolio_schema.sql. Existing holding ownership policies apply.
alter table holdings add column if not exists manual_value numeric check (manual_value >= 0);
alter table holdings add column if not exists valuation_date date;
alter table holdings add column if not exists valuation_source text;
