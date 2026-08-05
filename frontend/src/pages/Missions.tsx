// pages/Missions.tsx — vista de misiones del TIE (V1.0 T4b, doc 21 §3·T4)
//
// Lo que el usuario necesita ver y decidir:
//   1. Qué está haciendo Aithera ahora mismo (y pararlo — kill-switch).
//   2. Qué plan propone antes de ejecutarlo (aprobar/rechazar — plan-mode).
//   3. Paso a paso, en vivo, el estado de cada nodo del grafo.
//
// Las misiones que esperan algo del usuario van primero (el backend ya las
// ordena así). Sondeo cada 2s solo mientras hay algo vivo — sin websockets:
// el estado real vive en disco (checkpoint por transición, T3), así que
// preguntar es barato y siempre da la verdad.
import { useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { useConfirm } from "@/components/ConfirmDialog";
import { useT } from "@/store/useI18n";

import { api, type Approval, type Mission, type MissionDetail, type NodeState, type TaskNode } from "@/lib/api";
import { MiniMarkdown } from "@/lib/miniMarkdown";
import { UserQuestionCard } from "@/components/UserQuestionCard";
import { usePendingQuestions } from "@/hooks/usePendingQuestions";

const STATE_KEY: Record<string, string> = {
  running: "missions.state.running",
  waiting: "missions.state.waiting",
  done: "missions.state.done",
  failed: "missions.state.failed",
  cancelled: "missions.state.cancelled",
};

const STATE_STYLE: Record<string, string> = {
  running: "bg-accent/15 text-accent border-accent/30",
  waiting: "bg-signal-warn/15 text-signal-warn border-signal-warn/30",
  done: "bg-signal-ok/15 text-signal-ok border-signal-ok/30",
  failed: "bg-signal-error/15 text-signal-error border-signal-error/30",
  cancelled: "bg-base-700 text-ink-dim border-base-600",
};

const NODE_KEY: Record<NodeState, string> = {
  pending: "missions.node.pending",
  ready: "missions.node.ready",
  running: "missions.node.running",
  waiting_approval: "missions.node.waiting_approval",
  waiting_event: "missions.node.waiting_event",
  done: "missions.node.done",
  failed: "missions.node.failed",
  skipped: "missions.node.skipped",
  cancelled: "missions.node.cancelled",
};

const NODE_DOT: Record<NodeState, string> = {
  pending: "bg-base-600",
  ready: "bg-base-500",
  running: "bg-accent animate-pulse",
  waiting_approval: "bg-signal-warn animate-pulse",
  waiting_event: "bg-signal-warn",
  done: "bg-signal-ok",
  failed: "bg-signal-error",
  skipped: "bg-base-600",
  cancelled: "bg-base-600",
};

function isLive(state: string) {
  return state === "running" || state === "waiting";
}

export default function Missions() {
  const t = useT();
  const [confirm, confirmDialog] = useConfirm();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<MissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  // [Fix bug real 2026-07-17] El resultado de un paso se recortaba con
  // line-clamp-3 sin ninguna forma de ver el resto. Un Set con los ids de los
  // pasos expandidos — se resetea solo al cambiar de misión (abajo).
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  // [S7·S8] El gate de PERMISO DE TOOL (nace en pleno vuelo del toolloop, R1,
  // posterior a T4b) no toca ni `graph.state` ni `node.state` — hasta ahora
  // solo existía panel para resolverlo en el Chat. Se correlaciona con la
  // misión seleccionada por `mission_id` (S7·S8-2/3).
  const [toolGate, setToolGate] = useState<Approval | null>(null);
  const selectedRef = useRef<string | null>(null);
  selectedRef.current = selected;
  // [2026-08-02] Preguntas al usuario de ESTA misión (a diferencia del Chat,
  // aquí sí se filtran: estás mirando una misión concreta). `detail?.id` es el
  // mismo id con el que el toolloop las etiquetó (`session_key` = mission.id).
  const { questions: allQuestions, refresh: refreshQuestions } = usePendingQuestions();

  const load = useCallback(async () => {
    try {
      const list = await api.getMissions();
      setMissions(list);
      const sel = selectedRef.current;
      let currentDetail: MissionDetail | null = null;
      if (sel) {
        // [Fix 2026-07-19] Una seleccion que ya no existe (recien borrada) no
        // puede tumbar la carga entera. Antes, su 404 caia al `catch` de abajo
        // y se mostraba "No se pudieron cargar las misiones" con la lista en
        // blanco, aunque el resto estuviera perfectamente. Ahora se suelta la
        // seleccion muerta y se sigue.
        if (list.some((m) => m.trace_id === sel)) {
          currentDetail = await api.getMission(sel);
          setDetail(currentDetail);
        } else {
          selectedRef.current = null;
          setSelected(null);
          setDetail(null);
        }
      } else if (list.length && !sel) {
        setSelected(list[0].trace_id);
      }
      if (currentDetail && isLive(currentDetail.state)) {
        const pending = await api.getApprovals();
        setToolGate(
          pending.find(
            (a) =>
              // [Sesión B, doc 40 §B5] `tie_tool_grant` (el gate de CONCESIÓN
              // de una herramienta que faltaba, S11) se quedó fuera cuando se
              // escribió esto en S7·S8 — se abre igual en pleno vuelo, bloquea
              // igual la misión y no caduca (PU3), pero aquí no salía y había
              // que ir al Chat a resolverlo.
              (a.action_type === "tie_tool_permission" || a.action_type === "tie_tool_grant") &&
              a.mission_id === currentDetail!.mission_id
          ) ?? null
        );
      } else {
        setToolGate(null);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("missions.loadError"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Sondeo solo si hay algo vivo (en curso o esperándote) Y la ventana visible
  // [P1]: seguir sondeando cada 2s una misión mientras la app está minimizada
  // es carga inútil; al volver a primer plano refresca solo.
  const anyLive = missions.some((m) => isLive(m.state)) || (!!detail && isLive(detail.state));
  usePolling(load, 2000, anyLive);

  useEffect(() => {
    if (!selected) return;
    setExpandedNodes(new Set());
    setToolGate(null);
    api.getMission(selected).then(setDetail).catch(() => undefined);
  }, [selected]);

  const toggleExpanded = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("missions.actionError"));
    } finally {
      setBusy(false);
    }
  };

  const nodes: TaskNode[] = detail?.graph ? Object.values(detail.graph.nodes) : [];
  // Dos mecanismos de gate distintos y AMBOS necesitan botones (bug real
  // reportado: el panel solo cubría el gate del PLAN — `graph.state==="draft"` —
  // y dejaba sin ninguna acción posible al gate de NODO, que pausa un paso
  // suelto en mitad de la ejecución con su propio `gate_id` y no toca
  // `graph.state`. Sin esto, una misión podía quedar "Esperando tu respuesta"
  // sin que hubiera ningún botón en la UI para responder.
  const awaitingPlan = detail?.state === "waiting" && detail?.graph?.state === "draft";
  const awaitingNode = !awaitingPlan
    ? nodes.find((n) => n.state === "waiting_approval" && n.gate_id)
    : undefined;
  // Las preguntas de la misión abierta. Se comparan contra los DOS ids porque
  // `mission_id` y `trace_id` pueden diferir (S7·S8) y el toolloop etiqueta
  // con el de la misión.
  // [2026-08-02] `detail.id` NO EXISTE en `MissionDetail` (los campos son
  // `mission_id` y `trace_id`): la comparación era siempre `=== undefined`, así
  // que la mitad "por id de misión" nunca casaba y solo quedaba `selected`, que
  // es el trace_id. Justo el caso que S7·S8 documentó como distinto — resultado:
  // una misión que había preguntado al usuario podía no mostrar aquí ni la
  // pregunta ni la respuesta. `tsc` lo señalaba; el error estaba sin corregir.
  const missionQuestions = allQuestions.filter(
    (q) => q.mission_id && (q.mission_id === detail?.mission_id || q.mission_id === selected),
  );

  return (
    <div className="h-full flex flex-col gap-4">
      {confirmDialog}
      <div className="glass-surface rounded-xl px-4 py-2.5 w-fit">
        <h1 className="text-lg font-semibold text-ink">{t("missions.title")}</h1>
        <p className="text-xs text-ink-faint mt-0.5">
          {t("missions.subtitle")}
        </p>
      </div>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        {/* Lista */}
        <div className="overflow-y-auto flex flex-col gap-2">
          {loading ? (
            <p className="text-xs text-ink-faint">{t("missions.loading")}</p>
          ) : missions.length === 0 ? (
            <div className="glass-surface rounded-xl p-4">
              <p className="text-sm text-ink">{t("missions.empty.title")}</p>
              <p className="text-xs text-ink-faint mt-1">
                {t("missions.empty.desc")}
              </p>
            </div>
          ) : (
            missions.map((m) => (
              // [Feature 2026-07-17] Antes era un <button> — no puede llevar
              // dentro el botón "×" de borrar (HTML no admite <button> anidado).
              // Div con el mismo comportamiento de clic + teclado.
              <div
                key={m.trace_id}
                role="button"
                tabIndex={0}
                onClick={() => setSelected(m.trace_id)}
                onKeyDown={(e) => e.key === "Enter" && setSelected(m.trace_id)}
                className={`relative text-left glass-surface rounded-xl p-3 border transition-colors cursor-pointer ${
                  selected === m.trace_id ? "border-accent/50" : "border-transparent hover:border-base-600"
                }`}
              >
                {!isLive(m.state) && (
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (!(await confirm({
                        title: t("missions.deleteConfirm.title"),
                        message: t("missions.deleteConfirm.message"),
                        confirmLabel: t("missions.deleteConfirm.confirmLabel"),
                      }))) return;
                      act(async () => {
                        await api.deleteMission(m.trace_id);
                        // El ref se asigna en RENDER, y `load()` corre justo
                        // despues de esto sin que haya habido re-render: hay
                        // que limpiarlo a mano o volveria a pedir la mision
                        // recien borrada.
                        if (selectedRef.current === m.trace_id) {
                          selectedRef.current = null;
                          setSelected(null);
                        }
                      });
                    }}
                    title={t("missions.delete")}
                    aria-label={t("missions.delete")}
                    className="absolute top-2 right-2 w-5 h-5 flex items-center justify-center rounded text-ink-faint hover:text-signal-error hover:bg-signal-error/10"
                  >
                    ×
                  </button>
                )}
                <div className="flex items-center justify-between gap-2 mb-1 pr-5">
                  <span className={`text-[10px] px-2 py-0.5 rounded border ${STATE_STYLE[m.state] ?? ""}`}>
                    {STATE_KEY[m.state] ? t(STATE_KEY[m.state]) : m.state}
                  </span>
                  <span className="text-[10px] text-ink-faint">
                    {m.node_count > 0 ? t("missions.steps", { n: m.node_count }) : t("missions.direct")}
                  </span>
                </div>
                <p className="text-sm text-ink line-clamp-2">{m.goal || t("missions.noGoal")}</p>
                <p className="text-[10px] text-ink-faint mt-1">
                  {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                  {m.channel ? ` · ${m.channel}` : ""}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Detalle */}
        <div className="overflow-y-auto">
          {!detail ? (
            <div className="glass-surface rounded-2xl p-5">
              <p className="text-sm text-ink-dim">{t("missions.selectPrompt")}</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="glass-surface rounded-2xl p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-base font-medium text-ink">{detail.goal || t("missions.noGoal")}</h2>
                    <p className="text-[11px] text-ink-faint mt-1">
                      <span className={`px-2 py-0.5 rounded border ${STATE_STYLE[detail.state] ?? ""}`}>
                        {STATE_KEY[detail.state] ? t(STATE_KEY[detail.state]) : detail.state}
                      </span>
                      {detail.model_used && <span className="ml-2">{t("missions.modelUsed", { model: detail.model_used })}</span>}
                    </p>
                  </div>
                  {isLive(detail.state) && (
                    <button
                      onClick={() => act(() => api.cancelMission(detail.trace_id))}
                      disabled={busy}
                      className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      {t("missions.stop")}
                    </button>
                  )}
                </div>

                {detail.outcome && (
                  <p className="text-sm text-ink-dim mt-3">
                    <MiniMarkdown text={detail.outcome} />
                  </p>
                )}
              </div>

              {/* Aprobación del plan — nada se ha ejecutado todavía */}
              {awaitingPlan && (
                <div className="rounded-2xl p-5 bg-signal-warn/10 border border-signal-warn/30">
                  <h3 className="text-sm font-medium text-signal-warn">{t("missions.planGate.title")}</h3>
                  <p className="text-xs text-ink-dim mt-1">
                    {t("missions.planGate.desc")}
                  </p>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => act(() => api.approvePlan(detail.trace_id, true))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
                    >
                      {t("missions.planGate.approve")}
                    </button>
                    <button
                      onClick={() => act(() => api.approvePlan(detail.trace_id, false))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      {t("missions.planGate.discard")}
                    </button>
                  </div>
                </div>
              )}

              {/* Aprobación de un paso suelto — se abrió DURANTE la ejecución
                  (no en el plan completo, TIE_PLAN_APPROVAL desactivado o caso
                  límite). Mismo patrón que el gate del plan, pero resuelve
                  directamente el gate_id de este nodo. */}
              {awaitingNode && (
                <div className="rounded-2xl p-5 bg-signal-warn/10 border border-signal-warn/30">
                  <h3 className="text-sm font-medium text-signal-warn">{t("missions.nodeGate.title")}</h3>
                  <p className="text-xs text-ink-dim mt-1">{awaitingNode.goal}</p>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => act(() => api.resolveApproval(awaitingNode.gate_id!, true))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
                    >
                      {t("missions.nodeGate.approve")}
                    </button>
                    <button
                      onClick={() => act(() => api.resolveApproval(awaitingNode.gate_id!, false))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      {t("missions.nodeGate.reject")}
                    </button>
                  </div>
                </div>
              )}

              {/* [S7·S8] Gate de PERMISO DE TOOL — se abre en pleno vuelo del
                  toolloop (R1), no forma parte del plan ni de un nodo, así que
                  no toca `graph.state` ni `node.state`: hasta ahora solo tenía
                  botones en el Chat. Se correlaciona por `mission_id`
                  (S7·S8-2/3). Mismo patrón de resolución que los otros dos. */}
              {toolGate && (
                <div className="rounded-2xl p-5 bg-signal-warn/10 border border-signal-warn/30">
                  <h3 className="text-sm font-medium text-signal-warn">{t("missions.toolGate.title")}</h3>
                  <p className="text-xs text-ink-dim mt-1">{toolGate.summary || toolGate.title}</p>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => act(() => api.resolveApproval(toolGate.gate_id, true))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
                    >
                      {t("missions.toolGate.approve")}
                    </button>
                    <button
                      onClick={() => act(() => api.resolveApproval(toolGate.gate_id, false))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      {t("missions.toolGate.reject")}
                    </button>
                  </div>
                </div>
              )}

              {/* [2026-08-02] PREGUNTAS de esta misión. A diferencia de los
                  gates de arriba (que se responden con sí/no), aquí la misión
                  espera un DATO — por eso se pinta la misma tarjeta de
                  pregunta que en el Chat, con sus opciones y su respuesta
                  libre, en vez de dos botones que no significarían nada. */}
              {missionQuestions.length > 0 && (
                <div className="flex flex-col gap-2">
                  {missionQuestions.map((q) => (
                    <UserQuestionCard
                      key={q.gate_id}
                      question={q}
                      onAnswered={() => { void refreshQuestions(); void load(); }}
                    />
                  ))}
                </div>
              )}

              {/* El grafo: los pasos */}
              {nodes.length > 0 && (
                <div className="glass-surface rounded-2xl p-5">
                  <h3 className="text-sm font-medium text-ink mb-3">
                    {t("missions.plan.title", { n: nodes.length })}
                  </h3>
                  <div className="flex flex-col gap-2">
                    {nodes.map((n, i) => (
                      <div key={n.id} className="flex items-start gap-3 py-2 border-b border-base-700/40 last:border-none">
                        <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${NODE_DOT[n.state]}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-ink">
                            <span className="text-ink-faint mr-1">{i + 1}.</span>
                            {n.goal}
                            {n.approval_required && (
                              <span className="ml-2 text-[10px] text-signal-warn">{t("missions.needsPermission")}</span>
                            )}
                          </p>
                          <p className="text-[10px] text-ink-faint mt-0.5">
                            {t(NODE_KEY[n.state])}
                            {n.depends_on.length > 0 && ` · ${t("missions.after", { deps: n.depends_on.join(", ") })}`}
                            {n.duration_ms != null && ` · ${n.duration_ms} ms`}
                          </p>
                          {n.error && <p className="text-[11px] text-signal-error mt-1">{n.error}</p>}
                          {n.result?.output != null && n.state === "done" && (() => {
                            const output = String(n.result.output);
                            // [Fix bug real 2026-07-17] Antes se recortaba con
                            // line-clamp-3 sin ninguna forma de ver el resto.
                            // Solo vale la pena el botón si de verdad hay algo
                            // que ocultar (texto largo o varias líneas).
                            const isLong = output.length > 220 || output.split("\n").length > 3;
                            const expanded = expandedNodes.has(n.id);
                            return (
                              <div className="mt-1">
                                <p className={`text-[11px] text-ink-dim ${!expanded && isLong ? "line-clamp-3" : ""}`}>
                                  <MiniMarkdown text={output} />
                                </p>
                                {isLong && (
                                  <button
                                    onClick={() => toggleExpanded(n.id)}
                                    className="text-[10px] text-accent hover:underline mt-0.5"
                                  >
                                    {expanded ? t("missions.seeLess") : t("missions.seeMore")}
                                  </button>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
