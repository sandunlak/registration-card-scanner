# Registration Card Scanner

An open-source, locally-runnable AI application that digitises handwritten and printed registration cards for a migration consultancy in Sri Lanka. Staff photograph or scan approximately 500 cards per event; the application extracts field values automatically, lets staff correct uncertain entries, and exports verified records to Excel — replacing manual data entry entirely.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Repository Layout](#repository-layout)
4. [Quick-Start Setup](#quick-start-setup)
5. [Development Commands](#development-commands)
6. [Environment Variables](#environment-variables)
7. [Coding Conventions](#coding-conventions)
8. [Security & Privacy](#security--privacy)
9. [Milestone Plan](#milestone-plan)

---

## Architecture Overview

```
Browser (Next.js)
      │   REST / multipart
      ▼
FastAPI  (Python)
  ├── Routers: health, projects, cards, templates, export
  ├── Services: ocr_service, image_service, export_service
  ├── Models / DB: SQLite via SQLModel
  └── Storage: local filesystem  (originals + thumbnails)
```

- **Frontend** — Next.js 15 App Router, TypeScript, Tailwind CSS.  Displays the review queue, confidence heat-map overlay, and project/template management.
- **Backend** — Python 3.11+, FastAPI. Image validation and preprocessing run locally; OCR is not part of the current image workflow.
- **Database** — SQLite (single file, zero-admin).  Phone numbers and all identifiers stored as `TEXT`.
- **Image storage** — Original, processed, and optional preprocessing variants are stored under the configured private `IMAGES_DIR`, scoped by project and registration record.
- **Export** — `openpyxl` generates `.xlsx` files on demand.

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.11 | 3.13 confirmed working |
| Node.js | 18 LTS | 24 confirmed working |
| npm | 9+ | bundled with Node |
| Git | 2.x | — |
| Windows / macOS / Linux | — | Windows 11 primary dev target |

> **No paid services or cloud API keys are required.**

---

## Repository Layout

```
registration-card-scanner/
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── app/               # App Router pages & layouts
│   │   ├── components/        # Reusable UI components
│   │   ├── lib/               # API client, utility helpers
│   │   └── types/             # Shared TypeScript types
│   ├── public/
│   ├── .env.local.example
│   └── package.json
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── routers/           # One file per resource
│   │   ├── services/          # Business logic (OCR, image, export)
│   │   ├── models/            # SQLModel ORM models
│   │   ├── schemas/           # Pydantic request / response schemas
│   │   └── core/              # Settings, DB session, logging
│   ├── data/
│   │   ├── images/            # Original card images (gitignored)
│   │   └── db/                # SQLite database file (gitignored)
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── docs/                      # Architecture diagrams, field-mapping specs
├── .gitignore
└── README.md
```

---

## Quick-Start Setup

### 1 — Clone

```bash
git clone <repo-url>
cd registration-card-scanner
```

### 2 — Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your preferred settings (all defaults work out of the box)

# Start the API server (auto-reloads on file changes)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is then available at **http://127.0.0.1:8000**
Interactive docs: **http://127.0.0.1:8000/docs**

### 3 — Frontend

```bash
cd frontend

# Install Node dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Start Next.js dev server
npm run dev
```

The UI is then available at **http://localhost:3000**

---

## Development Commands

### Backend

| Command | Purpose |
|---------|---------|
| `uvicorn app.main:app --reload` | Start API with hot-reload |
| `pytest` | Run all tests (9 passing) |
| `pytest -v tests/test_projects.py` | Run project & field CRUD tests |
| `alembic upgrade head` | Run database schema migrations |
| `python -m app.core.backup --action backup` | Safe online snapshot of SQLite database |
| `python -m app.core.backup --action restore --file <path>` | Restore database snapshot |
| `ruff check .` | Lint Python code |
| `ruff format .` | Format Python code |
| `mypy app/` | Type-check |

See [`docs/DATABASE_BACKUP.md`](docs/DATABASE_BACKUP.md) for full backup and disaster recovery procedures.
See [`docs/IMAGE_WORKFLOW.md`](docs/IMAGE_WORKFLOW.md) for upload endpoints, image storage, retention, and privacy details.

### Frontend

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Next.js dev server |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npm test` | Node test runner (`node --test`) |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/db/app.db` | SQLite connection string |
| `IMAGES_DIR` | `./data/images` | Private root for original, processed, and variant images |
| `MAX_UPLOAD_SIZE_MB` | `20` | Per-image upload limit |
| `MAX_IMAGE_PIXELS` | `40000000` | Maximum decoded pixels per image |
| `MAX_IMAGES_PER_BATCH` | `10` | Maximum files in one batch request |
| `IMAGE_RETENTION_DAYS` | `90` | Days before originals are eligible for deletion |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SERVER_URL` | `http://127.0.0.1:8000` | Private FastAPI origin used by the Next.js same-origin proxy |
| `NEXT_PUBLIC_API_URL` | unset | Legacy fallback for the FastAPI origin; prefer `API_SERVER_URL` |
| `NEXT_ALLOWED_DEV_ORIGINS` | `10.69.1.115` | Comma-separated LAN hostnames allowed to load Next.js development assets |

> **Rule:** Never commit `.env` or `.env.local` files. Only commit `.env.example` / `.env.local.example`.

---

## Coding Conventions

### Python (backend)

- Python >= 3.11; use `from __future__ import annotations` everywhere.
- Type-annotate all function signatures; `mypy` must pass with no errors.
- Use `ruff` for linting and formatting (configured in `pyproject.toml`).
- One router file per REST resource (`routers/cards.py`, `routers/projects.py`, ...).
- One service file per capability (`services/ocr_service.py`, `services/export_service.py`, ...).
- Never raise bare `Exception`; use custom exception classes in `app/core/exceptions.py`.
- Store phone numbers, IDs, and reference codes as `String` columns, never `Integer`.
- Return explicit `None` / empty list rather than inventing placeholder values for uncertain OCR fields.
- Log at `WARNING` or above whenever OCR confidence drops below a configurable threshold.

### TypeScript (frontend)

- Strict mode enabled (`"strict": true` in `tsconfig.json`).
- No `any` types; prefer `unknown` and narrow explicitly.
- API calls live in `src/lib/api/` — one file per backend resource.
- Components receive data as props; no direct `fetch` calls inside leaf components.
- Uncertain / low-confidence fields must be visually flagged (yellow border + icon) — never silently shown as confirmed.

### General

- All user-visible strings must be in English (add i18n hooks for Sinhala/Tamil later).
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `chore:`, ...).
- Every PR must include or update a test covering the changed behaviour.

---

## Security & Privacy

- Registration card images contain personal data (names, passport numbers, phone numbers). Treat them as sensitive.
- Images are stored only on the local machine and are **never** transmitted to a third-party service.
- The `data/images/` directory is `.gitignore`d; **never** commit card images.
- Image retention is controlled by `IMAGE_RETENTION_DAYS`. A future housekeeping job will enforce deletion.
- CORS is restricted to `localhost` origins during development. Configure `ALLOWED_ORIGINS` explicitly for any deployment.
- File uploads are validated by extension, declared MIME type when present, decoded format, byte size, and decoded pixel dimensions before being saved.
- Authentication is not implemented. The local development environment is not ready to expose to an untrusted network, even though image routes enforce project scoping.
- SQLite database files are `.gitignore`d.

Image files and retention limitations are described in [`docs/IMAGE_WORKFLOW.md`](docs/IMAGE_WORKFLOW.md).

---

## Milestone Plan

See [docs/MILESTONES.md](docs/MILESTONES.md) for the complete, task-by-task plan.