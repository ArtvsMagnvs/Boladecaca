// pages/Workspace/AgentChip.tsx — icono de agente en marco (V0.87 W2c)
//
// Mapeo de estado del marco (fijado en el plan para no dejarlo ambiguo):
// gris = is_active=false sin fallo reciente · rojo = is_active=false y la
// ultima AgentExecution tiene status="failed" · azul animado = is_active=true
// (punto de luz recorriendo el marco, CSS/SVG puro).
//
// 3 niveles de detalle segun el tamano disponible de la tarjeta de PROYECTO
// (pedido explicito): "icon" (solo el marco+icono), "compact" (+nombre),
// "full" (+skills+contador de tareas). El propio AgentChip no decide el
// nivel — lo recibe como prop desde ProjectCard, que ya calcula el tamano.
import type { Agent, AgentExecution } from "@/lib/api";

export type ChipSize = "icon" | "compact" | "full";

const SKILLS_PREVIEW = 3;

function statusBuckets(executions: AgentExecution[]) {
  let pending = 0, running = 0, done = 0;
  for (const e of executions) {
    if (e.status === "pending") pending++;
    else if (e.status === "running") running++;
    else done++; // completed | failed | cancelled -> "terminadas"
  }
  return { pending, running, done };
}

interface Props {
  agent: Agent;
  size: ChipSize;
  lastExecutionFailed: boolean;
  executions: AgentExecution[];
  // El arrastre para reordenar lo lleva el <div data-agent-id> que envuelve
  // a este chip en AgentsSection.tsx (onPointerDown ahi) — no hace falta que
  // AgentChip sepa nada de reorden, solo mostrar el estado "isDragging".
  isDragging?: boolean;
  onOpen: () => void; // clic simple -> AgentDetailPopup
  onOpenFullscreen: () => void; // doble clic -> W2d (pantalla completa)
}

export function AgentChip({
  agent, size, lastExecutionFailed, executions, isDragging, onOpen, onOpenFullscreen,
}: Props) {
  const ringClass = agent.is_active
    ? "agent-ring-active"
    : lastExecutionFailed
      ? "border-signal-error/70"
      : "border-ink-faint/40";

  const icon = (
    <div
      className={`relative shrink-0 h-9 w-9 rounded-full border-2 flex items-center justify-center text-base bg-base-800 ${ringClass}`}
    >
      {agent.is_active && <span className="agent-ring-glow" aria-hidden />}
      <span className="relative z-[1]">{agent.icon || "🤖"}</span>
    </div>
  );

  if (size === "icon") {
    return (
      <button
        onClick={onOpen}
        onDoubleClick={onOpenFullscreen}
        title={agent.name}
        className={`shrink-0 ${isDragging ? "opacity-50" : ""}`}
      >
        {icon}
      </button>
    );
  }

  const buckets = statusBuckets(executions);
  const skills = agent.skills ?? [];
  const shownSkills = skills.slice(0, SKILLS_PREVIEW);
  const extraSkills = skills.length - shownSkills.length;

  return (
    <div
      onClick={onOpen}
      onDoubleClick={(e) => { e.stopPropagation(); onOpenFullscreen(); }}
      className={`flex items-center gap-2.5 glass-surface rounded-xl px-2.5 py-2 cursor-pointer hover:border-accent/25 border border-transparent transition-all ${
        isDragging ? "opacity-50" : ""
      }`}
    >
      {icon}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-ink truncate">{agent.name}</span>
        </div>
        {size === "full" && (
          <>
            {skills.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {shownSkills.map((s) => (
                  <span key={s} className="text-[9px] px-1.5 py-0.5 rounded bg-base-700/60 text-ink-faint">{s}</span>
                ))}
                {extraSkills > 0 && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-base-700/60 text-ink-faint" title={skills.slice(SKILLS_PREVIEW).join(", ")}>
                    +{extraSkills} más
                  </span>
                )}
              </div>
            )}
            <div className="flex items-center gap-2 mt-1 text-[9px] text-ink-faint">
              <span>{buckets.pending} pendientes</span>
              <span>·</span>
              <span>{buckets.running} en progreso</span>
              <span>·</span>
              <span>{buckets.done} terminadas</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
