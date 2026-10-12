# Implementation Milestones

Each milestone is a small, independently reviewable and testable increment. Stop after each milestone and await review before proceeding.

---

## Milestone 1 — Project Scaffold ✅ *(current)*

**Goal:** Establish a working monorepo skeleton that both the frontend and backend can be started from.

| Task | Done? |
|------|-------|
| Monorepo directory structure | ✅ |
| `.gitignore` covering Python, Node, images, DB, env files | ✅ |
| `README.md` with architecture, setup, conventions, security | ✅ |
| FastAPI app with `/health` endpoint | ✅ |
| Next.js App Router scaffold (TypeScript, Tailwind) | ✅ |
| Landing page with live backend health badge | ✅ |
| Backend `requirements.txt`, `pyproject.toml` | ✅ |
| Frontend `.env.local.example` | ✅ |
| Backend `.env.example` | ✅ |
| Pytest test for `/health` | ✅ |
| `docs/MILESTONES.md` (this file) | ✅ |

**How to verify:**
```
# Backend
cd backend && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] pydantic-settings sqlmodel aiosqlite httpx pytest pytest-asyncio
uvicorn app.main:app --reload   → http://127.0.0.1:8000/health returns {"status":"ok"}
pytest                          → 2 tests pass

# Frontend
cd frontend && npm install && npm run dev  → http://localhost:3000
```

---

## Milestone 2 — Database Models & Project Management

**Goal:** Define the full data model and expose CRUD APIs for Projects, Card Templates, and Cards.

### Tasks

1. **SQLModel table definitions**
   - `Project` — name, description, created_at, event_date
   - `CardTemplate` — project_id, field definitions (JSON), layout hints
   - `Card` — project_id, template_id, image_path, status (`pending | reviewed | exported`), created_at
   - `CardField` — card_id, key, raw_value (`TEXT`), corrected_value (`TEXT | NULL`), confidence, needs_review

   > **Rule:** `phone`, `passport_no`, `nic`, and all reference codes must be `String` columns.

2. **Alembic migration setup** (or auto-create via SQLModel on startup for dev)

3. **Routers**
   - `GET/POST /api/v1/projects`
   - `GET/PUT/DELETE /api/v1/projects/{id}`
   - `GET/POST /api/v1/projects/{id}/templates`
   - `GET /api/v1/projects/{id}/cards`

4. **Pydantic schemas** matching every router

5. **Tests**
   - CRUD round-trip for Project and CardTemplate
   - Verify phone stored as string, not coerced to int

6. **Frontend stub pages**
   - `/projects` — list all projects
   - `/projects/new` — create project form
   - `/projects/[id]` — project dashboard (card list)

**Exit criteria:** `pytest` green; `npm run build` succeeds; project CRUD verified in browser.

---

## Milestone 3 — Image Upload & Storage

**Goal:** Staff can upload card images; the backend validates, stores, and thumbnails them.

### Tasks

1. `POST /api/v1/projects/{id}/cards/upload` — multipart upload
   - Validate MIME type against `ALLOWED_MIME_TYPES`
   - Validate size against `MAX_UPLOAD_SIZE_MB`
   - Save original to `data/images/originals/<project_id>/<uuid>.<ext>`
   - Generate 400 px thumbnail with Pillow → `data/images/thumbnails/…`
   - Create `Card` DB record with `status="pending"`

2. `GET /api/v1/cards/{id}/image` — serve original (access-controlled)
3. `GET /api/v1/cards/{id}/thumbnail` — serve thumbnail

4. **Frontend**
   - Drag-and-drop upload zone on the project dashboard
   - Progress indicator per file
   - Thumbnail grid of uploaded cards

5. **Tests**
   - Upload a valid JPEG — assert 201, file on disk, thumbnail created
   - Upload oversized file — assert 413
   - Upload wrong MIME — assert 415

**Exit criteria:** Upload 5 test images via UI; thumbnails appear in grid; originals on disk.

---

## Milestone 4 — OCR Integration (PaddleOCR)

**Goal:** After upload, OCR runs automatically and extracted field values are stored.

### Tasks

1. Install PaddleOCR in the virtual environment (CPU-only paddlepaddle)
2. `services/ocr_service.py`
   - `extract_fields(image_path, template) → list[ExtractedField]`
   - Never invent values: if confidence < threshold, set `value=None` and `needs_review=True`
   - Log `WARNING` for every low-confidence field

3. Background task triggered after upload (FastAPI `BackgroundTasks`)
4. `Card.status` transitions: `pending → processing → ocr_complete`
5. Polling endpoint `GET /api/v1/cards/{id}/status`

6. **Frontend**
   - Status indicator on thumbnail (spinner, ✓, ⚠ needs-review)
   - Card detail page shows extracted fields

7. **Tests**
   - Mock `extract_fields` — assert DB fields populated correctly
   - Assert low-confidence field has `needs_review=True`

**Exit criteria:** Upload a card image; status transitions to `ocr_complete`; fields appear in UI.

---

## Milestone 5 — Handwriting Recognition Model

**Goal:** Supplement PaddleOCR with a pretrained handwriting model for cursive / handwritten fields.

### Tasks

1. Evaluate and select a pretrained model (e.g., TrOCR `microsoft/trocr-base-handwritten` via HuggingFace Transformers, or equivalent — CPU-runnable, no paid API)
2. `services/handwriting_service.py` — wrap model inference
3. Routing logic in `ocr_service.py`: use handwriting model for fields the template marks as `handwritten=True`
4. Combined confidence score computation
5. Tests with sample handwritten card images (stored in `tests/fixtures/`)

**Exit criteria:** Handwritten name/address fields extracted with reasonable accuracy on test images.

---

## Milestone 6 — Human Review Interface

**Goal:** Staff can review, correct, and approve every card before export.

### Tasks

1. **Review queue page** `/projects/[id]/review`
   - List cards with status filter (pending, needs-review, approved)
   - Keyboard shortcuts: ← → to navigate cards

2. **Card review panel**
   - Original image (zoomable)
   - Extracted fields alongside image
   - Low-confidence fields highlighted in amber
   - Inline text inputs for corrections
   - `PUT /api/v1/cards/{id}/fields/{key}` — save correction
   - "Approve card" button → `Card.status = "reviewed"`

3. **Tests**
   - Submit a correction — assert `corrected_value` stored, `needs_review=False`
   - Approve a card — assert status updated

**Exit criteria:** Staff can correct OCR errors and approve cards; queue shows remaining count.

---

## Milestone 7 — Excel Export

**Goal:** Export all reviewed cards for a project to a `.xlsx` file.

### Tasks

1. `services/export_service.py`
   - `export_project(project_id) → bytes`
   - One row per card, one column per field key defined in the template
   - Use `corrected_value` if set, else `raw_value`
   - Highlight rows where any field still `needs_review=True`

2. `GET /api/v1/projects/{id}/export` — streams the `.xlsx` file

3. **Frontend** — "Export to Excel" button on project dashboard

4. **Tests**
   - Export a project with 3 mock cards — assert `.xlsx` has correct rows/columns
   - Assert phone number exported as string, not a number

**Exit criteria:** Download `.xlsx`; open in Excel; verify data fidelity.

---

## Milestone 8 — Card Template Designer

**Goal:** Staff can define new card layouts (field names, positions, types) without code changes.

### Tasks

1. Template editor UI — drag-drop field regions over a sample card image
2. Field metadata: label, field type (`text | date | phone | passport | checkbox`), `handwritten` flag, required flag
3. `PUT /api/v1/projects/{id}/templates/{tid}` — save template JSON
4. OCR service reads field regions from the template to crop and process

**Exit criteria:** Create a template for a new card layout; run OCR; fields extracted correctly.

---

## Milestone 9 — Image Retention Housekeeping

**Goal:** Enforce the `IMAGE_RETENTION_DAYS` policy automatically.

### Tasks

1. Background script / scheduled task that deletes originals older than the threshold after export confirmation
2. `Card.original_deleted_at` timestamp column
3. CLI command: `python -m app.cli housekeep --dry-run`
4. Tests asserting correct files deleted / preserved

---

## Milestone 10 — Polish, Packaging, and Deployment Guide

**Goal:** The application is easy for non-technical staff to install and run.

### Tasks

1. One-command start script (`start.ps1` / `start.sh`)
2. Electron wrapper evaluation (optional — let staff double-click to launch)
3. Final security audit: CORS, input validation, no sensitive data in logs
4. User guide PDF / Markdown
5. Performance test: process 500 cards and verify throughput

---

> **Process rule:** Each milestone ends with `pytest` passing, `npm run build` succeeding (or `npm run dev` verified), and a brief written review from the project owner before the next milestone begins.
