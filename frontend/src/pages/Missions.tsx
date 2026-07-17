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

import { api, type Mission, type MissionDetail, type NodeState, type TaskNode } from "@/lib/api";

const STATE_LABEL: Record<string, string> = {
  running: "En curso",
  waiting: "Esperando tu respuesta",
  done: "Completada",
  failed: "Fallida",
  cancelled: "Cancelada",
};

const STATE_STYLE: Record<string, string> = {
  running: "bg-accent/15 text-accent border-accent/30",
  waiting: "bg-signal-warn/15 text-signal-warn border-signal-warn/30",
  done: "bg-signal-ok/15 text-signal-ok border-signal-ok/30",
  failed: "bg-signal-error/15 text-signal-error border-signal-error/30",
  cancelled: "bg-base-700 text-ink-dim border-base-600",
};

const NODE_LABEL: Record<NodeState, string> = {
  pending: "Pendiente",
  ready: "Lista",
  running: "Ejecutando",
  waiting_approval: "Esperando permiso",
  waiting_event: "Esperando evento",
  done: "Hecha",
  failed: "Falló",
  skipped: "Omitida",
  cancelled: "Cancelada",
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
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<MissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const selectedRef = useRef<string | null>(null);
  selectedRef.current = selected;

  const load = useCallback(async () => {
    try {
      const list = await api.getMissions();
      setMissions(list);
      const sel = selectedRef.current;
      if (sel) {
        setDetail(await api.getMission(sel));
      } else if (list.length && !sel) {
        setSelected(list[0].trace_id);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las misiones.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Sondeo solo si hay algo vivo (en curso o esperándote).
  useEffect(() => {
    const anyLive = missions.some((m) => isLive(m.state)) || (detail && isLive(detail.state));
    if (!anyLive) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [missions, detail, load]);

  useEffect(() => {
    if (!selected) return;
    api.getMission(selected).then(setDetail).catch(() => undefined);
  }, [selected]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "La acción falló.");
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

  return (
    <div className="h-full flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-ink">Misiones</h1>
        <p className="text-xs text-ink-faint mt-0.5">
          Lo que Aithera está haciendo por ti: el plan, cada paso y su estado.
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
            <p className="text-xs text-ink-faint">Cargando…</p>
          ) : missions.length === 0 ? (
            <div className="glass-surface rounded-xl p-4">
              <p className="text-sm text-ink">Todavía no hay misiones.</p>
              <p className="text-xs text-ink-faint mt-1">
                Cuando le pidas algo que necesite varios pasos, aparecerá aquí con su plan.
              </p>
            </div>
          ) : (
            missions.map((m) => (
              <button
                key={m.trace_id}
                onClick={() => setSelected(m.trace_id)}
                className={`text-left glass-surface rounded-xl p-3 border transition-colors ${
                  selected === m.trace_id ? "border-accent/50" : "border-transparent hover:border-base-600"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className={`text-[10px] px-2 py-0.5 rounded border ${STATE_STYLE[m.state] ?? ""}`}>
                    {STATE_LABEL[m.state] ?? m.state}
                  </span>
                  <span className="text-[10px] text-ink-faint">
                    {m.node_count > 0 ? `${m.node_count} paso(s)` : "directa"}
                  </span>
                </div>
                <p className="text-sm text-ink line-clamp-2">{m.goal || "(sin objetivo)"}</p>
                <p className="text-[10px] text-ink-faint mt-1">
                  {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                  {m.channel ? ` · ${m.channel}` : ""}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Detalle */}
        <div className="overflow-y-auto">
          {!detail ? (
            <div className="glass-surface rounded-2xl p-5">
              <p className="text-sm text-ink-dim">Elige una misión para ver su plan.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="glass-surface rounded-2xl p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-base font-medium text-ink">{detail.goal || "(sin objetivo)"}</h2>
                    <p className="text-[11px] text-ink-faint mt-1">
                      <span className={`px-2 py-0.5 rounded border ${STATE_STYLE[detail.state] ?? ""}`}>
                        {STATE_LABEL[detail.state] ?? detail.state}
                      </span>
                      {detail.model_used && <span className="ml-2">modelo: {detail.model_used}</span>}
                    </p>
                  </div>
                  {isLive(detail.state) && (
                    <button
                      onClick={() => act(() => api.cancelMission(detail.trace_id))}
                      disabled={busy}
                      className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      Parar
                    </button>
                  )}
                </div>

                {detail.outcome && (
                  <p className="text-sm text-ink-dim mt-3 whitespace-pre-wrap">{detail.outcome}</p>
                )}
              </div>

              {/* Aprobación del plan — nada se ha ejecutado todavía */}
              {awaitingPlan && (
                <div className="rounded-2xl p-5 bg-signal-warn/10 border border-signal-warn/30">
                  <h3 className="text-sm font-medium text-signal-warn">Este plan necesita tu visto bueno</h3>
                  <p className="text-xs text-ink-dim mt-1">
                    Toca algo sensible, así que no he ejecutado nada todavía. Si lo apruebas, haré
                    estos pasos sin volver a preguntarte uno por uno.
                  </p>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => act(() => api.approvePlan(detail.trace_id, true))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
                    >
                      Aprobar y ejecutar
                    </button>
                    <button
                      onClick={() => act(() => api.approvePlan(detail.trace_id, false))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      Descartar
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
                  <h3 className="text-sm font-medium text-signal-warn">Este paso necesita tu permiso</h3>
                  <p className="text-xs text-ink-dim mt-1">{awaitingNode.goal}</p>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => act(() => api.resolveApproval(awaitingNode.gate_id!, true))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
                    >
                      Aprobar
                    </button>
                    <button
                      onClick={() => act(() => api.resolveApproval(awaitingNode.gate_id!, false))}
                      disabled={busy}
                      className="text-xs px-3 py-2 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                    >
                      Rechazar
                    </button>
                  </div>
                </div>
              )}

              {/* El grafo: los pasos */}
              {nodes.length > 0 && (
                <div className="glass-surface rounded-2xl p-5">
                  <h3 className="text-sm font-medium text-ink mb-3">
                    Plan · {nodes.length} paso(s)
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
                              <span className="ml-2 text-[10px] text-signal-warn">pide permiso</span>
                            )}
                          </p>
                          <p className="text-[10px] text-ink-faint mt-0.5">
                            {NODE_LABEL[n.state]}
                            {n.depends_on.length > 0 && ` · tras ${n.depends_on.join(", ")}`}
                            {n.duration_ms != null && ` · ${n.duration_ms} ms`}
                          </p>
                          {n.error && <p className="text-[11px] text-signal-error mt-1">{n.error}</p>}
                          {n.result?.output != null && n.state === "done" && (
                            <p className="text-[11px] text-ink-dim mt-1 line-clamp-3">
                              {String(n.result.output)}
                            </p>
                          )}
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
