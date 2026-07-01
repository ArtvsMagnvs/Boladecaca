import { useState, useEffect } from "react";
import { api, type Task } from "@/lib/api";

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  useEffect(() => {
    api.getTasks().then(setTasks).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      const created = await api.createTask({ title: newTitle, status: "pending", priority: "medium" });
      setTasks(prev => [...prev, created]);
      setNewTitle("");
      setShowForm(false);
    } catch {}
  };

  const handleToggle = async (task: Task) => {
    try {
      const newStatus = task.status === "completed" ? "pending" : "completed";
      await api.updateTask(task.id, { status: newStatus });
      setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: newStatus } : t));
    } catch {}
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTask(id);
      setTasks(prev => prev.filter(t => t.id !== id));
    } catch {}
  };

  const priorityColors: Record<string, string> = { high: "text-signal-error", medium: "text-signal-warn", low: "text-signal-ok" };

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-ink">Tareas</h1>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30 hover:bg-accent/25">
          + Nueva tarea
        </button>
      </div>

      {showForm && (
        <div className="glass-surface rounded-2xl p-4 flex gap-3">
          <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Nombre de la tarea" className="flex-1 bg-base-800 border border-base-700 rounded-xl px-4 py-2 text-sm text-ink placeholder:text-ink-faint" onKeyDown={e => e.key === "Enter" && handleCreate()} />
          <button onClick={handleCreate} className="px-4 py-2 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30">Crear</button>
          <button onClick={() => setShowForm(false)} className="px-4 py-2 bg-base-700/50 text-ink-dim rounded-xl text-sm">Cancelar</button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="text-center text-ink-dim py-10">Cargando...</div>
        ) : tasks.length === 0 ? (
          <div className="text-center text-ink-dim py-10">No hay tareas. Crea una con el botón de arriba.</div>
        ) : (
          <div className="flex flex-col gap-2">
            {tasks.map(task => (
              <div key={task.id} className="glass-surface rounded-xl p-4 flex items-center gap-4">
                <button onClick={() => handleToggle(task)} className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ${task.status === "completed" ? "bg-accent/30 border-accent/50" : "border-base-600"}`}>
                  {task.status === "completed" && <span className="text-accent text-xs">✓</span>}
                </button>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${task.status === "completed" ? "line-through text-ink-dim" : "text-ink"}`}>{task.title}</p>
                  {task.description && <p className="text-xs text-ink-faint mt-0.5 truncate">{task.description}</p>}
                </div>
                <span className={`text-[10px] font-medium uppercase tracking-wider shrink-0 ${priorityColors[task.priority] || "text-ink-faint"}`}>{task.priority}</span>
                <button onClick={() => handleDelete(task.id)} className="text-signal-error/60 hover:text-signal-error text-xs shrink-0">×</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
