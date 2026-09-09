# Setu

Skill-mapping and placement platform. Students build a structured skill profile, faculty see batch-level skill gaps against live market demand, recruiters get ranked candidates. One matching engine (`backend/app/engine.py`) powers all three views.

## Demo logins

The seeded demo accounts all use the password `setu1234`:

| Role      | Email                 |
|-----------|-----------------------|
| Student   | student@setu.demo     |
| Faculty   | faculty@setu.demo     |
| Recruiter | recruiter@setu.demo   |

## Run locally without Docker

Requirements: Python 3.11, Node 20+, and a PostgreSQL connection string. Neon works for both development and production.

### Backend

From the repository root, run these commands in PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and set `DATABASE_URL` to your Neon connection string. Replace `JWT_SECRET` with a long random value. Keep `.env` private and never commit it.

Then, from the `backend` directory:

```powershell
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

In a second PowerShell terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the app at http://localhost:5173. The Vite development proxy forwards `/api` requests to the backend on port `8000`.

### Tests

From the `backend` directory:

```powershell
pip install -r requirements-dev.txt
pytest
```

### Optional skill-vector generation

The checked-in `backend/app/data/skill_vectors.json` is enough for normal runtime use. Only install this extra dependency if you need to regenerate vectors:

```powershell
pip install sentence-transformers==3.3.1
python scripts/generate_skill_vectors.py
```

## Run with Docker

For a persistent database, put your Neon connection string in `backend/.env`:

```
DATABASE_URL=postgresql://<user>:<password>@<neon-host>/<database>?sslmode=require
JWT_SECRET=<long-random-secret>
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

Docker loads these values into the backend. The local `db` container still starts, but it is not used when `DATABASE_URL` points to Neon.

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

To use Docker's local PostgreSQL instead of Neon, set this value in `backend/.env`:

```env
DATABASE_URL=postgresql://setu:setu@db:5432/setu
```

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
