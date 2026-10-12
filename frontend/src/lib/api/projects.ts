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
