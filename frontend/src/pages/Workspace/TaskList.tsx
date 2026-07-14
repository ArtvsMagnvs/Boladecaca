// pages/Workspace/TaskList.tsx — lista de tareas del milestone activo primero,
// luego el resto (backlog). Extraida de index.tsx en W2b para vivir dentro del
// cuerpo de ProjectCard (V0.87 W2b) sin duplicar logica.
import { useMemo } from "react";
import type { Task } from "@/lib/api";
import { DONE_STATUSES, PRIORITY_DOT } from "./shared";

export function TaskList({
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
        const done = DONE_STATUSES.has((t.status || "").toLowerCase());
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
