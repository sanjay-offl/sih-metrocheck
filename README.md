# MetroCheck — Legal Metrology Compliance Checker

**Scan. Detect. Enforce.**

An AI-powered compliance checking system for packaged commodities under the
**Legal Metrology (Packaged Commodities) Rules, 2011**.

> Built for **Smart India Hackathon 2025 — Problem Statement 26034**
> Ministry of Consumer Affairs, Food & Public Distribution
> Department of Consumer Affairs (DoCA)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Manual Setup (No Docker)](#manual-setup-no-docker)
- [How Compliance Checks Work](#how-compliance-checks-work)
- [Legal Rules Covered](#legal-rules-covered)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Deployment Notes](#deployment-notes)

---

## Overview

Enforcement officers upload a photograph of any packaged commodity label. The
system:

1. Extracts every piece of text from the label with **Gemini Flash 2.0** vision
   (with a **Tesseract OCR** fallback when no API key is configured).
2. Checks every mandatory declaration against the **Legal Metrology
   (Packaged Commodities) Rules, 2011** using a deterministic rule engine.
3. Flags violations with the exact **rule reference**, detected vs required
   values, and a recommended fix.
4. Scores the label **0–100%** and classifies it as *compliant*,
   *non-compliant*, or *partially compliant*.
5. Generates a government-grade **PDF inspection report** (with a JSON twin).

### Key features

- Role-based access: **Admin**, **Enforcement Officer**, **Viewer**
- JWT authentication (bcrypt-hashed passwords)
- Rule catalogue exposed via API for UI display
- Daily compliance trend charts and top-violation analytics
- Product master automatically built from inspected packages
- Redis-cached extractions (24h TTL) with one-click reprocessing

### Legal source

The rule catalogue is based on the Department of Consumer Affairs official
index for the **Legal Metrology Act, 2009** and the **Legal Metrology
(Packaged Commodities) Rules, 2011**:

<https://consumeraffairs.gov.in/pages/legal-metrology-act>

The page also lists amendments and implementation guidance. The application
uses the core declaration checks as an assistive screening tool; officers must
verify the latest applicable notification before taking enforcement action.

---

## Architecture

```
┌────────────┐   HTTPS/JSON    ┌──────────────────┐
│  Next.js 14│ ──────────────▶ │     FastAPI      │
│  (frontend)│                 │  (backend :8000) │
│    :3000   │   JWT bearer    │                  │
└────────────┘                 │  ┌────────────┐  │
                               │  │ Compliance │  │
                               │  │   Engine   │  │
                               │  └─────┬──────┘  │
                               │        │         │
            ┌──────────────────┼────────┼─────────┼──────────────┐
            ▼                  ▼        ▼         ▼              ▼
      ┌──────────┐      ┌──────────┐ ┌──────┐ ┌──────┐  ┌───────────────┐
      │  Gemini   │      │ Postgres │ │Redis │ │Reports│  │  Uploads/     │
      │ Flash 2.0 │      │   :5432  │ │:6379 │ │ PDFs  │  │  images       │
      │   + OCR   │      └──────────┘ └──────┘ └──────┘  └───────────────┘
      └──────────┘
```

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn-style UI,
  Zustand, Axios, Recharts
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0, Alembic, Pydantic v2
- **AI**: Google Gemini Flash 2.0 (`gemini-2.0-flash`) via `google-generativeai`
- **OCR fallback**: Tesseract via `pytesseract`
- **Database**: PostgreSQL 15 · **Cache**: Redis 7 · **Reports**: ReportLab

---

## Quick Start (Docker Compose)

Prerequisites: Docker + Docker Compose v2, a Gemini API key.

```bash
# 1. Configure environment
cp .env.example .env
#    →  set GEMINI_API_KEY and generate SECRET_KEY:
#       python -c "import secrets; print(secrets.token_urlsafe(48))"
#    →  (optional) override POSTGRES_* credentials

# 2. Start the stack (postgres + redis + backend + frontend)
docker compose up --build

# 3. Wait for postgres to become healthy, then seed users:
docker compose exec backend python seed.py

# 4. Open the app
open http://localhost:3000
```

**Seeded accounts** (from `backend/seed.py`):

| Role   | Email                       | Password     |
|--------|-----------------------------|--------------|
| Admin  | `admin@metrocheck.gov.in`   | `Admin@1234` |
| Officer| `officer1@metrocheck.gov.in`| `Officer@1234`|
| Officer| `officer2@metrocheck.gov.in`| `Officer@1234`|

> **Change these passwords immediately** in any non-demo deployment.

**Without a Gemini API key**, `scan/engine` reports `tesseract` and extraction
falls back to OCR + heuristic parsing — the full pipeline still runs.

---

## Manual Setup (No Docker)

### Backend

```bash
# 1. Environment
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure backend/.env
cp .env.example .env 2>/dev/null || true   # or create from template below
#    DATABASE_URL=postgresql://metrocheck:metrocheck123@localhost:5432/metrocheck_db
#    REDIS_URL=redis://localhost:6379
#    GEMINI_API_KEY=your_key
#    SECRET_KEY=change_me
#    CORS_ORIGINS=http://localhost:3000

# 3. Create the database
createdb metrocheck_db   # or via psql:  CREATE DATABASE metrocheck_db;

# 4. Migrations
alembic upgrade head     # or skip: app auto-creates tables on startup (dev only)

# 5. Seed users
python seed.py

# 6. Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev   # → http://localhost:3000
```

---

## How Compliance Checks Work

1. **Upload** (`POST /api/v1/scan/upload`) — validates the image (JPEG/PNG/WebP,
   ≤ 20 MB) and queues a background task.
2. **Extraction** — Gemini Flash 2.0 returns a strict JSON payload for ~30 label
   fields (manufacturer, net quantity, MRP, dates, consumer care, barcode,
   category, estimated font sizes, confidence, all visible text…).
3. **Adjudication** — the compliance engine runs every applicable check, records
   each one in a `check_matrix`, and computes a severity-weighted score:
   - critical = 3, major = 2, minor = 1
4. **Report** — ReportLab renders an A4 PDF with the government header, scan
   metadata, extracted declarations table, violation cards, and a signature box.
   A JSON twin is available via `?format=json`.

---

## Legal Rules Covered

| Rule | Declaration | Severity |
|------|-------------|----------|
| Rule 4(1)(a) | Manufacturer/Packer/Importer name & address | Critical |
| Rule 4(1)(b) | Net quantity in SI units | Critical |
| Rule 4(1)(c) | Month & year of manufacture / packing / import | Critical |
| Rule 4(1)(c) | Best before / use-by date (food) | Critical |
| Rule 4(1)(d) | Common or generic name | Major |
| Rule 4(1)(e) | Batch / lot number | Major |
| Rule 4(1)(f) | MRP declaration | Critical |
| Rule 4(1)(g) | Consumer care name, address & phone | Major |
| Rule 4(1)(i) | Country of origin (imports) | Critical |
| Rule 6 | SI units for net quantity | Major |
| Rule 10 | Minimum font size (see table) | Major |
| Rule 11 | MRP inclusive of all taxes | Critical |
| Rule 14 | No misleading / quantity-implying claims | Minor |
| Schedule II | Fibre content (textiles) | Major |
| Schedule III | Voltage / wattage rating (electronics) | Major |

### Font size requirements (Rule 10)

| Net quantity | Minimum height |
|--------------|----------------|
| ≤ 200 g / 200 ml | 1 mm |
| 200 – 500 g / 200 – 500 ml | 2 mm |
| 500 g – 1 kg / 500 ml – 1 L | 4 mm |
| > 1 kg / 1 L | 6 mm |

---

## API Reference

Base URL: `http://localhost:8000/api/v1` — all endpoints (except `auth/login`)
require `Authorization: Bearer <token>`.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login, returns JWT + user |
| GET | `/auth/me` | Current user |
| POST | `/auth/register` | Create user (**admin only**) |
| GET | `/auth/users` | List users (**admin only**) |
| PATCH | `/auth/users/{id}` | Update user (**admin only**) |
| DELETE | `/auth/users/{id}` | Delete user (**admin only**) |
| GET | `/auth/users/count` | User totals |

### Scan

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scan/upload` | Upload image (multipart: `file`, `location?`, `notes?`) |
| GET | `/scan/` | List scans (`skip`, `limit`, `status`, `q`) |
| GET | `/scan/{scan_id}` | Scan detail incl. extracted data + result |
| POST | `/scan/{scan_id}/reprocess` | Re-run extraction (bypasses cache) |
| DELETE | `/scan/{scan_id}` | Delete a scan |
| GET | `/scan/rules` | Rule catalogue for UI display |
| GET | `/scan/engine` | Active engine (`gemini` / `tesseract`) |

### Products

| Method | Path | Description |
|--------|------|-------------|
| GET | `/products/` | List products (`q`, `category`, pagination) |
| GET | `/products/categories` | Category counts |
| GET | `/products/{id}` | Product detail + scan history |
| PATCH | `/products/{id}` | Edit product (officer override) |
| DELETE | `/products/{id}` | Delete product (**admin only**) |

### Reports

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reports/generate/{scan_id}` | Generate PDF (`?format=pdf\|json`, `?force=`) |
| GET | `/reports/` | List reports |
| GET | `/reports/{report_id}` | Report metadata |
| GET | `/reports/download/{report_id}` | Download the file |
| DELETE | `/reports/{report_id}` | Delete a report |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/stats` | KPI summary + recent scans |
| GET | `/dashboard/trends` | Daily compliance series (`?days=14`) |
| GET | `/dashboard/violations` | Ranked rule breaches |

---

## Environment Variables

| Variable | Used by | Default | Description |
|----------|---------|---------|-------------|
| `GEMINI_API_KEY` | backend | — | Google AI Studio key (enables Gemini) |
| `GEMINI_MODEL` | backend | `gemini-2.0-flash` | Vision model override |
| `SECRET_KEY` | backend | — | JWT signing secret (generate random) |
| `DATABASE_URL` | backend | — | SQLAlchemy Postgres URL |
| `REDIS_URL` | backend | `redis://localhost:6379` | Redis connection |
| `CORS_ORIGINS` | backend | `http://localhost:3000` | Comma-separated allowed origins |
| `DEBUG` | backend | `false` | FastAPI debug / auto-create tables |
| `RUN_MIGRATIONS` | backend (compose) | `true` | Run Alembic on boot |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | Backend base URL (browser-facing) |
| `POSTGRES_USER/PASSWORD/DB` | compose | `metrocheck/…` | Postgres service credentials |

---

## Deployment Notes

- **Frontend (Vercel)**: build with `next build`; set `NEXT_PUBLIC_API_URL` to the
  public backend HTTPS URL. The Dockerfile uses `output: 'standalone'`.
- **Backend (Railway / Render / Fly.io)**: run `uvicorn app.main:app`; set all
  `*.env` values in the platform dashboard; attach managed Postgres + Redis;
  run `alembic upgrade head` and `python seed.py` once as release commands.
- **File storage**: uploads and generated reports are written to the local
  filesystem. For horizontal scaling, mount a shared volume or swap the file
  utilities for S3/MinIO.
- **Production checklist**: set a strong `SECRET_KEY`, rotate seed passwords,
  restrict `CORS_ORIGINS`, enable HTTPS, and consider rate-limiting on
  `/scan/upload`.

---

## License

Internal / hackathon prototype for SIH 2025 Problem **26034**. Not a substitute
for human adjudication — PDF reports note that they are subject to review by a
legal metrology officer before enforcement action.