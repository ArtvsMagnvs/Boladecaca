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

type Status = "idle" | "saving" | "loading" | "error" | "executing";

const AGENT_TYPE_OPTIONS = [
  { id: "generic", label: "Generico" },
  { id: "architect", label: "Arquitecto" },
  { id: "code", label: "Asistente de codigo" },
  { id: "research", label: "Investigacion" },
  { id: "custom", label: "Personalizado" },
];

const STATUS_COLOR: Record<string, string> = {
  pending: "text-ink-dim",
  running: "text-accent animate-pulse",
  completed: "text-signal-ok",
  failed: "text-signal-error",
  cancelled: "text-signal-warn",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

export default function Agents() {
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
      setErrorMsg(`Error cargando: ${(e as Error).message}`);
      setStatus("error");
    }
  }, []);

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
      setErrorMsg("El nombre es obligatorio");
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
      setErrorMsg(`Error guardando: ${(e as Error).message}`);
      setStatus("error");
    }
  };

  const deleteAgent = async () => {
    if (!selectedId) return;
    if (!confirm(`Eliminar agente "${formName}"? Esto borra tambien su historial de ejecuciones.`)) return;
    try {
      await api.deleteAgent(selectedId);
      setSelectedId(null);
      await refreshAgents();
    } catch (e) {
      setErrorMsg(`Error borrando: ${(e as Error).message}`);
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
      // Arranca polling para esta ejecucion
      pollExecution(ex.id);
    } catch (e) {
      setErrorMsg(`Error lanzando tarea: ${(e as Error).message}`);
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
      setErrorMsg(`Error cancelando: ${(e as Error).message}`);
    }
  };

  const deleteExecution = async (execId: number) => {
    try {
      await api.cancelOrDeleteExecution(execId);
      setExecutions((prev) => prev.filter((e) => e.id !== execId));
      if (activeExecId === execId) setActiveExecId(null);
    } catch (e) {
      setErrorMsg(`Error eliminando: ${(e as Error).message}`);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
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
          <h1 className="text-xl font-semibold text-ink">Agentes</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            Crea agentes con herramientas y lanza tareas sobre ellos.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedId(null)}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 hover:bg-accent/25 text-accent transition-colors"
          >
            + Nuevo agente
          </button>
        </div>
      </div>

      {/* COL 1: Lista de agentes */}
      <aside
        className="glass-surface rounded-2xl p-3 overflow-y-auto"
        style={{ minHeight: 0 }}
      >
        <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-3 px-1">
          Lista ({agents?.length ?? 0})
        </h3>
        {agents === null ? (
          <div className="text-xs text-ink-faint px-2">Cargando...</div>
        ) : agents.length === 0 ? (
          <div className="text-xs text-ink-faint px-2 py-4">
            Aun no hay agentes. Pulsa "+ Nuevo agente" para crear uno.
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
            {selectedId ? `Editar: ${formName || "(sin nombre)"}` : "Nuevo agente"}
          </h2>
          {selectedId && (
            <button
              onClick={deleteAgent}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error hover:bg-signal-error/25 transition-colors"
            >
              Eliminar
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Nombre *">
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="ej. Architect"
              className="form-input"
            />
          </Field>
          <Field label="Tipo">
            <select
              value={formType}
              onChange={(e) => setFormType(e.target.value)}
              className="form-input"
            >
              {AGENT_TYPE_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Descripcion">
          <input
            value={formDesc}
            onChange={(e) => setFormDesc(e.target.value)}
            placeholder="Que hace este agente"
            className="form-input"
          />
        </Field>

        <Field label="System prompt">
          <textarea
            value={formPrompt}
            onChange={(e) => setFormPrompt(e.target.value)}
            placeholder="Eres un agente especializado en..."
            rows={4}
            className="form-input resize-y"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Timeout maximo (segundos)">
            <input
              type="number"
              min={1}
              max={3600}
              value={formTimeout}
              onChange={(e) => setFormTimeout(parseInt(e.target.value) || 60)}
              className="form-input"
            />
          </Field>
          <Field label="Activo">
            <label className="flex items-center gap-2 h-10 px-3 rounded-lg bg-base-900/40 cursor-pointer">
              <input
                type="checkbox"
                checked={formActive}
                onChange={(e) => setFormActive(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
              <span className="text-sm text-ink">
                {formActive ? "Si" : "No"}
              </span>
            </label>
          </Field>
        </div>

        {/* Tools multi-select */}
        <Field label="Herramientas permitidas">
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
                    <p className="text-sm font-medium text-ink truncate">{tool.name}</p>
                    <p className="text-[10px] text-ink-faint line-clamp-2">{tool.description}</p>
                    <p className="text-[10px] text-accent mt-0.5">
                      {tool.actions.length} accion{tool.actions.length !== 1 ? "es" : ""}
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
              ? "Guardando..."
              : selectedId
              ? "Guardar cambios"
              : "Crear agente"}
          </button>
        </div>
      </section>

      {/* COL 3: Panel de ejecucion */}
      <aside
        className="glass-surface rounded-2xl p-4 flex flex-col overflow-hidden"
        style={{ minHeight: 0 }}
      >
        <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-3">
          Ejecucion
        </h3>

        {!selectedId ? (
          <div className="text-xs text-ink-faint px-2 py-4">
            Selecciona un agente de la izquierda para poder lanzar tareas.
          </div>
        ) : (
          <>
            {/* Input nueva tarea */}
            <div className="space-y-2">
              <textarea
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                placeholder="Describe la tarea para el agente..."
                rows={3}
                className="form-input resize-y text-sm"
              />
              <button
                onClick={executeTask}
                disabled={!taskInput.trim() || status === "executing"}
                className="w-full px-3 py-2 rounded-lg bg-accent text-base-950 font-medium text-sm hover:bg-accent-glow transition-colors disabled:opacity-50"
              >
                {status === "executing" ? "Lanzando..." : "Ejecutar"}
              </button>
            </div>

            {/* Historial */}
            <div className="mt-5 flex-1 flex flex-col min-h-0">
              <h4 className="text-[10px] uppercase tracking-wider text-ink-faint mb-2">
                Historial ({executions.length})
              </h4>
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {executions.length === 0 && (
                  <p className="text-xs text-ink-faint px-2 py-2">
                    Aun no hay ejecuciones para este agente.
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
          {execution.task_description || "(sin descripcion)"}
        </p>
        <span className={`text-[10px] font-medium shrink-0 ${STATUS_COLOR[execution.status] || "text-ink-faint"}`}>
          {STATUS_LABEL[execution.status] || execution.status}
        </span>
      </div>
      {toolCalls.length > 0 && (
        <p className="text-[10px] text-ink-faint mt-1.5">
          {toolCalls.length} tool{toolCalls.length !== 1 ? "s" : ""}: {toolCalls.map((tc) => tc.tool_id).join(", ")}
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
          Cancelar
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
          Eliminar
        </button>
      )}
    </div>
  );
}
