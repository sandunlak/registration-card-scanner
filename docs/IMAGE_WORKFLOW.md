# Card Image Workflow

Milestone 3 stores card images locally and prepares color previews and separate preprocessing variants. It does not run OCR, send images to external services, or guarantee that text can be recognized accurately.

## API

The API is available under both `/api/projects` and the compatibility alias `/api/v1/projects`. All endpoints below require the image's project ID; an image belonging to another project returns `404`.

| Method and path | Purpose |
|---|---|
| `POST /api/projects/{project_id}/images` | Upload one multipart `file`; returns image metadata with `201`. |
| `POST /api/projects/{project_id}/images/batch` | Upload repeated multipart `files`; returns an ordered per-file success or failure outcome. |
| `GET /api/projects/{project_id}/images` | List project image metadata. |
| `GET /api/projects/{project_id}/images/{image_id}` | Get status and metadata. |
| `GET /api/projects/{project_id}/images/{image_id}/preview?variant=original` | Serve an original, processed, or named variant preview. |
| `POST /api/projects/{project_id}/images/{image_id}/retry` | Reprocess the existing original without creating a registration record. |
| `POST /api/projects/{project_id}/images/{image_id}/adjust` | Set rotation and optional normalized crop, then reprocess from the original. |
| `POST /api/projects/{project_id}/images/{image_id}/replace` | Replace image bytes while retaining the existing registration record. |
| `DELETE /api/projects/{project_id}/images/{image_id}` | Delete the image files and its linked registration record; returns `204`. |

Accepted image formats are JPEG, PNG, and WebP. Limits are `MAX_UPLOAD_SIZE_MB` per file, `MAX_IMAGE_PIXELS` decoded pixels per image, and `MAX_IMAGES_PER_BATCH` files per batch. Uploads are read in bounded chunks. File extension and declared MIME type are checked against the decoded image format; neither is trusted by itself.

An image response has this shape (timestamps abbreviated):

```json
{
  "id": 17,
  "project_id": 4,
  "record_id": 29,
  "status": "ready",
  "metadata": {
    "width": 1200,
    "height": 760,
    "original_width": 3024,
    "original_height": 4032,
    "boundary_detected": true,
    "quality_warnings": []
  },
  "variants": ["grayscale", "denoised", "contrast", "adaptive_threshold"],
  "rotation": 0,
  "crop": null,
  "error_message": null,
  "created_at": "2026-10-13T10:00:00Z",
  "updated_at": "2026-10-13T10:00:00Z"
}
```

The batch response is `{ "items": [{ "image": <image response> }, { "failure": { "status": "failed", "error_message": "..." } }] }`. Status values are `uploaded`, `processing`, `ready`, and `failed`. Quality warning codes include `low_resolution`, `possible_blur`, `poor_lighting`, `low_contrast`, `card_may_be_cut_off`, and `boundary_not_detected`. They are advisory, not upload rejection criteria.

Adjustments accept a clockwise rotation and crop fractions relative to the original image:

```json
{
  "rotation": 90,
  "crop": { "x": 0.08, "y": 0.1, "width": 0.84, "height": 0.78 }
}
```

Omit or set `crop` to `null` to use the full original. The image preview endpoint is the only way to read stored image bytes; responses use private no-store caching and never include filesystem paths.

## Storage And Privacy

Files use server-generated UUID names under the configured storage root:

```text
<IMAGES_DIR>/projects/<project_id>/records/<record_id>/originals/<uuid>.<ext>
<IMAGES_DIR>/projects/<project_id>/records/<record_id>/processed/<uuid>.jpg
<IMAGES_DIR>/projects/<project_id>/records/<record_id>/variants/<uuid>.<ext>
```

`RegistrationRecord.source_image_path` contains only a relative original storage key. Image bytes are not stored in SQLite. The image directory is gitignored. On POSIX systems, storage directories are restricted to owner access and files to owner read/write; on Windows, use a local directory whose ACL is restricted to the staff account. Do not place it in a web server's public directory.

The original uploaded bytes are preserved. EXIF orientation is normalized only for derived output. Boundary detection applies perspective correction only when a plausible four-corner contour is found; otherwise the color preview preserves the uncropped framing and reports `boundary_not_detected`. Grayscale, denoising, contrast enhancement, and adaptive threshold are separate variants.

Authentication is not implemented. Project IDs provide cross-project scoping but are not user authentication. Keep the API bound to localhost and do not expose this development environment to an untrusted network.

## Retention And Backups

`IMAGE_RETENTION_DAYS` documents the intended retention period, but automatic expiration is not implemented until the housekeeping milestone. Staff can delete an image from the project Images tab; this also deletes the linked registration record and all generated image files. Deletion is permanent.

SQLite backups do not include the separate image directory. Securely back up both `DATABASE_URL` and `IMAGES_DIR`; keep them protected as personal data, and restore a matching pair. Apply retention and deletion policies to backup copies separately. Do not include real card images or personal data in tests or source control.