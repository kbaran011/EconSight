# Phase 4 — DevOps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerise the full EconSight stack with Docker Compose and extend GitHub Actions CI to cover the frontend.

**Architecture:** Three Docker services — `postgres` (PostgreSQL 16), `backend` (FastAPI/uvicorn), `frontend` (Vite build served by nginx). The backend lifespan calls `init_db()` so the schema is created automatically on first start. CI extends the existing `ci.yml` with a `frontend` job running `tsc -b`, `eslint`, and `vite build`. Consulting deck and Loom demo are user-driven and not in scope here.

**Tech Stack:** Docker, Docker Compose v2, nginx:alpine, node:20-alpine, python:3.12-slim, GitHub Actions

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `Dockerfile` | Create | Backend image (python:3.12-slim, installs package + WeasyPrint deps, runs uvicorn) |
| `frontend/Dockerfile` | Create | Frontend image (multi-stage: node build → nginx serve) |
| `frontend/nginx.conf` | Create | nginx SPA config — serve `dist/`, proxy `/api/` to backend |
| `docker-compose.yml` | Create | Orchestrates postgres + backend + frontend with env, healthchecks, depends_on |
| `.env.docker.example` | Create | Committed template showing required vars (no real values) |
| `.env.docker` | Create | Local secrets file — gitignored, never committed |
| `src/econsight/api/main.py` | Modify | Add `init_db()` call to FastAPI lifespan so schema is created on startup |
| `.github/workflows/ci.yml` | Modify | Fix python-version to 3.12; add `frontend` job: tsc -b + eslint + build |
| `.gitignore` | Modify | Add `.env.docker` entry |

---

## Task 1: Add `init_db()` to FastAPI lifespan

**Files:**
- Modify: `src/econsight/api/main.py`

This makes the container self-healing — the schema is created idempotently at every startup, so the DB is ready before the first API call hits.

- [ ] Open `src/econsight/api/main.py`. The current lifespan is:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await maybe_ingest_rag()
    yield
```

Replace with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from econsight.db.connection import init_db
    await init_db()
    await maybe_ingest_rag()
    yield
```

- [ ] Start the backend locally and verify it still boots without errors:

```bash
cd "AI PROJECT/EconSight"
.venv/bin/uvicorn econsight.api.main:app --port 8000 &
sleep 3 && curl -s http://localhost:8000/api/ping
pkill -f "uvicorn econsight"
```

Expected: `{"status":"ok"}`

- [ ] Commit:

```bash
git add src/econsight/api/main.py
git commit -m "feat: call init_db() in FastAPI lifespan for self-healing schema setup"
```

---

## Task 2: Backend Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] Create `Dockerfile` at the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# WeasyPrint requires Pango, Cairo, Harfbuzz, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libharfbuzz0b \
    fontconfig fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
COPY sql/ sql/

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "econsight.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] Build and smoke-test the image:

```bash
docker build -t econsight-backend .
docker run --rm econsight-backend python -c "import econsight; print('ok')"
```

Expected: prints `ok`, exits 0.

- [ ] Commit:

```bash
git add Dockerfile
git commit -m "feat: backend Dockerfile (python:3.12-slim, WeasyPrint deps, sql/ included)"
```

---

## Task 3: Frontend Dockerfile + nginx config

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Proxy API calls to the backend service (keeps full /api/ prefix — FastAPI expects it)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA fallback — all non-asset routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] Create `frontend/Dockerfile` (multi-stage):

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] Build and verify the frontend image in isolation:

```bash
cd "AI PROJECT/EconSight/frontend"
docker build -t econsight-frontend .
docker run --rm -p 3000:80 econsight-frontend &
sleep 2
curl -s http://localhost:3000 | grep -o '<title>.*</title>'
docker stop $(docker ps -q --filter ancestor=econsight-frontend)
```

Expected: `<title>EconSight — Canadian Economic Intelligence</title>`

- [ ] Commit:

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: frontend multi-stage Dockerfile + nginx SPA + API proxy config"
```

---

## Task 4: Docker Compose

**Files:**
- Modify: `.gitignore`
- Create: `.env.docker.example`
- Create: `.env.docker` (gitignored)
- Create: `docker-compose.yml`

- [ ] Add `.env.docker` to `.gitignore` **first** — before creating the file:

```bash
echo ".env.docker" >> ".gitignore"
git add .gitignore
git commit -m "chore: gitignore .env.docker"
```

- [ ] Create `.env.docker.example` (committed, no real secrets):

```env
POSTGRES_PASSWORD=changeme
GROQ_API_KEY=your_groq_key_here
```

- [ ] Create `.env.docker` (local only, never committed — fill in real values):

```env
POSTGRES_PASSWORD=<your_postgres_password>
GROQ_API_KEY=<your_groq_api_key>
```

- [ ] Verify it is gitignored before proceeding:

```bash
git check-ignore -v .env.docker
```

Expected: prints `.env.docker` — if nothing prints, stop and fix `.gitignore` first.

- [ ] Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: econsight
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: .
    env_file: .env.docker
    environment:
      DB_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/econsight
      DB_URL_READONLY: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/econsight
      CORS_ORIGINS: '["http://localhost"]'
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/ping')\""]
      interval: 10s
      timeout: 5s
      retries: 6

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] Bring the stack up and run acceptance checks:

```bash
cd "AI PROJECT/EconSight"
docker compose --env-file .env.docker up --build -d

# Wait for all services to be healthy (~30–60s)
docker compose ps

# API smoke test
curl -s http://localhost/api/ping

# Frontend smoke test
curl -s http://localhost | grep -o '<title>.*</title>'

# Indicators endpoint (confirms DB schema + data path)
curl -s http://localhost/api/indicators | python3 -c "import json,sys; d=json.load(sys.stdin); print('rows:', len(d))"
```

Expected:
- All three services healthy/running
- `/api/ping` → `{"status":"ok"}`
- `/` → EconSight title
- `/api/indicators` → `rows: 36` (or similar — confirms DB is seeded; may be 0 on first run until pipeline is re-run inside the container)

- [ ] Tear down:

```bash
docker compose down
```

- [ ] Commit:

```bash
git add docker-compose.yml .env.docker.example
git commit -m "feat: Docker Compose — postgres + backend + frontend with healthchecks"
```

---

## Task 5: Extend CI with frontend job

**Files:**
- Modify: `.github/workflows/ci.yml`

Current CI has `lint` and `test` jobs using Python 3.11. Changes needed:
- Fix `python-version` to `"3.12"` (stable; 3.14 may not be on all runners)
- Add `frontend` job

- [ ] Open `.github/workflows/ci.yml`. Change both `python-version: "3.11"` instances to `"3.12"`.

- [ ] Append the `frontend` job to the jobs section:

```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx tsc -b
      - run: npx eslint src/
      - run: npm run build
```

- [ ] Commit and push:

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add frontend job (tsc -b + eslint + build), fix python-version to 3.12"
git push
```

- [ ] Watch GitHub Actions: all three jobs (`lint`, `test`, `frontend`) must go green.

---

## Task 6: README update

**Files:**
- Modify: `README.md`

- [ ] Add to `README.md`:
  - Docker quickstart section
  - Required env vars (link to `.env.docker.example`)
  - Placeholder for Loom demo URL

```markdown
## Quick Start (Docker)

```bash
cp .env.docker.example .env.docker
# Fill in POSTGRES_PASSWORD and GROQ_API_KEY in .env.docker
docker compose --env-file .env.docker up --build
```

Open http://localhost — the full stack runs in three containers.

## Environment Variables

See `.env.docker.example` for required vars. Never commit `.env.docker`.

## Demo

<!-- Add Loom URL here after recording -->
```

- [ ] Commit:

```bash
git add README.md
git commit -m "docs: Docker quickstart, env var reference, demo placeholder"
```

---

## Non-Software Phase 4 Items (User-driven)

| Item | What to do |
|------|-----------|
| **Consulting deck** | Use the About page as the script. Slides: Problem → Data Sources → Architecture → Key Findings (health score, forecasts) → Live Demo → Next Steps. 8–10 slides. |
| **Loom demo** | 3–5 min walkthrough: Dashboard → Indicators (switch series) → Ask (2 questions) → Report download. Add URL to README when done. |
