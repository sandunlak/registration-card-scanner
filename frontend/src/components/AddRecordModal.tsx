"use client";

import { useState } from "react";
import { createProjectRecord, updateProjectRecord } from "@/lib/api/projects";
import { createRecordFormData, serializeRecordFormData } from "@/lib/recordForm";
import type {
  ProjectField,
  RegistrationRecord,
  RecordReviewStatus,
} from "@/types";

interface AddRecordModalProps {
  projectId: number;
  fields: ProjectField[];
  isOpen: boolean;
  onClose: () => void;
  onRecordSaved: (record: RegistrationRecord) => void;
  editingRecord?: RegistrationRecord | null;
}

export default function AddRecordModal({
  projectId,
  fields,
  isOpen,
  onClose,
  onRecordSaved,
  editingRecord,
}: AddRecordModalProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>(() =>
    createRecordFormData(fields, editingRecord?.extracted_data)
  );

  const [reviewStatus, setReviewStatus] = useState<RecordReviewStatus>(
    editingRecord?.review_status ?? "pending"
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleChange = (key: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleMultiSelectToggle = (key: string, option: string) => {
    const raw = formData[key];
    const current: string[] = Array.isArray(raw) ? [...raw.map(String)] : [];
    const index = current.indexOf(option);
    if (index >= 0) {
      current.splice(index, 1);
    } else {
      current.push(option);
    }
    setFormData((prev) => ({ ...prev, [key]: current }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const cleanedData = serializeRecordFormData(fields, formData);

    try {
      if (editingRecord) {
        const updated = await updateProjectRecord(projectId, editingRecord.id, {
          extracted_data: cleanedData,
          review_status: reviewStatus,
        });
        onRecordSaved(updated);
      } else {
        const created = await createProjectRecord(projectId, {
          extracted_data: cleanedData,
          review_status: reviewStatus,
        });
        onRecordSaved(created);
      }
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save record";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {editingRecord ? `Edit Card Record #${editingRecord.id}` : "Manual Card Data Entry"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter or correct attendee information according to configured card fields.
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
        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-4 flex-1">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm flex items-start gap-2">
              <span className="font-bold">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {fields.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-sm">
              <p>No fields configured for this project yet.</p>
              <p className="text-xs text-slate-500 mt-1">
                Please add fields in the Field Settings tab before entering records.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {fields.map((field) => {
                const key = field.field_key;
                const rawVal = formData[key];
                const val = rawVal !== undefined && rawVal !== null ? String(rawVal) : "";
                const placeholder = field.validation_config?.placeholder ?? "";

                return (
                  <div
                    key={field.id}
                    className={
                      field.field_type === "multi_select" || field.field_label.length > 30
                        ? "sm:col-span-2"
                        : ""
                    }
                  >
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      {field.field_label}{" "}
                      {field.required && <span className="text-red-400">*</span>}
                    </label>

                    {/* Field type input rendering */}
                    {field.field_type === "phone" ? (
                      <div className="relative">
                        <span className="absolute left-3 top-2.5 text-slate-500 text-xs">📞</span>
                        <input
                          type="text"
                          required={field.required}
                          placeholder={placeholder || "0771234567"}
                          value={val}
                          onChange={(e) => handleChange(key, e.target.value)}
                          className="w-full bg-slate-800/80 border border-slate-700 rounded-xl pl-8 pr-3 py-2 text-white placeholder-slate-500 text-sm font-mono focus:outline-none focus:border-indigo-500"
                        />
                      </div>
                    ) : field.field_type === "date" ? (
                      <input
                        type="date"
                        required={field.required}
                        value={val}
                        onChange={(e) => handleChange(key, e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                      />
                    ) : field.field_type === "number" ? (
                      <input
                        type="number"
                        required={field.required}
                        placeholder={placeholder}
                        value={val}
                        onChange={(e) => handleChange(key, e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                      />
                    ) : field.field_type === "email" ? (
                      <input
                        type="email"
                        required={field.required}
                        placeholder={placeholder || "user@example.com"}
                        value={val}
                        onChange={(e) => handleChange(key, e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                      />
                    ) : field.field_type === "boolean" ? (
                      <label className="flex items-center gap-3 bg-slate-800/50 border border-slate-700 rounded-xl p-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(formData[key])}
                          onChange={(e) => handleChange(key, e.target.checked)}
                          className="w-4 h-4 text-indigo-600 rounded bg-slate-900 border-slate-700 focus:ring-indigo-500"
                        />
                        <span className="text-xs text-slate-300">
                          {field.field_label} (Checked = Yes)
                        </span>
                      </label>
                    ) : field.field_type === "single_select" ? (
                      <fieldset className="space-y-2 rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                        <legend className="sr-only">{field.field_label}</legend>
                        {field.validation_config?.options?.map((option) => (
                          <label key={option} className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
                            <input
                              type="radio"
                              name={key}
                              value={option}
                              required={field.required}
                              checked={formData[key] === option}
                              onChange={() => handleChange(key, option)}
                              className="h-4 w-4 accent-indigo-500"
                            />
                            <span>{option}</span>
                          </label>
                        ))}
                      </fieldset>
                    ) : field.field_type === "multi_select" ? (
                      <fieldset className="space-y-2 rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                        <legend className="sr-only">{field.field_label}</legend>
                        {field.validation_config?.options?.map((option) => (
                          <label key={option} className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
                            <input
                              type="checkbox"
                              checked={Array.isArray(formData[key]) && (formData[key] as string[]).includes(option)}
                              onChange={() => handleMultiSelectToggle(key, option)}
                              className="h-4 w-4 rounded accent-indigo-500"
                            />
                            <span>{option}</span>
                          </label>
                        ))}
                        <p className="text-xs text-slate-400">Leave all unchecked if no option is marked on the card.</p>
                      </fieldset>
                    ) : (
                      <input
                        type="text"
                        required={field.required}
                        placeholder={placeholder}
                        value={val}
                        onChange={(e) => handleChange(key, e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Review status selector */}
          <div className="pt-4 border-t border-slate-800">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Review Status
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              {[
                { val: "pending", label: "Pending", desc: "Awaiting staff check" },
                { val: "needs_review", label: "Needs Review", desc: "Uncertain or flagged" },
                { val: "reviewed", label: "Reviewed & Verified", desc: "Ready for export" },
              ].map((s) => (
                <button
                  key={s.val}
                  type="button"
                  onClick={() => setReviewStatus(s.val as RecordReviewStatus)}
                  className={`p-2.5 rounded-xl border text-left text-xs transition-all ${
                    reviewStatus === s.val
                      ? s.val === "reviewed"
                        ? "bg-emerald-500/15 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500"
                        : s.val === "needs_review"
                        ? "bg-amber-500/15 border-amber-500 text-amber-300 ring-1 ring-amber-500"
                        : "bg-indigo-500/15 border-indigo-500 text-indigo-300 ring-1 ring-indigo-500"
                      : "bg-slate-800/40 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <span className="font-semibold block">{s.label}</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">{s.desc}</span>
                </button>
              ))}
            </div>
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
              disabled={isSubmitting || fields.length === 0}
              className="px-5 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Saving Record…
                </>
              ) : editingRecord ? (
                "Save Changes"
              ) : (
                "Add Record"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
