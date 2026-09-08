# Setu

Skill-mapping and placement platform. Students build a structured skill profile, faculty see batch-level skill gaps against live market demand, recruiters get ranked candidates. One matching engine (`backend/app/engine.py`) powers all three views.

## Demo logins (password for all: `setu1234`)

| Role      | Email                 |
|-----------|-----------------------|
| Student   | student@setu.demo     |
| Faculty   | faculty@setu.demo     |
| Recruiter | recruiter@setu.demo   |

## Run locally (Windows, no Docker)

Requirements: Python 3.11+, Node 20+, a Postgres connection string (Neon free tier works).

Backend, in one terminal:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `backend\.env`, paste your Neon connection string into `DATABASE_URL`, set any long random `JWT_SECRET`. Then:

```
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Frontend, in a second terminal:

```
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Run with Docker

For a persistent database, put your Neon connection string in `backend/.env`:

```
DATABASE_URL=postgresql://<user>:<password>@<neon-host>/<database>?sslmode=require
JWT_SECRET=<long-random-secret>
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

Docker loads these values into the backend. The local Postgres container remains available as a fallback only when `DATABASE_URL` points to `db:5432`.

```
docker compose up --build
```

App on http://localhost:8080, API on http://localhost:8000/docs.

Run migrations and seed demo data against the configured database when needed:

```
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
```

`seed.py` replaces existing demo/application data, so run it only for a fresh database or when you intentionally want to reset seeded data.

## Deploy to a public URL

1. Push this folder to a GitHub repo.
2. Neon: create a project, copy the connection string.
3. Render: New > Blueprint, pick the repo (uses `render.yaml`). Set `DATABASE_URL` to the Neon string and `CORS_ORIGINS` to your future Vercel URL. After the first deploy open Shell on the service and run `python seed.py`.
4. Vercel: import the repo, set root directory to `frontend`, add env `VITE_API_URL=https://<your-render-service>.onrender.com`. Deploy.
5. Back in Render, make sure `CORS_ORIGINS` contains the exact Vercel URL (no trailing slash), then redeploy.

## Folders

- `backend/app/engine.py` matching and gap engine, pure functions, no database access
- `backend/app/routers/` one file per role plus auth and reference data
- `backend/alembic/` database migrations
- `backend/seed.py` demo data: 83 skills, 61 students, 25 postings, market feed import
- `frontend/src/pages/` landing, auth, and the three role dashboards
- `frontend/src/api.js` every backend call in one place
