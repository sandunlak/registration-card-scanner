"use client";

import { use, useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import AddFieldModal from "@/components/AddFieldModal";
import AddRecordModal from "@/components/AddRecordModal";
import ImagesWorkspace from "@/components/ImagesWorkspace";
import {
  getProject,
  updateProject,
  archiveProject,
  restoreProject,
  getProjectFields,
  deleteProjectField,
  reorderProjectFields,
  getProjectRecords,
  updateProjectRecord,
} from "@/lib/api/projects";
import type {
  Project,
  ProjectField,
  RegistrationRecord,
  RecordListResponse,
} from "@/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

function ProjectDetailContent({ params }: PageProps) {
  const resolvedParams = use(params);
  const projectId = parseInt(resolvedParams.id, 10);

  const [project, setProject] = useState<Project | null>(null);
  const [fields, setFields] = useState<ProjectField[]>([]);
  const [recordsResponse, setRecordsResponse] = useState<RecordListResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"records" | "fields" | "images" | "settings">("records");

  // Record filtering & pagination
  const [recordPage, setRecordPage] = useState(1);
  const [recordStatusFilter, setRecordStatusFilter] = useState<string>("");
  const [recordsLoading, setRecordsLoading] = useState(false);

  // Field modal state
  const [isFieldModalOpen, setIsFieldModalOpen] = useState(false);
  const [editingField, setEditingField] = useState<ProjectField | null>(null);

  // Record modal state
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<RegistrationRecord | null>(null);

  // Settings form state
  const [editName, setEditName] = useState("");
  const [editEventName, setEditEventName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // Load project and fields
  const loadProjectAndFields = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([getProject(projectId), getProjectFields(projectId)])
      .then(([projData, fieldsData]) => {
        setProject(projData);
        setFields(fieldsData);
        setEditName(projData.name);
        setEditEventName(projData.event_name || "");
        setEditDescription(projData.description || "");
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load project details.";
        setError(message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    let ignore = false;
    Promise.all([getProject(projectId), getProjectFields(projectId)])
      .then(([projData, fieldsData]) => {
        if (!ignore) {
          setProject(projData);
          setFields(fieldsData);
          setEditName(projData.name);
          setEditEventName(projData.event_name || "");
          setEditDescription(projData.description || "");
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          const message = err instanceof Error ? err.message : "Failed to load project details.";
          setError(message);
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [projectId]);

  useEffect(() => {
    let ignore = false;
    getProjectRecords(projectId, recordPage, 15, recordStatusFilter || undefined)
      .then((res) => {
        if (!ignore) {
          setRecordsResponse(res);
          setRecordsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          console.error("Failed to load records:", err);
          setRecordsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [projectId, recordPage, recordStatusFilter]);

  // Field Reordering: Move Up / Down
  const handleMoveField = async (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= fields.length) return;

    const newFields = [...fields];
    const [moved] = newFields.splice(index, 1);
    newFields.splice(targetIndex, 0, moved);

    setFields(newFields);

    try {
      const updated = await reorderProjectFields(
        projectId,
        newFields.map((f) => f.id)
      );
      setFields(updated);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Reordering failed";
      alert(message);
      loadProjectAndFields();
    }
  };

  // Field Deletion
  const handleDeleteField = async (field: ProjectField) => {
    if (
      !confirm(
        `Are you sure you want to delete the field "${field.field_label}"? Existing records will keep their raw data, but the field will no longer be visible in forms.`
      )
    ) {
      return;
    }
    try {
      await deleteProjectField(projectId, field.id);
      setFields((prev) => prev.filter((f) => f.id !== field.id));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Delete failed";
      alert(message);
    }
  };

  // Quick mark record as reviewed
  const handleQuickReview = async (record: RegistrationRecord) => {
    try {
      const nextStatus = record.review_status === "reviewed" ? "pending" : "reviewed";
      const updated = await updateProjectRecord(projectId, record.id, {
        review_status: nextStatus,
      });
      setRecordsResponse((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((r) => (r.id === updated.id ? updated : r)),
            }
          : prev
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Update failed";
      alert(message);
    }
  };

  // Archive / Restore Project
  const handleArchiveToggle = async () => {
    if (!project) return;
    try {
      if (project.status === "active") {
        const updated = await archiveProject(project.id);
        setProject(updated);
      } else {
        const updated = await restoreProject(project.id);
        setProject(updated);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Action failed";
      alert(message);
    }
  };

  // Save Settings
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editName.trim()) return;
    setIsSavingSettings(true);
    setSettingsSuccess(false);
    try {
      const updated = await updateProject(projectId, {
        name: editName.trim(),
        event_name: editEventName.trim() || null,
        description: editDescription.trim() || null,
      });
      setProject(updated);
      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save settings";
      alert(message);
    } finally {
      setIsSavingSettings(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Loading project details…</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-4">
          <div className="text-4xl">⚠️</div>
          <h1 className="text-lg font-bold text-white">Project Not Found</h1>
          <p className="text-sm text-slate-400 max-w-md">{error || "Could not locate this project."}</p>
          <Link
            href="/"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold"
          >
            ← Back to Projects Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar currentPageTitle={project.name} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Breadcrumb & Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Link
                href="/"
                className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1 font-medium"
              >
                <span>←</span>
                <span>Projects</span>
              </Link>
              <span className="text-slate-600 text-xs">/</span>
              <span
                className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${
                  project.status === "active"
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                    : "bg-slate-700/20 border-slate-700/40 text-slate-400"
                }`}
              >
                {project.status}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <span>{project.name}</span>
            </h1>

            {project.event_name && (
              <p className="text-sm text-indigo-400 font-medium mt-1 flex items-center gap-1.5">
                <span>📍</span>
                <span>{project.event_name}</span>
              </p>
            )}

            {project.description && (
              <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
                {project.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleArchiveToggle}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                project.status === "active"
                  ? "border-slate-700 bg-slate-800/40 text-slate-300 hover:bg-slate-800 hover:text-white"
                  : "border-emerald-600/40 bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30"
              }`}
            >
              {project.status === "active" ? "Archive Project" : "Restore Project"}
            </button>

            <button
              onClick={() => {
                setEditingRecord(null);
                setIsRecordModalOpen(true);
              }}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl font-semibold text-xs shadow-lg shadow-indigo-600/25 flex items-center gap-1.5 transition-all hover:scale-[1.02]"
            >
              <span>+</span>
              <span>Add Record</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-slate-800">
          {[
            {
              id: "records",
              label: `Records (${recordsResponse?.total ?? 0})`,
              icon: "📋",
            },
            {
              id: "fields",
              label: `Fields & Card Layout (${fields.length})`,
              icon: "⚙️",
            },
            { id: "images", label: "Images", icon: "▧" },
            { id: "settings", label: "Project Settings", icon: "🛠️" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as "records" | "fields" | "images" | "settings")}
              className={`px-4 py-3 text-xs sm:text-sm font-medium border-b-2 transition-all flex items-center gap-2 -mb-px ${
                activeTab === tab.id
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* ── TAB 1: RECORDS ──────────────────────────────────────────────── */}
        {activeTab === "records" && (
          <div className="space-y-4">
            {/* Filter and Action bar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-2xl border border-slate-800/80">
              <div className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800/60 self-start sm:self-auto">
                {[
                  { id: "", label: "All Records" },
                  { id: "pending", label: "Pending" },
                  { id: "needs_review", label: "Needs Review" },
                  { id: "reviewed", label: "Reviewed" },
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setRecordStatusFilter(s.id);
                      setRecordPage(1);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      recordStatusFilter === s.id
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              <div className="text-xs text-slate-400 flex items-center gap-2">
                <span>
                  Showing {recordsResponse?.items.length ?? 0} of {recordsResponse?.total ?? 0} cards
                </span>
              </div>
            </div>

            {/* Table */}
            {recordsLoading ? (
              <div className="text-center py-20 space-y-3">
                <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading records…</p>
              </div>
            ) : !recordsResponse || recordsResponse.items.length === 0 ? (
              <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
                <div className="text-3xl">🪪</div>
                <h3 className="text-sm font-semibold text-slate-200">
                  {recordStatusFilter
                    ? `No cards found with status "${recordStatusFilter}"`
                    : "No registration cards logged yet"}
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Staff can enter records manually now, or upload batches of photographed registration cards in Milestone 3.
                </p>
                <button
                  onClick={() => {
                    setEditingRecord(null);
                    setIsRecordModalOpen(true);
                  }}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold mt-2"
                >
                  + Add First Record
                </button>
              </div>
            ) : (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-semibold text-[11px] tracking-wider">
                      <tr>
                        <th className="py-3 px-4">#ID</th>
                        <th className="py-3 px-4">Status</th>
                        {/* Display up to 4 configured fields in columns */}
                        {fields.slice(0, 4).map((f) => (
                          <th key={f.id} className="py-3 px-4">
                            {f.field_label}
                          </th>
                        ))}
                        <th className="py-3 px-4">Logged At</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {recordsResponse.items.map((record) => (
                        <tr
                          key={record.id}
                          className="hover:bg-slate-800/30 transition-colors"
                        >
                          <td className="py-3 px-4 font-mono text-slate-500">
                            #{record.id}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${
                                record.review_status === "reviewed"
                                  ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                                  : record.review_status === "needs_review"
                                  ? "bg-amber-500/15 border-amber-500/30 text-amber-300"
                                  : "bg-indigo-500/15 border-indigo-500/30 text-indigo-300"
                              }`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${
                                  record.review_status === "reviewed"
                                    ? "bg-emerald-400"
                                    : record.review_status === "needs_review"
                                    ? "bg-amber-400"
                                    : "bg-indigo-400"
                                }`}
                              />
                              {record.review_status.replace("_", " ")}
                            </span>
                          </td>

                          {/* Dynamic Field Values */}
                          {fields.slice(0, 4).map((f) => {
                            const val = record.extracted_data[f.field_key];
                            return (
                              <td key={f.id} className="py-3 px-4 font-medium text-slate-200">
                                {val === null || val === undefined || val === "" ? (
                                  <span className="text-slate-600">—</span>
                                ) : Array.isArray(val) ? (
                                  val.join(", ")
                                ) : typeof val === "boolean" ? (
                                  val ? "Yes" : "No"
                                ) : (
                                  String(val)
                                )}
                              </td>
                            );
                          })}

                          <td className="py-3 px-4 text-slate-500 text-[11px]">
                            {new Date(record.created_at).toLocaleDateString()}
                          </td>

                          <td className="py-3 px-4 text-right space-x-2">
                            <button
                              onClick={() => handleQuickReview(record)}
                              title={
                                record.review_status === "reviewed"
                                  ? "Unmark reviewed"
                                  : "Mark as reviewed"
                              }
                              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
                                record.review_status === "reviewed"
                                  ? "border-emerald-600/40 text-emerald-300 hover:bg-emerald-600/20"
                                  : "border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800"
                              }`}
                            >
                              {record.review_status === "reviewed" ? "✓ Verified" : "Verify"}
                            </button>

                            <button
                              onClick={() => {
                                setEditingRecord(record);
                                setIsRecordModalOpen(true);
                              }}
                              className="px-2.5 py-1 rounded-lg text-[11px] font-medium border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                            >
                              Edit
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {recordsResponse.pages > 1 && (
                  <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-950/40">
                    <button
                      onClick={() => setRecordPage((p) => Math.max(1, p - 1))}
                      disabled={recordPage <= 1}
                      className="px-3 py-1 bg-slate-800 rounded-lg disabled:opacity-40 hover:bg-slate-700 text-slate-200"
                    >
                      ← Previous
                    </button>
                    <span>
                      Page {recordPage} of {recordsResponse.pages}
                    </span>
                    <button
                      onClick={() =>
                        setRecordPage((p) => Math.min(recordsResponse.pages, p + 1))
                      }
                      disabled={recordPage >= recordsResponse.pages}
                      className="px-3 py-1 bg-slate-800 rounded-lg disabled:opacity-40 hover:bg-slate-700 text-slate-200"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 2: FIELDS & CARD LAYOUT ─────────────────────────────────── */}
        {activeTab === "fields" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-2xl border border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-white">Configured Card Fields</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Define the fields present on this event&apos;s physical cards. Reorder fields using the arrows to match the visual layout.
                </p>
              </div>
              <button
                onClick={() => {
                  setEditingField(null);
                  setIsFieldModalOpen(true);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto shadow-md"
              >
                <span>+</span>
                <span>Add Field</span>
              </button>
            </div>

            {fields.length === 0 ? (
              <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
                <div className="text-3xl">⚙️</div>
                <h3 className="text-sm font-semibold text-slate-200">No fields configured</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Add field definitions (e.g. Student Name, Mobile Number, Email) to start collecting data for this card format.
                </p>
                <button
                  onClick={() => {
                    setEditingField(null);
                    setIsFieldModalOpen(true);
                  }}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold"
                >
                  + Add First Field
                </button>
              </div>
            ) : (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
                <div className="divide-y divide-slate-800/60">
                  {fields.map((field, idx) => (
                    <div
                      key={field.id}
                      className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/25 transition-colors"
                    >
                      {/* Left: Reorder arrows & label */}
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col gap-0.5">
                          <button
                            onClick={() => handleMoveField(idx, "up")}
                            disabled={idx === 0}
                            title="Move Up"
                            className="text-slate-400 hover:text-white disabled:opacity-20 p-1 rounded hover:bg-slate-800 text-xs"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => handleMoveField(idx, "down")}
                            disabled={idx === fields.length - 1}
                            title="Move Down"
                            className="text-slate-400 hover:text-white disabled:opacity-20 p-1 rounded hover:bg-slate-800 text-xs"
                          >
                            ▼
                          </button>
                        </div>

                        <span className="text-xs font-mono text-slate-500 w-5">
                          #{idx + 1}
                        </span>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-white">
                              {field.field_label}
                            </span>
                            {field.required && (
                              <span className="bg-red-500/15 border border-red-500/30 text-red-300 text-[10px] px-1.5 py-0.2 rounded font-medium">
                                Required
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                            <span className="font-mono text-indigo-400 text-[11px]">
                              {field.field_key}
                            </span>
                            <span>•</span>
                            <span className="capitalize">{field.field_type.replace("_", " ")}</span>
                            {field.validation_config?.options && (
                              <>
                                <span>•</span>
                                <span className="text-slate-400 text-[11px]">
                                  {field.validation_config.options.length} options
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-2 self-end sm:self-auto">
                        <button
                          onClick={() => {
                            setEditingField(field);
                            setIsFieldModalOpen(true);
                          }}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteField(field)}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-900/40 text-red-400 hover:bg-red-900/20 hover:text-red-300 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: PROJECT SETTINGS ─────────────────────────────────────── */}
        {activeTab === "settings" && (
          <div className="max-w-2xl bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
            <div>
              <h3 className="text-base font-bold text-white">Project Metadata</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Update project name, event location, or internal staff notes.
              </p>
            </div>

            {settingsSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-4 py-2.5 rounded-xl text-xs flex items-center gap-2">
                <span>✓</span>
                <span>Settings saved successfully.</span>
              </div>
            )}

            <form onSubmit={handleSaveSettings} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Project Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Event / Intake Name
                </label>
                <input
                  type="text"
                  value={editEventName}
                  onChange={(e) => setEditEventName(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-between">
                <button
                  type="submit"
                  disabled={isSavingSettings}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-xl text-xs font-semibold shadow-md disabled:opacity-50"
                >
                  {isSavingSettings ? "Saving…" : "Save Changes"}
                </button>

                <button
                  type="button"
                  onClick={handleArchiveToggle}
                  className="text-xs text-red-400 hover:text-red-300 underline"
                >
                  {project.status === "active" ? "Archive this project" : "Restore this project"}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === "images" && <ImagesWorkspace projectId={projectId} />}
      </main>

      {/* Modals */}
      <AddFieldModal
        projectId={projectId}
        isOpen={isFieldModalOpen}
        editingField={editingField}
        onClose={() => {
          setIsFieldModalOpen(false);
          setEditingField(null);
        }}
        onFieldSaved={(saved) => {
          setFields((prev) => {
            const exists = prev.some((f) => f.id === saved.id);
            if (exists) {
              return prev.map((f) => (f.id === saved.id ? saved : f));
            }
            return [...prev, saved];
          });
        }}
      />

      <AddRecordModal
        projectId={projectId}
        fields={fields}
        isOpen={isRecordModalOpen}
        editingRecord={editingRecord}
        onClose={() => {
          setIsRecordModalOpen(false);
          setEditingRecord(null);
        }}
        onRecordSaved={(saved) => {
          setRecordsResponse((prev) => {
            if (!prev) return null;
            const exists = prev.items.some((r) => r.id === saved.id);
            if (exists) {
              return {
                ...prev,
                items: prev.items.map((r) => (r.id === saved.id ? saved : r)),
              };
            }
            return {
              ...prev,
              total: prev.total + 1,
              items: [saved, ...prev.items],
            };
          });
        }}
      />
    </div>
  );
}

function ProjectDetailSkeleton() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />
      <div className="flex-1 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-400">Loading project details…</p>
      </div>
    </div>
  );
}

export default function ProjectDetailPage({ params }: PageProps) {
  return (
    <Suspense fallback={<ProjectDetailSkeleton />}>
      <ProjectDetailContent params={params} />
    </Suspense>
  );
}
