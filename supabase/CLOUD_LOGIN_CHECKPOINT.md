# Cloud authentication checkpoint — October 12, 2026

## Implemented and checked

- Email/password login and signup use Supabase only. Failed cloud requests never create password-free local accounts. Try Demo remains explicit and local.
- Successful cloud authentication clears the demo identity so it cannot mask the cloud session after reload.
- Session restoration uses the Supabase session lifecycle. Auth callbacks update state without calling Supabase APIs inside the callback.
- Signup requests a confirmation redirect to the running origin's `/auth` page. Confirmation-required signups remain signed out, and the sign-in button stays usable after the confirmation notice.
- Cloud sign-out is scoped to the current browser.
- Authentication regression tests cover configuration errors, confirmation, demo-to-cloud transition, invalid credentials, legacy mock sessions, session restoration, logout and connection errors.
- 48 frontend tests and the production build passed.

## Restored project check

After the owner restored the project, the configured endpoint returned HTTP 200 for public auth settings. Email authentication and signup are enabled; email confirmation is required. The existing public client key is accepted, so no environment change was necessary.

Zero-row API requests to portfolios, accounts, holdings, transactions, financial_goals and watchlists all returned HTTP 200. This confirms table availability, not authenticated writes or correctness of ownership policies. No project settings or cloud rows have been changed.

The browser extension disconnected while opening the local app login. The owner has been asked to sign in directly at http://localhost:5173/auth with an app account, or register and confirm its email. Successful live login and persistence remain pending.

## Continue after owner sign-in

1. Locate the intended project and inspect its status. Confirm the active project URL and public browser key. Do not place a secret/service-role key in Vite configuration.
2. Update `frontend/.env` only if its public connection settings are stale, then restart Vite.
3. Check email/password authentication and the allowed redirect URLs for `http://localhost:5173/auth` (and the actual deployed origin if used). Preserve the project's email-confirmation policy.
4. Have the owner sign in to the app directly in the browser, or create/confirm their account. Do not request passwords in chat.
5. Verify the cloud identity survives reload and logout works. Check the workspace sync status separately from authentication; the tables and ownership policies in `portfolio_schema.sql` must exist for portfolio sync.

Real cloud login, confirmation-mail delivery and authenticated persistence remain unverified until an app account is available. The project connection is now verified healthy.

Implementation references: [Supabase auth events](https://supabase.com/docs/reference/javascript/auth-onauthstatechange) and [password authentication](https://supabase.com/docs/guides/auth/passwords).

## Two-account staging check

1. In the staging project, apply `portfolio_schema.sql`, `multi_asset_schema.sql`, then `portfolio_relationship_isolation.sql`. The last migration prevents authenticated users from attaching their holdings and transactions to another user's portfolio or brokerage account. It leaves existing records untouched.
2. Use two confirmed, disposable staging accounts. Set these variables locally or in a private env file outside the repository: `CLOUD_SMOKE_URL`, `CLOUD_SMOKE_PUBLIC_KEY`, `CLOUD_SMOKE_USER_A`, `CLOUD_SMOKE_PASSWORD_A`, `CLOUD_SMOKE_USER_B`, and `CLOUD_SMOKE_PASSWORD_B`. Use a publishable or anon key so row-level security applies.
3. From the repository root, run `node --env-file="path-to-private-env-file" frontend/scripts/cloud-isolation-check.mjs`. It adds two broker fixtures and a manual buy to a temporary portfolio, signs in again, checks persistence and isolation, then removes the fixtures. It does not contact the brokers.
4. In the deployed browser app, repeat the import for each configured broker to verify the hosted callback and preview. Verify the manual buy remains visible after both imports and sign-in. The database check and the broker callback check cover different parts of the workflow.

For a local database regression check, run `psql -d <fresh-disposable-database> -f supabase/test_portfolio_relationship_isolation.sql` as the database administrator on a disposable PostgreSQL instance. It creates a local stand-in for the Supabase auth role and checks both users' permissions without real credentials.
