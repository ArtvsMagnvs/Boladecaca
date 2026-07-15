// pages/Workspace/AgentCreatePopup.tsx — crear agente desde una tarjeta
// (V0.87 W2c). Popup delgado y propio que reusa api.createAgent — no se
// fuerza extraer el formulario de pages/Agents.tsx (entrelazado con el
// estado de esa página); duplicar unos campos es el precio de no tocarla.
import { useEffect, useState } from "react";
import { api, type Agent, type ToolInfo } from "@/lib/api";
import { Modal, ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";
import { SkillPickerPopup } from "./SkillPickerPopup";

const AGENT_TYPES = ["generic", "claude_code", "minimax", "ollama", "custom"];
const EMOJI_CHOICES = ["🤖", "🧠", "⚙️", "🔧", "📊", "🔍", "✉️", "📅", "🗂️", "⚡"];

interface Props {
  projectId: number;
  onSave: (data: Partial<Agent>) => Promise<void>;
  onClose: () => void;
}

export function AgentCreatePopup({ projectId, onSave, onClose }: Props) {
  const [name, setName] = useState("");
  const [agentType, setAgentType] = useState("generic");
  const [description, setDescription] = useState("");
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [allowedTools, setAllowedTools] = useState<string[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [icon, setIcon] = useState("🤖");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTools().then((r) => setTools(r.tools)).catch(() => {});
  }, []);

  const toggleTool = (id: string) =>
    setAllowedTools((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        agent_type: agentType,
        description: description || null,
        allowed_tools: allowedTools,
        is_active: isActive,
        project_id: projectId,
        skills,
        icon,
      });
    } catch (e) {
      // Sin esto, un fallo (nombre duplicado, backend caido, etc.) se veia
      // como "no pasa nada al pulsar Crear" — el popup se quedaba abierto
      // sin ninguna pista de por que.
      setError(e instanceof Error ? e.message : "No se pudo crear el agente.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
    <Modal
      title="Nuevo agente"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className={btnGhost}>Cancelar</button>
          <button onClick={handleSave} disabled={!name.trim() || saving} className={btnPrimary}>
            {saving ? "Creando…" : "Crear"}
          </button>
        </>
      }
    >
      <ErrorBanner message={error} />
      <div>
        <label className={fieldLabel}>Nombre</label>
        <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} placeholder="Nombre del agente" autoFocus />
      </div>

      <div>
        <label className={fieldLabel}>Icono</label>
        <div className="flex gap-1.5 flex-wrap">
          {EMOJI_CHOICES.map((e) => (
            <button
              key={e}
              onClick={() => setIcon(e)}
              className={`h-8 w-8 rounded-lg flex items-center justify-center text-base border ${icon === e ? "border-accent bg-accent/15" : "border-base-700 hover:border-base-600"}`}
            >
              {e}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>Tipo</label>
          <select value={agentType} onChange={(e) => setAgentType(e.target.value)} className={fieldInput}>
            {AGENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Estado</label>
          <select value={isActive ? "1" : "0"} onChange={(e) => setIsActive(e.target.value === "1")} className={fieldInput}>
            <option value="1">Activo</option>
            <option value="0">Inactivo</option>
          </select>
        </div>
      </div>

      <div>
        <label className={fieldLabel}>Descripción</label>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder="Qué hace este agente" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className={fieldLabel} style={{ margin: 0 }}>Skills</label>
          <button onClick={() => setSkillPickerOpen(true)} className="text-[11px] text-accent hover:text-accent-soft">+ Skill</button>
        </div>
        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {skills.map((s) => (
              <span key={s} className="text-[11px] px-2 py-0.5 rounded bg-base-700/60 text-ink-dim flex items-center gap-1">
                {s}
                <button onClick={() => setSkills((prev) => prev.filter((x) => x !== s))} className="text-ink-faint hover:text-signal-error">×</button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-ink-faint">Sin skills. Añade con "+ Skill".</p>
        )}
      </div>

      <div>
        <label className={fieldLabel}>Herramientas permitidas</label>
        <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
          {tools.map((t) => (
            <label key={t.tool_id} className="flex items-center gap-2 text-xs text-ink-dim">
              <input type="checkbox" checked={allowedTools.includes(t.tool_id)} onChange={() => toggleTool(t.tool_id)} className="accent-accent h-3.5 w-3.5" />
              {t.name}
            </label>
          ))}
          {tools.length === 0 && <p className="text-[11px] text-ink-faint">Cargando catálogo…</p>}
        </div>
      </div>
    </Modal>

    {skillPickerOpen && (
      <SkillPickerPopup
        selected={skills}
        onApply={(names) => { setSkills(names); setSkillPickerOpen(false); }}
        onClose={() => setSkillPickerOpen(false)}
      />
    )}
    </>
  );
}
