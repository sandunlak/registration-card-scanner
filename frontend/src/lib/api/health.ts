/**
 * API client helpers — health resource.
 *
 * All fetch calls for a given backend resource live in a single file here.
 * No direct fetch calls inside page/component files.
 */

import type { HealthResponse } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json() as Promise<HealthResponse>;
}
