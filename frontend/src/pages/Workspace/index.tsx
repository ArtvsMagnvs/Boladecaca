// pages/Workspace/index.tsx — WPMS: Vista Proyecto (V0.87 W2a)
//
// Una columna de contenido, sin dashboard saturado (doc 18 §9.1): panel de
// proyectos a la izquierda + detalle del proyecto a la derecha (cabecera +
// versión + progreso + enlaces + milestones + tareas + actividad reciente).
// La edición es 100% por ratón (popups). El board Kanban + drag&drop es W2b.
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api, type Project, type Task, type Milestone, type WorkspaceProgress,
} from "@/lib/api";
import { TaskPopup } from "./TaskPopup";
import { ProjectPopup } from "./ProjectPopup";
import { MilestonePopup } from "./MilestonePopup";

const DONE = new Set(["done", "completed"]);
const isDone = (s: string) => DONE.has((s || "").toLowerCase());

const PRIORITY_DOT: Record<string, string> = {
  high: "bg-signal-error", medium: "bg-signal-warn", low: "bg-ink-faint",
};
const MS_STATUS_LABEL: Record<string, string> = {
  planned: "Planificado", active: "Activo", done: "Completado", archived: "Archivado",
};

function pct(ratio: number) { return Math.round((ratio || 0) * 100); }

export default function Workspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [progress, setProgress] = useState<WorkspaceProgress | null>(null);
  const [loading, setLoading] = useState(true);

  // Popups: undefined = cerrado; null = crear; objeto = editar.
  const [taskEdit, setTaskEdit] = useState<Task | null | undefined>(undefined);
  const [projectEdit, setProjectEdit] = useState<Project | null | undefined>(undefined);
  const [milestoneEdit, setMilestoneEdit] = useState<Milestone | null | undefined>(undefined);

  const selected = useMemo(() => projects.find((p) => p.id === selectedId) ?? null, [projects, selectedId]);
  const activeMilestone = useMemo(
    () => milestones.find((m) => m.status === "active") ?? milestones[0] ?? null,
    [milestones],
  );

  const loadProjects = useCallback(async () => {
    const ps = await api.getProjects();
    setProjects(ps);
    setSelectedId((cur) => (cur && ps.some((p) => p.id === cur) ? cur : ps[0]?.id ?? null));
    setLoading(false);
  }, []);

  const loadProjectDetail = useCallback(async (pid: number) => {
    const [ms, ts, prog] = await Promise.all([
      api.getMilestones(pid),
      api.getTasks(0, 500),
      api.getWorkspaceProgress(pid).catch(() => null),
    ]);
    setMilestones(ms);
    setTasks(ts.filter((t) => t.project_id === pid));
    setProgress(prog);
  }, []);

  useEffect(() => { loadProjects().catch(() => setLoading(false)); }, [loadProjects]);
  useEffect(() => {
    if (selectedId == null) { setMilestones([]); setTasks([]); setProgress(null); return; }
    loadProjectDetail(selectedId).catch(() => {});
  }, [selectedId, loadProjectDetail]);

  const refreshAll = useCallback(async () => {
    await loadProjects();
    if (selectedId != null) await loadProjectDetail(selectedId);
  }, [loadProjects, loadProjectDetail, selectedId]);

  // --- Task handlers ---
  const saveTask = async (data: Partial<Task>) => {
    if (taskEdit) await api.updateTask(taskEdit.id, data);
    else await api.createTask(data);
    setTaskEdit(undefined);
    if (selectedId != null) await loadProjectDetail(selectedId);
    await loadProjects(); // progress vive en Project
  };
  const deleteTask = async (id: number) => {
    await api.deleteTask(id);
    setTaskEdit(undefined);
    if (selectedId != null) await loadProjectDetail(selectedId);
    await loadProjects();
  };
  const toggleTaskDone = async (t: Task) => {
    await api.updateTask(t.id, { status: isDone(t.status) ? "pending" : "completed" });
    if (selectedId != null) await loadProjectDetail(selectedId);
    await loadProjects();
  };

  // --- Project handlers ---
  const saveProject = async (data: Partial<Project>) => {
    if (projectEdit) await api.updateProject(projectEdit.id, data);
    else { const created = await api.createProject(data); setSelectedId(created.id); }
    setProjectEdit(undefined);
    await refreshAll();
  };
  const deleteProject = async (id: number) => {
    await api.deleteProject(id);
    setProjectEdit(undefined);
    setSelectedId(null);
    await loadProjects();
  };

  // --- Milestone handlers ---
  const saveMilestone = async (data: Partial<Milestone>) => {
    if (milestoneEdit) await api.updateMilestone(milestoneEdit.id, data);
    else await api.createMilestone(data);
    setMilestoneEdit(undefined);
    if (selectedId != null) await loadProjectDetail(selectedId);
  };
  const deleteMilestone = async (id: number) => {
    await api.deleteMilestone(id);
    setMilestoneEdit(undefined);
    if (selectedId != null) await loadProjectDetail(selectedId);
  };
  const completeMilestone = async (id: number) => {
    await api.completeMilestone(id);
    setMilestoneEdit(undefined);
    await refreshAll();
  };

  const recentTasks = useMemo(
    () => [...tasks].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? "")).slice(0, 5),
    [tasks],
  );

  const overallRatio = progress?.overall.ratio ?? selected?.progress ?? 0;

  return (
    <div className="h-full flex gap-4">
      {/* ---- Panel de proyectos ---- */}
      <aside className="w-56 shrink-0 flex flex-col gap-2">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xs uppercase tracking-wide text-ink-faint">Proyectos</h2>
          <button onClick={() => setProjectEdit(null)} className="text-accent hover:text-accent-soft text-lg leading-none px-1" title="Nuevo proyecto">+</button>
        </div>
        <div className="flex-1 overflow-y-auto flex flex-col gap-1">
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={`text-left px-3 py-2 rounded-xl text-sm border transition-all ${
                p.id === selectedId
                  ? "bg-accent/12 text-ink border-accent/25"
                  : "text-ink-dim hover:bg-base-700/40 border-transparent"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate">{p.name}</span>
                {p.current_version && <span className="text-[10px] text-ink-faint shrink-0">{p.current_version}</span>}
              </div>
              <div className="mt-1.5 h-1 bg-base-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent/50 rounded-full" style={{ width: `${pct(p.progress)}%` }} />
              </div>
            </button>
          ))}
          {!loading && projects.length === 0 && (
            <p className="text-xs text-ink-faint px-3 py-4">Sin proyectos. Crea uno con +.</p>
          )}
        </div>
      </aside>

      {/* ---- Detalle del proyecto ---- */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {loading ? (
          <div className="text-center text-ink-dim py-16">Cargando…</div>
        ) : !selected ? (
          <div className="text-center text-ink-dim py-16">Selecciona o crea un proyecto.</div>
        ) : (
          <div className="flex flex-col gap-5 max-w-3xl">
            {/* Cabecera */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h1 className="text-xl font-semibold text-ink truncate">{selected.name}</h1>
                  {selected.current_version && (
                    <span className="text-xs px-2 py-0.5 rounded-md bg-accent/12 text-accent border border-accent/25">v{selected.current_version}</span>
                  )}
                  <span className="text-xs px-2 py-0.5 rounded-md bg-base-700/60 text-ink-dim">{selected.status}</span>
                </div>
                {selected.description && <p className="text-sm text-ink-dim mt-1.5">{selected.description}</p>}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button onClick={() => setProjectEdit(selected)} className="text-xs text-ink-dim hover:text-ink px-2 py-1.5 rounded-lg border border-base-700">Editar</button>
                <button onClick={() => setTaskEdit(null)} className="text-xs px-3 py-1.5 bg-accent/15 text-accent rounded-lg border border-accent/30 hover:bg-accent/25">+ Tarea</button>
              </div>
            </div>

            {/* Progreso del milestone activo (u overall) */}
            <div className="glass-surface rounded-2xl p-4">
              <div className="flex justify-between items-center text-xs mb-2">
                <span className="text-ink-dim">
                  {activeMilestone ? <>Milestone activo · <span className="text-ink">{activeMilestone.name}</span></> : "Progreso del proyecto"}
                </span>
                <span className="text-ink font-medium">
                  {activeMilestone?.progress ? `${activeMilestone.progress.done}/${activeMilestone.progress.total}` : ""} · {pct(activeMilestone?.progress?.ratio ?? overallRatio)}%
                </span>
              </div>
              <div className="h-2 bg-base-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent/60 rounded-full transition-all" style={{ width: `${pct(activeMilestone?.progress?.ratio ?? overallRatio)}%` }} />
              </div>
            </div>

            {/* Enlaces repo/docs */}
            {(selected.repo_path || (selected.docs && selected.docs.length > 0)) && (
              <div className="flex flex-wrap gap-2">
                {selected.repo_path && (
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-base-800 border border-base-700 text-ink-dim" title={selected.repo_path}>📁 repo</span>
                )}
                {(selected.docs ?? []).map((d, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-lg bg-base-800 border border-base-700 text-ink-dim" title={d.url_or_path}>🔗 {d.label}</span>
                ))}
              </div>
            )}

            {/* Milestones */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-ink">Milestones</h3>
                <button onClick={() => setMilestoneEdit(null)} className="text-xs text-accent hover:text-accent-soft">+ Milestone</button>
              </div>
              <div className="flex flex-col gap-1.5">
                {milestones.map((m) => (
                  <button key={m.id} onClick={() => setMilestoneEdit(m)} className="text-left glass-surface rounded-xl px-3.5 py-2.5 hover:border-accent/30 border border-transparent transition-all">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${m.status === "active" ? "bg-accent/15 text-accent" : m.status === "done" ? "bg-signal-ok/15 text-signal-ok" : "bg-base-700/60 text-ink-faint"}`}>{MS_STATUS_LABEL[m.status] ?? m.status}</span>
                        <span className="text-sm text-ink truncate">{m.name}</span>
                        {m.version && <span className="text-[10px] text-ink-faint shrink-0">v{m.version}</span>}
                      </div>
                      {m.progress && <span className="text-xs text-ink-faint shrink-0 tabular-nums">{m.progress.done}/{m.progress.total} · {pct(m.progress.ratio)}%</span>}
                    </div>
                  </button>
                ))}
                {milestones.length === 0 && <p className="text-xs text-ink-faint px-1 py-2">Sin milestones. Añade uno para trabajar por versiones.</p>}
              </div>
            </section>

            {/* Tareas */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-ink">
                  Tareas {activeMilestone ? <span className="text-ink-faint font-normal">· {activeMilestone.name}</span> : ""}
                </h3>
              </div>
              <TaskList
                tasks={tasks}
                activeMilestoneId={activeMilestone?.id ?? null}
                onToggle={toggleTaskDone}
                onOpen={(t) => setTaskEdit(t)}
              />
            </section>

            {/* Actividad reciente (solo lectura) */}
            {recentTasks.length > 0 && (
              <section>
                <h3 className="text-sm font-medium text-ink mb-2">Actividad reciente</h3>
                <div className="flex flex-col gap-1">
                  {recentTasks.map((t) => (
                    <div key={t.id} className="text-xs text-ink-faint flex items-center gap-2">
                      <span className={`h-1.5 w-1.5 rounded-full ${isDone(t.status) ? "bg-signal-ok" : "bg-ink-faint/50"}`} />
                      <span className="truncate text-ink-dim">{t.title}</span>
                      <span className="ml-auto shrink-0">{(t.updated_at ?? "").slice(0, 10)}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>

      {/* ---- Popups ---- */}
      {taskEdit !== undefined && (
        <TaskPopup
          task={taskEdit}
          projects={projects}
          milestones={milestones}
          defaultProjectId={selectedId}
          defaultMilestoneId={activeMilestone?.id ?? null}
          onSave={saveTask}
          onDelete={deleteTask}
          onClose={() => setTaskEdit(undefined)}
        />
      )}
      {projectEdit !== undefined && (
        <ProjectPopup
          project={projectEdit}
          onSave={saveProject}
          onDelete={deleteProject}
          onClose={() => setProjectEdit(undefined)}
        />
      )}
      {milestoneEdit !== undefined && selectedId != null && (
        <MilestonePopup
          milestone={milestoneEdit}
          projectId={selectedId}
          onSave={saveMilestone}
          onDelete={deleteMilestone}
          onComplete={completeMilestone}
          onClose={() => setMilestoneEdit(undefined)}
        />
      )}
    </div>
  );
}

// Lista de tareas: las del milestone activo primero, luego el resto (backlog).
function TaskList({
  tasks, activeMilestoneId, onToggle, onOpen,
}: {
  tasks: Task[];
  activeMilestoneId: number | null;
  onToggle: (t: Task) => void;
  onOpen: (t: Task) => void;
}) {
  const shown = useMemo(() => {
    const inActive = tasks.filter((t) => activeMilestoneId != null && t.milestone_id === activeMilestoneId);
    const rest = tasks.filter((t) => activeMilestoneId == null || t.milestone_id !== activeMilestoneId);
    return activeMilestoneId != null ? [...inActive, ...rest] : tasks;
  }, [tasks, activeMilestoneId]);

  if (shown.length === 0) return <p className="text-xs text-ink-faint px-1 py-2">Sin tareas. Crea una con “+ Tarea”.</p>;

  return (
    <div className="flex flex-col gap-1">
      {shown.map((t) => {
        const done = DONE.has((t.status || "").toLowerCase());
        const check = t.checklist ?? [];
        return (
          <div key={t.id} className="group flex items-center gap-3 glass-surface rounded-xl px-3.5 py-2.5 hover:border-accent/25 border border-transparent transition-all">
            <button
              onClick={() => onToggle(t)}
              className={`h-4 w-4 rounded border flex items-center justify-center shrink-0 ${done ? "bg-accent/30 border-accent/50" : "border-base-600 hover:border-accent/50"}`}
              title={done ? "Marcar pendiente" : "Marcar hecha"}
            >
              {done && <span className="text-accent text-[10px]">✓</span>}
            </button>
            <button onClick={() => onOpen(t)} className="flex-1 min-w-0 text-left">
              <div className="flex items-center gap-2">
                <span className={`text-sm truncate ${done ? "line-through text-ink-faint" : "text-ink"}`}>{t.title}</span>
                {check.length > 0 && <span className="text-[10px] text-ink-faint shrink-0">☑ {check.filter((c) => c.done).length}/{check.length}</span>}
              </div>
            </button>
            <div className="flex items-center gap-2.5 shrink-0">
              {t.due_date && <span className="text-[11px] text-ink-faint tabular-nums">{t.due_date.slice(0, 10)}</span>}
              <span className={`h-2 w-2 rounded-full ${PRIORITY_DOT[t.priority] ?? "bg-ink-faint"}`} title={`Prioridad: ${t.priority}`} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
