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

## Milestone 2 — Database Models & Project Management ✅

**Goal:** Implement a fully functional project-management and configurable-field system for a local-first registration card digitization application.

| Task | Done? |
|------|-------|
| SQLModel database models (`Project`, `ProjectField`, `RegistrationRecord`) | ✅ |
| Phone numbers and IDs enforced as strings to preserve leading zeros | ✅ |
| Alembic migration support (`alembic>=1.13.0`, migration revision generated & applied) | ✅ |
| Native SQLite online backup & restore procedure (`docs/DATABASE_BACKUP.md`) | ✅ |
| Project REST endpoints (`GET/POST /api/projects`, `GET/PATCH /api/projects/{id}`, archive & restore) | ✅ |
| Field REST endpoints (`GET/POST /api/projects/{id}/fields`, `PATCH/DELETE /api/projects/{id}/fields/{fid}`, reorder) | ✅ |
| Registration record REST endpoints with pagination (`GET/POST/PATCH /api/projects/{id}/records`) | ✅ |
| Cross-project access protection (prevents ID tampering across projects) | ✅ |
| Strict validation service for required and typed fields | ✅ |
| Frontend professional dashboard (`page.tsx`) with metrics and project list | ✅ |
| Create Project modal with presets (Enquiry Form, Admission Form, Blank) | ✅ |
| Project detail page (`/projects/[id]`) with Records table, Field Layout editor, and Settings | ✅ |
| Dynamic field management (add, edit, delete, move up/down) | ✅ |
| Manual card record data entry modal dynamically driven by configured fields | ✅ |
| Backend test suite with pytest (9 tests passing) | ✅ |
| Frontend test suite with node:test & full TypeScript / ESLint compliance | ✅ |

**Exit criteria:** `pytest` green; `npm run build` succeeds; project & field CRUD verified.

---

## Milestone 3 — Mobile Image Capture and Preprocessing ✅

**Goal:** Staff can capture or upload private card images, review preprocessing and quality warnings, and make manual corrections without OCR.

| Task | Done? |
|------|-------|
| JPEG, PNG, and WebP verification by extension, MIME, and decoded contents | ✅ |
| Bounded upload reads, per-file size limits, batch count, and decoded pixel limits | ✅ |
| EXIF normalization, best-effort boundary detection, and perspective correction | ✅ |
| Separate color output and reusable grayscale, denoise, contrast, and threshold variants | ✅ |
| Quality warnings for resolution, blur, lighting, contrast, crop edges, and detection | ✅ |
| Project/record-scoped UUID storage and additive image metadata migration | ✅ |
| Upload one or many, metadata, private previews, retry, adjust, replace, and delete APIs | ✅ |
| Mobile camera capture, multi-select, per-image progress, preview, crop, rotate, and lifecycle UI | ✅ |
| Tests for validation, preprocessing, project isolation, cleanup, retry, deletion, and legacy DB data | ✅ |
| Endpoint, backup, retention, and security documentation | ✅ |

**Exit criteria:** Verified by backend and frontend test suites and production build. Images remain local; OCR is not integrated in this milestone.

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
