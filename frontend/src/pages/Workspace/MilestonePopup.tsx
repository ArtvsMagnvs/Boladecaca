// pages/Workspace/MilestonePopup.tsx — editor de milestone (V0.87 WPMS W2a)
//
// El milestone es el eje de versión (doc 18 §3.4). "Completar" propaga la
// versión al proyecto y activa el siguiente (versionado, §6) — acción explícita.
import { useState } from "react";
import type { Milestone } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";
import { MS_STATUS_KEY } from "./shared";
import { useT } from "@/store/useI18n";

const STATUSES = [
  { value: "planned", labelKey: MS_STATUS_KEY.planned },
  { value: "active", labelKey: MS_STATUS_KEY.active },
  { value: "done", labelKey: MS_STATUS_KEY.done },
  { value: "archived", labelKey: MS_STATUS_KEY.archived },
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
  const tr = useT();
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
      setError(e instanceof Error ? e.message : tr("workspace.milestonePopup.saveFailed"));
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
      setError(e instanceof Error ? e.message : tr("workspace.milestonePopup.completeFailed"));
    } finally {
      setSaving(false);
    }
  };

  const canComplete = milestone && milestone.status !== "done" && onComplete;

  return (
    <Modal
      title={milestone ? tr("workspace.milestonePopup.editTitle") : tr("workspace.milestonePopup.newTitle")}
      onClose={onClose}
      footer={
        <>
          {milestone && onDelete && (
            <button onClick={() => onDelete(milestone.id)} className="mr-auto px-3 py-2 text-signal-error/70 hover:text-signal-error text-sm">
              {tr("common.delete")}
            </button>
          )}
          {canComplete && (
            <button onClick={handleComplete} disabled={saving} className="px-3 py-2 text-signal-ok/80 hover:text-signal-ok text-sm border border-signal-ok/30 rounded-xl disabled:opacity-40">
              {tr("workspace.milestonePopup.complete")}
            </button>
          )}
          <button onClick={onClose} className={btnGhost}>{tr("common.cancel")}</button>
          <button onClick={handleSave} disabled={!name.trim() || saving} className={btnPrimary}>
            {saving ? tr("agents.saving") : tr("common.save")}
          </button>
        </>
      }
    >
      <ErrorBanner message={error} />
      <div>
        <label className={fieldLabel}>{tr("agents.field.name")}</label>
        <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} placeholder={tr("workspace.milestonePopup.namePlaceholder")} autoFocus />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>{tr("workspace.milestonePopup.version")}</label>
          <input value={version ?? ""} onChange={(e) => setVersion(e.target.value)} className={fieldInput} placeholder="0.9" />
        </div>
        <div>
          <label className={fieldLabel}>{tr("workspace.taskPopup.statusLabel")}</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldInput}>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{tr(s.labelKey)}</option>)}
          </select>
        </div>
        <div className="col-span-2">
          <label className={fieldLabel}>{tr("workspace.milestonePopup.targetDate")}</label>
          <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} className={fieldInput} />
        </div>
      </div>
      <div>
        <label className={fieldLabel}>{tr("workspace.milestonePopup.versionGoal")}</label>
        <textarea value={description ?? ""} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder={tr("workspace.milestonePopup.versionGoalPlaceholder")} />
      </div>
      {milestone?.status === "done" && (
        <p className="text-xs text-signal-ok/80">{tr("workspace.milestonePopup.alreadyDone")}</p>
      )}
    </Modal>
  );
}
