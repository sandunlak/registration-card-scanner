"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import CreateProjectModal from "@/components/CreateProjectModal";
import { getProjects, archiveProject, restoreProject } from "@/lib/api/projects";
import type { Project } from "@/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "archived">("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const fetchProjects = useCallback(() => {
    setLoading(true);
    setError(null);
    getProjects()
      .then((data) => {
        setProjects(data);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load projects from backend API.";
        setError(message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let ignore = false;
    getProjects()
      .then((data) => {
        if (!ignore) {
          setProjects(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          const message = err instanceof Error ? err.message : "Failed to load projects from backend API.";
          setError(message);
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleArchiveToggle = async (project: Project, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      if (project.status === "active") {
        const updated = await archiveProject(project.id);
        setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      } else {
        const updated = await restoreProject(project.id);
        setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Action failed";
      alert(message);
    }
  };

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const matchesStatus =
        statusFilter === "all" ? true : p.status === statusFilter;
      const matchesSearch =
        search.trim() === ""
          ? true
          : p.name.toLowerCase().includes(search.toLowerCase()) ||
            (p.event_name && p.event_name.toLowerCase().includes(search.toLowerCase()));
      return matchesStatus && matchesSearch;
    });
  }, [projects, statusFilter, search]);

  const activeCount = projects.filter((p) => p.status === "active").length;
  const totalRecords = projects.reduce((acc, p) => acc + (p.record_count || 0), 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Top Summary Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Registration Card Digitisation
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Local AI-assisted registration card processing for migration and education events.
              Configure card layouts, extract attendee details, and export clean data to Excel.
            </p>
          </div>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="self-start md:self-auto bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-semibold text-sm shadow-lg shadow-indigo-600/25 flex items-center gap-2 transition-all hover:scale-[1.02]"
          >
            <span>+</span>
            <span>New Intake Project</span>
          </button>
        </div>

        {/* Metrics Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Total Intake Projects
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-bold text-white">{projects.length}</span>
              <span className="text-xs text-slate-500">configured</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block">
              Active Events
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-bold text-emerald-300">{activeCount}</span>
              <span className="text-xs text-slate-500">in progress</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block">
              Records Digitised
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-bold text-indigo-300">{totalRecords}</span>
              <span className="text-xs text-slate-500">cards logged</span>
            </div>
          </div>
        </div>

        {/* Controls: Search & Status Filters */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/40 p-2 rounded-2xl border border-slate-800/80">
          <div className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800/60 self-start sm:self-auto">
            {(
              [
                { id: "all", label: "All Projects" },
                { id: "active", label: "Active" },
                { id: "archived", label: "Archived" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === tab.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative flex-1 max-w-sm">
            <span className="absolute left-3.5 top-2.5 text-slate-500 text-xs">🔍</span>
            <input
              type="text"
              placeholder="Search by project or event name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Project List / Grid */}
        {loading ? (
          <div className="text-center py-24 space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-slate-400">Loading projects from backend…</p>
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center space-y-3">
            <p className="text-sm text-red-400 font-medium">{error}</p>
            <button
              onClick={fetchProjects}
              className="px-4 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 rounded-lg text-xs transition-colors"
            >
              Retry Connection
            </button>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-4">
            <div className="text-4xl">📂</div>
            <div>
              <h2 className="text-base font-semibold text-slate-200">
                {search || statusFilter !== "all"
                  ? "No matching projects found"
                  : "No intake projects yet"}
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                {search || statusFilter !== "all"
                  ? "Try adjusting your search terms or status filter."
                  : "Create your first project to start setting up card field templates and logging attendee cards."}
              </p>
            </div>
            {!search && statusFilter === "all" && (
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all"
              >
                + Create First Project
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredProjects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="group bg-slate-900/70 hover:bg-slate-900 border border-slate-800/90 hover:border-indigo-500/50 rounded-2xl p-5 shadow-sm transition-all flex flex-col justify-between hover:shadow-indigo-500/5"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <span
                      className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${
                        project.status === "active"
                          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                          : "bg-slate-700/20 border-slate-700/40 text-slate-400"
                      }`}
                    >
                      {project.status}
                    </span>

                    <button
                      onClick={(e) => handleArchiveToggle(project, e)}
                      title={project.status === "active" ? "Archive project" : "Restore project"}
                      className="text-xs text-slate-500 hover:text-slate-300 px-2 py-0.5 rounded hover:bg-slate-800 transition-colors"
                    >
                      {project.status === "active" ? "Archive" : "Restore"}
                    </button>
                  </div>

                  <h2 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors mt-3">
                    {project.name}
                  </h2>

                  {project.event_name && (
                    <p className="text-xs text-indigo-400/90 font-medium mt-0.5 flex items-center gap-1.5">
                      <span>📍</span>
                      <span>{project.event_name}</span>
                    </p>
                  )}

                  {project.description && (
                    <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                      {project.description}
                    </p>
                  )}
                </div>

                <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-3">
                    <span title="Configured card fields">
                      ⚙️ <strong className="text-slate-200">{project.field_count ?? 0}</strong> fields
                    </span>
                    <span title="Processed registration cards">
                      📋 <strong className="text-slate-200">{project.record_count ?? 0}</strong> cards
                    </span>
                  </div>

                  <span className="text-indigo-400 group-hover:translate-x-0.5 transition-transform">
                    Open →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onProjectCreated={(newProject) => {
          setProjects((prev) => [newProject, ...prev]);
        }}
      />
    </div>
  );
}
