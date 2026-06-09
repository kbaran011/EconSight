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
| `postgres` | Railway managed plugin | No Dockerfile needed — Railway provisions and injects `DATABASE_URL` automatically |
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

Only the proxy target changes. All other nginx config (SPA fallback, gzip, headers) is untouched.

### 2. `frontend/Dockerfile` — envsubst at container start

The final stage CMD is updated to substitute `${BACKEND_URL}` into the nginx config at runtime before starting nginx:

```dockerfile
CMD ["/bin/sh", "-c", \
  "envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template \
   > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
```

The nginx config is copied as `.template` and the resolved version is written to `.conf` at startup. This is the canonical Docker pattern for runtime nginx config.

### 3. `railway.toml` (new, repo root) — backend service config

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

### 4. `frontend/railway.toml` (new) — frontend service config

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 5. `README.md` — add Railway deployment section

New section after "Quick Start (Docker)" explaining:
- One-click deploy badge (optional)
- Step-by-step: create project → add Postgres plugin → add backend service → add frontend service → set env vars → deploy

---

## Environment Variables

### Backend service
| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Injected automatically by Railway Postgres plugin |
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

- `docker-compose.yml` — local dev workflow identical
- All Python / FastAPI source
- All React / TypeScript source
- GitHub Actions CI workflows

The docker-compose stack continues to use `proxy_pass http://backend:8000` (the compose service name). Railway uses the env var. Both work correctly in their respective environments because the template file is only resolved in the Railway container.

---

## Deployment Steps (Manual — Railway Dashboard)

1. Push branch to GitHub.
2. Open [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
3. Add **PostgreSQL** plugin → Railway injects `DATABASE_URL` into all services.
4. Add **Service** → select repo root → Railway detects `railway.toml` → names it `backend`.
5. Set backend env vars: `GROQ_API_KEY`, `AUTO_SEED=true`, `AUTO_SEED_MODELS=true`.
6. Add another **Service** → select repo, set root directory to `frontend` → Railway detects `frontend/railway.toml` → names it `frontend`.
7. Set frontend env var: `BACKEND_URL=backend.railway.internal:8000`.
8. Set backend `CORS_ORIGINS` to the Railway-assigned frontend domain once known.
9. Deploy all → watch logs for `Seeding data…` in backend, `nginx` started in frontend.
10. Open the frontend Railway domain → full stack is live.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Railway private DNS not resolving at nginx startup | envsubst runs at container start; backend is up before first request arrives |
| `AUTO_SEED` takes 3–8 min — frontend shows "Seeding…" | Already handled by `DataFreshness` badge polling `/api/status` every 5s |
| CORS mismatch on first deploy | Set `CORS_ORIGINS` in backend env vars once frontend domain is known; redeploy backend |
| WeasyPrint system deps missing | Already installed in root Dockerfile from Phase 4 |
| Cold start / 512 MB RAM limit on free tier | FastAPI + sentence-transformers is ~400 MB; upgrade to 1 GB if OOM |

---

## Success Criteria

- `https://<project>.railway.app` loads the Dashboard with live data.
- `/api/ping` returns `{"status": "ok"}`.
- Health score badge appears in the nav.
- Ask page returns an answer (GROQ_API_KEY configured).
- Report page downloads a PDF.
