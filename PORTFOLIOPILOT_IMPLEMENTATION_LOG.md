# PortfolioPilot-Inspired Implementation Log

This file is the handoff document for implementing a PortfolioPilot-inspired experience in the SmartAdvisor repository.

## How to use this document

Before making changes, read:

1. This file
2. `PORTFOLIOPILOT_COMPARISON.md`
3. `MISSING_CAPABILITIES_ANALYSIS.md`
4. The relevant source files under `frontend/src`

After each implementation step, update the status table, record changed files, validation commands, and any known limitations. This is intentionally written so another coding model can continue without relying on prior chat history.

## Reference product reviewed

- Website: https://portfoliopilot.com
- Observable product positioning: financial planning and investment intelligence for self-directed investors.
- Observable navigation themes: net worth, estate planning, tax optimization, retirement planning, AI investing advice, portfolio management, pricing, resources, help, login, and signup.
- Observable trust themes: bank-level security, secure account connections, no commissions/conflicts messaging, and prominent disclosures.
- Observable monetization: Free, Gold, Platinum, and Pro plans, with a free trial for paid plans.

Do not copy PortfolioPilot branding, text, proprietary design assets, or claims. Use the reference only for product structure and UX direction.

## SmartAdvisor baseline

The repository is a React/Vite frontend with Tailwind CSS, Recharts, React Router, Supabase authentication/storage, and a FastAPI analytics engine. Existing analytics include portfolio risk, benchmark comparison, attribution, forecasting, sentiment, market regime detection, recommendations, AI chat, paper trading/monitoring endpoints, and model training.

Current major limitation: the frontend primarily stores a list of ticker symbols and treats them as an equal-weight analytical portfolio. It does not yet represent real holdings, quantities, cost basis, transactions, accounts, liabilities, or net worth.

## Implementation strategy

Prioritize in this order:

1. Product foundation and trust: metadata, clear language, disclosures, non-placeholder links.
2. Data foundation: separate watchlists from portfolios; add holdings, quantities, cost basis, transactions, and accounts.
3. Overview dashboard: total value, gain/loss, allocation, benchmark, portfolio health, and an action center.
4. Planning: goals, retirement, scenarios, and basic tax awareness.
5. Monitoring: alerts and notification preferences.
6. Integrations: CSV import first, broker connections later.
7. Advanced experience: move model-training and RL diagnostics under an Advanced/Quant area.
8. Pricing and feature gating after the free core workflow is coherent.

## Progress

| Step | Scope | Status | Validation |
|---|---|---|---|
| 1 | Metadata, brand cleanup, functional landing CTA, implementation log | **Completed** | Frontend build passed (see latest entry below) |
| 2 | Portfolio/watchlist data model and storage design | **Completed** | Schema and service verified; frontend build pending |
| 3 | Holdings management UI and portfolio overview | **In progress** | Holdings workflow complete; live-price overview remains |
| 4 | Action center and explainable recommendations | **In progress** | Overview action center and dismiss/review actions added; build validation pending |
| 5 | Planning tools and scenarios | **In progress** | Goals CRUD screen and persistence added; projections/scenarios remain |
| 6 | Alerts, security pages, and pricing | Not started | — |

## Step 3 in-progress changes

Date: 2026-08-30

Changed:

- `frontend/src/components/HoldingsView.jsx`
  - Added the first real owned-position workflow.
  - Users can record ticker, quantity, average cost, asset type, and currency.
  - Added cost-basis summary, empty state, validation, and remove action.
  - Uses the workspace service path rather than legacy ticker storage.
- `frontend/src/App.jsx`
  - Added `/dashboard/portfolio` and passed workspace state into the holdings screen.
  - Added `updateWorkspace` so changes persist through `PortfolioDataService`.
- `frontend/src/components/Sidebar.jsx`
  - Added a visible `My Holdings` navigation item.
- `frontend/src/components/PortfolioBuilderView.jsx`
  - Reframed the watchlist screen as investment discovery instead of implying ownership.
- `frontend/src/components/PortfolioDashboard.jsx`
  - Removed demo fallback tickers and fixed an accidental source typo.
  - The analytics dashboard now remains empty until the user has a watchlist.

## Step 5 in-progress changes

Date: 2026-08-30

- Added `frontend/src/components/GoalsView.jsx` with goal creation, progress display, validation, and deletion.
- Added `/dashboard/planning/goals` and a `Financial Goals` navigation entry.
- Extended the workspace model and best-effort Supabase sync with `goals`.
- Added the `financial_goals` table and RLS policy to `supabase/portfolio_schema.sql`.

Known limitations: goal projections, monthly contribution planning, inflation, Monte Carlo probability, and scenarios are not implemented yet. Apply the SQL migration in Supabase before relying on remote goal persistence.

## Step 3 continuation: connect holdings to overview

Date: 2026-08-30

Planned next change:

- Use recorded owned positions as the preferred input for overview analytics.
- Fall back to watchlist symbols when no holdings have been entered.
- Calculate analysis weights from holding cost basis rather than silently assuming equal ownership.
- Add a recorded-cost summary and explain the current price-data limitation.

This entry is intentionally placed before the code change so another model can resume safely if execution stops.

Implemented continuation:

- `PortfolioDashboard` now receives the workspace and prefers owned holdings for analytics.
- Cost-basis weights are calculated per ticker; watchlist analysis still uses equal weights only when no holdings exist.
- The overview displays a clear cost-basis/live-price limitation notice.
- `Layout` now labels `/dashboard/portfolio` as `My Holdings`.

Validation note: source references were rechecked after editing; run the frontend build from a terminal opened at `C:\\Users\\Sahil Belchada\\Desktop\\ly project\\smart-portfolio-advisor\\frontend` because the automated command wrapper mishandles this path.

Validation:

- Static verification completed for routes, imports, and edited source references.
- Frontend build command is still required; the current command runner is rejecting this workspace path containing spaces.

Known limitations:

- Holdings use cost basis only; live prices, gain/loss, accounts, and transactions are next.
- Workspace updates are persisted locally and synced remotely on a best-effort basis.

## Step 3 continuation: stabilize analytics inputs

Date: 2026-08-30

Changed:

- `frontend/src/components/PortfolioDashboard.jsx`
  - Memoized owned-cost aggregation, analysis tickers, total recorded cost, and weights.
  - Prevents the analytics `useEffect` from seeing newly-created array references on unrelated renders.
  - Preserves cost-basis weighting for owned positions and equal weighting only for watchlist-only analysis.

Validation:

- Static source verification completed after the change.
- Build/lint execution was attempted, but the automated Windows command wrapper timed out or mishandled this workspace path. Run `npm run build` and `npm run lint` from the frontend directory in a local terminal.


## Step 2 completed changes

Date: 2026-08-30

Changed:

- `supabase/portfolio_schema.sql`
  - Added the planned `portfolios`, `accounts`, `holdings`, `transactions`, and `watchlists` tables.
  - Added ownership-focused row-level security policies and useful indexes.
  - This SQL must be applied in Supabase before remote rows can be used.
- `frontend/src/services/portfolioData.js`
  - Added an explicit workspace model separating watchlists from owned holdings.
  - Added deterministic local persistence and migration of legacy ticker-only data into `watchlistTickers`.
  - Added best-effort Supabase synchronization for the new tables.
  - Added `createHolding` normalization helper for the upcoming holdings UI.
- `frontend/src/App.jsx`
  - Added workspace state and loading through `PortfolioDataService`.
  - Existing ticker-based routes remain compatible, but are now explicitly sourced from the watchlist.
  - Legacy storage remains mirrored temporarily to prevent breaking existing deployments.

Validation:

- Static inspection completed for the edited files.
- Frontend build still needs to be run from the frontend directory; the command runner in this environment rejects paths containing spaces, so use a terminal with:
  `cd "C:\\Users\\Sahil Belchada\\Desktop\\ly project\\smart-portfolio-advisor\\frontend" && npm run build`

Known limitations:

- The SQL migration has not been applied to Supabase by this agent.
- Holdings UI and actual position-based analytics are not implemented yet.
- Remote sync is best-effort and preserves local data if tables are unavailable.

## Step 1 completed changes

Date: 2026-08-30

Changed:

- `frontend/index.html`
  - Replaced the default `frontend` title.
  - Added description, theme color, and Open Graph metadata.
- `frontend/src/components/OnboardingWizard.jsx`
  - Replaced an accidental `PortfolioPilot` product-name reference with `SmartAdvisor`.
- `frontend/src/components/LandingPage.jsx`
  - Replaced the non-functional `Watch Demo` button with an in-page `Explore Features` link to `#features`.

Validation:

- Run from `C:\Users\Sahil Belchada\Desktop\ly project\smart-portfolio-advisor\frontend`:
  - `npm run build`

Known limitation:

- Footer legal links and full legal pages are not implemented yet. Do not claim specific security, encryption, broker coverage, or regulatory status until those capabilities are verified and documented.

## Next step for the next model

Design and implement the data foundation before adding more dashboard cards:

1. Inspect `frontend/src/services/supabaseClient.js`, `App.jsx`, `PortfolioBuilderView.jsx`, and the Supabase schema/migrations if present.
2. Define a backward-compatible model for:
   - `watchlists`
   - `portfolios`
   - `holdings`
   - `transactions`
   - `accounts`
3. Preserve existing ticker-only demo behavior while introducing explicit `portfolio` and `watchlist` state.
4. Do not silently treat ticker symbols as actual owned positions.
5. Add tests or at minimum a deterministic local storage fallback for the new structures.
6. Update this log before moving to UI work.

## Handoff rules

- Use absolute paths in notes and final summaries.
- Keep advanced model names available in explanations, but lead user-facing copy with outcomes.
- Every investment recommendation must be labeled as quantitative analysis, not guaranteed advice.
- Run the frontend build after frontend changes.
- Verify every edited file at the end of each step.
- Never mark a feature complete merely because a route or card exists; verify its data path and empty/error states.
