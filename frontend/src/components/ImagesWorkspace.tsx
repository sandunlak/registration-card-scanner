"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  adjustProjectImage,
  deleteProjectImage,
  getImagePreviewUrl,
  getProjectImages,
  replaceProjectImage,
  retryImagePreprocessing,
  uploadProjectImage,
} from "@/lib/api/projects";
import type { ImageAsset, ImageAdjust } from "@/types";

interface ImagesWorkspaceProps {
  projectId: number;
}

interface UploadState {
  id: number;
  progress: number;
  status: "uploading" | "ready" | "failed";
  message?: string;
}

interface CropSelection {
  x: number;
  y: number;
  width: number;
  height: number;
}

const variantLabels: Record<string, string> = {
  grayscale: "Grayscale",
  denoised: "Denoised",
  contrast: "Contrast enhanced",
  adaptive_threshold: "Adaptive threshold",
};

const warningLabels: Record<string, string> = {
  low_resolution: "Low resolution may limit readability.",
  possible_blur: "The image may be out of focus.",
  poor_lighting: "Lighting is very dark or bright.",
  low_contrast: "The image has low contrast.",
  card_may_be_cut_off: "The card may touch or cross the image edge.",
  boundary_not_detected: "Card boundaries were not detected; the original framing is preserved.",
};

function imageError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default function ImagesWorkspace({ projectId }: ImagesWorkspaceProps) {
  const [images, setImages] = useState<ImageAsset[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [preview, setPreview] = useState("processed");
  const [rotation, setRotation] = useState<0 | 90 | 180 | 270>(0);
  const [crop, setCrop] = useState<CropSelection | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [operationNotice, setOperationNotice] = useState<string | null>(null);
  const [busyImageId, setBusyImageId] = useState<number | null>(null);
  const [replaceProgress, setReplaceProgress] = useState<number | null>(null);
  const replaceInput = useRef<HTMLInputElement>(null);
  const nextUploadId = useRef(0);
  const dragStart = useRef<{ x: number; y: number } | null>(null);

  const loadImages = useCallback(async () => {
    setPageError(null);
    try {
      const items = await getProjectImages(projectId);
      setImages(items);
      setSelectedId((current) => current && items.some((item) => item.id === current)
        ? current
        : items[0]?.id ?? null);
    } catch (error: unknown) {
      setPageError(imageError(error, "Could not load project images."));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void loadImages();
  }, [loadImages]);

  const selected = images.find((image) => image.id === selectedId) ?? null;

  useEffect(() => {
    setRotation(selected?.rotation ?? 0);
    setCrop(null);
  }, [selectedId, selected?.rotation]);

  const updateImage = (updated: ImageAsset) => {
    setImages((current) => current.map((image) => image.id === updated.id ? updated : image));
    setSelectedId(updated.id);
    setPreview("processed");
    setCrop(null);
  };

  const uploadFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setOperationError(null);
    setOperationNotice(null);
    for (const file of Array.from(files)) {
      const id = ++nextUploadId.current;
      setUploads((current) => [...current, { id, progress: 0, status: "uploading" }]);
      try {
        const image = await uploadProjectImage(projectId, file, (progress) => {
          setUploads((current) => current.map((item) => item.id === id ? { ...item, progress } : item));
        });
        setImages((current) => [image, ...current]);
        setSelectedId(image.id);
        setUploads((current) => current.map((item) => item.id === id
          ? { ...item, progress: 100, status: "ready" }
          : item));
      } catch (error: unknown) {
        setUploads((current) => current.map((item) => item.id === id
          ? { ...item, status: "failed", message: imageError(error, "Upload failed.") }
          : item));
      }
    }
    await loadImages();
  };

  const runImageAction = async (action: () => Promise<ImageAsset>, success: string) => {
    if (!selected) return;
    setBusyImageId(selected.id);
    setOperationError(null);
    setOperationNotice(null);
    try {
      const updated = await action();
      updateImage(updated);
      if (updated.status === "failed") {
        setOperationError(updated.error_message ?? "Image preprocessing failed.");
      } else {
        setOperationNotice(success);
      }
    } catch (error: unknown) {
      setOperationError(imageError(error, "Image operation failed."));
    } finally {
      setBusyImageId(null);
    }
  };

  const pointFromEvent = (event: React.PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)),
      y: Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height)),
    };
  };

  const onCropStart = (event: React.PointerEvent<HTMLDivElement>) => {
    if (preview !== "original" || !selected) return;
    const point = pointFromEvent(event);
    dragStart.current = point;
    setCrop({ ...point, width: 0, height: 0 });
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onCropMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragStart.current) return;
    const point = pointFromEvent(event);
    setCrop({
      x: Math.min(dragStart.current.x, point.x),
      y: Math.min(dragStart.current.y, point.y),
      width: Math.abs(point.x - dragStart.current.x),
      height: Math.abs(point.y - dragStart.current.y),
    });
  };

  const onCropEnd = () => {
    dragStart.current = null;
  };

  const applyAdjustment = () => {
    if (!selected) return;
    const adjustment: ImageAdjust = {
      rotation,
      crop: crop && crop.width > 0.02 && crop.height > 0.02 ? crop : null,
    };
    void runImageAction(
      () => adjustProjectImage(projectId, selected.id, adjustment),
      "Processed preview updated."
    );
  };

  const deleteSelected = async () => {
    if (!selected || !window.confirm("Delete this image and its linked registration record? This cannot be undone.")) return;
    setBusyImageId(selected.id);
    setOperationError(null);
    try {
      await deleteProjectImage(projectId, selected.id);
      const remaining = images.filter((image) => image.id !== selected.id);
      setImages(remaining);
      setSelectedId(remaining[0]?.id ?? null);
      setOperationNotice("Image and linked record deleted.");
    } catch (error: unknown) {
      setOperationError(imageError(error, "Could not delete the image."));
    } finally {
      setBusyImageId(null);
    }
  };

  const replaceSelected = async (file: File | undefined) => {
    if (!selected || !file) return;
    const id = selected.id;
    setBusyImageId(id);
    setOperationError(null);
    setOperationNotice(null);
    try {
      setReplaceProgress(0);
      updateImage(await replaceProjectImage(projectId, id, file, setReplaceProgress));
      setOperationNotice("Image replaced; linked registration record was retained.");
    } catch (error: unknown) {
      setOperationError(imageError(error, "Could not replace the image."));
    } finally {
      setBusyImageId(null);
      setReplaceProgress(null);
    }
  };

  return (
    <section className="space-y-5" aria-label="Project card images">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Card images</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400">
            Images stay on this machine. Quality warnings are advisory; preprocessing does not guarantee accurate text recognition.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-100 hover:bg-slate-700">
            Capture card
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={(event) => {
                void uploadFiles(event.currentTarget.files);
                event.currentTarget.value = "";
              }}
            />
          </label>
          <label className="cursor-pointer rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500">
            Add images
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={(event) => {
                void uploadFiles(event.currentTarget.files);
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>
      </div>

      {pageError && <div role="alert" className="border-l-2 border-red-400 bg-red-950/30 px-3 py-2 text-sm text-red-200">{pageError}</div>}
      {operationError && <div role="alert" className="border-l-2 border-red-400 bg-red-950/30 px-3 py-2 text-sm text-red-200">{operationError}</div>}
      {operationNotice && <div role="status" className="border-l-2 border-emerald-400 bg-emerald-950/25 px-3 py-2 text-sm text-emerald-200">{operationNotice}</div>}

      {uploads.length > 0 && (
        <div className="space-y-2" aria-label="Upload progress">
          {uploads.map((upload) => (
            <div key={upload.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-slate-800 py-2">
              <div>
                <p className="text-xs text-slate-200">
                  Image {upload.id} · {upload.status === "uploading" ? `Uploading ${upload.progress}%` : upload.status === "ready" ? "Uploaded" : "Failed"}
                </p>
                {upload.status === "uploading" && <progress className="mt-1 h-1.5 w-full accent-indigo-400" max={100} value={upload.progress} />}
                {upload.message && <p className="mt-1 text-xs text-red-300">{upload.message}</p>}
              </div>
              {upload.status === "failed" && <span className="text-xs text-red-300">Needs attention</span>}
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <p className="py-12 text-center text-sm text-slate-400">Loading images…</p>
      ) : images.length === 0 ? (
        <div className="border border-dashed border-slate-700 py-16 text-center">
          <h3 className="text-sm font-semibold text-slate-200">No card images yet</h3>
          <p className="mt-2 text-xs text-slate-400">Capture a card with a mobile camera or select several images.</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(220px,0.72fr)_minmax(0,1.8fr)]">
          <div className="space-y-1" aria-label="Uploaded card images">
            {images.map((image) => (
              <button
                key={image.id}
                type="button"
                onClick={() => {
                  setSelectedId(image.id);
                  setPreview("processed");
                  setCrop(null);
                  setOperationError(null);
                }}
                className={`grid w-full grid-cols-[64px_minmax(0,1fr)] items-center gap-3 border-b border-slate-800 p-2 text-left ${selectedId === image.id ? "bg-slate-800/80" : "hover:bg-slate-900"}`}
                aria-pressed={selectedId === image.id}
              >
                <Image
                  src={getImagePreviewUrl(projectId, image.id, "processed", image.updated_at)}
                  alt=""
                  width={64}
                  height={48}
                  unoptimized
                  className="h-12 w-16 bg-slate-800 object-contain"
                />
                <span className="min-w-0">
                  <span className="block text-xs font-medium text-slate-100">Card #{image.record_id}</span>
                  <span className={`mt-1 block text-[11px] ${image.status === "ready" ? "text-emerald-300" : image.status === "failed" ? "text-red-300" : "text-amber-300"}`}>
                    {image.status === "ready" ? "Ready" : image.status === "failed" ? "Failed" : image.status}
                  </span>
                </span>
              </button>
            ))}
          </div>

          {selected && (
            <div className="min-w-0 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-white">Card #{selected.record_id}</h3>
                  <p className="mt-1 text-xs text-slate-400">
                    {selected.metadata.width} × {selected.metadata.height} px · {selected.status}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => void runImageAction(() => retryImagePreprocessing(projectId, selected.id), "Preprocessing finished.")} disabled={busyImageId === selected.id} className="rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50">Retry processing</button>
                  <button type="button" onClick={() => replaceInput.current?.click()} disabled={busyImageId === selected.id} className="rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50">Retake / replace</button>
                  <input ref={replaceInput} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => { void replaceSelected(event.currentTarget.files?.[0]); event.currentTarget.value = ""; }} />
                  <button type="button" onClick={() => void deleteSelected()} disabled={busyImageId === selected.id} className="rounded-md border border-red-900/60 px-2.5 py-1.5 text-xs text-red-300 hover:bg-red-950/40 disabled:opacity-50">Delete</button>
                </div>
              </div>
              {replaceProgress !== null && busyImageId === selected.id && (
                <progress className="h-1.5 w-full accent-indigo-400" max={100} value={replaceProgress} aria-label="Replacement upload progress" />
              )}

              {selected.metadata.quality_warnings.length > 0 && (
                <ul className="space-y-1 border-l-2 border-amber-400 bg-amber-950/20 px-3 py-2" aria-label="Image quality warnings">
                  {selected.metadata.quality_warnings.map((warning) => (
                    <li key={warning} className="text-xs text-amber-100">{warningLabels[warning] ?? warning}</li>
                  ))}
                </ul>
              )}
              {selected.status === "failed" && selected.error_message && <p role="alert" className="text-xs text-red-300">{selected.error_message}</p>}

              <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
                <div role="group" aria-label="Preview version" className="inline-flex border border-slate-700">
                  {["original", "processed", ...selected.variants].map((variant) => (
                    <button key={variant} type="button" onClick={() => { setPreview(variant); setCrop(null); }} aria-pressed={preview === variant} className={`px-2.5 py-1.5 text-xs ${preview === variant ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}>
                      {variant === "original" ? "Original" : variant === "processed" ? "Processed" : variantLabels[variant] ?? variant}
                    </button>
                  ))}
                </div>
                <div className="ml-auto flex gap-1">
                  <button type="button" aria-label="Rotate counterclockwise" title="Rotate counterclockwise" onClick={() => setRotation((value) => ((value + 270) % 360) as 0 | 90 | 180 | 270)} className="h-8 w-8 border border-slate-700 text-sm text-slate-200 hover:bg-slate-800">↶</button>
                  <button type="button" aria-label="Rotate clockwise" title="Rotate clockwise" onClick={() => setRotation((value) => ((value + 90) % 360) as 0 | 90 | 180 | 270)} className="h-8 w-8 border border-slate-700 text-sm text-slate-200 hover:bg-slate-800">↷</button>
                </div>
              </div>

              <div className="flex min-h-64 justify-center overflow-auto bg-black/40 p-3">
                <div
                  className={`relative inline-block self-center ${preview === "original" ? "cursor-crosshair touch-none" : ""}`}
                  onPointerDown={onCropStart}
                  onPointerMove={onCropMove}
                  onPointerUp={onCropEnd}
                  onPointerCancel={onCropEnd}
                >
                  <Image
                    src={getImagePreviewUrl(projectId, selected.id, preview, selected.updated_at)}
                    alt={`${preview === "original" ? "Original" : "Processed"} card image ${selected.record_id}`}
                    width={selected.metadata.width}
                    height={selected.metadata.height}
                    unoptimized
                    className="block max-h-[min(65vh,560px)] max-w-full select-none object-contain"
                  />
                  {preview === "original" && crop && crop.width > 0.01 && crop.height > 0.01 && (
                    <div
                      className="pointer-events-none absolute border-2 border-emerald-300 bg-emerald-300/15"
                      style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.width * 100}%`, height: `${crop.height * 100}%` }}
                    />
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-slate-400">On the original preview, drag across the card to set a crop. Rotation and crop always start from the preserved original.</p>
                <button type="button" onClick={applyAdjustment} disabled={busyImageId === selected.id || (rotation === 0 && (!crop || crop.width < 0.02 || crop.height < 0.02))} className="rounded-md bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40">
                  {busyImageId === selected.id ? "Processing…" : "Apply adjustments"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}