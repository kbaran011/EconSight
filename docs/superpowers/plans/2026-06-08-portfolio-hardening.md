# Portfolio Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make EconSight interview-ready — one-command Docker demo, honest docs, CI smoke tests, UI polish.

**Architecture:** Background auto-seed on empty DB, relative API URLs in Docker, bundled notebooks/models, `/api/status` for freshness, GHA docker + cron jobs.

**Tech Stack:** Python 3.12, FastAPI, Docker Compose, Vite env injection, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-06-08-portfolio-hardening-design.md`

---

## Wave 0 — Demo Foundations

### Task 1: Seed module + status endpoint

**Files:**
- Create: `src/econsight/db/seed.py`
- Create: `src/econsight/api/routers/status.py`
- Modify: `src/econsight/config.py`
- Modify: `src/econsight/api/main.py`
- Modify: `src/econsight/api/schemas.py`

- [ ] Add `auto_seed`, `auto_seed_models` to Settings
- [ ] Implement `maybe_seed_data()` with background task + state tracking
- [ ] Add `GET /api/status` endpoint
- [ ] Wire into lifespan

### Task 2: Docker assets + deps

**Files:**
- Modify: `Dockerfile`
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`

- [ ] COPY notebooks/, models/ into image
- [ ] Add jupyter + nbconvert to runtime deps
- [ ] Set AUTO_SEED=true in compose

### Task 3: Frontend API URL

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/.env.development`
- Modify: `frontend/Dockerfile`

- [ ] Use `import.meta.env.VITE_API_BASE_URL`
- [ ] Build arg for Docker

### Task 4: Env cleanup

**Files:**
- Modify: `.env.example`
- Modify: `.env.docker.example`

---

## Wave 1 — Credibility

### Task 5: Docker CI

**Files:**
- Modify: `.github/workflows/ci.yml`

### Task 6: GHA scheduled pipeline

**Files:**
- Create: `.github/workflows/pipeline-cron.yml`

### Task 7: About page + README

**Files:**
- Modify: `frontend/src/pages/About.tsx`
- Modify: `README.md`

---

## Wave 2 — Demo Polish

### Task 8: All 9 indicators

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Indicators.tsx`

### Task 9: Freshness UX

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

### Task 10: Mobile nav

**Files:**
- Modify: `frontend/src/App.tsx`
