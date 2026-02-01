# Smart Health API (Backend)

FastAPI backend for the unified health data platform.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- PostgreSQL (for non-demo or when using demo with a real DB)

## Setup

1. **Install dependencies**

   ```bash
   cd backend
   uv sync
   ```

2. **Environment**

   Create a `.env` in the `backend` directory (optional):

   ```env
   DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/healthdata
   DEMO_MODE=true
   ```

   - `DATABASE_URL`: PostgreSQL connection string. Default: `postgresql+psycopg2://postgres:postgres@localhost:5432/healthdata`
   - `DEMO_MODE`: Set to `true` to create tables on startup and seed deterministic mock data when the DB is empty. Default: `false`

## Run

**Development (with demo data)**

```bash
cd backend
DEMO_MODE=true uv run python main.py
```

Or with uvicorn and auto-reload:

```bash
cd backend
DEMO_MODE=true uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production (no demo seeding)**

```bash
cd backend
uv run python main.py
```

- API: http://localhost:8000  
- OpenAPI docs: http://localhost:8000/docs  
- Health check: http://localhost:8000/healthz  

## Demo mode

When `DEMO_MODE=true`:

1. On startup, all tables are created (`metadata.create_all`).
2. If no health metrics exist, 90 days of deterministic mock data are seeded:
   - 5 metrics: `sleep_hours`, `steps`, `calories`, `resting_hr`, `weight`
   - **Known anomaly:** `resting_hr` spike for 3 consecutive days (days 45–47).
   - **Known correlation:** `sleep_hours` negatively correlates with `calories` with a 1-day lag (formula in `core/mock_data.py`).

No Alembic or background jobs are used.
