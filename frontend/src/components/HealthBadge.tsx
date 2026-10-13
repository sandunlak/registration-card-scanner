"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api/health";
import type { HealthResponse } from "@/types";

export default function HealthBadge() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let ignore = false;
    getHealth()
      .then((response) => {
        if (!ignore) setData(response);
      })
      .catch(() => {
        if (!ignore) setData(null);
      })
      .finally(() => {
        if (!ignore) setChecked(true);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const online = data?.status === "ok";

  if (!checked) return <HealthBadgeFallback />;

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
