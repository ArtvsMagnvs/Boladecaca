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
import { api, type Agent, type AgentExecution } from "@/lib/api";
import { fieldLabel, fieldInput, btnPrimary } from "./Modal";

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

  const skills = agent.skills ?? [];
  const tools = agent.allowed_tools ?? [];

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
          <p className="text-[11px] text-ink-faint">{agent.agent_type}</p>
        </div>
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
          {agent.description && <p className="text-xs text-ink-dim">{agent.description}</p>}

          <div>
            <label className={fieldLabel}>Skills</label>
            {skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {skills.map((s) => <span key={s} className="text-[11px] px-2 py-0.5 rounded bg-base-700/60 text-ink-dim">{s}</span>)}
              </div>
            ) : <p className="text-[11px] text-ink-faint">Sin skills.</p>}
          </div>

          <div>
            <label className={fieldLabel}>Permisos / herramientas</label>
            {tools.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {tools.map((t) => <span key={t} className="text-[11px] px-2 py-0.5 rounded bg-accent/10 text-accent">{t}</span>)}
              </div>
            ) : <p className="text-[11px] text-ink-faint">Sin herramientas permitidas.</p>}
          </div>

          <div>
            <label className={fieldLabel}>Timeout</label>
            <p className="text-xs text-ink-dim">{agent.max_execution_time ?? "—"}s por tarea</p>
          </div>
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
    </div>
  );
}
