// Agents.tsx - Pagina de gestion de agentes V0.5 (Fase 2 AgentManager + ExecutionEngine)
//
// Estructura (CSS Grid 3 zonas):
//   ┌────────────────┬─────────────────────┬──────────────────────┐
//   │  LISTA         │   FORMULARIO         │   PANEL EJECUCION    │
//   │  de agentes    │   crear / editar     │   (chat historico +  │
//   │  con click     │   con selector de    │   input nueva tarea + │
//   │  para editar   │   tools (multi)      │   lista de ultimas   │
//   │                │                      │   ejecuciones)        │
//   └────────────────┴─────────────────────┴──────────────────────┘

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, type Agent, type AgentExecution, type ToolInfo } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useConfirm } from "@/components/ConfirmDialog";
import { useT } from "@/store/useI18n";

type Status = "idle" | "saving" | "loading" | "error" | "executing";

const AGENT_TYPE_KEYS = [
  { id: "generic", key: "agents.type.generic" },
  { id: "architect", key: "agents.type.architect" },
  { id: "code", key: "agents.type.code" },
  { id: "research", key: "agents.type.research" },
  { id: "custom", key: "agents.type.custom" },
];

const STATUS_COLOR: Record<string, string> = {
  pending: "text-ink-dim",
  running: "text-accent animate-pulse",
  completed: "text-signal-ok",
  failed: "text-signal-error",
  cancelled: "text-signal-warn",
};

const STATUS_KEY: Record<string, string> = {
  pending: "agents.status.pending",
  running: "agents.status.running",
  completed: "agents.status.completed",
  failed: "agents.status.failed",
  cancelled: "agents.status.cancelled",
};

export default function Agents() {
  const t = useT();
  const [confirm, confirmDialog] = useConfirm();
  // --- Estado global de la pagina ---
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // --- Estado del agente seleccionado (null = modo "nuevo") ---
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selectedAgent = useMemo(
    () => agents?.find((a) => a.id === selectedId) ?? null,
    [agents, selectedId],
  );

  // --- Form state ---
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("generic");
  const [formDesc, setFormDesc] = useState("");
  const [formPrompt, setFormPrompt] = useState("");
  const [formTools, setFormTools] = useState<string[]>([]);
  // Qué descripciones de tool están desplegadas (se cortaban a 2 líneas y no
  // había forma de leer los límites de seguridad de cada una).
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [formTimeout, setFormTimeout] = useState(300);
  const [formActive, setFormActive] = useState(true);

  // --- Estado de ejecucion ---
  const [taskInput, setTaskInput] = useState("");
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [activeExecId, setActiveExecId] = useState<number | null>(null);
  // V0.8.1 (Paso 2): cableado del nucleo al ciclo de vida de ejecucion.
  // Granular selector para no re-render por cambios de coreState (pitfall #4).
  const setCoreState = useAppStore((s) => s.setCoreState);
  const pulseError   = useAppStore((s) => s.pulseError);
  // Guardamos el id de la ejecucion que esta animando el nucleo; si el
  // componente se desmonta a mitad, el cleanup del useEffect de abajo lo
  // devuelve a idle.
  const nucleoExecIdRef = useRef<number | null>(null);

  // ------------------------------------------------------------------
  // Carga inicial
  // ------------------------------------------------------------------

  const refreshAgents = useCallback(async () => {
    try {
      setStatus("loading");
      const [a, t] = await Promise.all([api.getAgents(), api.getTools()]);
      setAgents(a || []);
      setTools(t?.tools || []);
      setStatus("idle");
    } catch (e) {
      setErrorMsg(t("agents.error.load", { msg: (e as Error).message }));
      setStatus("error");
    }
  }, [t]);

  useEffect(() => {
    refreshAgents();
  }, [refreshAgents]);

  // Carga ejecuciones cuando cambia el agente seleccionado.
  useEffect(() => {
    if (!selectedId) {
      setExecutions([]);
      return;
    }
    api
      .getAgentExecutions(selectedId, 50)
      .then((ex) => setExecutions(ex || []))
      .catch(() => setExecutions([]));
  }, [selectedId]);

  // ------------------------------------------------------------------
  // Sincroniza el formulario con el agente seleccionado
  // ------------------------------------------------------------------

  useEffect(() => {
    if (!selectedAgent) {
      // Modo "nuevo" - reset
      setFormName("");
      setFormType("generic");
      setFormDesc("");
      setFormPrompt("");
      setFormTools([]);
      setFormTimeout(300);
      setFormActive(true);
      return;
    }
    setFormName(selectedAgent.name);
    setFormType(selectedAgent.agent_type || "generic");
    setFormDesc(selectedAgent.description || "");
    setFormPrompt(selectedAgent.system_prompt || "");
    setFormTools(selectedAgent.allowed_tools || []);
    setFormTimeout(selectedAgent.max_execution_time || 300);
    setFormActive(selectedAgent.is_active);
  }, [selectedAgent]);

  // ------------------------------------------------------------------
  // Guardar (crear o actualizar)
  // ------------------------------------------------------------------

  const saveAgent = async () => {
    if (!formName.trim()) {
      setErrorMsg(t("agents.nameRequired"));
      setStatus("error");
      return;
    }
    setStatus("saving");
    setErrorMsg(null);
    const payload = {
      name: formName.trim(),
      agent_type: formType,
      description: formDesc.trim() || null,
      system_prompt: formPrompt.trim() || null,
      allowed_tools: formTools,
      max_execution_time: formTimeout,
      is_active: formActive,
    };
    try {
      let saved: Agent;
      if (selectedId) {
        saved = await api.updateAgent(selectedId, payload);
      } else {
        saved = await api.createAgent(payload);
        setSelectedId(saved.id);
      }
      await refreshAgents();
      setStatus("idle");
    } catch (e) {
      setErrorMsg(t("agents.error.save", { msg: (e as Error).message }));
      setStatus("error");
    }
  };

  const deleteAgent = async () => {
    if (!selectedId) return;
    if (!(await confirm({
      title: t("agents.deleteConfirm.title", { name: formName }),
      message: t("agents.deleteConfirm.message"),
      confirmLabel: t("agents.deleteConfirm.confirmLabel"),
    }))) return;
    try {
      await api.deleteAgent(selectedId);
      setSelectedId(null);
      await refreshAgents();
    } catch (e) {
      setErrorMsg(t("agents.error.delete", { msg: (e as Error).message }));
      setStatus("error");
    }
  };

  // ------------------------------------------------------------------
  // Ejecucion de tareas
  // ------------------------------------------------------------------

  const executeTask = async () => {
    if (!selectedId || !taskInput.trim()) return;
    setStatus("executing");
    setErrorMsg(null);
    try {
      const ex = await api.executeAgent(selectedId, taskInput.trim());
      setActiveExecId(ex.id);
      setTaskInput("");
      // Refresca el historial
      const list = await api.getAgentExecutions(selectedId, 50);
      setExecutions(list || []);
      // V0.8.1 (Paso 2): ejecucion lanzada, nucleo en "processing".
      // Se mantendra aqui hasta que el useEffect de abajo vea que la
      // ejecucion ha terminado (status terminal).
      nucleoExecIdRef.current = ex.id;
      setCoreState("processing");
      setStatus("idle");
      // Arranca polling para esta ejecucion. Se GUARDA su cancelador: antes se
      // descartaba y la cadena de sondeos quedaba viva tras salir de la pagina.
      pollCancelRef.current?.();          // corta el sondeo anterior, si lo hubiera
      pollCancelRef.current = pollExecution(ex.id);
    } catch (e) {
      setErrorMsg(t("agents.error.launch", { msg: (e as Error).message }));
      setStatus("error");
      pulseError();
    }
  };

  // V0.8.1 (Paso 2): si el usuario sale de /agents mientras una ejecucion
  // sigue corriendo, devolvemos el nucleo a idle para no dejarlo pegado
  // en "processing". Tambien cubrimos el caso de error en el lanzamiento.
  useEffect(() => {
    return () => {
      if (nucleoExecIdRef.current !== null) {
        setCoreState("idle");
        nucleoExecIdRef.current = null;
      }
    };
  }, [setCoreState]);

  // V0.8.1 (Paso 2): cuando la ejecucion activa pasa a estado terminal,
  // el nucleo vuelve a idle. Es la unica forma de soltar el processing
  // porque pollExecution hace await en bucle sin devolvernos una promesa.
  useEffect(() => {
    if (activeExecId === null) return;
    const ex = executions.find((e) => e.id === activeExecId);
    if (!ex) return;
    const isTerminal =
      ex.status === "completed" ||
      ex.status === "failed" ||
      ex.status === "cancelled";
    if (isTerminal && nucleoExecIdRef.current === activeExecId) {
      nucleoExecIdRef.current = null;
      // Usamos pulseError para que el nucleo haga un pulso rojo breve
      // y vuelva solo a idle (pitfall #3 de aithera-hub-corestate).
      if (ex.status === "failed") {
        pulseError();
      } else {
        setCoreState("idle");
      }
    }
  }, [executions, activeExecId, setCoreState, pulseError]);

  // [Fix 2026-07-19] El sondeo se CANCELA al desmontar. Antes, quien llamaba
  // descartaba la función de limpieza que esto devuelve (línea del `executeTask`),
  // así que la cadena `setTimeout(tick, 1500)` seguía viva para siempre: al
  // navegar fuera, `AppLayout` desmonta la página (key={pathname}) pero el
  // temporizador seguía pidiendo la ejecución cada 1,5s, y cada visita nueva
  // apilaba OTRA cadena. Esas peticiones eternas son las que agotaban las 6
  // conexiones del navegador y dejaban la UI esperando.
  //
  // Por qué salió ahora y no antes: hasta R4 una ejecución era la demo de V0.5 y
  // terminaba al instante, así que el sondeo se paraba solo y la fuga no se
  // notaba. Desde R4 es una misión real del TIE que dura minutos.
  const pollCancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      pollCancelRef.current?.();
      pollCancelRef.current = null;
    };
  }, []);

  const pollExecution = useCallback((execId: number) => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      try {
        const ex = await api.getExecution(execId);
        setActiveExecId((cur) => (cur === execId ? execId : cur));
        // Actualizamos la lista de ejecuciones
        setExecutions((prev) => {
          const idx = prev.findIndex((p) => p.id === execId);
          if (idx === -1) return [ex, ...prev];
          const next = [...prev];
          next[idx] = ex;
          return next;
        });
        if (ex.status === "pending" || ex.status === "running") {
          setTimeout(tick, 1500);
        }
      } catch {
        // Silenciar errores de polling
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, []);

  const cancelExecution = async (execId: number) => {
    try {
      await api.cancelOrDeleteExecution(execId);
      // Refresca
      if (selectedId) {
        const list = await api.getAgentExecutions(selectedId, 50);
        setExecutions(list || []);
      }
      setActiveExecId(null);
      // V0.8.1 (Paso 2): cancelacion manual -> nucleo a idle inmediato
      if (nucleoExecIdRef.current === execId) {
        nucleoExecIdRef.current = null;
        setCoreState("idle");
      }
    } catch (e) {
      setErrorMsg(t("agents.error.cancel", { msg: (e as Error).message }));
    }
  };

  const deleteExecution = async (execId: number) => {
    try {
      await api.cancelOrDeleteExecution(execId);
      setExecutions((prev) => prev.filter((e) => e.id !== execId));
      if (activeExecId === execId) setActiveExecId(null);
    } catch (e) {
      setErrorMsg(t("agents.error.remove", { msg: (e as Error).message }));
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <>
    {confirmDialog}
    <div
      className="h-full gap-4 p-2"
      style={{
        display: "grid",
        gridTemplateColumns: "260px 1fr 360px",
        gridTemplateRows: "auto 1fr",
        minHeight: "100%",
      }}
    >
      {/* Cabecera */}
      <div
        className="col-span-3 flex items-center justify-between"
        style={{ gridColumn: "1 / -1" }}
      >
        <div>
          <h1 className="text-xl font-semibold text-ink">{t("agents.title")}</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            {t("agents.subtitle")}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedId(null)}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 hover:bg-accent/25 text-accent transition-colors"
          >
            {t("agents.newAgent")}
          </button>
        </div>
      </div>

      {/* COL 1: Lista de agentes */}
      <aside
        className="glass-surface rounded-2xl p-3 overflow-y-auto"
        style={{ minHeight: 0 }}
      >
        <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-3 px-1">
          {t("agents.list.title", { n: agents?.length ?? 0 })}
        </h3>
        {agents === null ? (
          <div className="text-xs text-ink-faint px-2">{t("agents.list.loading")}</div>
        ) : agents.length === 0 ? (
          <div className="text-xs text-ink-faint px-2 py-4">
            {t("agents.list.empty")}
          </div>
        ) : (
          <ul className="space-y-1">
            {agents.map((a) => (
              <li
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`cursor-pointer rounded-lg px-3 py-2 transition-colors ${
                  selectedId === a.id
                    ? "bg-accent/15 ring-1 ring-accent/30"
                    : "hover:bg-base-800/40"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-ink truncate font-medium">{a.name}</span>
                  <span
                    className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                      a.is_active ? "bg-signal-ok" : "bg-ink-faint"
                    }`}
                  />
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-ink-faint">{a.agent_type}</span>
                  {a.allowed_tools && a.allowed_tools.length > 0 && (
                    <span className="text-[10px] text-accent">
                      {a.allowed_tools.length} tool{a.allowed_tools.length !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* COL 2: Formulario */}
      <section
        className="glass-surface rounded-2xl p-6 overflow-y-auto"
        style={{ minHeight: 0 }}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-medium text-ink">
            {selectedId ? t("agents.editTitle", { name: formName || t("agents.noName") }) : t("agents.newTitle")}
          </h2>
          {selectedId && (
            <button
              onClick={deleteAgent}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error hover:bg-signal-error/25 transition-colors"
            >
              {t("agents.delete")}
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label={t("agents.field.name")}>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder={t("agents.namePlaceholder")}
              className="form-input"
            />
          </Field>
          <Field label={t("agents.field.type")}>
            <select
              value={formType}
              onChange={(e) => setFormType(e.target.value)}
              className="form-input"
            >
              {AGENT_TYPE_KEYS.map((o) => (
                <option key={o.id} value={o.id}>{t(o.key)}</option>
              ))}
            </select>
          </Field>
        </div>

        <Field label={t("agents.field.description")}>
          <input
            value={formDesc}
            onChange={(e) => setFormDesc(e.target.value)}
            placeholder={t("agents.descPlaceholder")}
            className="form-input"
          />
        </Field>

        <Field label={t("agents.field.systemPrompt")}>
          <textarea
            value={formPrompt}
            onChange={(e) => setFormPrompt(e.target.value)}
            placeholder={t("agents.promptPlaceholder")}
            rows={4}
            className="form-input resize-y"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label={t("agents.field.timeout")}>
            <input
              type="number"
              min={1}
              max={3600}
              value={formTimeout}
              onChange={(e) => setFormTimeout(parseInt(e.target.value) || 60)}
              className="form-input"
            />
          </Field>
          <Field label={t("agents.field.active")}>
            <label className="flex items-center gap-2 h-10 px-3 rounded-lg bg-base-900/40 cursor-pointer">
              <input
                type="checkbox"
                checked={formActive}
                onChange={(e) => setFormActive(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
              <span className="text-sm text-ink">
                {formActive ? t("agents.yes") : t("agents.no")}
              </span>
            </label>
          </Field>
        </div>

        {/* Tools multi-select */}
        <Field label={t("agents.field.tools")}>
          <div className="grid grid-cols-2 gap-2">
            {tools.map((tool) => {
              const checked = formTools.includes(tool.tool_id);
              return (
                <label
                  key={tool.tool_id}
                  className={`flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    checked
                      ? "bg-accent/15 ring-1 ring-accent/30"
                      : "bg-base-900/40 hover:bg-base-800/40"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormTools((prev) => [...prev, tool.tool_id]);
                      } else {
                        setFormTools((prev) => prev.filter((t) => t !== tool.tool_id));
                      }
                    }}
                    className="h-4 w-4 mt-0.5 accent-accent"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-ink">{tool.name}</p>
                    {/* La descripción explica QUÉ puede hacer la tool y con qué
                        límites de seguridad — cortarla a 2 líneas ocultaba justo
                        esa parte. Ahora se despliega entera bajo demanda. */}
                    <p className={`text-[10px] text-ink-faint ${expandedTools.has(tool.tool_id) ? "" : "line-clamp-2"}`}>
                      {tool.description}
                    </p>
                    {(tool.description?.length ?? 0) > 90 && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();   // no marca/desmarca el checkbox del label
                          e.stopPropagation();
                          setExpandedTools((prev) => {
                            const next = new Set(prev);
                            next.has(tool.tool_id) ? next.delete(tool.tool_id) : next.add(tool.tool_id);
                            return next;
                          });
                        }}
                        className="text-[10px] text-accent hover:underline mt-0.5"
                      >
                        {expandedTools.has(tool.tool_id) ? t("agents.seeLess") : t("agents.seeMore")}
                      </button>
                    )}
                    <p className="text-[10px] text-accent mt-0.5">
                      {t("agents.actionsCount", { n: tool.actions.length })}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
        </Field>

        {/* Acciones */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-base-700/30">
          <AnimatePresence>
            {errorMsg && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="text-xs text-signal-error"
              >
                {errorMsg}
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={saveAgent}
            disabled={status === "saving"}
            className="ml-auto px-5 py-2 rounded-lg bg-accent text-base-950 font-medium text-sm hover:bg-accent-glow transition-colors disabled:opacity-50"
          >
            {status === "saving"
              ? t("agents.saving")
              : selectedId
              ? t("agents.saveChanges")
              : t("agents.create")}
          </button>
        </div>
      </section>

      {/* COL 3: Panel de ejecucion */}
      <aside
        className="glass-surface rounded-2xl p-4 flex flex-col overflow-hidden"
        style={{ minHeight: 0 }}
      >
        <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-3">
          {t("agents.execution.title")}
        </h3>

        {!selectedId ? (
          <div className="text-xs text-ink-faint px-2 py-4">
            {t("agents.execution.selectPrompt")}
          </div>
        ) : (
          <>
            {/* Input nueva tarea */}
            <div className="space-y-2">
              <textarea
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                placeholder={t("agents.execution.taskPlaceholder")}
                rows={3}
                className="form-input resize-y text-sm"
              />
              <button
                onClick={executeTask}
                disabled={!taskInput.trim() || status === "executing"}
                className="w-full px-3 py-2 rounded-lg bg-accent text-base-950 font-medium text-sm hover:bg-accent-glow transition-colors disabled:opacity-50"
              >
                {status === "executing" ? t("agents.execution.launching") : t("agents.execution.run")}
              </button>
            </div>

            {/* Historial */}
            <div className="mt-5 flex-1 flex flex-col min-h-0">
              <h4 className="text-[10px] uppercase tracking-wider text-ink-faint mb-2">
                {t("agents.execution.history", { n: executions.length })}
              </h4>
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {executions.length === 0 && (
                  <p className="text-xs text-ink-faint px-2 py-2">
                    {t("agents.execution.empty")}
                  </p>
                )}
                {executions.map((ex) => (
                  <ExecutionCard
                    key={ex.id}
                    execution={ex}
                    isActive={ex.id === activeExecId}
                    onSelect={() => setActiveExecId(ex.id)}
                    onCancel={() => cancelExecution(ex.id)}
                    onDelete={() => deleteExecution(ex.id)}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </aside>
    </div>
    </>
  );
}

// ----------------------------------------------------------------------
// Subcomponentes
// ----------------------------------------------------------------------

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}

function ExecutionCard({
  execution,
  isActive,
  onSelect,
  onCancel,
  onDelete,
}: {
  execution: AgentExecution;
  isActive: boolean;
  onSelect: () => void;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  const isRunning = execution.status === "running" || execution.status === "pending";
  const toolCalls: { tool_id: string; action: string; ok: boolean }[] = (() => {
    try {
      return execution.tool_calls ? JSON.parse(execution.tool_calls) : [];
    } catch {
      return [];
    }
  })();

  return (
    <div
      onClick={onSelect}
      className={`rounded-lg p-3 cursor-pointer transition-colors ${
        isActive
          ? "bg-accent/10 ring-1 ring-accent/30"
          : "bg-base-900/40 hover:bg-base-800/40"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-ink line-clamp-2 flex-1">
          {execution.task_description || t("agents.execution.noDescription")}
        </p>
        <span className={`text-[10px] font-medium shrink-0 ${STATUS_COLOR[execution.status] || "text-ink-faint"}`}>
          {STATUS_KEY[execution.status] ? t(STATUS_KEY[execution.status]) : execution.status}
        </span>
      </div>
      {toolCalls.length > 0 && (
        <p className="text-[10px] text-ink-faint mt-1.5">
          {t("agents.execution.toolsCount", { n: toolCalls.length, list: toolCalls.map((tc) => tc.tool_id).join(", ") })}
        </p>
      )}
      {execution.status === "completed" && execution.result && (
        <p className="text-[11px] text-ink-dim mt-1.5 line-clamp-3">
          {execution.result}
        </p>
      )}
      {execution.error_message && (
        <p className="text-[11px] text-signal-error mt-1.5 line-clamp-2">
          {execution.error_message}
        </p>
      )}
      {isRunning && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          className="mt-2 text-[10px] px-2 py-1 rounded bg-signal-warn/15 text-signal-warn hover:bg-signal-warn/25"
        >
          {t("agents.execution.cancel")}
        </button>
      )}
      {!isRunning && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="mt-2 text-[10px] px-2 py-1 rounded bg-base-700/30 text-ink-faint hover:bg-base-700/60"
        >
          {t("agents.execution.delete")}
        </button>
      )}
    </div>
  );
}
