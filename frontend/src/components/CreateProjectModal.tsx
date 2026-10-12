"use client";

import { useState } from "react";
import { PROJECT_PRESETS } from "@/lib/presets";
import { createProject } from "@/lib/api/projects";
import type { Project, ProjectFieldCreate } from "@/types";

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

export default function CreateProjectModal({
  isOpen,
  onClose,
  onProjectCreated,
}: CreateProjectModalProps) {
  const [name, setName] = useState("");
  const [eventName, setEventName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState("enquiry");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const activePreset = PROJECT_PRESETS.find((p) => p.id === selectedPresetId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const initialFields: ProjectFieldCreate[] = activePreset
        ? activePreset.fields.map((f, i) => ({ ...f, display_order: i + 1 }))
        : [];

      const created = await createProject({
        name: name.trim(),
        event_name: eventName.trim() || undefined,
        description: description.trim() || undefined,
        fields: initialFields.length > 0 ? initialFields : undefined,
      });

      onProjectCreated(created);
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create project";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Create New Intake Project</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Set up a card intake project with configurable fields for your event.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-5 flex-1">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm flex items-start gap-2">
              <span className="font-bold">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Project Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Colombo Education Fair October 2026"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Event or Intake Name
            </label>
            <input
              type="text"
              placeholder="e.g. BMICH Hall A Intake"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Description / Staff Notes
            </label>
            <textarea
              rows={2}
              placeholder="Add details about expected volume (e.g. 500 cards), staff assigned, or instructions."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Starting Field Template
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {PROJECT_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => setSelectedPresetId(preset.id)}
                  className={`text-left p-3 rounded-xl border transition-all text-xs flex flex-col justify-between ${
                    selectedPresetId === preset.id
                      ? "border-indigo-500 bg-indigo-500/15 text-white ring-1 ring-indigo-500"
                      : "border-slate-800 bg-slate-800/40 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <div>
                    <span className="font-semibold block text-slate-200">{preset.name}</span>
                    <span className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-tight">
                      {preset.description}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono mt-2 text-indigo-400">
                    {preset.fields.length} {preset.fields.length === 1 ? "field" : "fields"}
                  </span>
                </button>
              ))}
            </div>

            {activePreset && activePreset.fields.length > 0 && (
              <div className="mt-3 bg-slate-950/40 rounded-xl p-3 border border-slate-800/80 text-xs">
                <span className="text-slate-400 block mb-1.5 font-medium">Included fields:</span>
                <div className="flex flex-wrap gap-1.5">
                  {activePreset.fields.map((f) => (
                    <span
                      key={f.field_key}
                      className="bg-slate-800 border border-slate-700/60 px-2 py-0.5 rounded text-[11px] text-slate-300"
                    >
                      {f.field_label} {f.required && <span className="text-red-400">*</span>}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-slate-500 mt-2">
                  You can edit, add, or delete any of these fields after creating the project.
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating Project…
                </>
              ) : (
                "Create Project"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
