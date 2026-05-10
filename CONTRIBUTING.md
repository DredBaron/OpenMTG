# Contributing to OpenMTG

Thanks for your interest in contributing. OpenMTG is a self-hosted MTG collection manager built with FastAPI and React. All contributions are reviewed by human maintainer(s).

> **Note:** Purely AI-generated code is not accepted. Please ensure all submitted code is human-written or human-reviewed.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Branch and PR Workflow](#branch-and-pr-workflow)
- [Reporting Issues](#reporting-issues)
- [Scryfall API Policy](#scryfall-api-policy)

---

## Getting Started

1. Fork the repository and clone your fork.
2. Check open issues and the current roadmap in `README.md` before starting new work to avoid duplicating in-progress efforts.
3. For significant changes, open an issue first to discuss the approach.

---

## Development Setup

### Prerequisites

- Docker + Docker Compose (for running the full stack)
- Python 3.12+ (for backend development/testing)
- Node.js 20+ (for frontend development)

### Backend

```bash
cd backend
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_test.txt
```

The backend requires a `DATABASE_URL` environment variable. In production this is assembled by Docker Compose; for local development you need to set it yourself before starting uvicorn:

```bash
DATABASE_URL=postgresql://openmtg:changeme@localhost/openmtg JWT_SECRET=dev-secret uvicorn main:app --reload
```

This requires a running PostgreSQL instance. If you don't have one locally, use the Full Stack (Docker) approach below instead — it's the simplest path for full-stack development.

Once running, the server listens on `http://127.0.0.1:8000`. There is no route at `/` — use `http://127.0.0.1:8000/docs` for the interactive API docs, or `/health` to confirm the server is up. Connection errors from the price refresh scheduler on startup are expected if PostgreSQL is not reachable; the server itself will still start.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173` by default.

### Full Stack (Docker)

```bash
cp .env.example .env
# edit .env with your values
docker compose up -d --build
```

The app will be available at `http://localhost:8080`.

---

## Running Tests

Backend tests use pytest with an in-memory SQLite database. No running PostgreSQL instance is needed.

Make sure the venv is activated, then run from the repo root:

```bash
source venv/bin/activate
pytest
```

Or from within the `backend/` directory:

```bash
source ../venv/bin/activate
pytest tests/
```

Tests are configured in `pytest.ini`. The test database and JWT secret are set automatically via environment variables in that file. Do not commit changes to those values.

All new backend routes or business logic should include corresponding tests in `backend/tests/`.

For the frontend, run the linter before submitting:

```bash
cd frontend
npm run lint
```

---

## Code Style

### Backend (Python)

- Follow PEP 8. Keep functions focused and avoid unnecessary abstractions.
- Route handlers live in `backend/routers/`. Business logic belongs in `backend/services/`.
- Database models go in `backend/models/`. Pydantic schemas go in `backend/schemas.py`.
- Any schema change that alters the database must include an Alembic migration.
- All Alembic migrations require, at minimum, a revision ID and the migration it revises.

To generate a new migration after updating models:

```bash
alembic revision --autogenerate -m "describe the change"
```

Migrations live in `backend/migrations/versions/` and run automatically on startup.

### Frontend (JavaScript/React)

- Components go in `frontend/src/components/`, pages in `frontend/src/pages/`.
- API calls are centralized in `frontend/src/api.js`, add new calls there rather than inline.
- Shared state uses TanStack Query. Avoid local fetch calls where a query hook is already available.
- Run `npm run lint` and resolve all warnings before submitting.

---

## Branch and PR Workflow

- The `main` branch contains the current stable release. Do not target `main` directly.
- The `dev` branch is the active development branch. Open all PRs against `dev`.
- Keep PRs focused as one feature or fix per PR makes review faster.
- Include a clear description of what changed and why.
- Reference any related issues with `Closes #<number>` in the PR description.

Branch naming suggestions:

```
feature/short-description
fix/short-description
chore/short-description
```

---

## Reporting Issues

When filing a bug report, please include:

- OpenMTG version (visible in the UI footer or `constants.py`)
- How you deployed (Docker image, built from source)
- Steps to reproduce
- What you expected vs. what happened
- Relevant logs (from `docker compose logs` or the browser console)

Feature requests are also welcome. Check the roadmap in `README.md` first to see if it's already planned.

---

## Scryfall API Policy

OpenMTG uses the [Scryfall API](https://scryfall.com/docs/api) for card data and pricing. The API rate limit is enforced at **2 requests per second** (hardcoded in `backend/services/scryfall_queue.py`). Do not raise this limit or bypass the rate limiter in any contribution. Contributions that violate Scryfall's [API guidelines](https://scryfall.com/docs/api) will not be accepted.

---

## License

By contributing, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](LICENSE).
