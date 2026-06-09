# EconSight — Railway Deployment Design

**Date:** 2026-06-09  
**Status:** Approved  
**Goal:** Deploy the full EconSight stack (PostgreSQL + FastAPI + React) to Railway so a live public URL can be shared during the IBM consulting interview.

---

## Problem

EconSight runs locally via Docker Compose and passes CI smoke tests, but there is no persistent public URL. Recruiters and interviewers cannot access the dashboard without cloning the repo and running the stack themselves.

---

## Chosen Approach: Three Railway Services (Monorepo)

Deploy three services inside one Railway project:

| Service | Source | Notes |
|---------|--------|-------|
| `postgres` | Railway managed plugin | No Dockerfile needed — Railway provisions and injects `DATABASE_URL` automatically into linked services |
| `backend` | Root `Dockerfile` | FastAPI on port 8000; healthcheck on `/api/ping` |
| `frontend` | `frontend/Dockerfile` | nginx serving the React SPA; proxies `/api/` to backend via private networking |

Internal communication uses Railway private DNS: `backend.railway.internal:8000`. No public hop between frontend and backend.

---

## Code Changes

### 1. `frontend/nginx.conf` — proxy target becomes injectable

**Before:**
```nginx
proxy_pass http://backend:8000;
```

**After:**
```nginx
proxy_pass http://${BACKEND_URL};
```

Two lines change in `nginx.conf`:

```nginx
location /api/ {
    resolver 127.0.0.11 valid=10s;   # added: defer DNS resolution per-request
    proxy_pass http://${BACKEND_URL}; # changed: was http://backend:8000
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**Why `resolver 127.0.0.11 valid=10s;`:** Without this, nginx resolves the upstream hostname (`backend.railway.internal`) once at startup. If the backend container isn't up yet, nginx fails to start. The Docker/Railway internal DNS resolver at `127.0.0.11` defers resolution to per-request so nginx starts cleanly regardless of backend readiness.

**Why the scoped `envsubst '\${BACKEND_URL}'` form (see Dockerfile change below):** nginx.conf contains other shell-like variables — `$host`, `$remote_addr`, `$uri` — that must not be substituted. The scoped form restricts envsubst to only `${BACKEND_URL}`, preventing nginx's own variables from being clobbered.

### 2. `frontend/Dockerfile` — template copy + envsubst at container start

Two changes to the serve stage:

**a. Change COPY to copy the config as a template** (so the original is preserved and envsubst writes the resolved version at runtime):
```dockerfile
# Before:
COPY nginx.conf /etc/nginx/conf.d/default.conf

# After:
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
```

**b. Replace the implicit nginx CMD with an explicit envsubst + nginx CMD:**
```dockerfile
CMD ["/bin/sh", "-c", "envsubst '\\${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
```

The `\\$` in the JSON string becomes `\$` in the shell command, which prevents the shell from expanding `${BACKEND_URL}` itself — so envsubst receives the literal string `${BACKEND_URL}` as its variable list and substitutes only that variable. Without the backslash escape, the shell expands `${BACKEND_URL}` to its value (e.g. `backend.railway.internal:8000`) before passing it to envsubst, causing envsubst to receive an invalid variable list and fall back to substituting all variables, clobbering `$host`, `$remote_addr`, and `$uri`.

At container start, envsubst substitutes only `${BACKEND_URL}`, writes `default.conf`, then nginx starts. The template file remains untouched for inspection.

**Note on `VITE_API_BASE_URL`:** The Dockerfile already has a `VITE_API_BASE_URL` build arg (defaults to empty string). This is intentional — the React app uses relative `/api/` paths, and the nginx proxy handles routing. No compile-time backend URL is needed, so this arg stays empty on Railway.

### 3. `docker-compose.yml` — add `BACKEND_URL` to frontend service

Since the Dockerfile now runs envsubst at startup, docker-compose must supply `BACKEND_URL` for local dev too. Add one environment variable to the frontend service:

```yaml
frontend:
  build: ./frontend
  environment:
    BACKEND_URL: backend:8000   # docker-compose service name + port
  ports:
    - "80:80"
  depends_on:
    backend:
      condition: service_healthy
```

Local dev continues to work identically — only the mechanism changes (env var instead of hardcoded hostname).

### 4. `railway.toml` (new, repo root) — backend service config

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

### 5. `frontend/railway.toml` (new) — frontend service config

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 6. `README.md` — add Railway deployment section

New section after "Quick Start (Docker)" with step-by-step instructions and the env var table (see Deployment Steps below).

---

## Environment Variables

### Backend service
| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Injected automatically by Railway into linked services (backend only; frontend does not receive it) |
| `GROQ_API_KEY` | From Railway project variables (secret) |
| `AUTO_SEED` | `true` |
| `AUTO_SEED_MODELS` | `true` |
| `CORS_ORIGINS` | `https://<frontend-domain>.railway.app` |

### Frontend service
| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `backend.railway.internal:8000` |

---

## What Is Unchanged

- All Python / FastAPI source
- All React / TypeScript source
- GitHub Actions CI workflows
- Local docker-compose workflow (minus the one new `BACKEND_URL` env var added to the frontend service)

---

## Deployment Steps (Manual — Railway Dashboard)

1. Push branch to GitHub.
2. Open [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
3. Add **PostgreSQL** plugin → Railway provisions a database. By default Railway injects `DATABASE_URL` into all services in the project; the frontend does not use it but receiving it is harmless. The backend reads it automatically.
4. Add **Service** → select repo root → Railway detects `railway.toml` → set name to `backend`.
5. Set backend env vars: `GROQ_API_KEY`, `AUTO_SEED=true`, `AUTO_SEED_MODELS=true`.
6. Add another **Service** → select repo, set root directory to `frontend` → Railway detects `frontend/railway.toml` → set name to `frontend`.
7. Set frontend env var: `BACKEND_URL=backend.railway.internal:8000`.
8. Note the Railway-assigned frontend public domain; set backend `CORS_ORIGINS=https://<frontend-domain>.railway.app`.
9. Deploy all → watch logs for `Seeding data…` in backend, `nginx` started in frontend.
10. Open the frontend Railway domain → full stack is live.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| envsubst clobbers nginx `$host`/`$remote_addr` | Scoped form `envsubst '\${BACKEND_URL}'` + backslash escape prevents shell pre-expansion |
| nginx fails to start if backend DNS not yet resolvable | `resolver 127.0.0.11 valid=10s;` in location block defers DNS to per-request |
| `AUTO_SEED` takes 3–8 min — frontend shows "Seeding…" | Already handled by `DataFreshness` badge polling `/api/status` every 5s |
| CORS mismatch on first deploy | Set `CORS_ORIGINS` once frontend domain is known; redeploy backend (fast) |
| WeasyPrint system deps missing | Already installed in root Dockerfile from Phase 4 |
| Cold start / 512 MB RAM limit on free tier | FastAPI + sentence-transformers is ~400 MB; upgrade to 1 GB if OOM |

---

## Success Criteria

- `https://<project>.railway.app` loads the Dashboard with live data.
- `/api/ping` returns `{"status": "ok"}`.
- Health score badge appears in the nav.
- Ask page returns an answer (GROQ_API_KEY configured).
- Report page downloads a PDF.
