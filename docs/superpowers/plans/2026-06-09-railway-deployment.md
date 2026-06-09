# Railway Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy EconSight (PostgreSQL + FastAPI + React) to Railway as three services so a live public URL exists for the IBM consulting interview.

**Architecture:** The frontend nginx container reads `BACKEND_URL` from an environment variable at startup (via envsubst), allowing the same Docker image to proxy to `backend:8000` in docker-compose and `backend.railway.internal:8000` on Railway. A `resolver 127.0.0.11` directive defers DNS lookup to per-request so nginx starts cleanly even if the backend isn't ready yet.

**Tech Stack:** nginx:alpine, envsubst (busybox built-in), Railway CLI/dashboard, Docker Compose

**Spec:** `docs/superpowers/specs/2026-06-09-railway-deployment-design.md`

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `frontend/nginx.conf` | Modify | Add `resolver 127.0.0.11 valid=10s;`; change `proxy_pass` to `http://${BACKEND_URL}` |
| `frontend/Dockerfile` | Modify | `COPY nginx.conf` → `.template`; add envsubst CMD |
| `docker-compose.yml` | Modify | Add `BACKEND_URL: backend:8000` to frontend service environment |
| `railway.toml` | Create | Backend service config (healthcheck, restart policy) |
| `frontend/railway.toml` | Create | Frontend service config (restart policy) |
| `README.md` | Modify | Add "Deploy to Railway" section after Docker quickstart |

---

## Task 1: Update `frontend/nginx.conf`

**Files:**
- Modify: `frontend/nginx.conf`

- [ ] **Step 1: Make the two-line change**

Replace the entire `location /api/` block. Full file after change:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        resolver 127.0.0.11 valid=10s;
        proxy_pass http://${BACKEND_URL};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Verify the diff is exactly two lines**

```bash
git diff frontend/nginx.conf
```

Expected: two changes only — `resolver` line added, `proxy_pass` value changed. No other lines touched.

---

## Task 2: Update `frontend/Dockerfile`

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Change COPY destination and add CMD**

Full file after change:

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
EXPOSE 80
CMD ["/bin/sh", "-c", "envsubst '\\${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
```

Key changes:
- Line 14: `default.conf` → `default.conf.template`
- Line 16: explicit CMD replacing nginx's default entrypoint

- [ ] **Step 2: Verify diff**

```bash
git diff frontend/Dockerfile
```

Expected: exactly two lines changed — the COPY destination and the new CMD.

---

## Task 3: Update `docker-compose.yml`

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add BACKEND_URL to the frontend service**

The frontend service block after change:

```yaml
  frontend:
    build: ./frontend
    environment:
      BACKEND_URL: backend:8000
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
```

- [ ] **Step 2: Verify diff**

```bash
git diff docker-compose.yml
```

Expected: two lines added (`environment:` key and `BACKEND_URL: backend:8000` value). Nothing else changed.

---

## Task 4: Verify docker-compose still works

**Files:** none — verification only

- [ ] **Step 1: Build frontend image**

```bash
docker compose --env-file .env.docker build frontend
```

Expected: build succeeds, no errors. The `.template` file is copied; the CMD is set.

- [ ] **Step 2: Verify envsubst runs correctly at container start**

```bash
docker compose --env-file .env.docker up -d frontend
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

Expected output contains:
```
proxy_pass http://backend:8000;
```

And does NOT contain `${BACKEND_URL}` — substitution happened. Also confirm `$host` and `$remote_addr` are present and unchanged.

- [ ] **Step 3: Run full stack smoke test**

```bash
docker compose --env-file .env.docker up --build -d
# Wait ~15s for backend healthcheck to pass
curl -sf http://localhost/api/ping
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Tear down**

```bash
docker compose --env-file .env.docker down -v
```

- [ ] **Step 5: Commit the three file changes together**

```bash
git add frontend/nginx.conf frontend/Dockerfile docker-compose.yml
git commit -m "feat: make nginx proxy target injectable via BACKEND_URL env var"
```

---

## Task 5: Create `railway.toml` (backend)

**Files:**
- Create: `railway.toml`

- [ ] **Step 1: Create the file**

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/api/ping"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Verify it parses as valid TOML**

```bash
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add railway.toml
git commit -m "feat: add Railway config for backend service"
```

---

## Task 6: Create `frontend/railway.toml` (frontend)

**Files:**
- Create: `frontend/railway.toml`

- [ ] **Step 1: Create the file**

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Verify it parses as valid TOML**

```bash
python3 -c "import tomllib; tomllib.load(open('frontend/railway.toml','rb')); print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/railway.toml
git commit -m "feat: add Railway config for frontend service"
```

---

## Task 7: Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the Railway deployment section**

Insert the following block immediately after the `## Quick Start (Docker) — Recommended for Demo` section (after the env var table, before `## Design Decisions`):

```markdown
## Deploy to Railway (Live Demo)

Railway runs the full stack in the cloud with a single public URL. Requires a free Railway account.

### One-time setup

1. Push this repo to GitHub.
2. Open [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select this repo.
3. Railway auto-detects `railway.toml` and creates the **backend** service.
4. Click **New** → **Database** → **Add PostgreSQL** — Railway provisions a database and injects `DATABASE_URL` into the backend automatically.
5. In the backend service **Variables** tab, set:

| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | Your key from [console.groq.com](https://console.groq.com) |
| `AUTO_SEED` | `true` |
| `AUTO_SEED_MODELS` | `true` |

6. Click **New** → **GitHub Repo** again → same repo → set **Root Directory** to `frontend` → Railway detects `frontend/railway.toml` and creates the **frontend** service.
7. In the frontend service **Variables** tab, set:

| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `backend.railway.internal:8000` |

8. Note the public domain Railway assigns to the frontend service (e.g. `econsight-frontend-xxxx.railway.app`). In the backend **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | `https://econsight-frontend-xxxx.railway.app` |

9. **Deploy all** — Railway builds and starts all three services.

First boot fetches live data and trains models (~3–8 min). Watch the nav bar for **"Seeding data…"** → **"Data through YYYY-MM"**.

> **Cost:** Railway's free tier includes $5/month credit — enough for a low-traffic demo. Upgrade to the $20/month Hobby plan for always-on uptime.
```

- [ ] **Step 2: Verify the section renders correctly (spot-check)**

```bash
grep -n "Deploy to Railway" README.md
```

Expected: one match showing the new heading.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Railway deployment guide to README"
```

---

## Task 8: Push and verify CI

- [ ] **Step 1: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 2: Watch CI**

Open the Actions tab on GitHub. The `docker` job is the key one — it runs `docker compose up --build`, waits for `/api/ping`, and checks `/api/status`. It will now exercise the envsubst CMD path since it uses the updated Dockerfile and docker-compose.yml.

Expected: all four jobs (`lint`, `test`, `frontend`, `docker`) pass green.

- [ ] **Step 3: If `docker` job fails, diagnose**

```bash
# Reproduce locally
docker compose --env-file .env.docker up --build
docker compose logs frontend
```

Common failure: envsubst CMD syntax error → check `frontend/Dockerfile` CMD quoting.

---

## Task 9: Deploy on Railway

> This task is manual — performed in the Railway dashboard following the README steps above (Task 7).

- [ ] **Step 1: Follow README "Deploy to Railway" section steps 1–9**

- [ ] **Step 2: Verify live deployment**

Once Railway shows all services as **Active**:

```bash
# Replace with your actual Railway frontend domain
curl -sf https://<your-frontend>.railway.app/api/ping
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Open the live URL in a browser**

Check:
- Dashboard loads with health score badge in nav
- Indicators page shows chart data
- Ask page accepts a question (requires GROQ_API_KEY)
- Report page offers PDF download

- [ ] **Step 4: Add live URL to README**

In `README.md`, update the Demo placeholder:

```markdown
## Demo

[Live demo](https://econsight-frontend-xxxx.railway.app) — full stack on Railway (PostgreSQL + FastAPI + React)
```

```bash
git add README.md
git commit -m "docs: add live Railway demo URL"
git push origin main
```
