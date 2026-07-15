// pages/Workspace/ProjectPopup.tsx — editor de proyecto (V0.87 WPMS W2a)
import { useState } from "react";
import type { Project, ProjectDoc } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";

const STATUSES = [
  { value: "active", label: "Activo" },
  { value: "paused", label: "Pausado" },
  { value: "done", label: "Terminado" },
];

interface Props {
  project: Project | null; // null = crear
  onSave: (data: Partial<Project>) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  onClose: () => void;
}

export function ProjectPopup({ project, onSave, onDelete, onClose }: Props) {
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [status, setStatus] = useState(project?.status ?? "active");
  const [currentVersion, setCurrentVersion] = useState(project?.current_version ?? "");
  const [targetVersion, setTargetVersion] = useState(project?.target_version ?? "");
  const [repoPath, setRepoPath] = useState(project?.repo_path ?? "");
  const [tags, setTags] = useState((project?.tags ?? []).join(", "));
  const [docs, setDocs] = useState<ProjectDoc[]>(project?.docs ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addDoc = () => setDocs((prev) => [...prev, { label: "", kind: "url", url_or_path: "" }]);
  const setDoc = (i: number, patch: Partial<ProjectDoc>) =>
    setDocs((prev) => prev.map((d, j) => (j === i ? { ...d, ...patch } : d)));

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        description: description || null,
        status,
        current_version: currentVersion || null,
        target_version: targetVersion || null,
        repo_path: repoPath || null,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        docs: docs.filter((d) => d.label.trim() && d.url_or_path.trim()),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el proyecto.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={project ? "Editar proyecto" : "Nuevo proyecto"}
      onClose={onClose}
      footer={
        <>
          {project && onDelete && (
            <button onClick={() => onDelete(project.id)} className="mr-auto px-3 py-2 text-signal-error/70 hover:text-signal-error text-sm">
              Eliminar
            </button>
          )}
          <button onClick={onClose} className={btnGhost}>Cancelar</button>
          <button onClick={handleSave} disabled={!name.trim() || saving} className={btnPrimary}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </>
      }
    >
      <ErrorBanner message={error} />
      <div>
        <label className={fieldLabel}>Nombre</label>
        <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} placeholder="Nombre del proyecto" autoFocus />
      </div>
      <div>
        <label className={fieldLabel}>Descripción</label>
        <textarea value={description ?? ""} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder="1-2 líneas" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>Estado</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldInput}>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Ruta del repo</label>
          <input value={repoPath ?? ""} onChange={(e) => setRepoPath(e.target.value)} className={fieldInput} placeholder="C:/repos/…" />
        </div>
        <div>
          <label className={fieldLabel}>Versión actual</label>
          <input value={currentVersion ?? ""} onChange={(e) => setCurrentVersion(e.target.value)} className={fieldInput} placeholder="0.8.7" />
        </div>
        <div>
          <label className={fieldLabel}>Versión objetivo</label>
          <input value={targetVersion ?? ""} onChange={(e) => setTargetVersion(e.target.value)} className={fieldInput} placeholder="0.9" />
        </div>
      </div>
      <div>
        <label className={fieldLabel}>Tags (separados por coma)</label>
        <input value={tags} onChange={(e) => setTags(e.target.value)} className={fieldInput} placeholder="ai, desktop, backend" />
      </div>
      <div>
        <label className={fieldLabel}>Enlaces / docs</label>
        <div className="flex flex-col gap-2">
          {docs.map((d, i) => (
            <div key={i} className="flex gap-2 group">
              <input value={d.label} onChange={(e) => setDoc(i, { label: e.target.value })} className={`${fieldInput} py-1.5 w-1/3`} placeholder="etiqueta" />
              <input value={d.url_or_path} onChange={(e) => setDoc(i, { url_or_path: e.target.value })} className={`${fieldInput} py-1.5 flex-1`} placeholder="url o ruta" />
              <button onClick={() => setDocs((prev) => prev.filter((_, j) => j !== i))} className="text-ink-faint hover:text-signal-error px-1">×</button>
            </div>
          ))}
          <button onClick={addDoc} className={`${btnGhost} self-start`}>+ Añadir enlace</button>
        </div>
      </div>
    </Modal>
  );
}
