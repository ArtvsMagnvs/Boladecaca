// pages/Workspace/AgentDetailPopup.tsx — detalle de agente, solo lectura
// (V0.87 W2c). Todavía NO es la vista de pantalla completa con panel de
// proceso (eso es W2d) — este popup normal muestra lo que ya es real hoy:
// permisos/tools, skills, y el contador de tareas por AgentExecution.status.
import { useState } from "react";
import type { Agent, AgentExecution } from "@/lib/api";
import { Modal, fieldLabel } from "./Modal";

function statusBuckets(executions: AgentExecution[]) {
  let pending = 0, running = 0, done = 0;
  for (const e of executions) {
    if (e.status === "pending") pending++;
    else if (e.status === "running") running++;
    else done++;
  }
  return { pending, running, done };
}

interface Props {
  agent: Agent;
  executions: AgentExecution[];
  onClose: () => void;
}

export function AgentDetailPopup({ agent, executions, onClose }: Props) {
  const [promptOpen, setPromptOpen] = useState(false);
  const buckets = statusBuckets(executions);
  const skills = agent.skills ?? [];
  const tools = agent.allowed_tools ?? [];

  return (
    <Modal title={`${agent.icon || "🤖"} ${agent.name}`} onClose={onClose} footer={<button onClick={onClose} className="text-sm text-ink-dim hover:text-ink px-3 py-2">Cerrar</button>}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] px-2 py-0.5 rounded bg-base-700/60 text-ink-dim">{agent.agent_type}</span>
        <span className={`text-[11px] px-2 py-0.5 rounded ${agent.is_active ? "bg-accent/15 text-accent" : "bg-base-700/60 text-ink-faint"}`}>
          {agent.is_active ? "Activo" : "Inactivo"}
        </span>
        <span className="text-[11px] text-ink-faint">timeout {agent.max_execution_time ?? "—"}s</span>
      </div>

      {agent.description && (
        <div>
          <label className={fieldLabel}>Descripción</label>
          <p className="text-sm text-ink-dim">{agent.description}</p>
        </div>
      )}

      <div>
        <label className={fieldLabel}>Skills</label>
        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {skills.map((s) => <span key={s} className="text-[11px] px-2 py-0.5 rounded bg-base-700/60 text-ink-dim">{s}</span>)}
          </div>
        ) : (
          <p className="text-xs text-ink-faint">Sin skills asignadas.</p>
        )}
      </div>

      <div>
        <label className={fieldLabel}>Permisos / herramientas</label>
        {tools.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {tools.map((t) => <span key={t} className="text-[11px] px-2 py-0.5 rounded bg-accent/10 text-accent">{t}</span>)}
          </div>
        ) : (
          <p className="text-xs text-ink-faint">Sin herramientas permitidas.</p>
        )}
      </div>

      <div>
        <label className={fieldLabel}>Tareas</label>
        <div className="flex items-center gap-3 text-xs text-ink-dim">
          <span>{buckets.pending} pendientes</span>
          <span>·</span>
          <span>{buckets.running} en progreso</span>
          <span>·</span>
          <span>{buckets.done} terminadas</span>
        </div>
      </div>

      {agent.system_prompt && (
        <div>
          <button onClick={() => setPromptOpen((v) => !v)} className={`${fieldLabel} flex items-center gap-1 cursor-pointer`}>
            System prompt {promptOpen ? "▾" : "▸"}
          </button>
          {promptOpen && <p className="text-xs text-ink-faint whitespace-pre-wrap mt-1">{agent.system_prompt}</p>}
        </div>
      )}
    </Modal>
  );
}
