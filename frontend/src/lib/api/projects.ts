/**
 * API client helpers for Projects, Fields, and Registration Records.
 */

import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectField,
  ProjectFieldCreate,
  ProjectFieldUpdate,
  RegistrationRecord,
  RegistrationRecordCreate,
  RegistrationRecordUpdate,
  RecordListResponse,
  ImageAsset,
  ImageAdjust,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        errorDetail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export async function getProjects(status?: string): Promise<Project[]> {
  const url = new URL(`${BASE}/api/projects`);
  if (status) {
    url.searchParams.set("status", status);
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  return handleResponse<Project[]>(res);
}

export async function getProject(id: number): Promise<Project> {
  const res = await fetch(`${BASE}/api/projects/${id}`, { cache: "no-store" });
  return handleResponse<Project>(res);
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  const res = await fetch(`${BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Project>(res);
}

export async function updateProject(id: number, data: ProjectUpdate): Promise<Project> {
  const res = await fetch(`${BASE}/api/projects/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Project>(res);
}

export async function archiveProject(id: number): Promise<Project> {
  const res = await fetch(`${BASE}/api/projects/${id}/archive`, {
    method: "POST",
  });
  return handleResponse<Project>(res);
}

export async function restoreProject(id: number): Promise<Project> {
  const res = await fetch(`${BASE}/api/projects/${id}/restore`, {
    method: "POST",
  });
  return handleResponse<Project>(res);
}

// ---------------------------------------------------------------------------
// Fields
// ---------------------------------------------------------------------------

export async function getProjectFields(projectId: number): Promise<ProjectField[]> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/fields`, {
    cache: "no-store",
  });
  return handleResponse<ProjectField[]>(res);
}

export async function createProjectField(
  projectId: number,
  data: ProjectFieldCreate
): Promise<ProjectField> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/fields`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProjectField>(res);
}

export async function updateProjectField(
  projectId: number,
  fieldId: number,
  data: ProjectFieldUpdate
): Promise<ProjectField> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/fields/${fieldId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ProjectField>(res);
}

export async function deleteProjectField(
  projectId: number,
  fieldId: number
): Promise<void> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/fields/${fieldId}`, {
    method: "DELETE",
  });
  await handleResponse<{ status: string; id: number }>(res);
}

export async function reorderProjectFields(
  projectId: number,
  fieldIds: number[]
): Promise<ProjectField[]> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/fields/reorder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ field_ids: fieldIds }),
  });
  return handleResponse<ProjectField[]>(res);
}

// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

export async function getProjectRecords(
  projectId: number,
  page: number = 1,
  limit: number = 20,
  reviewStatus?: string
): Promise<RecordListResponse> {
  const url = new URL(`${BASE}/api/projects/${projectId}/records`);
  url.searchParams.set("page", String(page));
  url.searchParams.set("limit", String(limit));
  if (reviewStatus) {
    url.searchParams.set("review_status", reviewStatus);
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  return handleResponse<RecordListResponse>(res);
}

export async function createProjectRecord(
  projectId: number,
  data: RegistrationRecordCreate
): Promise<RegistrationRecord> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<RegistrationRecord>(res);
}

export async function updateProjectRecord(
  projectId: number,
  recordId: number,
  data: RegistrationRecordUpdate
): Promise<RegistrationRecord> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/records/${recordId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<RegistrationRecord>(res);
}

// ---------------------------------------------------------------------------
// Images
// ---------------------------------------------------------------------------

export async function getProjectImages(projectId: number): Promise<ImageAsset[]> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/images`, { cache: "no-store" });
  const body = await handleResponse<{ items: ImageAsset[] }>(res);
  return body.items;
}

export function getImagePreviewUrl(
  projectId: number,
  imageId: number,
  variant: string,
  updatedAt?: string
): string {
  const url = new URL(`${BASE}/api/projects/${projectId}/images/${imageId}/preview`);
  url.searchParams.set("variant", variant);
  if (updatedAt) url.searchParams.set("v", updatedAt);
  return url.toString();
}

export function uploadProjectImage(
  projectId: number,
  file: File,
  onProgress: (percent: number) => void
): Promise<ImageAsset> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${BASE}/api/projects/${projectId}/images`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Network error while uploading the image."));
    request.onload = () => {
      let body: { detail?: unknown } & Partial<ImageAsset>;
      try {
        body = JSON.parse(request.responseText) as { detail?: unknown } & Partial<ImageAsset>;
      } catch {
        reject(new Error(`Upload failed: ${request.status}`));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(typeof body.detail === "string" ? body.detail : `Upload failed: ${request.status}`));
        return;
      }
      onProgress(100);
      resolve(body as ImageAsset);
    };
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

async function imageRequest<T>(url: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  return handleResponse<T>(response);
}

export function retryImagePreprocessing(projectId: number, imageId: number): Promise<ImageAsset> {
  return imageRequest(`${BASE}/api/projects/${projectId}/images/${imageId}/retry`, "POST");
}

export function adjustProjectImage(
  projectId: number,
  imageId: number,
  adjustment: ImageAdjust
): Promise<ImageAsset> {
  return imageRequest(
    `${BASE}/api/projects/${projectId}/images/${imageId}/adjust`,
    "POST",
    adjustment
  );
}

export function replaceProjectImage(
  projectId: number,
  imageId: number,
  file: File,
  onProgress: (percent: number) => void
): Promise<ImageAsset> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${BASE}/api/projects/${projectId}/images/${imageId}/replace`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Network error while replacing the image."));
    request.onload = () => {
      let body: { detail?: unknown } & Partial<ImageAsset>;
      try {
        body = JSON.parse(request.responseText) as { detail?: unknown } & Partial<ImageAsset>;
      } catch {
        reject(new Error(`Replace failed: ${request.status}`));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(typeof body.detail === "string" ? body.detail : `Replace failed: ${request.status}`));
        return;
      }
      onProgress(100);
      resolve(body as ImageAsset);
    };
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

export function deleteProjectImage(projectId: number, imageId: number): Promise<void> {
  return imageRequest(`${BASE}/api/projects/${projectId}/images/${imageId}`, "DELETE");
}
