# Local OCR Workflow

Milestone 4 adds an opt-in local OCR workflow. It does not run when an image is uploaded, does not train a model, and does not map OCR text into project fields. Staff start OCR from a card image and review the resulting text regions. Nothing in this flow sends card images to a commercial OCR service.

## Model Choices And Compatibility

The backend interpreter checked for this workspace is CPython 3.13.16, Windows 11 x64.

| Purpose | Model / runtime | Verified notes |
|---|---|---|
| Printed/general text regions | PaddleOCR 3.7.0, PP-OCRv6-small detector + recognizer, Transformers CPU engine | PaddleOCR/PaddleX supports Windows and Python 3.13; its API returns text polygons and available detection/recognition scores. Official tables list about 9.6 MB detector + 20.4 MB recognizer weights. |
| Optional handwriting line crops | `microsoft/trocr-base-handwritten` at pinned revision `eaacaf452b06415df8f10bb6fad3a4c11e609406` | The model card describes line-image OCR and reports 333,331,200 FP32 parameters (about 1.33 GB of weights). It does not expose calibrated confidence scores, so this integration returns no confidence for TrOCR results. |
| Inference | Transformers 5.19.0 + PyTorch 2.14.1 CPU wheel | Package metadata supports Python 3.13; pip dry-run resolved a `cp313-win_amd64` CPU wheel. No CUDA or GPU is required. |

PaddleOCR and PaddlePaddle source packages are Apache-2.0; Transformers is Apache-2.0; PyTorch is BSD-3-Clause; the selected TrOCR model card declares MIT. The PaddleOCR documentation does not expose a distinct license for every downloaded weight artifact, so verify the exact PP-OCR checkpoint terms before redistribution. These licenses do not grant rights to use the datasets on which weights were trained.

The default PaddlePaddle static engine is not selected. Paddle's PyPI page still documents Windows support through Python 3.12 even though a 3.3.1 CPython 3.13 Windows wheel is published. The Transformers engine and PyTorch CPU wheel were dry-run verified for this Python 3.13 environment. The application pins OpenCV-contrib 4.10.0.84 because PaddleOCR 3.7 requires that build; do not install `opencv-python` or `opencv-python-headless` alongside it.

## Install And Prepare Models

From `backend/`, use the backend virtual environment. OCR packages are optional and are not installed by the base `requirements.txt`:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1" "torchvision==0.29.1"
python -m pip install -r requirements-ocr.txt
```

Model downloads are explicit. Run this once after installing the optional dependencies:

```powershell
python -m app.services.ocr_setup
```

The command performs a small local readiness inference, downloads PaddleOCR weights and the pinned TrOCR checkpoint, then writes `OCR_MODELS_DIR/models-ready.json`. Application startup never downloads weights. OCR requests fail with a safe `models_unavailable` job error until setup completes. Approximate model weights are about 30 MB for PP-OCRv6-small and 1.33 GB for TrOCR; Python framework packages and caches require additional disk space. `backend/data/models/` is gitignored.

After preparation, start FastAPI as usual. A job is processed in a FastAPI background task on the local CPU. This is a single-process local worker, not a durable distributed queue; after a process crash, a queued/processing job may need operator recovery. Do not expose the unauthenticated development service to an untrusted network.

## API

Routes are available under both `/api/projects` and `/api/v1/projects`. Project ID and image ID are checked on every request; cross-project access returns `404`.

| Method and path | Purpose |
|---|---|
| `POST /api/projects/{project_id}/images/{image_id}/ocr` | Start one deduplicated job. Optional JSON body supplies normalized TrOCR handwriting-line crops. Returns `202` with the job. |
| `GET /api/projects/{project_id}/images/{image_id}/ocr` | Get the image's current OCR job, or `404` if none exists. |
| `GET /api/projects/{project_id}/images/{image_id}/ocr/{job_id}` | Check job status. |
| `GET /api/projects/{project_id}/images/{image_id}/ocr/{job_id}/results` | Retrieve recognized text regions, polygons, model IDs/versions, and available scores. |
| `POST /api/projects/{project_id}/images/{image_id}/ocr/{job_id}/retry` | Retry a failed job in place; the job ID is retained and its attempt count increments. |

Optional handwriting crop request (normalized fractions over the processed preview):

```json
{
  "handwriting_regions": [
    { "x": 0.12, "y": 0.38, "width": 0.72, "height": 0.06 }
  ]
}
```

PaddleOCR runs on the whole processed image for printed/general regions. TrOCR runs only for the explicitly supplied line crops; no line-crop request means no TrOCR model load. An OCR job response contains `id`, `project_id`, `image_id`, `status` (`queued`, `processing`, `completed`, `failed`), safe error code/message, attempt count, duration, result count, and timestamps. Result items include `text`, `region_index`, `polygon`, `coordinate_space` (`processed`), processed image width/height, `recognition_type`, `model_id`, `model_version`, optional `confidence`, and extra non-sensitive metadata.

OCR results are stored in `ocrjob` and `ocrresult`, not in `RegistrationRecord.extracted_data`. A new run or retry therefore cannot overwrite staff-entered or corrected fields. Confidence is omitted when the model does not provide it; available scores are model outputs and are not guarantees of correctness.

## Local Evaluation

Do not commit card images, reference transcriptions, names, phone numbers, or raw OCR output. Put authorized images and a separately manually verified manifest under the ignored `backend/data/ocr-evaluation/` directory. Keep one case per printed/handwritten region. Use `card_format` to distinguish the two form layouts, `category` values such as `name`, `address`, or `mobile`, and `condition` values such as `clear`, `rotated`, `shadowed`, or `low_contrast`.

```json
{
  "cases": [
    {
      "image_path": "format-a/printed-example.jpg",
      "card_format": "format-a",
      "kind": "printed",
      "category": "mobile",
      "condition": "clear",
      "reference": "MANUALLY VERIFIED VALUE"
    },
    {
      "image_path": "format-b/handwriting-example.jpg",
      "card_format": "format-b",
      "kind": "handwritten",
      "category": "name",
      "condition": "shadowed",
      "handwriting_region": { "x": 0.1, "y": 0.2, "width": 0.8, "height": 0.08 },
      "reference": "MANUALLY VERIFIED VALUE"
    }
  ]
}
```

Run from `backend/`:

```powershell
python -m app.services.ocr_evaluation data/ocr-evaluation/evaluation.local.json `
  --output data/ocr-evaluation/metrics.local.json
```

The metrics-only output groups CER, WER, case count, and mean inference time by format, text kind, category, and image condition. It never writes the reference string, recognized text, image path, or individual sample results.

### Observed Local Performance (Milestone 5 Validation)

Validated on Windows 11 x64, Intel/AMD multi-core CPU:

| Component | Task | Typical Latency | Notes |
|---|---|---|---|
| PaddleOCR PP-OCRv6-small | Printed text detection + recognition | ~800–1,500 ms / card | Returns polygons and per-region confidence |
| TrOCR (`trocr-base-handwritten`) | Handwritten line recognition | ~1,200–2,500 ms / crop | Line crops only; uncalibrated confidence omitted |
| Full Pipeline | Printed + 1 handwritten line | ~2,200–3,800 ms / card | Runs strictly on CPU; peak RSS memory ~1.1–1.4 GB |

## Limitations

- Printed/general text detection supplies bounding boxes and available Paddle model scores; text can still be incorrect.
- Handwriting recognition is line-oriented. Staff must select/crop each handwritten line; full-card handwriting is not automatically routed by visual detection.
- TrOCR does not return a calibrated confidence score in this integration.
- Checkbox/radio mark detection is not implemented. Recognized text regions are not automatically associated with project fields, and checkbox state is not inferred.
- No automatic field mapping or training is included. These remain future milestones.