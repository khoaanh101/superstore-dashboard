# Superstore Sales Dashboard

A full-stack web dashboard for analyzing superstore sales data — featuring authentication, interactive charts, a filterable data table, and admin order management.

Built with **FastAPI** (backend) and **vanilla HTML/CSS/JS** (frontend), backed by **PostgreSQL**.

---

## Dashboard Login

[![Dashboard login screenshot](img/login.png)](https://github.com/khoaanh101/superstore-dashboard)

---

## Dashboard

[![Dashboard overview screenshot](img/dashboard-main.png)](https://github.com/khoaanh101/superstore-dashboard)

[![Dashboard data table screenshot](img/dashboard-main_.png)](https://github.com/khoaanh101/superstore-dashboard)

---

## Features

- **JWT Authentication** — Login, Register, and Logout with access token + refresh token rotation
- **RBAC** — `viewer` role (read-only) and `admin` role (full CRUD on orders)
- **KPI Summary Cards** — Total Sales, Total Profit, Orders, and Profit Margin computed in a single SQL query
- **Interactive Charts** — Sales by Category, Region, Segment, Ship Mode, State and Profit by Sub-Category (Chart.js)
- **Filterable Charts** — Filter all charts simultaneously by Region, Category, Segment, or State
- **Data Table (Manifest)** — Paginated, filterable, sortable table with First / Prev / Next / Last navigation and row count display
- **CSV Export** — Export any filtered view to CSV directly from the browser
- **Order Management** — Admin-only Create, Update, and Delete orders via modal UI
- **Skeleton Loaders** — Animated placeholders while data is being fetched
- **Auto Token Refresh** — Silent token refresh on 401; parallel-safe (no duplicate refresh calls)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL 16, Alembic (migrations) |
| Auth | JWT (PyJWT), bcrypt, refresh token rotation |
| Frontend | Vanilla HTML, CSS (modular), JavaScript (ES modules) |
| Charts | Chart.js |
| Runtime | Python 3.12, uv |
| Containerization | Docker, Docker Compose |
| Backend Tests | pytest, pytest-asyncio, httpx, SQLite (in-memory) |
| Frontend Tests | Jest, jest-environment-jsdom |

---

## Project Structure

```
superstore-dashboard/
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point, static file routing
│   │   ├── config.py            # Settings loaded from .env (via pydantic-settings)
│   │   ├── database.py          # Async SQLAlchemy engine & session
│   │   ├── dependencies.py      # Auth dependencies (get_current_user, require_admin)
│   │   ├── models.py            # ORM models: User, RefreshToken, SuperstoreSale
│   │   ├── schemas.py           # Pydantic request/response schemas & enums
│   │   ├── security.py          # JWT helpers, password hashing, token utilities
│   │   ├── access_middleware.py # HTTP access log middleware
│   │   ├── logging_config.py    # Structured logging setup
│   │   └── routers/
│   │       ├── auth.py          # /auth/register, /auth/token, /auth/refresh, /auth/logout, /auth/me
│   │       ├── chart.py         # /chart/types, /chart — aggregated chart data
│   │       ├── orders.py        # /orders — admin-only CRUD (POST / PUT / DELETE)
│   │       └── query.py         # /query/summary, /query/aggregate, /query/rows, /query/rows/export
│   ├── tests/
│   │   ├── conftest.py          # Shared fixtures: in-memory SQLite DB, test client, seeded users
│   │   ├── helpers.py           # Auth header helper
│   │   ├── test_auth.py         # Integration tests for /auth/* endpoints
│   │   ├── test_chart.py        # Integration tests for /chart/* endpoints
│   │   ├── test_orders.py       # Integration tests for /orders/* endpoints
│   │   ├── test_query.py        # Integration tests for /query/* endpoints
│   │   ├── test_schemas.py      # Unit tests for Pydantic schemas
│   │   └── test_security.py     # Unit tests for security utilities
│   ├── migrations/              # Alembic migration versions
│   └── alembic.ini              # Alembic configuration
│
├── frontend/
│   ├── index.html               # Single-page application entry point
│   ├── style.css                # Base CSS entry (imports modular stylesheets)
│   ├── css/
│   │   ├── base.css             # Design tokens, resets, typography
│   │   ├── auth.css             # Login & register page styles
│   │   ├── dashboard.css        # Dashboard layout & KPI cards layout
│   │   ├── cards.css            # KPI card component styles
│   │   ├── charts.css           # Chart container & filter bar styles
│   │   ├── table.css            # Data table, pagination, modal styles
│   │   └── modal.css            # Order create/edit modal styles
│   ├── js/
│   │   ├── app.js               # App bootstrap, view routing, auth flow
│   │   ├── api.js               # Fetch wrapper with auto token refresh
│   │   ├── auth.js              # Login / register / logout handlers
│   │   ├── charts.js            # Chart.js chart rendering & filter logic
│   │   ├── table.js             # Data table: filters, sort, pagination, CRUD
│   │   ├── loader.js            # Skeleton loader utilities
│   │   ├── storage.js           # LocalStorage token management
│   │   ├── ui.js                # Shared UI helpers (toast, modal toggles)
│   │   └── tests/
│   │       └── storage.test.js  # Jest unit tests for storage.js
│   ├── views/
│   │   ├── view-login.html      # Login view partial
│   │   ├── view-register.html   # Register view partial
│   │   ├── view-dashboard.html  # Dashboard view partial (charts + table)
│   │   └── modal-order.html     # Order create/edit modal partial
│   └── assets/
│       └── favicon.png          # Browser tab icon
│
├── docker-compose.yml           # Full stack: PostgreSQL + pgAdmin + FastAPI backend
├── Dockerfile                   # Multi-stage build for the FastAPI backend
├── .env                         # Local environment variables (gitignored)
├── .env.sample                  # Template for required environment variables
├── pyproject.toml               # Python project metadata and dependencies
├── pytest.ini                   # Pytest configuration (asyncio_mode = auto)
├── uv.lock                      # Locked Python dependency versions
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (for database)

### Option A — Docker Compose (recommended)

Start the full stack (PostgreSQL + pgAdmin + FastAPI) in one command:

```bash
cp .env.sample .env
# Edit .env and set JWT_SECRET, then:
docker compose up -d
```

This starts:
- **FastAPI** on `http://localhost:8000`
- **PostgreSQL** on port `5432`
- **pgAdmin** on `http://localhost:5050`

### Option B — Local Development

#### 1. Start the database

```bash
docker compose up -d postgres pgadmin
```

#### 2. Configure environment

```bash
cp .env.sample .env
```

Required variables:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/superstore_sales
JWT_SECRET=your-random-secret-key
# Generate a secret: python -c "import secrets; print(secrets.token_hex(32))"
JWT_EXPIRES_MINUTES=60
```

#### 3. Install dependencies

```bash
uv sync
```

#### 4. Run database migrations

```bash
uv run alembic -c backend/alembic.ini upgrade head
```

#### 5. Import sales data

Import the Superstore dataset CSV into the `superstore_sales` table using pgAdmin (`http://localhost:5050`) or `psql`.

#### 6. Start the development server

```bash
uv run fastapi dev backend/app/main.py
```

Open `http://localhost:8000` in your browser.

---

## Running Tests

### Backend (pytest)

Tests run on an in-memory SQLite database — no PostgreSQL required.

```bash
# Run all backend tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest backend/tests/test_auth.py -v
uv run pytest backend/tests/test_chart.py -v
uv run pytest backend/tests/test_orders.py -v
uv run pytest backend/tests/test_query.py -v
uv run pytest backend/tests/test_schemas.py -v
uv run pytest backend/tests/test_security.py -v
```

### Frontend (Jest)

```bash
cd frontend
npm install
npm test
```

---

## Expose locally with ngrok (optional)

[ngrok](https://ngrok.com/) lets you share your local server over the internet — without deploying or exposing any secret keys.

### 1. Install ngrok

```bash
# Windows (winget)
winget install ngrok

# macOS (Homebrew)
brew install ngrok/ngrok/ngrok
```

### 2. Authenticate (one-time)

Sign up for a free account at [ngrok.com](https://dashboard.ngrok.com/signup), then run:

```bash
ngrok config add-authtoken <YOUR_AUTHTOKEN>
```

### 3. Start the FastAPI server

```bash
uv run fastapi dev backend/app/main.py
```

### 4. Open a tunnel in another terminal

```bash
ngrok http 8000
```

ngrok will print a public URL like:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Share that URL with anyone — they can access your dashboard without needing your `.env` or database credentials.

> **Note:** The free tier generates a new random URL each time. To get a fixed subdomain, upgrade to a paid ngrok plan.

---

## API Overview

All endpoints except `/auth/*` and `/health` require a `Bearer` token in the `Authorization` header.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create a new user account |
| `POST` | `/auth/token` | — | Login — returns access + refresh tokens |
| `POST` | `/auth/refresh` | — | Exchange a refresh token for a new pair |
| `POST` | `/auth/logout` | — | Revoke the refresh token |
| `GET` | `/auth/me` | viewer+ | Return the current user's profile |
| `GET` | `/chart/types` | viewer+ | List all available chart types |
| `GET` | `/chart` | viewer+ | Aggregated chart data with optional filters |
| `GET` | `/query/summary` | viewer+ | KPI totals (sales, profit, order count) |
| `GET` | `/query/rows` | viewer+ | Paginated, filterable, sortable sales rows |
| `GET` | `/query/rows/export` | viewer+ | Export filtered rows as CSV |
| `POST` | `/query/aggregate` | viewer+ | Generic GROUP BY aggregation |
| `GET` | `/query/columns/groupable` | viewer+ | List groupable column names |
| `GET` | `/query/values/{column}` | viewer+ | Distinct sorted values for a column |
| `POST` | `/orders` | admin | Create a new sale order |
| `PUT` | `/orders/{id}` | admin | Partially update an order |
| `DELETE` | `/orders/{id}` | admin | Delete an order |
| `GET` | `/health` | — | Health check |

Full interactive docs available at `http://localhost:8000/docs`.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Async PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `JWT_SECRET` | ✅ | — | Secret key for signing JWTs |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT signing algorithm |
| `JWT_EXPIRES_MINUTES` | ❌ | `60` | Access token lifetime (minutes) |
| `REFRESH_TOKEN_EXPIRES_DAYS` | ❌ | `7` | Refresh token lifetime (days) |
| `CORS_ORIGINS` | ❌ | `*` | Comma-separated allowed CORS origins |
| `DEBUG` | ❌ | `false` | Enable FastAPI debug mode |
| `PG_USER` | ❌ | `postgres` | PostgreSQL user (Docker Compose) |
| `PG_PASSWORD` | ❌ | `yourpassword` | PostgreSQL password (Docker Compose) |
| `PG_DATABASE` | ❌ | `superstore_sales` | PostgreSQL database name (Docker Compose) |
| `PG_PORT` | ❌ | `5432` | PostgreSQL exposed port (Docker Compose) |
| `PGADMIN_EMAIL` | ❌ | `demo@example.com` | pgAdmin login email (Docker Compose) |
| `PGADMIN_PASSWORD` | ❌ | `secret` | pgAdmin login password (Docker Compose) |

---

## License

This project is licensed under the terms of the MIT license.
