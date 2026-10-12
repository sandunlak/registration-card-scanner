"use client";

import Link from "next/link";
import { Suspense } from "react";
import HealthBadge, { HealthBadgeFallback } from "./HealthBadge";

interface NavbarProps {
  currentPageTitle?: string;
}

export default function Navbar({ currentPageTitle }: NavbarProps) {
  return (
    <nav className="border-b border-slate-700/60 bg-slate-900/95 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="flex items-center gap-2.5 text-white hover:text-indigo-400 transition-colors group"
        >
          <div className="w-9 h-9 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-xl shadow-inner group-hover:scale-105 transition-transform">
            🪪
          </div>
          <div>
            <span className="font-bold text-base tracking-tight block leading-tight">
              Card Scanner
            </span>
            <span className="text-[11px] text-slate-400 block leading-tight">
              Migration Consultancy Intake
            </span>
          </div>
        </Link>

        {currentPageTitle && (
          <div className="hidden sm:flex items-center gap-2 text-sm text-slate-400 pl-4 border-l border-slate-700/60">
            <span>/</span>
            <span className="text-slate-200 font-medium truncate max-w-xs">
              {currentPageTitle}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <Suspense fallback={<HealthBadgeFallback />}>
          <HealthBadge />
        </Suspense>
      </div>
    </nav>
  );
}
