// pages/Workspace/MilestonePopup.tsx — editor de milestone (V0.87 WPMS W2a)
//
// El milestone es el eje de versión (doc 18 §3.4). "Completar" propaga la
// versión al proyecto y activa el siguiente (versionado, §6) — acción explícita.
import { useState } from "react";
import type { Milestone } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";

const STATUSES = [
  { value: "planned", label: "Planificado" },
  { value: "active", label: "Activo" },
  { value: "done", label: "Completado" },
  { value: "archived", label: "Archivado" },
];

interface Props {
  milestone: Milestone | null; // null = crear
  projectId: number;
  onSave: (data: Partial<Milestone>) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  onComplete?: (id: number) => Promise<void>;
  onClose: () => void;
}

export function MilestonePopup({ milestone, projectId, onSave, onDelete, onComplete, onClose }: Props) {
  const [name, setName] = useState(milestone?.name ?? "");
  const [version, setVersion] = useState(milestone?.version ?? "");
  const [description, setDescription] = useState(milestone?.description ?? "");
  const [status, setStatus] = useState(milestone?.status ?? "planned");
  const [targetDate, setTargetDate] = useState((milestone?.target_date ?? "").slice(0, 10));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        project_id: projectId,
        name: name.trim(),
        version: version || null,
        description: description || null,
        status,
        target_date: targetDate ? new Date(targetDate).toISOString() : null,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el milestone.");
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!milestone || !onComplete) return;
    setSaving(true);
    setError(null);
    try {
      await onComplete(milestone.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar el milestone.");
    } finally {
      setSaving(false);
    }
  };

  const canComplete = milestone && milestone.status !== "done" && onComplete;

  return (
    <Modal
      title={milestone ? "Editar milestone" : "Nuevo milestone"}
      onClose={onClose}
      footer={
        <>
          {milestone && onDelete && (
            <button onClick={() => onDelete(milestone.id)} className="mr-auto px-3 py-2 text-signal-error/70 hover:text-signal-error text-sm">
              Eliminar
            </button>
          )}
          {canComplete && (
            <button onClick={handleComplete} disabled={saving} className="px-3 py-2 text-signal-ok/80 hover:text-signal-ok text-sm border border-signal-ok/30 rounded-xl disabled:opacity-40">
              ✓ Completar
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
        <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} placeholder="p.ej. V0.9 — Automation Engine" autoFocus />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>Versión</label>
          <input value={version ?? ""} onChange={(e) => setVersion(e.target.value)} className={fieldInput} placeholder="0.9" />
        </div>
        <div>
          <label className={fieldLabel}>Estado</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldInput}>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div className="col-span-2">
          <label className={fieldLabel}>Fecha objetivo</label>
          <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} className={fieldInput} />
        </div>
      </div>
      <div>
        <label className={fieldLabel}>Objetivo de la versión</label>
        <textarea value={description ?? ""} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder="Qué entrega esta versión" />
      </div>
      {milestone?.status === "done" && (
        <p className="text-xs text-signal-ok/80">Este milestone está completado.</p>
      )}
    </Modal>
  );
}
