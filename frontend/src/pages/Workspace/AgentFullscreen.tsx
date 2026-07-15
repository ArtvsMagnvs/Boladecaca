// pages/Workspace/AgentFullscreen.tsx — agente a pantalla completa (V0.87 W2d)
//
// Doble clic en un AgentChip abre esto ocupando el MISMO espacio que una
// ProjectCard expandida (el área del Workspace, no la pantalla del SO) —
// por eso vive en WorkspaceCanvas como overlay de nivel superior, NO dentro
// de la ProjectCard pequeña que lo abrió (si viviera ahi, no podria "salirse"
// de unos límites de 260x180px).
//
// Panel de proceso — alcance HONESTO (auditado agent_manager.py antes de
// diseñar esto): la ejecución de agentes hoy es un placeholder de V0.5 (demo
// fija: list_dir → list_scripts → git status; el propio código dice "la IA
// todavía no devuelve tool_calls estructurados"). No hay razonamiento real
// que transmitir en vivo, así que este panel muestra tarea → estado (con
// sondeo mientras pending/running) → resultado final + tool_calls, NUNCA un
// streaming de tokens inventado. Cuando el TIE (V1.0, doc 14) produzca
// trazas reales, este mismo panel se puede enchufar a ellas sin rehacerse.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Agent, type AgentExecution, type ToolInfo } from "@/lib/api";
import { ErrorBanner, fieldLabel, fieldInput, btnPrimary, btnGhost } from "./Modal";
import { useModeloIAOptions } from "./useModeloIAOptions";
import { SkillPickerPopup } from "./SkillPickerPopup";

const EMOJI_CHOICES = ["🤖", "🧠", "⚙️", "🔧", "📊", "🔍", "✉️", "📅", "🗂️", "⚡"];
const POLL_MS = 1800;

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente", running: "En progreso", completed: "Completada", failed: "Fallida", cancelled: "Cancelada",
};
const STATUS_COLOR: Record<string, string> = {
  pending: "text-ink-faint", running: "text-accent", completed: "text-signal-ok", failed: "text-signal-error", cancelled: "text-ink-faint",
};

function parseToolCalls(raw: string | null): Array<{ tool_id?: string; action?: string; ok?: boolean }> {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

interface Props {
  agentId: number;
  onClose: () => void;
}

export function AgentFullscreen({ agentId, onClose }: Props) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [taskInput, setTaskInput] = useState("");
  const [sending, setSending] = useState(false);
  const [iconPickerOpen, setIconPickerOpen] = useState(false);
  const pollRef = useRef<number | null>(null);
  const modeloOptions = useModeloIAOptions();

  // V0.87 (WPMS W2e): edicion completa — antes solo icono/is_active eran
  // editables (via updateAgent directo desde el header); el resto era de
  // solo lectura. Estado de formulario separado del `agent` real: solo se
  // sincroniza con la BD al pulsar "Guardar", nunca antes.
  const [editing, setEditing] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [agentType, setAgentType] = useState("generic");
  const [maxExecutionTime, setMaxExecutionTime] = useState(300);
  const [skills, setSkills] = useState<string[]>([]);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [allowedTools, setAllowedTools] = useState<string[]>([]);
  const [tools, setTools] = useState<ToolInfo[]>([]);

  useEffect(() => {
    api.getTools().then((r) => setTools(r.tools)).catch(() => {});
  }, []);

  const startEditing = () => {
    if (!agent) return;
    setName(agent.name);
    setDescription(agent.description ?? "");
    setAgentType(agent.agent_type || "generic");
    setMaxExecutionTime(agent.max_execution_time ?? 300);
    setSkills(agent.skills ?? []);
    setAllowedTools(agent.allowed_tools ?? []);
    setEditError(null);
    setEditing(true);
  };

  const toggleTool = (id: string) =>
    setAllowedTools((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));

  const loadAgent = useCallback(async () => {
    const a = await api.getAgent(agentId);
    setAgent(a);
  }, [agentId]);

  const loadExecutions = useCallback(async () => {
    const list = await api.getAgentExecutions(agentId, 50);
    // cronologico: mas antigua primero, como un historial de conversacion.
    setExecutions([...list].reverse());
    return list;
  }, [agentId]);

  useEffect(() => {
    loadAgent().catch(() => {});
    loadExecutions().catch(() => {});
  }, [loadAgent, loadExecutions]);

  // Sondeo mientras haya alguna ejecucion pendiente/en progreso — es lo mas
  // "en vivo" que puede ser honestamente este panel hoy (ver nota de alcance
  // arriba). Se detiene solo cuando ya no queda nada pendiente.
  useEffect(() => {
    const hasPending = executions.some((e) => e.status === "pending" || e.status === "running");
    if (!hasPending) {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
      return;
    }
    if (pollRef.current) return;
    pollRef.current = window.setInterval(() => { loadExecutions().catch(() => {}); }, POLL_MS);
    return () => {
      if (pollRef.current) { window.clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [executions, loadExecutions]);

  const updateAgent = async (patch: Partial<Agent>) => {
    const updated = await api.updateAgent(agentId, patch);
    setAgent(updated);
    // El AgentChip de la tarjeta pequena que abrio esto es OTRA instancia con
    // sus propios datos ya cargados — se refresca al cerrar (ver onClose en
    // WorkspaceCanvas, que sube un refreshTick), no en cada cambio aqui.
  };

  const saveEdit = async () => {
    if (!name.trim()) return;
    setEditSaving(true);
    setEditError(null);
    try {
      await updateAgent({
        name: name.trim(),
        description: description || null,
        agent_type: agentType,
        max_execution_time: maxExecutionTime,
        skills,
        allowed_tools: allowedTools,
      });
      setEditing(false);
    } catch (e) {
      setEditError(e instanceof Error ? e.message : "No se pudo guardar el agente.");
    } finally {
      setEditSaving(false);
    }
  };

  const sendTask = async () => {
    const task = taskInput.trim();
    if (!task) return;
    setSending(true);
    try {
      await api.executeAgent(agentId, task);
      setTaskInput("");
      await loadExecutions();
    } catch {
      // fail-soft: si el lanzamiento falla, el usuario lo ve porque la lista
      // no gana una fila nueva — no hace falta un segundo banner de error
      // aqui encima del proceso ya visible.
    } finally {
      setSending(false);
    }
  };

  if (!agent) {
    return (
      <div className="absolute inset-0 glass-surface rounded-2xl flex items-center justify-center text-ink-faint text-sm">
        Cargando agente…
      </div>
    );
  }

  const agentSkills = agent.skills ?? [];
  const agentTools = agent.allowed_tools ?? [];
  const modeloLabel = modeloOptions.find((o) => o.value === agent.agent_type)?.label || agent.agent_type;

  return (
    <div className="absolute inset-0 glass-surface rounded-2xl border border-base-700 shadow-glass flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b border-base-700/60 shrink-0">
        <div className="relative">
          <button
            onClick={() => setIconPickerOpen((v) => !v)}
            className="h-10 w-10 rounded-full border-2 agent-ring-active bg-base-800 flex items-center justify-center text-lg relative"
            title="Cambiar icono"
          >
            {agent.is_active && <span className="agent-ring-glow" aria-hidden />}
            <span className="relative z-[1]">{agent.icon || "🤖"}</span>
          </button>
          {iconPickerOpen && (
            <div className="absolute top-12 left-0 z-10 glass-surface rounded-xl border border-base-700 p-2 flex gap-1 flex-wrap w-48">
              {EMOJI_CHOICES.map((e) => (
                <button
                  key={e}
                  onClick={() => { updateAgent({ icon: e }); setIconPickerOpen(false); }}
                  className="h-7 w-7 rounded-lg flex items-center justify-center text-sm hover:bg-base-700/60"
                >
                  {e}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-ink truncate">{agent.name}</h2>
          <p className="text-[11px] text-ink-faint">{modeloLabel}</p>
        </div>
        {!editing && (
          <button onClick={startEditing} className="text-[11px] px-2.5 py-1 rounded-lg border border-base-700 text-ink-dim hover:border-accent/40 hover:text-accent">
            Editar
          </button>
        )}
        <button
          onClick={() => updateAgent({ is_active: !agent.is_active })}
          className={`text-[11px] px-2.5 py-1 rounded-lg border ${agent.is_active ? "border-accent/40 bg-accent/15 text-accent" : "border-base-700 text-ink-faint"}`}
        >
          {agent.is_active ? "Activo" : "Inactivo"}
        </button>
        <button onClick={onClose} className="text-ink-faint hover:text-ink text-sm px-2" title="Restaurar">⤡</button>
      </div>

      {/* Cuerpo: info a la izquierda, proceso a la derecha */}
      <div className="flex-1 min-h-0 flex">
        <div className="w-72 shrink-0 border-r border-base-700/60 overflow-y-auto p-4 flex flex-col gap-4">
          {editing ? (
            <>
              <ErrorBanner message={editError} />
              <div>
                <label className={fieldLabel}>Nombre</label>
                <input value={name} onChange={(e) => setName(e.target.value)} className={fieldInput} autoFocus />
              </div>
              <div>
                <label className={fieldLabel}>Descripción</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${fieldInput} resize-none`} placeholder="Qué hace este agente" />
              </div>
              <div>
                <label className={fieldLabel}>Modelo IA</label>
                <select value={agentType} onChange={(e) => setAgentType(e.target.value)} className={fieldInput}>
                  {modeloOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
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
                ) : <p className="text-[11px] text-ink-faint">Sin skills. Añade con "+ Skill".</p>}
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
              <div>
                <label className={fieldLabel}>Timeout (segundos)</label>
                <input
                  type="number"
                  value={maxExecutionTime}
                  onChange={(e) => setMaxExecutionTime(Math.max(1, Math.min(3600, Number(e.target.value) || 300)))}
                  className={fieldInput}
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setEditing(false)} className={`${btnGhost} flex-1`}>Cancelar</button>
                <button onClick={saveEdit} disabled={!name.trim() || editSaving} className={`${btnPrimary} flex-1`}>
                  {editSaving ? "Guardando…" : "Guardar"}
                </button>
              </div>
            </>
          ) : (
            <>
              {agent.description && <p className="text-xs text-ink-dim">{agent.description}</p>}

              <div>
                <label className={fieldLabel}>Skills</label>
                {agentSkills.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {agentSkills.map((s) => <span key={s} className="text-[11px] px-2 py-0.5 rounded bg-base-700/60 text-ink-dim">{s}</span>)}
                  </div>
                ) : <p className="text-[11px] text-ink-faint">Sin skills.</p>}
              </div>

              <div>
                <label className={fieldLabel}>Permisos / herramientas</label>
                {agentTools.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {agentTools.map((t) => <span key={t} className="text-[11px] px-2 py-0.5 rounded bg-accent/10 text-accent">{t}</span>)}
                  </div>
                ) : <p className="text-[11px] text-ink-faint">Sin herramientas permitidas.</p>}
              </div>

              <div>
                <label className={fieldLabel}>Timeout</label>
                <p className="text-xs text-ink-dim">{agent.max_execution_time ?? "—"}s por tarea</p>
              </div>
            </>
          )}
        </div>

        <div className="flex-1 min-w-0 flex flex-col">
          <div className="px-4 py-2 border-b border-base-700/40">
            <p className="text-[10.5px] text-ink-faint">
              Aithera todavía no razona en vivo — esto llega con el TIE (V1.0). Por ahora: estado real + resultado real de cada ejecución.
            </p>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 flex flex-col gap-3">
            {executions.length === 0 && (
              <p className="text-xs text-ink-faint text-center py-8">Sin ejecuciones todavía. Lanza una tarea abajo.</p>
            )}
            {executions.map((ex) => {
              const calls = parseToolCalls(ex.tool_calls);
              const busy = ex.status === "pending" || ex.status === "running";
              return (
                <div key={ex.id} className="flex flex-col gap-1.5">
                  <div className="self-end max-w-[85%] bg-accent/12 text-ink rounded-xl rounded-tr-sm px-3 py-2 text-xs">
                    {ex.task_description || "(sin descripción)"}
                  </div>
                  <div className="self-start max-w-[85%] glass-surface rounded-xl rounded-tl-sm px-3 py-2 text-xs flex flex-col gap-1.5">
                    <div className={`flex items-center gap-1.5 ${STATUS_COLOR[ex.status] ?? "text-ink-dim"}`}>
                      {busy && <span className="h-2 w-2 rounded-full bg-current animate-pulse" />}
                      <span>{STATUS_LABEL[ex.status] ?? ex.status}</span>
                    </div>
                    {ex.result && <p className="text-ink-dim whitespace-pre-wrap">{ex.result}</p>}
                    {ex.error_message && <p className="text-signal-error">{ex.error_message}</p>}
                    {calls.length > 0 && (
                      <div className="flex flex-col gap-0.5 mt-1 border-t border-base-700/40 pt-1.5">
                        {calls.map((c, i) => (
                          <span key={i} className="text-[10.5px] text-ink-faint">
                            {c.ok ? "✓" : "✗"} {c.tool_id}·{c.action}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="px-4 py-3 border-t border-base-700/60 flex gap-2 shrink-0">
            <input
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !sending) sendTask(); }}
              className={fieldInput}
              placeholder="Describe la tarea…"
            />
            <button onClick={sendTask} disabled={!taskInput.trim() || sending} className={btnPrimary}>
              {sending ? "…" : "Enviar"}
            </button>
          </div>
        </div>
      </div>

      {skillPickerOpen && (
        <SkillPickerPopup
          selected={skills}
          onApply={(names) => { setSkills(names); setSkillPickerOpen(false); }}
          onClose={() => setSkillPickerOpen(false)}
        />
      )}
    </div>
  );
}
