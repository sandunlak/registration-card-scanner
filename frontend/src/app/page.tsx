/**
 * Landing page for the Registration Card Scanner application.
 *
 * This is a static placeholder — it shows the app name, a brief description
 * of upcoming features, and a live health-check ping to the backend.
 * Actual application UI is built in subsequent milestones.
 */

import { Suspense } from "react";
import HealthBadge, { HealthBadgeFallback } from "@/components/HealthBadge";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white flex flex-col">
      {/* ── Nav bar ───────────────────────────────────────────────────── */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-2xl select-none">🪪</span>
          <span className="font-semibold text-lg tracking-tight">
            Card Scanner
          </span>
        </div>
        <Suspense fallback={<HealthBadgeFallback />}>
          <HealthBadge />
        </Suspense>
      </nav>

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 gap-8">
        {/* Badge */}
        <span className="inline-flex items-center gap-2 bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-medium px-4 py-1.5 rounded-full tracking-wide uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Milestone 1 — Setup
        </span>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight max-w-3xl">
          Registration{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
            Card Scanner
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg text-slate-300 max-w-2xl leading-relaxed">
          AI-powered digitisation of handwritten and printed registration cards
          for migration consultancy events. Automates data extraction, flags
          uncertain fields for staff review, and exports verified records to
          Excel — all running locally, free of charge.
        </p>

        {/* Feature grid */}
        <div className="grid sm:grid-cols-3 gap-4 mt-4 max-w-3xl w-full text-left">
          {[
            {
              icon: "🔍",
              title: "OCR Extraction",
              desc: "PaddleOCR + handwriting model extracts field values automatically.",
            },
            {
              icon: "✏️",
              title: "Human Review",
              desc: "Low-confidence fields are highlighted for staff correction before saving.",
            },
            {
              icon: "📊",
              title: "Excel Export",
              desc: "Verified records exported to .xlsx with one click.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="bg-white/5 hover:bg-white/10 transition-colors border border-white/10 rounded-2xl p-5"
            >
              <div className="text-3xl mb-3">{f.icon}</div>
              <h2 className="font-semibold text-white mb-1">{f.title}</h2>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* CTA placeholder */}
        <p className="text-slate-500 text-sm mt-4">
          Full application UI coming in Milestone 3.
        </p>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/10 px-8 py-4 text-center text-xs text-slate-500">
        Registration Card Scanner · Open-source · Runs entirely on your machine
      </footer>
    </main>
  );
}
