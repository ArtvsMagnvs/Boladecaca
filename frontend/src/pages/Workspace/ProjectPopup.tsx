// pages/Workspace/ProjectPopup.tsx — editor de proyecto (V0.87 WPMS W2a)
import { useState } from "react";
import type { Project, ProjectDoc } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";
import { useT } from "@/store/useI18n";

const STATUSES = [
  { value: "active", labelKey: "workspace.projectPopup.status.active" },
  { value: "paused", labelKey: "workspace.projectPopup.status.paused" },
  { value: "done", labelKey: "workspace.projectPopup.status.done" },
];

interface Props {
  project: Project | null; // null = crear
  onSave: (data: Partial<Project>) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  // V0.87 (WPMS W4, doc 18 §5.1): archivar es distinto de borrar — el
  // proyecto sigue listado y consultable, solo deja de contar como activo.
  onArchive?: (id: number) => Promise<void>;
  onClose: () => void;
}

export function ProjectPopup({ project, onSave, onDelete, onArchive, onClose }: Props) {
  const tr = useT();
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [status, setStatus] = useState(project?.status ?? "active");
  const [currentVersion, setCurrentVersion] = useState(project?.current_version ?? "");
  const [targetVersion, setTargetVersion] = useState(project?.target_version ?? "");
  const [repoPath, setRepoPath] = useState(project?.repo_path ?? "");
  const [githubUrl, setGithubUrl] = useState(project?.github_url ?? "");
  const [showCreateRepoNote, setShowCreateRepoNote] = useState(false);
  const [tags, setTags] = useState((project?.tags ?? []).join(", "));
  const [docs, setDocs] = useState<ProjectDoc[]>(project?.docs ?? []);
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // V0.87 (WPMS W2e): solo existe dentro de Electron (preload.cjs). En el
  // navegador normal (Browser pane / desarrollo web) se oculta el botón y
  // queda solo el campo de texto manual — degradación sin romper nada.
  const canPickFolder = typeof window !== "undefined" && !!window.aithera?.pickFolder;
  const pickFolder = async () => {
    const picked = await window.aithera?.pickFolder();
    if (picked) setRepoPath(picked);
  };

  // [2026-07-25] Dos formas de adjuntar material al proyecto, con la MISMA
  // estructura (`Project.docs`) y distinguidas por `kind`:
  //   kind="url"  → un enlace web que se escribe a mano (documentación online,
  //                 un board, un vídeo de referencia…).
  //   kind="file" → un ARCHIVO real del ordenador, elegido con el diálogo
  //                 nativo (que es el único que puede dar la ruta absoluta).
  // Los agentes del proyecto leen estas rutas con la tool `filesystem` /
  // `document`, que valida que estén dentro de HOME antes de abrirlas.
  const addLink = () => setDocs((prev) => [...prev, { label: "", kind: "url", url_or_path: "" }]);
  const canPickFiles = typeof window !== "undefined" && !!window.aithera?.pickFiles;
  const addFiles = async () => {
    const picked = (await window.aithera?.pickFiles()) ?? [];
    if (!picked.length) return;
    setDocs((prev) => [
      ...prev,
      // El nombre del archivo sirve de etiqueta por defecto (editable): así
      // adjuntar 5 archivos no obliga a teclear 5 nombres.
      ...picked.map((p) => ({
        label: p.split(/[\\/]/).pop() || p,
        kind: "file",
        url_or_path: p,
      })),
    ]);
  };
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
        github_url: githubUrl || null,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        docs: docs.filter((d) => d.label.trim() && d.url_or_path.trim()),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("workspace.projectPopup.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!project || !onArchive) return;
    setArchiving(true);
    setError(null);
    try {
      await onArchive(project.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("workspace.projectPopup.archiveFailed"));
    } finally {
      setArchiving(false);
    }
  };

  return (
    <Modal
      title={project ? tr("workspace.projectPopup.editTitle") : tr("workspace.projectPopup.newTitle")}
      onClose={onClose}
      footer={
        <>
          {project && onDelete && (
            <button onClick={() => onDelete(project.id)} className="mr-auto px-3 py-2 text-signal-error/70 hover:text-signal-error text-sm">
              {tr("common.delete")}
            </button>
          )}
          {project && onArchive && !project.archived_at && (
            <button onClick={handleArchive} disabled={archiving} className="px-3 py-2 text-ink-faint hover:text-ink-dim text-sm">
              {archiving ? tr("workspace.projectPopup.archiving") : tr("workspace.projectPopup.archive")}
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
      {project?.archived_at && (
        <p className="text-[11px] text-ink-faint bg-base-800/40 rounded-lg px-3 py-2">
          {tr("workspace.projectPopup.archivedNote", { date: project.archived_at.slice(0, 10) })}
        </p>
      )}
      <div>
        <label className={fieldLabel}>{tr("agents.field.name")}</label>
        <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} placeholder={tr("workspace.projectPopup.namePlaceholder")} autoFocus />
      </div>
      <div>
        <label className={fieldLabel}>{tr("agents.field.description")}</label>
        <textarea value={description ?? ""} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder={tr("workspace.projectPopup.descPlaceholder")} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>{tr("workspace.projectPopup.statusLabel")}</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldInput}>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{tr(s.labelKey)}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>{tr("workspace.projectPopup.localFolder")}</label>
          <div className="flex gap-1.5">
            <input value={repoPath ?? ""} onChange={(e) => setRepoPath(e.target.value)} className={fieldInput} placeholder="C:/repos/…" />
            {canPickFolder && (
              <button type="button" onClick={pickFolder} className={`${btnGhost} px-2.5 whitespace-nowrap`} title={tr("workspace.projectPopup.pickFolder")}>
                📁
              </button>
            )}
          </div>
        </div>
        <div>
          <label className={fieldLabel}>{tr("workspace.projectPopup.currentVersion")}</label>
          <input value={currentVersion ?? ""} onChange={(e) => setCurrentVersion(e.target.value)} className={fieldInput} placeholder="0.8.7" />
        </div>
        <div>
          <label className={fieldLabel}>{tr("workspace.projectPopup.targetVersion")}</label>
          <input value={targetVersion ?? ""} onChange={(e) => setTargetVersion(e.target.value)} className={fieldInput} placeholder="0.9" />
        </div>
        <div>
          <label className={fieldLabel}>{tr("workspace.projectPopup.githubRepo")}</label>
          <div className="flex gap-1.5">
            <input value={githubUrl ?? ""} onChange={(e) => setGithubUrl(e.target.value)} className={fieldInput} placeholder="https://github.com/…" />
            {!githubUrl && (
              <button
                type="button"
                onClick={() => setShowCreateRepoNote((v) => !v)}
                className={`${btnGhost} px-2.5 whitespace-nowrap text-[11px]`}
              >
                {tr("workspace.projectPopup.createRepo")}
              </button>
            )}
          </div>
          {showCreateRepoNote && (
            <p className="text-[11px] text-ink-faint mt-1 leading-snug">
              {tr("workspace.projectPopup.createRepoNote")}
            </p>
          )}
        </div>
      </div>
      <div>
        <label className={fieldLabel}>{tr("workspace.projectPopup.tagsLabel")}</label>
        <input value={tags} onChange={(e) => setTags(e.target.value)} className={fieldInput} placeholder="ai, desktop, backend" />
      </div>
      <div>
        <label className={fieldLabel}>{tr("workspace.projectPopup.linksDocs")}</label>
        <div className="flex flex-col gap-2">
          {docs.map((d, i) => (
            <div key={i} className="flex gap-2 group items-center">
              {/* Icono según el tipo: enlace web o archivo local. Deja claro de
                  un vistazo qué es cada fila (antes todo parecía lo mismo). */}
              <span
                className="shrink-0 text-[13px] w-5 text-center"
                title={d.kind === "file"
                  ? tr("workspace.projectPopup.kindFile")
                  : tr("workspace.projectPopup.kindUrl")}
              >
                {d.kind === "file" ? "📄" : "🔗"}
              </span>
              <input value={d.label} onChange={(e) => setDoc(i, { label: e.target.value })} className={`${fieldInput} py-1.5 w-1/3`} placeholder={tr("workspace.projectPopup.docLabelPlaceholder")} />
              <input
                value={d.url_or_path}
                onChange={(e) => setDoc(i, { url_or_path: e.target.value })}
                className={`${fieldInput} py-1.5 flex-1 ${d.kind === "file" ? "font-mono text-[12px]" : ""}`}
                placeholder={d.kind === "file"
                  ? tr("workspace.projectPopup.docPathPlaceholder")
                  : tr("workspace.projectPopup.docUrlPlaceholder")}
                title={d.url_or_path}
              />
              <button onClick={() => setDocs((prev) => prev.filter((_, j) => j !== i))} className="text-ink-faint hover:text-signal-error px-1">×</button>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <button onClick={addLink} className={btnGhost}>{tr("workspace.projectPopup.addLink")}</button>
            {canPickFiles && (
              <button onClick={addFiles} className={btnGhost}>{tr("workspace.projectPopup.addFiles")}</button>
            )}
          </div>
          <p className="text-[11px] text-ink-faint">{tr("workspace.projectPopup.docsHint")}</p>
        </div>
      </div>
    </Modal>
  );
}
