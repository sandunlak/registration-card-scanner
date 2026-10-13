"use client";

import { useState } from "react";
import { createProjectField, updateProjectField } from "@/lib/api/projects";
import type { ProjectField, FieldType, ValidationConfig } from "@/types";

interface AddFieldModalProps {
  projectId: number;
  isOpen: boolean;
  onClose: () => void;
  onFieldSaved: (field: ProjectField) => void;
  editingField?: ProjectField | null;
}

const FIELD_TYPES: { type: FieldType; label: string; desc: string }[] = [
  { type: "text", label: "Text", desc: "Names, addresses, schools, qualifications" },
  { type: "phone", label: "Phone Number", desc: "Stored as string to preserve leading zeros (077...)" },
  { type: "email", label: "Email Address", desc: "Validated email format" },
  { type: "date", label: "Date", desc: "Calendar date (YYYY-MM-DD)" },
  { type: "number", label: "Number", desc: "Numeric count, age, scores" },
  { type: "boolean", label: "Yes / No Toggle", desc: "Consent, attendance, checklist" },
  { type: "single_select", label: "Single Choice (Radio Buttons)", desc: "Choose one option, or leave blank" },
  { type: "multi_select", label: "Checkbox Group", desc: "Choose any marked options; leave unchecked if none" },
];

export default function AddFieldModal({
  projectId,
  isOpen,
  onClose,
  onFieldSaved,
  editingField,
}: AddFieldModalProps) {
  const [fieldLabel, setFieldLabel] = useState(editingField?.field_label ?? "");
  const [fieldKey, setFieldKey] = useState(editingField?.field_key ?? "");
  const [fieldType, setFieldType] = useState<FieldType>(editingField?.field_type ?? "text");
  const [required, setRequired] = useState(editingField?.required ?? false);
  const [placeholder, setPlaceholder] = useState(
    editingField?.validation_config?.placeholder ?? ""
  );
  const [optionsStr, setOptionsStr] = useState(
    editingField?.validation_config?.options?.join(", ") ?? ""
  );
  const [minValue, setMinValue] = useState<string>(
    editingField?.validation_config?.min_value !== undefined
      ? String(editingField.validation_config.min_value)
      : ""
  );
  const [maxValue, setMaxValue] = useState<string>(
    editingField?.validation_config?.max_value !== undefined
      ? String(editingField.validation_config.max_value)
      : ""
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Auto-generate key when typing label in create mode
  const handleLabelChange = (val: string) => {
    setFieldLabel(val);
    if (!editingField) {
      const generatedKey = val
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      setFieldKey(generatedKey);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fieldLabel.trim()) {
      setError("Field label is required.");
      return;
    }
    if (!fieldKey.trim()) {
      setError("Field key is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const validationConfig: ValidationConfig = {};
    if (placeholder.trim()) validationConfig.placeholder = placeholder.trim();

    if (fieldType === "single_select" || fieldType === "multi_select") {
      const options = optionsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (options.length === 0) {
        setError("Please provide at least one option for select fields.");
        setIsSubmitting(false);
        return;
      }
      validationConfig.options = options;
    }

    if (fieldType === "number") {
      if (minValue.trim() !== "") validationConfig.min_value = parseFloat(minValue);
      if (maxValue.trim() !== "") validationConfig.max_value = parseFloat(maxValue);
    }

    try {
      if (editingField) {
        const updated = await updateProjectField(projectId, editingField.id, {
          field_label: fieldLabel.trim(),
          field_type: fieldType,
          required,
          validation_config:
            Object.keys(validationConfig).length > 0 ? validationConfig : undefined,
        });
        onFieldSaved(updated);
      } else {
        const created = await createProjectField(projectId, {
          field_key: fieldKey.trim().toLowerCase(),
          field_label: fieldLabel.trim(),
          field_type: fieldType,
          required,
          validation_config:
            Object.keys(validationConfig).length > 0 ? validationConfig : undefined,
        });
        onFieldSaved(created);
      }
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save field";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {editingField ? "Edit Field Configuration" : "Add New Field to Card Layout"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Define the data type and validation rules for this registration card field.
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

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Field Label <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. WhatsApp Number, NIC or Passport"
              value={fieldLabel}
              onChange={(e) => handleLabelChange(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Field Key (Code Identifier) <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={Boolean(editingField)}
              placeholder="e.g. whatsapp_number"
              value={fieldKey}
              onChange={(e) => setFieldKey(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-mono disabled:opacity-60 disabled:cursor-not-allowed"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Alphanumeric characters and underscores only. Used in Excel export column names.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Data Type <span className="text-red-400">*</span>
            </label>
            <select
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value as FieldType)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm"
            >
              {FIELD_TYPES.map((ft) => (
                <option key={ft.type} value={ft.type}>
                  {ft.label} — ({ft.desc})
                </option>
              ))}
            </select>
          </div>

          {/* Required toggle */}
          <div className="bg-slate-800/40 border border-slate-800 p-3 rounded-xl flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-slate-200 block">Mandatory Field</span>
              <span className="text-xs text-slate-400 block">
                Flag cards as needing staff review if this value is missing or unreadable.
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={required}
                onChange={(e) => setRequired(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>

          {/* Conditional Options for Select Fields */}
          {(fieldType === "single_select" || fieldType === "multi_select") && (
            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-3.5 space-y-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-indigo-300">
                {fieldType === "multi_select" ? "Checkbox Options" : "Single-choice Options"} (Comma-Separated) <span className="text-red-400">*</span>
              </label>
              <textarea
                rows={2}
                placeholder="Option A, Option B, Option C"
                value={optionsStr}
                onChange={(e) => setOptionsStr(e.target.value)}
                className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-xs resize-none"
              />
            </div>
          )}

          {/* Conditional Min/Max for Number Fields */}
          {fieldType === "number" && (
            <div className="grid grid-cols-2 gap-3 bg-slate-800/30 border border-slate-800 rounded-xl p-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Minimum Value
                </label>
                <input
                  type="number"
                  placeholder="e.g. 1"
                  value={minValue}
                  onChange={(e) => setMinValue(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Maximum Value
                </label>
                <input
                  type="number"
                  placeholder="e.g. 100"
                  value={maxValue}
                  onChange={(e) => setMaxValue(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                />
              </div>
            </div>
          )}

          {/* Placeholder helper */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Input Placeholder / Example
            </label>
            <input
              type="text"
              placeholder="e.g. 077xxxxxxx or Colombo 07"
              value={placeholder}
              onChange={(e) => setPlaceholder(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
            />
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
                  Saving Field…
                </>
              ) : editingField ? (
                "Update Field"
              ) : (
                "Add Field"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
