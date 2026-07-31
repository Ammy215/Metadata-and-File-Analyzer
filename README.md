# FileShield — Metadata & File Intelligence Analyzer

Enterprise-oriented file intelligence platform: upload a file, get back hashes, entropy analysis, extracted metadata, keyword/YARA threat matches, and a weighted risk score/verdict. Includes per-user auth, an admin console, audit logging, and a PDF report export.

## Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0, PostgreSQL. Background analysis runs as FastAPI `BackgroundTasks` in the same process (see `backend/app/tasks/analysis_tasks.py`) - no separate worker or message broker.
- **Frontend**: React 18 + Vite, React Router, Tailwind CSS, Framer Motion
- **Reverse proxy** (local/Docker only): nginx, routing `/` to the frontend and `/api/` to the backend
- **Orchestration**: Docker Compose (4 services: `backend`, `db`, `frontend`, `nginx`) for local development; the cloud deployment target splits the frontend (Vercel) and backend+DB (Render + managed Postgres) onto different origins instead - see [Deployment](#deployment).

### On the Celery/Redis question

This was originally built and tested with Celery + Redis (including verified resilience against a broker outage). It was deliberately replaced with in-process `BackgroundTasks` for the actual free-tier deployment target: Render's free tier has no Background Worker option at all (only Web Services, Static Sites, Postgres, and Key-Value are free), so running a Celery worker for genuinely $0 would mean disguising it as a fake Web Service and paying an external pinger to keep it awake - a workaround stacked on a workaround, not a real solution.

The trade-off: a `BackgroundTask` has no durable queue, so a process restart mid-analysis kills that task outright, unlike a properly-configured Celery task which would survive in Redis. In practice Celery's advantage wasn't even fully realized here either - `task_acks_late` was never set, so a worker killed mid-task (as opposed to just losing its Redis connection, which *was* tested) would have lost the task too. The mitigation now: a periodic sweep detects any upload stuck at `analyzed=false` for 30 minutes to 6 hours and automatically retries it - verified by hard-killing the backend mid-analysis and confirming the file self-heals within one sweep cycle, with no data loss and no manual intervention.

## Analyzers

Hash (MD5/SHA1/SHA256) · Shannon entropy (with format-aware handling so compressed media/Office files aren't false-flagged) · Metadata/EXIF/GPS extraction · Keyword/pattern matching · MIME-vs-extension mismatch detection · YARA rule matching · PDF (page count, embedded JavaScript/forms/objects) · PE/executable (imports, sections, suspicious API usage) · Video/audio (via ffmpeg/ffprobe) · Excel (formulas, macros, external links).

## Storage lifecycle

Raw uploaded files are only ever needed transiently, during analysis - nothing serves the original bytes back afterward (only a generated PDF report). A file is deleted from disk immediately after its analysis completes and commits. A periodic sweep (every 15 minutes) both retries analysis for anything stuck at `analyzed=false` for too long (see above) and deletes leftover files from uploads 48 hours to 30 days old as a backstop. Uploads are also capped at 5 concurrent unanalyzed files per user, rejected with a `429` past that, to guard against bursting uploads faster than analysis can keep up.

## Running it locally

Requires Docker Desktop.

```bash
git clone <this-repo-url>
cd "Metadata & File Intelligence Analyzer"
cp .env.example .env               # then edit: set a real POSTGRES_PASSWORD
cp backend/.env.example backend/.env   # then edit: set SECRET_KEY and SUPER_ADMIN_PASSWORD
docker compose up -d --build
```

Then open **http://localhost**. First time only, create the super-admin account:

```bash
docker compose exec backend python create_super_admin_auto.py
```

This creates the account defined by `SUPER_ADMIN_EMAIL`/`SUPER_ADMIN_PASSWORD` in `backend/.env` (no credentials are hardcoded anywhere in the codebase).

Verify everything's healthy:

```bash
docker compose ps        # all 4 services should show "Up", db/backend show "(healthy)"
curl http://localhost/health
```

Stop everything (data persists):

```bash
docker compose down
```

`docker compose down -v` additionally wipes the database volume - only use that if you actually want a clean slate.

## Configuration

Two `.env` files, neither committed (see `.gitignore`):
- **`.env`** (repo root) — Postgres credentials used by Docker Compose.
- **`backend/.env`** — `SECRET_KEY`, `SUPER_ADMIN_PASSWORD`, CORS origins, feature flags, etc. `SECRET_KEY` and `SUPER_ADMIN_PASSWORD` are required with no defaults; the app won't start without them.

Copy the corresponding `.env.example` file and fill in real values before running.

## Deployment

Local Docker Compose puts the frontend and backend behind one nginx origin. The actual free-tier deployment target splits them onto different origins instead:

- **Frontend**: Vercel (static Vite build; `frontend/vercel.json` provides the SPA fallback that nginx's `try_files` handled locally).
- **Backend**: Render Web Service, with `VITE_API_URL` set at the frontend's build time to the backend's real Render URL (axios prefixes every relative `/api/...` call with it - see `frontend/src/main.jsx`).
- **Database**: a managed Postgres (e.g. Render Postgres or Neon), pointed at via `DATABASE_URL`.
- **CORS**: `backend/.env`'s `CORS_ORIGINS` must include the real Vercel domain.

## Security notes

JWT auth (access + refresh tokens) with role-based access (USER/ADMIN/SUPER_ADMIN), plus API-key auth as an alternate method — both scoped so a credential only ever authenticates as its own owner, with strict per-user data isolation enforced on every endpoint. Bcrypt password hashing, per-IP rate limiting (failed-login lockout and registration throttling), audit logging, and file-content validation (not just extension checks) on every upload.

## License

No license file yet — all rights reserved by default until one is added.
