// pages/Workspace/TaskBoard.tsx — board Kanban de tareas (V0.87 WPMS W3b)
//
// Solo se monta cuando la ProjectCard está expandida (ancho completo del
// lienzo, ver ProjectCard.tsx) — con la tarjeta compacta el TaskList plano
// sigue siendo la vista, 3 columnas no caben con sentido en poco ancho.
//
// Arrastre: mismo patrón que AgentsSection.tsx (Pointer Events nativos, sin
// librería — doc 16 principio 5), extendido de 1 a 3 columnas. `colsRef`
// espeja el estado en un ref (igual que `orderRef` en AgentsSection) para
// que `endDrag` lea SIEMPRE el valor más reciente sin closures obsoletas —
// ya se demostró necesario en esta misma sección de la app.
//
// Persistencia: al soltar, solo se renumera `order_index` de la columna de
// DESTINO (la de origen no necesita renumerarse — quitar un elemento no
// rompe el orden relativo de los que quedan). El estado local es optimista
// para el gesto; el padre (ProjectCard) recarga desde el backend después,
// que es la fuente de verdad — mismo patrón no-optimista que el resto del
// Workspace (crear/editar siempre termina en un `load()`).
import { useCallback, useEffect, useRef, useState } from "react";
import type { Task, Milestone } from "@/lib/api";
import { PRIORITY_DOT } from "./shared";

const CLICK_THRESHOLD_PX = 5;

export type TaskColumnKey = "pending" | "in_progress" | "completed";
const COLUMNS: Array<{ key: TaskColumnKey; label: string }> = [
  { key: "pending", label: "Pendiente" },
  { key: "in_progress", label: "En progreso" },
  { key: "completed", label: "Hecha" },
];
const COLUMN_KEYS = COLUMNS.map((c) => c.key);

function statusToColumn(status: string | null | undefined): TaskColumnKey {
  const s = (status || "").toLowerCase();
  if (s === "in_progress") return "in_progress";
  if (s === "completed" || s === "done") return "completed";
  return "pending";
}

function groupTasks(tasks: Task[]): Record<TaskColumnKey, Task[]> {
  const cols: Record<TaskColumnKey, Task[]> = { pending: [], in_progress: [], completed: [] };
  for (const t of tasks) cols[statusToColumn(t.status)].push(t);
  for (const k of COLUMN_KEYS) {
    cols[k].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0) || a.id - b.id);
  }
  return cols;
}

export interface TaskUpdatePatch {
  id: number;
  order_index?: number;
  status?: string;
}

interface Props {
  tasks: Task[];
  milestones: Milestone[];
  onOpen: (t: Task) => void;
  onQuickCreate: (status: TaskColumnKey) => void;
  onReorder: (updates: TaskUpdatePatch[]) => Promise<void>;
  // true mientras hay un popup abierto encima (TaskPopup/MilestonePopup) —
  // los atajos de teclado se pausan para no competir con lo que se escribe ahi.
  disabled: boolean;
}

const SHORTCUTS: Array<[string, string]> = [
  ["N", "Nueva tarea (en la columna seleccionada)"],
  ["Enter", "Abrir la tarea seleccionada"],
  ["↑ / ↓", "Moverse dentro de la columna"],
  ["← / →", "Cambiar de columna"],
  ["1 / 2 / 3", "Mover la tarea seleccionada a Pendiente / En progreso / Hecha"],
  ["?", "Mostrar/ocultar esta ayuda"],
  ["Arrastrar", "Mover una tarjeta entre columnas o reordenarla"],
];

export function TaskBoard({ tasks, milestones, onOpen, onQuickCreate, onReorder, disabled }: Props) {
  const [cols, setCols] = useState<Record<TaskColumnKey, Task[]>>(() => groupTasks(tasks));
  const colsRef = useRef(cols);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  const columnRefs = useRef<Record<TaskColumnKey, HTMLDivElement | null>>({
    pending: null, in_progress: null, completed: null,
  });
  const dragState = useRef<{ id: number; originalStatus: string; startX: number; startY: number; moved: boolean } | null>(null);
  const boardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const grouped = groupTasks(tasks);
    colsRef.current = grouped;
    setCols(grouped);
  }, [tasks]);

  useEffect(() => {
    if (!disabled) boardRef.current?.focus();
  }, [disabled]);

  const milestoneName = useCallback(
    (id: number | null | undefined) => (id != null ? milestones.find((m) => m.id === id)?.name : undefined),
    [milestones],
  );

  const onPointerMove = useCallback((e: PointerEvent) => {
    const d = dragState.current;
    if (!d) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.moved && Math.hypot(dx, dy) > CLICK_THRESHOLD_PX) d.moved = true;
    if (!d.moved) return;

    let targetCol: TaskColumnKey | null = null;
    for (const k of COLUMN_KEYS) {
      const el = columnRefs.current[k];
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (e.clientX >= r.left && e.clientX <= r.right) { targetCol = k; break; }
    }
    if (!targetCol) return;

    const draggedTask = COLUMN_KEYS.map((k) => colsRef.current[k]).flat().find((t) => t.id === d.id);
    if (!draggedTask) return;

    const withoutDragged: Record<TaskColumnKey, Task[]> = {
      pending: colsRef.current.pending.filter((t) => t.id !== d.id),
      in_progress: colsRef.current.in_progress.filter((t) => t.id !== d.id),
      completed: colsRef.current.completed.filter((t) => t.id !== d.id),
    };

    const containerEl = columnRefs.current[targetCol];
    const cardEls = containerEl ? [...containerEl.querySelectorAll<HTMLElement>("[data-task-id]")] : [];
    let insertIdx = withoutDragged[targetCol].length;
    for (let i = 0; i < cardEls.length; i++) {
      const r = cardEls[i].getBoundingClientRect();
      if (e.clientY < r.top + r.height / 2) { insertIdx = i; break; }
    }
    withoutDragged[targetCol] = [
      ...withoutDragged[targetCol].slice(0, insertIdx),
      { ...draggedTask, status: targetCol },
      ...withoutDragged[targetCol].slice(insertIdx),
    ];

    colsRef.current = withoutDragged;
    setCols(withoutDragged);
  }, []);

  const endDrag = useCallback(async () => {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", endDrag);
    const d = dragState.current;
    dragState.current = null;
    setDraggingId(null);
    if (!d?.moved) return;

    const finalCol = COLUMN_KEYS.find((k) => colsRef.current[k].some((t) => t.id === d.id));
    if (!finalCol) return;

    const updates: TaskUpdatePatch[] = [];
    colsRef.current[finalCol].forEach((t, i) => {
      const patch: TaskUpdatePatch = { id: t.id };
      let dirty = false;
      if ((t.order_index ?? -1) !== i) { patch.order_index = i; dirty = true; }
      if (t.id === d.id && statusToColumn(d.originalStatus) !== finalCol) {
        patch.status = finalCol;
        dirty = true;
      }
      if (dirty) updates.push(patch);
    });
    if (updates.length > 0) await onReorder(updates);
  }, [onPointerMove, onReorder]);

  const startDrag = (t: Task) => (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    dragState.current = { id: t.id, originalStatus: t.status, startX: e.clientX, startY: e.clientY, moved: false };
    setSelected(t.id);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endDrag);
  };

  const moveSelectedToColumn = async (dest: TaskColumnKey) => {
    if (selected == null) return;
    const current = COLUMN_KEYS.find((k) => colsRef.current[k].some((t) => t.id === selected));
    if (!current || current === dest) return;
    await onReorder([{ id: selected, status: dest, order_index: colsRef.current[dest].length }]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (e.key === "?") { e.preventDefault(); setHelpOpen((v) => !v); return; }
    if (e.key === "n" || e.key === "N") {
      e.preventDefault();
      const col = selected != null ? COLUMN_KEYS.find((k) => cols[k].some((t) => t.id === selected)) : null;
      onQuickCreate(col ?? "pending");
      return;
    }
    if (e.key === "Enter") {
      const t = COLUMN_KEYS.map((k) => cols[k]).flat().find((t) => t.id === selected);
      if (t) { e.preventDefault(); onOpen(t); }
      return;
    }
    if (["1", "2", "3"].includes(e.key)) {
      e.preventDefault();
      moveSelectedToColumn(COLUMN_KEYS[Number(e.key) - 1]);
      return;
    }
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
      e.preventDefault();
      const curCol = selected != null ? COLUMN_KEYS.find((k) => cols[k].some((t) => t.id === selected)) : null;
      if (!curCol) {
        for (const k of COLUMN_KEYS) { if (cols[k].length > 0) { setSelected(cols[k][0].id); break; } }
        return;
      }
      const list = cols[curCol];
      const idx = list.findIndex((t) => t.id === selected);
      if (e.key === "ArrowUp" && idx > 0) setSelected(list[idx - 1].id);
      else if (e.key === "ArrowDown" && idx < list.length - 1) setSelected(list[idx + 1].id);
      else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        const colIdx = COLUMN_KEYS.indexOf(curCol);
        const nextColIdx = e.key === "ArrowLeft" ? colIdx - 1 : colIdx + 1;
        if (nextColIdx >= 0 && nextColIdx < COLUMN_KEYS.length) {
          const nextList = cols[COLUMN_KEYS[nextColIdx]];
          if (nextList.length > 0) setSelected(nextList[Math.min(idx, nextList.length - 1)].id);
        }
      }
    }
  };

  return (
    <div
      ref={boardRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="outline-none relative"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-ink-dim">Tareas</h3>
        <button
          onClick={() => setHelpOpen((v) => !v)}
          className="h-5 w-5 rounded-full border border-base-700 text-[10px] text-ink-faint hover:border-accent/40 hover:text-accent flex items-center justify-center"
          title="Atajos de teclado"
        >
          ?
        </button>
      </div>

      {helpOpen && (
        <div className="absolute top-7 right-0 z-20 glass-surface rounded-xl border border-base-700 p-3 w-64 shadow-glass">
          <p className="text-[10px] uppercase tracking-wide text-ink-faint mb-2">Atajos de teclado</p>
          <div className="flex flex-col gap-1.5">
            {SHORTCUTS.map(([key, desc]) => (
              <div key={key} className="flex items-start gap-2 text-[11px]">
                <span className="shrink-0 px-1.5 py-0.5 rounded bg-base-700/60 text-ink-dim font-mono">{key}</span>
                <span className="text-ink-faint">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        {COLUMNS.map(({ key, label }) => (
          <div key={key} className="flex flex-col gap-2 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-ink-dim">{label}</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-ink-faint tabular-nums">{cols[key].length}</span>
                <button
                  onClick={() => onQuickCreate(key)}
                  className="text-[11px] text-accent hover:text-accent-soft leading-none"
                  title={`Nueva tarea en ${label}`}
                >
                  +
                </button>
              </div>
            </div>
            <div
              ref={(el) => { columnRefs.current[key] = el; }}
              data-column={key}
              className="flex flex-col gap-1.5 min-h-[40px] rounded-xl p-1 bg-base-900/30"
            >
              {cols[key].map((t) => {
                const check = t.checklist ?? [];
                const ms = milestoneName(t.milestone_id);
                return (
                  <div
                    key={t.id}
                    data-task-id={t.id}
                    onPointerDown={startDrag(t)}
                    onClick={() => { setSelected(t.id); onOpen(t); }}
                    className={`glass-surface rounded-lg px-2.5 py-2 cursor-pointer border transition-all ${
                      selected === t.id ? "border-accent/50" : "border-transparent hover:border-accent/25"
                    } ${draggingId === t.id ? "opacity-50" : ""}`}
                  >
                    <div className="flex items-start gap-1.5">
                      <span className={`h-2 w-2 rounded-full shrink-0 mt-0.5 ${PRIORITY_DOT[t.priority] ?? "bg-ink-faint"}`} title={`Prioridad: ${t.priority}`} />
                      <span className="text-xs text-ink flex-1 min-w-0 break-words">{t.title}</span>
                    </div>
                    {(ms || check.length > 0 || t.due_date) && (
                      <div className="flex items-center gap-2 mt-1 pl-3.5 text-[10px] text-ink-faint">
                        {ms && <span className="truncate">{ms}</span>}
                        {check.length > 0 && <span className="shrink-0">☑ {check.filter((c) => c.done).length}/{check.length}</span>}
                        {t.due_date && <span className="shrink-0 tabular-nums ml-auto">{t.due_date.slice(0, 10)}</span>}
                      </div>
                    )}
                  </div>
                );
              })}
              {cols[key].length === 0 && (
                <p className="text-[10.5px] text-ink-faint px-1 py-2 text-center">Sin tareas.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
