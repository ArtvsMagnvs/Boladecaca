// pages/Workspace/ProjectCard.tsx — la tarjeta-ventana de un proyecto (V0.87 W2b)
//
// Chrome de ventana (header arrastrable + asas de resize + minimizar/expandir)
// alrededor del contenido de detalle que W2a construyo (cabecera/progreso/
// enlaces/milestones/tareas/actividad) — se traslada aqui, no se reescribe.
// Cada tarjeta carga sus propios milestones/tareas (lazy: solo si esta fuera
// de la estanteria), para no pedir datos de proyectos que el usuario no ha
// abierto. La seccion "Agentes" (W2c, AgentsSection) hace su propio fetch
// perezoso igual, con su propio umbral de tamano (iconos/completa).
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Project, type Task, type Milestone, type WorkspaceProgress } from "@/lib/api";
import { pct, MS_STATUS_LABEL } from "./shared";
import { TaskList } from "./TaskList";
import { TaskBoard, KANBAN_SHORTCUTS, type TaskColumnKey, type TaskUpdatePatch } from "./TaskBoard";
import { TaskPopup } from "./TaskPopup";
import { MilestonePopup } from "./MilestonePopup";
import { AgentsSection } from "./AgentsSection";
import { AutomationSection } from "./AutomationSection";
import { HelpButton, windowShortcuts } from "./HelpPanel";
import { useDragResize, MIN_CARD_W, MIN_CARD_H, type CardLayout, type Rect } from "./useWindowCard";

interface Props {
  project: Project;
  allProjects: Project[];
  layout: CardLayout;
  bounds: { width: number; height: number };
  onInteractStart: () => void;
  onCommit: (patch: Partial<CardLayout>) => void;
  onMinimize: () => void;
  onToggleExpanded: () => void;
  isOverShelf: (clientX: number, clientY: number) => boolean;
  onEditProject: () => void;
  onProjectsRefresh: () => void;
  // V0.87 (W4): abre (o trae al frente) la ventana-tarjeta del agente — ya
  // no es "fullscreen", el usuario la redimensiona como una ProjectCard.
  onOpenAgentWindow: (agentId: number) => void;
  agentsRefreshTick: number; // fuerza refetch de AgentsSection cuando cambia algo en la ventana del agente
}

export function ProjectCard({
  project, allProjects, layout, bounds, onInteractStart, onCommit,
  onMinimize, onToggleExpanded, isOverShelf, onEditProject, onProjectsRefresh,
  onOpenAgentWindow, agentsRefreshTick,
}: Props) {
  // Alto "en vivo" mientras se arrastra un asa de resize — separado del
  // layout.h ya confirmado (el que vive en el padre + localStorage). Pedido
  // explicito: el contenido se reorganiza MIENTRAS se redimensiona, no solo
  // al soltar. Se limpia en cuanto el gesto termina (handleCommit).
  const [liveH, setLiveH] = useState<number | null>(null);

  const handleCommit = useCallback(
    (patch: Partial<CardLayout>) => {
      setLiveH(null);
      onCommit(patch);
    },
    [onCommit],
  );

  const { nodeRef, headerHandlers, resizeHandlers } = useDragResize({
    layout, bounds, onCommit: handleCommit, onInteractStart,
    isOverShelf, onDropOnShelf: onMinimize,
    onLiveResize: useCallback((r: Rect) => setLiveH(r.h), []),
  });

  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [progress, setProgress] = useState<WorkspaceProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [taskEdit, setTaskEdit] = useState<Task | null | undefined>(undefined);
  const [milestoneEdit, setMilestoneEdit] = useState<Milestone | null | undefined>(undefined);
  // V0.87 (WPMS W3b): columna de origen del alta rápida desde el Kanban (tecla
  // "N" o el "+" de una columna) — la tarea nueva nace ya en esa columna.
  const [taskQuickStatus, setTaskQuickStatus] = useState<TaskColumnKey>("pending");
  // V0.87 (W4): panel de ayuda (?) de la cabecera — un solo estado, tanto el
  // botón visible como la tecla "?" del Kanban (delegada via onToggleHelp)
  // abren/cierran lo mismo.
  const [helpOpen, setHelpOpen] = useState(false);

  const activeMilestone = useMemo(
    () => milestones.find((m) => m.status === "active") ?? milestones[0] ?? null,
    [milestones],
  );

  const load = useCallback(async () => {
    const [ms, ts, prog] = await Promise.all([
      api.getMilestones(project.id),
      api.getTasks(0, 500),
      api.getWorkspaceProgress(project.id).catch(() => null),
    ]);
    setMilestones(ms);
    setTasks(ts.filter((t) => t.project_id === project.id));
    setProgress(prog);
    setLoading(false);
  }, [project.id]);

  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const saveTask = async (data: Partial<Task>) => {
    if (taskEdit) await api.updateTask(taskEdit.id, data);
    else await api.createTask({ ...data, project_id: project.id });
    setTaskEdit(undefined);
    await load();
    onProjectsRefresh(); // Project.progress vive fuera de esta tarjeta
  };
  const deleteTask = async (id: number) => {
    await api.deleteTask(id);
    setTaskEdit(undefined);
    await load();
    onProjectsRefresh();
  };
  const toggleTaskDone = async (t: Task) => {
    const done = t.status === "done" || t.status === "completed";
    await api.updateTask(t.id, { status: done ? "pending" : "completed" });
    await load();
    onProjectsRefresh();
  };
  // V0.87 (WPMS W3b): drag&drop en el board Kanban — TaskBoard ya calculó qué
  // tareas cambian de order_index/status; aquí solo se persiste y se recarga
  // desde el backend (fuente de verdad), mismo patrón no-optimista que el
  // resto del Workspace.
  const reorderTasks = async (updates: TaskUpdatePatch[]) => {
    await Promise.all(updates.map((u) => api.updateTask(u.id, { order_index: u.order_index, status: u.status })));
    await load();
    onProjectsRefresh(); // el status pudo cambiar a/desde "completed" -> afecta al progreso
  };
  const quickCreateTask = (status: TaskColumnKey) => {
    setTaskQuickStatus(status);
    setTaskEdit(null);
  };

  const saveMilestone = async (data: Partial<Milestone>) => {
    if (milestoneEdit) await api.updateMilestone(milestoneEdit.id, data);
    else await api.createMilestone(data);
    setMilestoneEdit(undefined);
    await load();
  };
  const deleteMilestone = async (id: number) => {
    await api.deleteMilestone(id);
    setMilestoneEdit(undefined);
    await load();
  };
  const completeMilestone = async (id: number) => {
    await api.completeMilestone(id);
    setMilestoneEdit(undefined);
    await load();
    onProjectsRefresh(); // current_version del proyecto cambia
  };

  const overallRatio = progress?.overall.ratio ?? project.progress ?? 0;
  const activeRatio = activeMilestone?.progress?.ratio ?? overallRatio;

  // Contenido adaptativo por tamano (pedido explicito del usuario): tarjeta
  // MUY pequena -> solo cabecera+progreso; PEQUENA -> +milestones+iconos de
  // agente; GRANDE/expandida -> +tareas+actividad+tarjetas de agente
  // completas+hueco de automatizaciones.
  const availableH = layout.expanded ? Infinity : (liveH ?? layout.h) - 56; // 56 ~ alto del header
  const showMilestones = layout.expanded || availableH > 140;
  const showAgentsIcons = layout.expanded || availableH > 140;
  const showAgentsFull = layout.expanded || availableH > 320;
  const showTasksAndActivity = layout.expanded || availableH > 320;

  const recentTasks = useMemo(
    () => [...tasks].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? "")).slice(0, 5),
    [tasks],
  );

  const rectStyle = layout.expanded
    ? undefined
    : { transform: `translate(${layout.x}px, ${layout.y}px)`, width: layout.w, height: layout.h, minWidth: MIN_CARD_W, minHeight: MIN_CARD_H };

  return (
    <div
      ref={nodeRef}
      className={`glass-surface rounded-2xl border border-base-700 shadow-glass flex flex-col overflow-hidden ${
        layout.expanded ? "absolute inset-0" : "absolute top-0 left-0"
      }`}
      style={{ ...rectStyle, zIndex: layout.zIndex }}
      onPointerDownCapture={onInteractStart}
    >
      {/* Header — asa de arrastre (solo si no esta expandida) */}
      <div
        {...(layout.expanded ? {} : headerHandlers)}
        onDoubleClick={onToggleExpanded}
        className={`flex items-center gap-2 px-3.5 py-2.5 border-b border-base-700/60 shrink-0 select-none ${
          layout.expanded ? "" : "cursor-grab active:cursor-grabbing"
        }`}
        title="Arrastra para mover · doble clic para expandir"
      >
        <div className="min-w-0 flex-1 flex items-center gap-2">
          <span className="text-sm font-semibold text-ink truncate">{project.name}</span>
          {project.current_version && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/12 text-accent shrink-0">v{project.current_version}</span>
          )}
        </div>
        <span onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
          <HelpButton
            open={helpOpen}
            onToggle={() => setHelpOpen((v) => !v)}
            extra={[...windowShortcuts(layout.expanded), ...(layout.expanded ? KANBAN_SHORTCUTS : [])]}
          />
        </span>
        <button onClick={(e) => { e.stopPropagation(); onEditProject(); }} className="text-ink-faint hover:text-ink text-xs px-1.5 shrink-0" title="Editar proyecto">✎</button>
        <button onClick={(e) => { e.stopPropagation(); onToggleExpanded(); }} className="text-ink-faint hover:text-ink text-xs px-1.5 shrink-0" title={layout.expanded ? "Restaurar" : "Expandir"}>
          {layout.expanded ? "⤡" : "⤢"}
        </button>
        <button onClick={(e) => { e.stopPropagation(); onMinimize(); }} className="text-ink-faint hover:text-ink text-sm px-1.5 shrink-0" title="Minimizar a la estantería">—</button>
      </div>

      {/* Cuerpo */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3.5 flex flex-col gap-3.5">
        {loading ? (
          <p className="text-xs text-ink-faint py-4">Cargando…</p>
        ) : (
          <>
            <div className="flex items-center justify-between gap-2">
              <button onClick={() => setTaskEdit(null)} className="text-xs px-2.5 py-1 bg-accent/15 text-accent rounded-lg border border-accent/30 hover:bg-accent/25">+ Tarea</button>
              <span className="text-[10px] text-ink-faint">{project.status}</span>
            </div>

            <div>
              <div className="flex justify-between items-center text-[11px] mb-1.5">
                <span className="text-ink-dim truncate">{activeMilestone ? activeMilestone.name : "Progreso"}</span>
                <span className="text-ink font-medium shrink-0 ml-2">
                  {activeMilestone?.progress ? `${activeMilestone.progress.done}/${activeMilestone.progress.total} · ` : ""}{pct(activeRatio)}%
                </span>
              </div>
              <div className="h-1.5 bg-base-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent/60 rounded-full transition-all" style={{ width: `${pct(activeRatio)}%` }} />
              </div>
            </div>

            {showMilestones && (
              <section>
                <div className="flex items-center justify-between mb-1.5">
                  <h3 className="text-xs font-medium text-ink-dim">Milestones</h3>
                  <button onClick={() => setMilestoneEdit(null)} className="text-[11px] text-accent hover:text-accent-soft">+ Milestone</button>
                </div>
                <div className="flex flex-col gap-1">
                  {milestones.map((m) => (
                    <button key={m.id} onClick={() => setMilestoneEdit(m)} className="text-left glass-surface rounded-lg px-2.5 py-1.5 hover:border-accent/30 border border-transparent transition-all">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className={`text-[9px] px-1 py-0.5 rounded shrink-0 ${m.status === "active" ? "bg-accent/15 text-accent" : m.status === "done" ? "bg-signal-ok/15 text-signal-ok" : "bg-base-700/60 text-ink-faint"}`}>{MS_STATUS_LABEL[m.status] ?? m.status}</span>
                          <span className="text-xs text-ink truncate">{m.name}</span>
                        </div>
                        {m.progress && <span className="text-[10px] text-ink-faint shrink-0 tabular-nums">{pct(m.progress.ratio)}%</span>}
                      </div>
                    </button>
                  ))}
                  {milestones.length === 0 && <p className="text-[11px] text-ink-faint px-1">Sin milestones.</p>}
                </div>
              </section>
            )}

            {/* Montada siempre (nunca condicionada a showAgentsIcons) y oculta por
                CSS cuando no toca mostrarla: el alto en vivo (liveH) puede cruzar
                el umbral muchas veces en un solo gesto de resize, y desmontar/
                remontar aqui dispararia el fetch de AgentsSection en cada cruce.
                Ocultar por CSS mantiene sus datos ya cargados entre umbrales. */}
            <div className={showAgentsIcons ? "" : "hidden"}>
              <AgentsSection
                projectId={project.id}
                size={showAgentsFull ? "full" : "icon"}
                onOpenAgent={onOpenAgentWindow}
                refreshTick={agentsRefreshTick}
              />
            </div>

            {showAgentsFull && <AutomationSection projectId={project.id} />}

            {showTasksAndActivity && (
              <>
                {/* V0.87 (WPMS W3b): el board Kanban necesita las 3 columnas
                    lado a lado — solo tiene sentido con el ancho completo del
                    lienzo (tarjeta expandida). Con la tarjeta compacta (alta
                    pero estrecha) la lista plana sigue siendo la vista. */}
                {layout.expanded ? (
                  <TaskBoard
                    tasks={tasks}
                    milestones={milestones}
                    onOpen={(t) => setTaskEdit(t)}
                    onQuickCreate={quickCreateTask}
                    onReorder={reorderTasks}
                    disabled={taskEdit !== undefined || milestoneEdit !== undefined}
                    onToggleHelp={() => setHelpOpen((v) => !v)}
                  />
                ) : (
                  <section>
                    <h3 className="text-xs font-medium text-ink-dim mb-1.5">
                      Tareas {activeMilestone ? <span className="text-ink-faint font-normal">· {activeMilestone.name}</span> : ""}
                    </h3>
                    <TaskList tasks={tasks} activeMilestoneId={activeMilestone?.id ?? null} onToggle={toggleTaskDone} onOpen={(t) => setTaskEdit(t)} />
                  </section>
                )}

                {recentTasks.length > 0 && (
                  <section>
                    <h3 className="text-xs font-medium text-ink-dim mb-1.5">Actividad reciente</h3>
                    <div className="flex flex-col gap-1">
                      {recentTasks.map((t) => (
                        <div key={t.id} className="text-[11px] text-ink-faint flex items-center gap-2">
                          <span className={`h-1.5 w-1.5 rounded-full ${t.status === "done" || t.status === "completed" ? "bg-signal-ok" : "bg-ink-faint/50"}`} />
                          <span className="truncate text-ink-dim">{t.title}</span>
                          <span className="ml-auto shrink-0">{(t.updated_at ?? "").slice(0, 10)}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )}
      </div>

      {/* Asas de resize — las 8 (4 bordes + 4 esquinas), solo cuando no esta
          expandida. Los bordes dejan un hueco de 12px en cada punta para que
          las esquinas (encima, sin solaparse) tengan su propia zona de clic. */}
      {!layout.expanded && (
        <>
          <div {...resizeHandlers.n} className="absolute top-0 left-3 right-3 h-2 cursor-ns-resize" />
          <div {...resizeHandlers.s} className="absolute bottom-0 left-3 right-3 h-2 cursor-ns-resize" />
          <div {...resizeHandlers.w} className="absolute left-0 top-3 bottom-3 w-2 cursor-ew-resize" />
          <div {...resizeHandlers.e} className="absolute right-0 top-3 bottom-3 w-2 cursor-ew-resize" />
          <div {...resizeHandlers.nw} className="absolute top-0 left-0 w-3 h-3 cursor-nwse-resize" />
          <div {...resizeHandlers.ne} className="absolute top-0 right-0 w-3 h-3 cursor-nesw-resize" />
          <div {...resizeHandlers.sw} className="absolute bottom-0 left-0 w-3 h-3 cursor-nesw-resize" />
          <div {...resizeHandlers.se} className="absolute bottom-0 right-0 w-3 h-3 cursor-nwse-resize" />
        </>
      )}

      {taskEdit !== undefined && (
        <TaskPopup
          task={taskEdit}
          projects={allProjects}
          milestones={milestones}
          defaultProjectId={project.id}
          defaultMilestoneId={activeMilestone?.id ?? null}
          defaultStatus={taskQuickStatus}
          onSave={saveTask}
          onDelete={deleteTask}
          onClose={() => { setTaskEdit(undefined); setTaskQuickStatus("pending"); }}
        />
      )}
      {milestoneEdit !== undefined && (
        <MilestonePopup
          milestone={milestoneEdit}
          projectId={project.id}
          onSave={saveMilestone}
          onDelete={deleteMilestone}
          onComplete={completeMilestone}
          onClose={() => setMilestoneEdit(undefined)}
        />
      )}
    </div>
  );
}
