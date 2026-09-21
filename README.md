# ExPlan

ExPlan is a local, desktop personal-finance journal. It uses a PySide6 graphical
interface and a SQLite database stored in the current user's home directory.
The application records accounts and transactions, then presents balances,
budgets, savings goals, analytics, and month-to-month comparisons.

This README describes the implementation that is present in this repository. It
does not imply that planned or placeholder UI is complete.

## Main features

### Implemented and exercised

- Username-or-email authentication with Argon2 password hashing.
- Registration with duplicate username/email checks.
- Automatic creation of a `Cash` account and six default categories for a new
  user.
- Session-scoped login, logout, and an application lock/unlock screen.
- Multiple accounts with opening/current balances and UGX display formatting.
- Income, expense, and same-user transfer transaction services.
- Transaction deletion with balance reversal.
- Recent transaction timeline UI with date grouping.
- Monthly category spending chart using Matplotlib.
- Monthly/yearly budgets and category/overall budget-usage calculation.
- Savings-goal creation, contribution, and withdrawal workflows.
- A time-machine view comparing selected-month and current-month
  income/expenses/savings.
- A dashboard command center with selectable periods, prior-period comparisons,
  cash-flow visualization, spending categories, budget health, active goals,
  account balances, recent activity, financial pulse insights, persisted custom
  date ranges, and cash-flow hover tooltips.
- Dark QSS theme and runtime appearance controls.
- SQLite schema creation on application startup.

### Present in the UI but incomplete or limited

- The Accounts view supports creating accounts through its dialog.
- Transaction search and category filters are applied to loaded transactions.
- Goals support contribution and withdrawal dialogs with user-scoped validation.
- Recurring transactions are modeled but have no service or UI workflow.
- Settings persist in a versioned JSON preferences document.
- The dashboard shows a compact selected-versus-prior-period comparison and
  routes to the full Time Machine view. Both views use shared transaction
  analytics; the full Time Machine remains a separate screen.
- Dashboard budget health evaluates transactions within the selected dashboard
  range, while the Budgets view retains each budget's configured period.

## Tech stack

- Python 3.12+ (the checked-in virtual environment currently uses Python 3.14)
- PySide6 6.11.x for the desktop UI
- SQLAlchemy 2.x ORM
- SQLite
- argon2-cffi for password hashing
- Matplotlib for analytics
- pytest for automated tests
- Django 5.2 for the optional parallel web/health workflow
- Alembic, Pydantic, and python-dateutil are declared in
  [`requirements.txt`](./requirements.txt), but no application code currently
  uses them directly.

## Architecture

The application follows a lightweight layered desktop architecture:

```text
src/main.py
  -> src/ui/app.py
       -> PySide6 views and dialogs
            -> service classes
                 -> SQLAlchemy models
                      -> SQLite database
```

- **UI:** [`src/ui/`](./src/ui/) contains the main window, views, dialogs,
  reusable transaction widgets, and the QSS stylesheet.
- **Services:** [`src/services/`](./src/services/) contains authentication,
  account, transaction, budget, and goal business logic.
- **Models:** [`src/models/`](./src/models/) defines SQLAlchemy entities and
  relationships.
- **Core:** [`src/core/config.py`](./src/core/config.py) creates the engine,
  session factory, database schema, and session generator.
  [`src/core/security.py`](./src/core/security.py) wraps Argon2 hashing and
  verification.
- **Repository layer:** [`src/repositories/base.py`](./src/repositories/base.py)
  provides a generic CRUD helper, but current services query SQLAlchemy
  directly and do not use this class.

There is no HTTP server, REST/GraphQL API, cloud database, or external
authentication integration in the desktop application. An optional Django
project is included as a separate web layer for CI/build validation; it
currently exposes only a GET `/health/` endpoint and does not replace the
PySide6 application or reuse the desktop SQLite schema.

## Project structure

```text
expense_manager/
├── src/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── ui/
│       ├── app.py
│       ├── components/
│       ├── dialogs/
│       ├── styles/main.qss
│       └── views/
├── django_project/          # Optional Django web-layer configuration
├── webapp/                   # Django health endpoint and tests
├── manage.py
├── .github/workflows/ci.yml # Django and desktop CI
├── tests/test_services.py
├── requirements.txt
└── README.md
```

The local `venv/` directory and pytest cache are development artifacts, not
application source.

## Setup and installation

PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The repository already contains a virtual environment in the audited checkout,
but recreating it from `requirements.txt` is the portable setup.

## Configuration and environment

There are no required environment variables or `.env` files. The optional
`ALEMBIC_DATABASE_URL` variable overrides the database URL for migration
commands and tests; normal application startup uses the local database path.

At import time, [`src/core/config.py`](./src/core/config.py) sets:

```text
Database: <user home>/.expense_manager/database.db
```

On Windows this is normally:

```text
C:\Users\<user>\.expense_manager\database.db
```

The login view may also write
`<user home>/.expense_manager/config.json` containing the last login
identifier. It does not store the password.

Appearance settings are stored in
`<user home>/.expense_manager/preferences.json` with a `version` field. Writes
use a temporary file and atomic replacement.

The application expects to be started from the repository root because the
stylesheet is opened using the relative path `src/ui/styles/main.qss`.

## Run locally

From the project root:

```powershell
.\venv\Scripts\python.exe src\main.py
```

Startup creates missing SQLite tables and opens the PySide6 window. A display
server is required for normal interactive use. For a headless smoke test on
Windows, the audited run used:

```powershell
$env:PYTHONPATH = "."
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe src\main.py
```

## Build and test

There is no packaging, installer, executable build, CI workflow, or deployment
configuration in the repository.

Run the automated tests:

```powershell
$env:PYTHONPATH = "."
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m pytest -q
```

Audited result: **19 passed**.

Run the optional Django workflow locally:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
```

The Django layer is also validated by
[`.github/workflows/ci.yml`](./.github/workflows/ci.yml), which runs Django
checks/tests, the PySide6 test suite, and Python compilation on pushes and pull
requests targeting `main`.

Compile-check the Python source:

```powershell
$env:PYTHONPATH = "."
.\venv\Scripts\python.exe -m compileall -q src tests
```

Audited result: **pass**.

## Authentication and data handling

- `AuthService.register()` checks username and email uniqueness, hashes the
  password with Argon2, creates the user, and creates default financial data.
- `AuthService.login()` accepts either username or email and stores the
  authenticated `User` in an in-process singleton.
- The lock screen keeps that in-process session and re-verifies the password.
- `AuthService.logout()` clears the singleton.
- All persistence is local SQLite through SQLAlchemy sessions.
- No user authorization/session token mechanism exists because this is a
  single-process desktop application.

## Verified current status

The following were executed in the audited checkout:

| Area | Result |
| --- | --- |
| Python compilation | Pass |
| Automated service/UI/migration/dashboard tests | 19 passed |
| SQLite schema initialization | Pass; database created under `~/.expense_manager` |
| Headless application startup | Process launched and remained alive during an 8-second smoke interval |
| Main-window navigation | All registered views were reached programmatically |
| Registration/login/duplicate/bad-password service flow | Pass |
| Income, expense, transfer, delete/reversal service flow | Pass |
| Budget and savings-goal service flow | Pass |
| Goal contribution and withdrawal flow | Pass |
| Fresh and legacy-snapshot migration tests | Pass |
| Versioned preferences save/load | Pass |
| Dashboard period persistence, snapshot, selected-range budgets, and empty-state behavior | Pass |
| Cash-flow chart hover tooltip hit area | Implemented; automated offscreen test coverage is limited |
| Dashboard headless composition smoke test | Pass |
| Budget/goal view construction | Pass |
| Unauthenticated transaction-dialog construction | Pass; dialog disables saving and shows a sign-in message |
| Interactive mouse/keyboard use, visual layout at multiple resolutions, and screen-reader behavior | Not tested |

## Known issues and limitations

### Critical

No critical production issue was proven by the executed tests. The application
is local-only and has no network API.

### High

1. **Migration compatibility:** existing databases without an
   `alembic_version` table are stamped as the current head during startup.
   This adopts the current schema but cannot infer unknown schema drift, so a
   backup is required before upgrades.

### Medium

1. The generic repository is unused, and direct service queries duplicate data
   access patterns.

### Low

1. The selected font-family value is only partially honored because Qt uses the
   first family in the configured family list.
2. Several declared dependencies are currently unused.
3. The default account/category setup and service input validation have no
   database constraints for many domain rules.

## Recommended next improvements

The improvements should be delivered as small, independently verifiable
iterations. Do not combine UI expansion, schema migration, and security-policy
changes in one release.

### Iteration 0 — Establish a safe baseline — COMPLETE

**Goal:** make future changes measurable without changing product behavior.

**Files:**

- [`tests/test_services.py`](./tests/test_services.py)
- Add focused tests under `tests/` as needed.

**Work:**

1. Add fixtures for a fresh in-memory database and authenticated user.
2. Add tests that document current behavior for accounts, transfers, budgets,
   goals, and login failures.
3. Add a test command that always sets `PYTHONPATH=.` and
   `QT_QPA_PLATFORM=offscreen`.
4. Recorded baseline before production changes: `5 passed`, compilation passed.

**Acceptance criteria:**

- Existing tests remain green.
- Every later iteration has at least one regression test before implementation.
- No production source behavior changes in this iteration.

**Verification:**

```powershell
$env:PYTHONPATH = "."
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m compileall -q src tests
```

### Iteration 1 — Enforce transaction and ownership invariants — COMPLETE

**Goal:** prevent financial data corruption and cross-user mutations.

**Files:**

- [`src/services/transaction_service.py`](./src/services/transaction_service.py)
- [`src/services/goal_service.py`](./src/services/goal_service.py)
- [`src/services/budget_service.py`](./src/services/budget_service.py)
- [`src/services/account_service.py`](./src/services/account_service.py)
- [`tests/test_services.py`](./tests/test_services.py)

**Work:**

1. Reject `amount <= 0` before changing any balance.
2. Validate that `category_id`, when provided, belongs to `user_id`.
3. Validate that a transfer target is different from the source account.
4. Validate that both transfer accounts belong to `user_id`.
5. Validate that `delete_transaction()` only reverses accounts owned by the
   transaction's user.
6. Change `GoalService.add_contribution()` to accept `user_id` and require
   goal ownership.
7. Apply the same user-scoped validation to budget/category mutations.
8. Use one transaction/rollback boundary so a failed balance update cannot
   leave a partially committed record.

**Acceptance criteria:**

- Zero and negative income, expense, and transfer amounts raise `ValueError`.
- Cross-user account, category, goal, and transfer IDs are rejected.
- Same-account transfers are rejected.
- Failed mutations leave balances and transaction rows unchanged.
- Existing valid service flows still pass.

**Verification:**

- Add positive and negative-path tests for every rule.
- Run the Iteration 0 test commands.

### Iteration 2 — Make dashboard totals truthful — COMPLETE

**Goal:** replace hard-coded dashboard values with database-backed monthly
aggregates.

**Files:**

- [`src/ui/views/dashboard_view.py`](./src/ui/views/dashboard_view.py)
- Prefer a reusable aggregate method in
  [`src/services/transaction_service.py`](./src/services/transaction_service.py)
- [`tests/test_services.py`](./tests/test_services.py)

**Work:**

1. Add a service method returning current-month income, expense, and savings.
2. Filter by authenticated `user_id`, transaction type, month, and year.
3. Exclude transfers from income and expense totals.
4. Update all three dashboard cards in `refresh()`.
5. Return zero for empty months without using placeholder UI logic.

**Acceptance criteria:**

- Seeded income and expenses appear in the correct cards.
- Transfers do not affect monthly income, expense, or savings.
- Another user's transactions never affect the result.
- Empty months display zero through the aggregate result.

**Verification:**

- Add service tests with same-month, prior-month, and transfer transactions.
- Construct and refresh the dashboard in an offscreen Qt test.

### Iteration 3 — Fix authentication guards and error reporting — COMPLETE

**Goal:** ensure invalid UI state fails safely and visibly.

**Files:**

- [`src/ui/dialogs/add_transaction_dialog.py`](./src/ui/dialogs/add_transaction_dialog.py)
- [`src/ui/views/budgets_view.py`](./src/ui/views/budgets_view.py)
- [`src/ui/views/goals_view.py`](./src/ui/views/goals_view.py)
- [`src/ui/views/login_view.py`](./src/ui/views/login_view.py)
- [`src/ui/views/lock_view.py`](./src/ui/views/lock_view.py)
- [`src/ui/views/settings_view.py`](./src/ui/views/settings_view.py)

**Work:**

1. Check authentication before loading dialog data.
2. Close or redirect unauthenticated dialogs instead of dereferencing
   `None`.
3. Replace bare `except:` blocks with specific exception handling.
4. Display validation and persistence errors in the relevant dialog.
5. Disable Save until required selections and positive amounts are valid.
6. Preserve the database error message in logs or a user-safe message without
   exposing sensitive internals.

**Acceptance criteria:**

- Constructing the transaction dialog while logged out no longer raises.
- Invalid form submissions show an actionable message.
- Database failures do not silently reject a form.
- Login and lock/unlock behavior remains unchanged for valid credentials.

**Verification:**

- Add offscreen Qt tests for unauthenticated construction and invalid saves.
- Run the full test suite with `QT_QPA_PLATFORM=offscreen`.

### Iteration 4 — Complete or remove visible unfinished workflows — COMPLETE

**Goal:** make every visible primary control functional.

**Files:**

- [`src/ui/views/accounts_view.py`](./src/ui/views/accounts_view.py)
- [`src/ui/views/transactions_view.py`](./src/ui/views/transactions_view.py)
- [`src/ui/dialogs/add_transaction_dialog.py`](./src/ui/dialogs/add_transaction_dialog.py)
- [`src/ui/views/goals_view.py`](./src/ui/views/goals_view.py)
- Add focused dialog/view tests under `tests/`.

**Work:**

1. Add an account dialog and connect `New Account`.
2. Validate account name, type, currency, and opening balance.
3. Populate the transaction category filter for the current user.
4. Apply search and category filters in one refresh/query path.
5. Add goal contribution and withdrawal workflows, including ownership and
   balance validation; or remove the unfinished controls until implemented.
6. Refresh affected views after each successful mutation.

**Acceptance criteria:**

- Every visible primary button has a working success and failure path.
- Search and category filtering change displayed transactions.
- Account and goal mutations are user-scoped and tested.
- No placeholder controls remain visible without an explicit disabled state.

**Verification:**

- Add Qt tests for each dialog and filter state.
- Manually exercise registration, account creation, transaction creation,
  filtering, goal contribution, and navigation.

### Iteration 5 — Persistence, migrations, and recovery — COMPLETE WITH LIMITATION

**Goal:** make local data upgrades and recovery safe.

**Files:**

- [`src/core/config.py`](./src/core/config.py)
- `alembic.ini`
- `alembic/`
- [`requirements.txt`](./requirements.txt)
- [`README.md`](./README.md)

**Work:**

1. Configure Alembic against the existing SQLite URL.
2. Create an initial migration matching the current models.
3. Change startup from unconditional `create_all()` to migration execution,
   while preserving a documented development bootstrap path.
4. Add an explicit database backup/export command or documented procedure.
5. Resolve the stylesheet path relative to the project/module location instead
   of the process working directory.
6. Persist settings only after defining a stable configuration schema.

**Acceptance criteria:**

- A fresh database can be created from migrations.
- A copy of an existing database can be upgraded without data loss.
- Startup from outside the repository root still finds the stylesheet.
- Backup and restore steps are documented and tested on a copy.

**Verification:**

- Test fresh migration, upgrade migration, and rollback/backup behavior on
  temporary databases.
- Do not run migrations against a user's real database during tests.

### Iteration 6 — Authentication hardening and release readiness — COMPLETE WITH FOLLOW-UPS

**Goal:** finish security controls and establish supported distribution.

**Files:**

- [`src/services/auth_service.py`](./src/services/auth_service.py)
- [`src/core/security.py`](./src/core/security.py)
- [`src/ui/views/login_view.py`](./src/ui/views/login_view.py)
- [`README.md`](./README.md)
- Add security-focused tests under `tests/`.

**Work:**

1. Define and enforce a minimum password policy.
2. Enforce failed-login throttling or a bounded local lockout policy.
3. Avoid writing unnecessary identifiers to disk, or document the privacy
   implication of `config.json`.
4. Review SQLite/config file permissions and backup handling.
5. Choose a supported packaging format such as a Windows executable/installer.
6. Add a release checklist covering migrations, backups, tests, and versioning.

**Acceptance criteria:**

- Password policy and lockout behavior are deterministic and tested.
- Error messages do not reveal whether a username or email exists beyond the
  chosen product policy.
- The supported installation/run path is documented and reproducible.
- A clean-machine smoke test is recorded before release.

## Suggested release gates

Every iteration should meet all of these gates before merging:

1. Focused tests for the changed behavior pass.
2. The complete test suite passes.
3. Python compilation passes.
4. No new broad exception handlers, silent fallbacks, or placeholder controls
   are introduced.
5. README functionality and known-issue sections are updated.
6. The change is manually smoke-tested if it affects Qt interaction.

## Deployment

No deployment target or packaging process was discoverable. The verified
distribution model is running the Python source from a checkout with the
declared dependencies installed. Any production distribution would need an
installer/package, database migration strategy, backup policy, and a
review of local-file permissions.
