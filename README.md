# FileShield — Metadata & File Intelligence Analyzer

Enterprise-oriented file intelligence platform: upload a file, get back hashes, entropy analysis, extracted metadata, keyword/YARA threat matches, and a weighted risk score/verdict. Includes per-user auth, an admin console, audit logging, and a PDF report export.

## Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0, PostgreSQL, Celery + Redis for background analysis
- **Frontend**: React 18 + Vite, React Router, Tailwind CSS, Framer Motion
- **Reverse proxy**: nginx (routes `/` to the frontend, `/api/` to the backend, `/flower/` to Celery monitoring)
- **Orchestration**: Docker Compose (7 services: `backend`, `celery_worker`, `db`, `flower`, `frontend`, `nginx`, `redis`)

## Analyzers

Hash (MD5/SHA1/SHA256) · Shannon entropy (with format-aware handling so compressed media/Office files aren't false-flagged) · Metadata/EXIF/GPS extraction · Keyword/pattern matching · MIME-vs-extension mismatch detection · YARA rule matching · PDF (page count, embedded JavaScript/forms/objects) · PE/executable (imports, sections, suspicious API usage) · Video/audio (via ffmpeg/ffprobe) · Excel (formulas, macros, external links).

## Running it

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
docker compose ps        # all 7 services should show "Up", db/redis/backend show "(healthy)"
curl http://localhost/health
```

Stop everything (data persists):

```bash
docker compose down
```

`docker compose down -v` additionally wipes the database/Redis volumes — only use that if you actually want a clean slate.

## Configuration

Two `.env` files, neither committed (see `.gitignore`):
- **`.env`** (repo root) — Postgres credentials used by Docker Compose.
- **`backend/.env`** — `SECRET_KEY`, `SUPER_ADMIN_PASSWORD`, CORS origins, feature flags, etc. `SECRET_KEY` and `SUPER_ADMIN_PASSWORD` are required with no defaults; the app won't start without them.

Copy the corresponding `.env.example` file and fill in real values before running.

## Security notes

JWT auth (access + refresh tokens) with role-based access (USER/ADMIN/SUPER_ADMIN), plus API-key auth as an alternate method — both scoped so a credential only ever authenticates as its own owner, with strict per-user data isolation enforced on every endpoint. Bcrypt password hashing, per-IP rate limiting (failed-login lockout and registration throttling), audit logging, and file-content validation (not just extension checks) on every upload.

## License

No license file yet — all rights reserved by default until one is added.
