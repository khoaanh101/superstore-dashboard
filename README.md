# Superstore Sales Dashboard

A full-stack web dashboard for analyzing superstore sales data — featuring authentication, interactive charts, and a filterable data table.

Built with **FastAPI** (backend) and **vanilla HTML/CSS/JS** (frontend), backed by **PostgreSQL**.

---

## Dashboard Login

<p align="center">
    <img src="img/login.png" alt="Login Page" width="800"/>
</p>

---

## Dashboard

<p align="center">
    <img src="img/dashboard-main.png>" alt="Dashboard Overview" width="800"/>
</p>

<p align="center">
    <img src="img/dashboard-main_.png>" alt="Data Table (Manifest)" width="800"/>

---

## Features

- **JWT Authentication** — Login, Register, and Logout with access token + refresh token rotation
- **KPI Summary Cards** — Total Sales, Total Profit, Orders, and Profit Margin computed in a single SQL query
- **Interactive Charts** — Sales by Category, Region, Segment, and Profit by Sub-Category (Chart.js)
- **Filterable Charts** — Filter all charts simultaneously by Region, Category, or State
- **Data Table (Manifest)** — Paginated, filterable table with First / Prev / Next / Last navigation and row count display
- **Skeleton Loaders** — Animated placeholders while data is being fetched
- **Auto Token Refresh** — Silent token refresh on 401; parallel-safe (no duplicate refresh calls)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL, Alembic (migrations) |
| Auth | JWT (PyJWT), bcrypt, refresh token rotation |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Charts | Chart.js |
| Runtime | Python 3.12, uv |

---

## Project Structure

```
superstore-dashboard/
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point, static file routing
│   │   ├── config.py        # Settings loaded from .env
│   │   ├── database.py      # Async SQLAlchemy engine & session
│   │   ├── dependencies.py  # Auth dependency (get_current_user)
│   │   ├── models.py        # ORM models: User, RefreshToken, SuperstoreSale
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── security.py      # JWT helpers, password hashing
│   │   └── routers/
│   │       ├── auth.py      # /auth/token, /auth/register, /auth/refresh, /auth/logout
│   │       ├── chart.py     # /chart — chart data aggregations
│   │       └── query.py     # /query/summary, /query/aggregate, /query/rows
│   ├── migrations/          # Alembic migration versions
│   └── alembic.ini          # Alembic configuration
│
├── frontend/
│   ├── index.html           # Single-page application entry point
│   ├── style.css            # Design system, layout, components
│   ├── app.js               # All frontend logic (auth, charts, table, API layer)
│   └── assets/
│       └── favicon.png      # Browser tab icon
│
├── postgre_env/
│   └── compose.yml          # Docker Compose for PostgreSQL + pgAdmin
│
├── .env                     # Local environment variables (gitignored)
├── .env.sample              # Template for required environment variables
├── pyproject.toml           # Python project metadata and dependencies
├── uv.lock                  # Locked dependency versions
└── README.md
```

---

## Getting Started

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL (or Docker for the included Compose setup)

### 2. Start the database

```bash
cd postgre_env
docker compose up -d
```

This starts PostgreSQL on port `5432` and pgAdmin on port `5050`.

### 3. Configure environment

Copy the sample file and fill in your values:

```bash
cp .env.sample .env
```

Required variables:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/superstore_sales
JWT_SECRET=your-random-secret-key        # generate: python -c "import secrets; print(secrets.token_hex(32))"
JWT_EXPIRES_MINUTES=60
```

### 4. Install dependencies

```bash
uv sync
```

### 5. Run database migrations

```bash
uv run alembic -c backend/alembic.ini upgrade head
```

### 6. Import sales data

Import the Superstore dataset CSV into the `superstore_sales` table using pgAdmin (`http://localhost:5050`) or `psql`.

### 7. Start the development server

First, activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Then start the server:

```bash
fastapi dev backend/app/main.py
```

Open `http://localhost:8000` in your browser.

---

## Expose locally with ngrok (optional)

[ngrok](https://ngrok.com/) lets you share your local server over the internet — without deploying or exposing any secret keys.

### 1. Install ngrok

Download from [https://ngrok.com/download](https://ngrok.com/download) and follow the OS-specific install instructions, **or** install via package manager:

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

In one terminal:

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

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/token` | Login — returns access + refresh tokens |
| `POST` | `/auth/refresh` | Exchange a refresh token for a new pair |
| `POST` | `/auth/logout` | Revoke the refresh token |
| `GET` | `/query/summary` | KPI totals (sales, profit, order count) |
| `GET` | `/query/rows` | Paginated sales rows with optional filters |
| `POST` | `/query/aggregate` | Generic GROUP BY aggregation |
| `GET` | `/chart` | Chart data for a specific chart type |
| `GET` | `/health` | Health check |

Full interactive docs available at `http://localhost:8000/docs`.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Async PostgreSQL connection string |
| `JWT_SECRET` | ✅ | — | Secret key for signing JWTs |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT signing algorithm |
| `JWT_EXPIRES_MINUTES` | ❌ | `60` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRES_DAYS` | ❌ | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | ❌ | `*` | Comma-separated allowed origins |
| `DEBUG` | ❌ | `false` | Enable FastAPI debug mode |
