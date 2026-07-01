import { useState, useEffect } from "react";
import { api, type Project } from "@/lib/api";

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  useEffect(() => {
    api.getProjects().then(setProjects).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const created = await api.createProject({ name: newName, description: newDesc, status: "active", progress: 0 });
      setProjects(prev => [...prev, created]);
      setNewName("");
      setNewDesc("");
      setShowForm(false);
    } catch {}
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteProject(id);
      setProjects(prev => prev.filter(p => p.id !== id));
    } catch {}
  };

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-ink">Proyectos</h1>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30 hover:bg-accent/25">
          + Nuevo proyecto
        </button>
      </div>

      {showForm && (
        <div className="glass-surface rounded-2xl p-4 flex flex-col gap-3">
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nombre del proyecto" className="bg-base-800 border border-base-700 rounded-xl px-4 py-2 text-sm text-ink placeholder:text-ink-faint" />
          <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Descripción (opcional)" rows={2} className="bg-base-800 border border-base-700 rounded-xl px-4 py-2 text-sm text-ink placeholder:text-ink-faint resize-none" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30">Crear</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 bg-base-700/50 text-ink-dim rounded-xl text-sm">Cancelar</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="text-center text-ink-dim py-10">Cargando...</div>
        ) : projects.length === 0 ? (
          <div className="text-center text-ink-dim py-10">No hay proyectos. Crea uno con el botón de arriba.</div>
        ) : (
          <div className="grid gap-4">
            {projects.map(p => (
              <div key={p.id} className="glass-surface rounded-2xl p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-ink">{p.name}</h3>
                    <p className="text-sm text-ink-dim mt-1">{p.description || "Sin descripción"}</p>
                  </div>
                  <button onClick={() => handleDelete(p.id)} className="text-signal-error/60 hover:text-signal-error text-sm">Eliminar</button>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-ink-faint mb-1">
                    <span>Progreso</span>
                    <span>{Math.round(p.progress * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-base-700 rounded-full overflow-hidden">
                    <div className="h-full bg-accent/60 rounded-full" style={{ width: `${p.progress * 100}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
