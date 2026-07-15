// pages/Workspace/TaskPopup.tsx — editor de tarea, ratón primero (V0.87 W2a)
//
// TODO editable con el ratón (selects/inputs/checkboxes normales); el teclado
// solo hace falta para escribir texto. Crear (task=null) o editar. El popup
// nunca saca de contexto (doc 18 §9.2). El board/drag&drop es W2b.
import { useState } from "react";
import type { Task, Milestone, Project, ChecklistItem, TaskLinks } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";

const STATUSES = [
  { value: "pending", label: "Pendiente" },
  { value: "in_progress", label: "En progreso" },
  { value: "completed", label: "Hecha" },
];
const PRIORITIES = [
  { value: "low", label: "Baja" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
];

interface Props {
  task: Task | null; // null = crear
  projects: Project[];
  milestones: Milestone[]; // del proyecto activo
  defaultProjectId?: number | null;
  defaultMilestoneId?: number | null;
  onSave: (data: Partial<Task>) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  onClose: () => void;
}

function isoDateInput(value?: string | null): string {
  if (!value) return "";
  return value.slice(0, 10); // YYYY-MM-DD
}

export function TaskPopup({
  task, projects, milestones, defaultProjectId, defaultMilestoneId, onSave, onDelete, onClose,
}: Props) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [status, setStatus] = useState(task?.status ?? "pending");
  const [priority, setPriority] = useState(task?.priority ?? "medium");
  const [projectId, setProjectId] = useState<number | null>(task?.project_id ?? defaultProjectId ?? null);
  const [milestoneId, setMilestoneId] = useState<number | null>(task?.milestone_id ?? defaultMilestoneId ?? null);
  const [dueDate, setDueDate] = useState(isoDateInput(task?.due_date));
  const [estimate, setEstimate] = useState(task?.estimate ?? "");
  const [checklist, setChecklist] = useState<ChecklistItem[]>(task?.checklist ?? []);
  const [newItem, setNewItem] = useState("");
  const [links, setLinks] = useState<TaskLinks>(task?.links ?? {});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setLink = (key: string, value: string) =>
    setLinks((prev) => {
      const next = { ...prev };
      if (value.trim()) next[key] = value;
      else delete next[key];
      return next;
    });

  const addChecklistItem = () => {
    const text = newItem.trim();
    if (!text) return;
    setChecklist((prev) => [...prev, { text, done: false }]);
    setNewItem("");
  };

  const handleSave = async () => {
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        title: title.trim(),
        description: description || null,
        status,
        priority,
        project_id: projectId,
        milestone_id: milestoneId,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        estimate: estimate || null,
        checklist,
        links,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la tarea.");
    } finally {
      setSaving(false);
    }
  };

  const doneCount = checklist.filter((c) => c.done).length;

  return (
    <Modal
      title={task ? "Editar tarea" : "Nueva tarea"}
      onClose={onClose}
      footer={
        <>
          {task && onDelete && (
            <button
              onClick={() => onDelete(task.id)}
              className="mr-auto px-3 py-2 text-signal-error/70 hover:text-signal-error text-sm"
            >
              Eliminar
            </button>
          )}
          <button onClick={onClose} className={btnGhost}>Cancelar</button>
          <button onClick={handleSave} disabled={!title.trim() || saving} className={btnPrimary}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </>
      }
    >
      <ErrorBanner message={error} />
      <div>
        <label className={fieldLabel}>Título</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} className={fieldInput} placeholder="¿Qué hay que hacer?" autoFocus />
      </div>

      <div>
        <label className={fieldLabel}>Descripción</label>
        <textarea value={description ?? ""} onChange={(e) => setDescription(e.target.value)} rows={3} className={`${fieldInput} resize-none`} placeholder="Detalle (opcional)" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>Estado</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldInput}>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Prioridad</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className={fieldInput}>
            {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Proyecto</label>
          <select
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
            className={fieldInput}
          >
            <option value="">— sin proyecto —</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Milestone</label>
          <select
            value={milestoneId ?? ""}
            onChange={(e) => setMilestoneId(e.target.value ? Number(e.target.value) : null)}
            className={fieldInput}
          >
            <option value="">— backlog —</option>
            {milestones.map((m) => <option key={m.id} value={m.id}>{m.name}{m.version ? ` (${m.version})` : ""}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Fecha límite</label>
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className={fieldInput} />
        </div>
        <div>
          <label className={fieldLabel}>Estimación</label>
          <input value={estimate ?? ""} onChange={(e) => setEstimate(e.target.value)} className={fieldInput} placeholder="p.ej. 2 sesiones" />
        </div>
      </div>

      {/* Checklist — subtareas ligeras (no cuentan para el progreso, doc 18 §8) */}
      <div>
        <label className={fieldLabel}>Checklist {checklist.length > 0 && <span className="text-ink-faint normal-case">· {doneCount}/{checklist.length}</span>}</label>
        <div className="flex flex-col gap-1.5">
          {checklist.map((item, i) => (
            <div key={i} className="flex items-center gap-2 group">
              <input
                type="checkbox"
                checked={item.done}
                onChange={() => setChecklist((prev) => prev.map((c, j) => j === i ? { ...c, done: !c.done } : c))}
                className="accent-accent h-4 w-4 shrink-0"
              />
              <span className={`flex-1 text-sm ${item.done ? "line-through text-ink-faint" : "text-ink-dim"}`}>{item.text}</span>
              <button onClick={() => setChecklist((prev) => prev.filter((_, j) => j !== i))} className="text-ink-faint hover:text-signal-error opacity-0 group-hover:opacity-100 text-sm px-1">×</button>
            </div>
          ))}
          <div className="flex gap-2 mt-1">
            <input
              value={newItem}
              onChange={(e) => setNewItem(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addChecklistItem(); } }}
              className={`${fieldInput} py-1.5`}
              placeholder="Añadir subtarea…"
            />
            <button onClick={addChecklistItem} className={btnGhost}>+</button>
          </div>
        </div>
      </div>

      {/* Links — traza al trabajo real (doc 18 §3.5) */}
      <div>
        <label className={fieldLabel}>Enlaces (opcional)</label>
        <div className="grid grid-cols-2 gap-2">
          <input value={links.commit ?? ""} onChange={(e) => setLink("commit", e.target.value)} className={`${fieldInput} py-1.5`} placeholder="commit" />
          <input value={links.pr ?? ""} onChange={(e) => setLink("pr", e.target.value)} className={`${fieldInput} py-1.5`} placeholder="PR" />
          <input value={links.mission_id ?? ""} onChange={(e) => setLink("mission_id", e.target.value)} className={`${fieldInput} py-1.5`} placeholder="mission_id (TIE)" />
          <input value={links.decision ?? ""} onChange={(e) => setLink("decision", e.target.value)} className={`${fieldInput} py-1.5`} placeholder="decisión" />
        </div>
      </div>
    </Modal>
  );
}
