// pages/Workspace/OrchestratorChat.tsx — el chat del ORQUESTADOR del proyecto
// [hotfix 2026-08-02, petición del usuario]
//
// EL HUECO QUE CIERRA: "en teoría los proyectos cada uno tiene su orquestrator,
// pero no hay un chat general en el proyecto para hablar con él... ahora solo
// puedes hablar con cada agente individualmente". Era literal: `Agent.role=
// "orchestrator"` (W2e) y el enrutado de `submit_mission` hacia el orquestador
// del proyecto (R4) llevaban versiones existiendo, pero nada creaba nunca un
// agente con ese rol, así que la ruta estaba escrita y muerta.
//
// POR QUÉ NO HAY UN CANAL DE CHAT NUEVO: el orquestador ES un agente (uno con
// `role="orchestrator"`), así que hablar con él es exactamente lanzarle
// encargos — `POST /api/agents/{id}/execute` + `GET .../executions`, los dos
// endpoints que la ventana de agente ya usaba desde W2d. Lo ÚNICO nuevo en el
// backend es `POST /api/projects/{id}/orchestrator`, que lo crea si aún no
// existe. Ventaja de reusar el camino de agente: el historial del chat se
// persiste solo (vive en `agent_executions`), así que sobrevive a cerrar la
// tarjeta y a reiniciar la app, sin inventar una tabla nueva.
//
// SU ALCANCE lo impone `Authority` en el TIE (proyecto + carpeta + tools), no
// un prompt: ver `app/tie/authority.py::ensure_orchestrator`.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Agent, type AgentExecution } from "@/lib/api";
import { MiniMarkdown } from "@/lib/miniMarkdown";
import { UserQuestionCard } from "@/components/UserQuestionCard";
import { usePendingQuestions } from "@/hooks/usePendingQuestions";
import { useT } from "@/store/useI18n";

const POLL_MS = 2000;

interface Props {
  projectId: number;
  /** Alto disponible: con la tarjeta expandida el chat respira más. */
  expanded: boolean;
}

export function OrchestratorChat({ projectId, expanded }: Props) {
  const tr = useT();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // [2026-08-02] Las preguntas que el orquestador tenga abiertas. Sin filtrar
  // por misión a propósito: desde esta tarjeta el usuario lanza los encargos,
  // y una pregunta sin responder BLOQUEA el trabajo — es justo lo que tiene
  // que ver aquí, aunque naciera en un paso interno de otra misión suya.
  const { questions, refresh: refreshQuestions } = usePendingQuestions();

  // Prepara (o recupera) el orquestador de ESTE proyecto. Idempotente en el
  // backend, así que montar la tarjeta varias veces no crea agentes de más.
  useEffect(() => {
    let cancelado = false;
    api
      .ensureProjectOrchestrator(projectId)
      .then((a) => {
        if (!cancelado) setAgent(a);
      })
      .catch((e) => {
        if (!cancelado) setError(e instanceof Error ? e.message : tr("workspace.orchestrator.failed"));
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadExecutions = useCallback(async () => {
    if (!agent) return;
    const list = await api.getAgentExecutions(agent.id, 30);
    setExecutions([...list].reverse()); // el backend los da del más nuevo al más viejo
  }, [agent]);

  useEffect(() => {
    loadExecutions().catch(() => {});
  }, [loadExecutions]);

  // Sondeo SOLO mientras haya algo en marcha (mismo criterio que
  // AgentWindowCard): una misión puede tardar minutos, pero un chat en reposo
  // no debe estar pidiendo nada.
  useEffect(() => {
    const vivo = executions.some((e) => e.status === "pending" || e.status === "running");
    if (!vivo) {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
      return;
    }
    if (pollRef.current) return;
    pollRef.current = window.setInterval(() => {
      loadExecutions().catch(() => {});
    }, POLL_MS);
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [executions, loadExecutions]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [executions]);

  const send = async () => {
    const texto = input.trim();
    if (!texto || !agent || sending) return;
    setSending(true);
    setError(null);
    try {
      await api.executeAgent(agent.id, texto);
      setInput("");
      await loadExecutions();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("workspace.orchestrator.sendFailed"));
    } finally {
      setSending(false);
    }
  };

  const bodyH = expanded ? "max-h-72" : "max-h-44";

  return (
    <section className="border-t border-base-700/60 pt-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-ink-dim flex items-center gap-1.5">
          <span aria-hidden>🧠</span>
          {tr("workspace.orchestrator.title")}
        </h3>
        {agent && (
          <span className="text-[10px] text-ink-faint truncate max-w-[45%]" title={agent.name}>
            {agent.name}
          </span>
        )}
      </div>

      <p className="text-[10px] text-ink-faint mb-2">{tr("workspace.orchestrator.hint")}</p>

      <div ref={scrollRef} className={`${bodyH} overflow-y-auto flex flex-col gap-2 mb-2 pr-1`}>
        {executions.length === 0 && !error && (
          <p className="text-[11px] text-ink-faint py-2">{tr("workspace.orchestrator.empty")}</p>
        )}
        {executions.map((ex) => (
          <div key={ex.id} className="flex flex-col gap-1">
            {/* Lo que le pediste */}
            <div className="self-end max-w-[85%] rounded-xl rounded-br-sm bg-accent/15 border border-accent/25 px-2.5 py-1.5">
              <p className="text-[11px] text-ink whitespace-pre-wrap break-words">{ex.task_description}</p>
            </div>
            {/* Lo que respondió — o en qué estado está, sin fingir que terminó */}
            <div className="self-start max-w-[92%] rounded-xl rounded-bl-sm glass-surface border border-base-700 px-2.5 py-1.5">
              {ex.status === "pending" || ex.status === "running" ? (
                <p className="text-[11px] text-accent flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                  {tr("workspace.orchestrator.working")}
                </p>
              ) : ex.status === "cancelled" ? (
                <p className="text-[11px] text-ink-faint">{tr("workspace.orchestrator.cancelled")}</p>
              ) : ex.result ? (
                <div className="text-[11px] text-ink-dim leading-relaxed break-words">
                  <MiniMarkdown text={ex.result} />
                </div>
              ) : (
                <p className="text-[11px] text-signal-error break-words">
                  {ex.error_message || tr("workspace.orchestrator.noAnswer")}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* [2026-08-02] Si Aithera está esperando una respuesta, la pregunta va
          ANTES del cuadro de escribir: es lo que bloquea el trabajo. */}
      {questions.length > 0 && (
        <div className="flex flex-col gap-2 mb-2">
          {questions.map((q) => (
            <UserQuestionCard
              key={q.gate_id}
              question={q}
              compact
              onAnswered={() => {
                void refreshQuestions();
                void loadExecutions();
              }}
            />
          ))}
        </div>
      )}

      {error && <p className="text-[11px] text-signal-error mb-2">{error}</p>}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          disabled={!agent}
          className="flex-1 min-w-0 bg-base-800/70 border border-base-600 rounded-lg px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-accent/60 disabled:opacity-50"
          placeholder={
            agent ? tr("workspace.orchestrator.placeholder") : tr("workspace.orchestrator.preparing")
          }
        />
        <button
          onClick={() => void send()}
          disabled={!agent || !input.trim() || sending}
          className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-40"
        >
          {sending ? "…" : tr("chat.send")}
        </button>
      </div>
    </section>
  );
}
