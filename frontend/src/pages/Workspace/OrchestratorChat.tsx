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
import ActivityTrail from "@/components/chat/ActivityTrail";
import { ChatComposer } from "./ChatComposer";
import { UserQuestionCard } from "@/components/UserQuestionCard";
import { usePendingQuestions } from "@/hooks/usePendingQuestions";
import { useT } from "@/store/useI18n";

/** El rastro viaja como JSON en un campo de texto. Nunca lanza: un `progress`
 *  corrupto o de una versión anterior simplemente no pinta nada. */
function parseProgress(raw: string | null | undefined): string[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

const POLL_MS = 2000;

interface Props {
  projectId: number;
  /** Alto disponible: con la tarjeta expandida el chat respira más. */
  expanded: boolean;
  /**
   * [2026-08-02] Dónde vive el chat dentro de la tarjeta:
   *  - "stack" (por defecto): apilado abajo del todo, con alto acotado.
   *  - "side": columna propia a la derecha, ocupando TODO el alto disponible.
   * El modo lateral es el que pidió el usuario para tarjetas anchas: con el
   * chat abajo apenas se veían un par de turnos, y lo que hace falta para
   * trabajar es ver el recorrido de la conversación.
   */
  placement?: "stack" | "side";
  /**
   * [2026-08-02, petición del usuario] Si se pasa, el chat lateral deja de
   * mostrar SIEMPRE al orquestador y muestra la conversación de ESTE agente
   * (el mismo mecanismo — `agent_executions` — solo que de otro `Agent`).
   * `undefined`/`null` = comportamiento de siempre, el orquestador general.
   */
  agentId?: number | null;
}

export function OrchestratorChat({ projectId, expanded, placement = "stack", agentId }: Props) {
  const tr = useT();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [input, setInput] = useState("");
  // [2026-08-02] Modelo elegido para el PRÓXIMO mensaje. Se conserva entre
  // turnos (comodidad) pero puede cambiarse en cada uno: el contexto de la
  // conversación vive en `agent_executions`, no en el modelo, así que
  // cambiar de proveedor a mitad de charla no pierde el hilo.
  const [model, setModel] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // [2026-08-02] Las preguntas que el orquestador tenga abiertas. Sin filtrar
  // por misión a propósito: desde esta tarjeta el usuario lanza los encargos,
  // y una pregunta sin responder BLOQUEA el trabajo — es justo lo que tiene
  // que ver aquí, aunque naciera en un paso interno de otra misión suya.
  const { questions, gates, refresh: refreshQuestions } = usePendingQuestions();

  // Prepara (o recupera) al agente de ESTE panel: el orquestador del
  // proyecto por defecto, o el agente concreto que el usuario haya
  // seleccionado en la lista lateral (`agentId`). Idempotente en el backend
  // para el orquestador, así que montar la tarjeta varias veces no crea
  // agentes de más. Se resetea TODO el estado de conversación al cambiar de
  // agente/proyecto — si no, un turno de un agente podría verse un instante
  // pegado a la conversación de otro mientras carga el nuevo.
  useEffect(() => {
    let cancelado = false;
    setAgent(null);
    setExecutions([]);
    setError(null);
    const p = agentId != null ? api.getAgent(agentId) : api.ensureProjectOrchestrator(projectId);
    p
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
  }, [projectId, agentId]);

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
      await api.executeAgent(agent.id, texto, undefined, model);
      setInput("");
      await loadExecutions();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("workspace.orchestrator.sendFailed"));
    } finally {
      setSending(false);
    }
  };

  // Apilado: alto acotado, para no ahogar al resto del contenido de la tarjeta.
  // Lateral: se come TODO el alto que le den (`flex-1`), que es justo el motivo
  // de existir del modo — ver el recorrido de la conversación.
  const side = placement === "side";
  const bodyH = side ? "flex-1 min-h-0" : expanded ? "max-h-72" : "max-h-44";

  return (
    <section className={side
      ? "h-full min-h-0 flex flex-col"
      : "border-t border-base-700/60 pt-3"}>
      {/* [2026-08-02, corrección] Antes el nombre del agente iba aparte, en
          pequeño, a la derecha — pedido explícito: que vaya PEGADO al título,
          con la MISMA tipografía ("Chat del agente Cordyceps Game Dev"), no
          como una etiqueta secundaria. Una sola línea, sin truncar el resto
          del encabezado. */}
      <div className="flex items-center justify-between mb-2 shrink-0 min-w-0">
        <h3 className="text-xs font-medium text-ink-dim flex items-center gap-1.5 min-w-0 truncate">
          <span aria-hidden className="shrink-0">{agentId != null ? "🤖" : "🧠"}</span>
          <span className="truncate">
            {agentId != null ? tr("workspace.orchestrator.agentChat") : tr("workspace.orchestrator.title")}
            {agent && <> {agent.name}</>}
          </span>
        </h3>
      </div>

      {agentId == null && (
        <p className="text-[10px] text-ink-faint mb-2 shrink-0">{tr("workspace.orchestrator.hint")}</p>
      )}

      <div ref={scrollRef} className={`${bodyH} overflow-y-auto flex flex-col gap-2 mb-2 pr-1`}>
        {executions.length === 0 && !error && (
          <p className="text-[11px] text-ink-faint py-2">
            {/* [2026-08-02, corrección] El texto de "reparte el trabajo entre
                los agentes" solo tiene sentido para el ORQUESTADOR — un
                agente normal NO reparte nada, es el que hace el trabajo. */}
            {agentId != null ? tr("workspace.orchestrator.emptyAgent") : tr("workspace.orchestrator.empty")}
          </p>
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
                <>
                  <p className="text-[11px] text-accent flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                    {tr("workspace.orchestrator.working")}
                  </p>
                  {/* [2026-08-02] EL RASTRO EN VIVO. Este chat no tiene stream
                      (sondea `agent_executions`), así que las líneas llegan
                      persistidas en `progress` — mismo componente y misma
                      lectura que en el chat principal. */}
                  <ActivityTrail lines={parseProgress(ex.progress)} live />
                </>
              ) : ex.status === "cancelled" ? (
                <p className="text-[11px] text-ink-faint">{tr("workspace.orchestrator.cancelled")}</p>
              ) : ex.result ? (
                <div className="text-[11px] text-ink-dim leading-relaxed break-words">
                  <MiniMarkdown text={ex.result} />
                  {/* Terminado: el rastro se pliega a un resumen desplegable. */}
                  <ActivityTrail lines={parseProgress(ex.progress)} />
                </div>
              ) : (
                <>
                  <p className="text-[11px] text-signal-error break-words">
                    {ex.error_message || tr("workspace.orchestrator.noAnswer")}
                  </p>
                  <ActivityTrail lines={parseProgress(ex.progress)} />
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* [Sesión B, doc 40 §B5] Un gate abierto en pleno vuelo (permiso de
          acción sensible o concesión de herramienta) BLOQUEA la misión hasta
          que se responda — y desde PU3 no caduca nunca. Sin estos botones aquí,
          el chat del agente se quedaba en "trabajando…" para siempre y había
          que ir a otra pantalla a desbloquearlo (o no enterarse). Mismo patrón
          de resolución que Missions.tsx: el endpoint genérico de A1. */}
      {gates.length > 0 && (
        <div className="flex flex-col gap-2 mb-2 shrink-0">
          {gates.map((g) => (
            <div
              key={g.gate_id}
              className="rounded-xl p-3 bg-signal-warn/10 border border-signal-warn/30"
            >
              <p className="text-[11px] font-medium text-signal-warn">
                {tr("missions.toolGate.title")}
              </p>
              <p className="text-[11px] text-ink-dim mt-1 break-words">
                {g.summary || g.title}
              </p>
              <div className="flex gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => {
                    void api
                      .resolveApproval(g.gate_id, true)
                      .catch(() => {})
                      .finally(() => {
                        void refreshQuestions();
                        void loadExecutions();
                      });
                  }}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25"
                >
                  {tr("missions.toolGate.approve")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void api
                      .resolveApproval(g.gate_id, false)
                      .catch(() => {})
                      .finally(() => {
                        void refreshQuestions();
                        void loadExecutions();
                      });
                  }}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20"
                >
                  {tr("missions.toolGate.reject")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* [2026-08-02] Si Aithera está esperando una respuesta, la pregunta va
          ANTES del cuadro de escribir: es lo que bloquea el trabajo. */}
      {questions.length > 0 && (
        <div className="flex flex-col gap-2 mb-2 shrink-0">
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

      {error && <p className="text-[11px] text-signal-error mb-2 shrink-0">{error}</p>}

      {/* [2026-08-02, peticiones 6 y 7] Adjuntar, dar acceso a carpetas,
          política de aprobación, selector de proveedor/modelo POR MENSAJE y
          micrófono. Mismo componente que el chat de un agente cualquiera. */}
      <div className="shrink-0">
        <ChatComposer
          agent={agent}
          value={input}
          onChange={setInput}
          onSend={() => void send()}
          sending={sending}
          model={model}
          onModelChange={setModel}
          onAgentChanged={() => { void api.getAgent(agent!.id).then(setAgent).catch(() => {}); }}
          compact
        />
      </div>
    </section>
  );
}
