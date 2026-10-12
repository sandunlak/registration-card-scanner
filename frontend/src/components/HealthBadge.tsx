/**
 * HealthBadge — pings the backend /health endpoint and shows a coloured
 * status indicator in the nav bar.
 *
 * Uses React Server Component fetch with no-store so every page load
 * reflects the real backend status.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type HealthData = { status: string; version: string };

async function fetchHealth(): Promise<HealthData | null> {
  try {
    const res = await fetch(`${API_URL}/health`, {
      cache: "no-store",
      // Short timeout — if the backend isn't up we still want the page to render
      signal: AbortSignal.timeout(2000),
    });
    if (!res.ok) return null;
    return (await res.json()) as HealthData;
  } catch {
    return null;
  }
}

export default async function HealthBadge() {
  const data = await fetchHealth();
  const online = data?.status === "ok";

  return (
    <div
      id="health-badge"
      aria-label={online ? "Backend online" : "Backend offline"}
      className={`flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border ${
        online
          ? "bg-emerald-500/15 border-emerald-400/30 text-emerald-300"
          : "bg-red-500/15 border-red-400/30 text-red-400"
      }`}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          online ? "bg-emerald-400 animate-pulse" : "bg-red-500"
        }`}
      />
      {online ? `API v${data?.version}` : "API offline"}
    </div>
  );
}

/** Shown while the async HealthBadge fetch is in-flight. */
export function HealthBadgeFallback() {
  return (
    <div
      id="health-badge-loading"
      aria-label="Checking API status"
      className="flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border bg-slate-500/15 border-slate-400/20 text-slate-400"
    >
      <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
      Checking API…
    </div>
  );
}
