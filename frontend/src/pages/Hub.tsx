// Hub.tsx — Pantalla principal de Aithera V0.3 (Fase 1 Estabilizacion Hub).
//
// Layout CSS Grid 280px / 1fr / 280px:
//   ┌─────────────┬─────────────────┬─────────────┐
//   │  Proyectos  │                 │  Próximos   │
//   │  Tareas     │   AI Core 3D    │  eventos    │
//   │  Agentes    │   (núcleo)      │  Chat       │
//   │             │                 │  (Email V7) │
//   ├─────────────┴─────────────────┴─────────────┤
//   │ Barra de estado: Backend ● | IA: ... | Voz  │
//   └─────────────────────────────────────────────┘
//
// Decisiones de diseño (Fase_1_Estabilizacion_Hub_V03.md):
// - Polling cada 30s para datos de los paneles y la barra de estado.
// - Clic en un proyecto → /projects, en tarea → /tasks, en AI Core → /chat.
// - AICore.tsx NO se modifica (es el corazón visual del producto y tiene
//   sus propios tests visuales).

import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  CoreSelectorButton,
  CoreModelView,
  loadStoredModel,
  type CoreModelId,
} from "@/components/hub/CoreSelector";
import { CoreDesignPanel } from "@/components/hub/CoreDesignPanel";
import {
  DEFAULT_CORE_DESIGN,
  loadStoredCoreDesigns,
  saveStoredCoreDesigns,
  type CoreDesignSettings,
} from "@/components/hub/coreDesign";

// Clave de localStorage para persistir el nucleo 3D seleccionado.
// Compartida con CoreSelector (mismo modulo la define).
const CORE_MODEL_STORAGE_KEY = "aithera.coreModel";
import { HubPanel } from "@/components/hub/HubPanel";
import { api, type Project, type Task, type CalendarEvent } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

// V0.7 extra (Fase 4): tipos para el estado real de Email en el Hub
interface EmailStatus {
  connected: boolean;
  email: string | null;
  has_credentials: boolean;
  libs_available: boolean;
}

const PRIORITY_COLOR: Record<string, string> = {
  high: "text-signal-error",
  medium: "text-signal-warn",
  low: "text-signal-ok",
};

// Tipos auxiliares para los endpoints que devuelve el backend V0.3
interface AgentItem {
  id: number;
  name: string;
  agent_type?: string | null;
  description?: string | null;
  system_prompt?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

interface ChatHistoryItem {
  role: string;
  content: string;
  created_at: string;
}

interface VoiceStatusInfo {
  configured: boolean;
  voices_count: number;
  message: string;
  source: "elevenlabs" | "espeak" | "none";
}

const HUB_POLL_INTERVAL_MS = 30_000;

export default function Hub() {
  const navigate = useNavigate();
  const { backendConnected, aiStatus, coreState } = useAppStore();

  // Datos crudos del backend (null = cargando, [] = ya cargado pero vacío)
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [events, setEvents] = useState<CalendarEvent[] | null>(null);
  const [agents, setAgents] = useState<AgentItem[] | null>(null);
  const [chatRecent, setChatRecent] = useState<ChatHistoryItem[] | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatusInfo | null>(null);
  // V0.7 extra: estado real de Email en el Hub
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  // V0.7.3 (Sprint 4, B7): digest diario del Email Assistant
  const [digest, setDigest] = useState<{
    triaged_total: number;
    urgent_pending: number;
    drafts_awaiting: number;
    meetings: { today: number; pending: number };
  } | null>(null);
  const [proposalsCount, setProposalsCount] = useState<{ pending: number; counter_sent: number; confirmed: number }>({
    pending: 0, counter_sent: 0, confirmed: 0,
  });
  // Nucleo 3D seleccionable desde la cabecera del Hub.
  // Persiste en localStorage (lo hacemos aqui directamente porque el
  // state vive en el Hub, no dentro de CoreSelector wrapper).
  const [coreModel, setCoreModel] = useState<CoreModelId>(loadStoredModel);
  const [coreDesigns, setCoreDesigns] = useState(loadStoredCoreDesigns);
  const currentCoreDesign = coreDesigns[coreModel] ?? DEFAULT_CORE_DESIGN;

  useEffect(() => {
    try {
      window.localStorage.setItem(CORE_MODEL_STORAGE_KEY, coreModel);
    } catch {
      // localStorage no disponible (modo incognito, etc.) — fallback silencioso.
    }
  }, [coreModel]);

  useEffect(() => {
    saveStoredCoreDesigns(coreDesigns);
  }, [coreDesigns]);

  const updateCurrentCoreDesign = useCallback((patch: Partial<CoreDesignSettings>) => {
    setCoreDesigns((prev) => ({
      ...prev,
      [coreModel]: {
        ...(prev[coreModel] ?? DEFAULT_CORE_DESIGN),
        ...patch,
      },
    }));
  }, [coreModel]);

  const resetCurrentCoreDesign = useCallback(() => {
    setCoreDesigns((prev) => ({
      ...prev,
      [coreModel]: { ...DEFAULT_CORE_DESIGN },
    }));
  }, [coreModel]);

  /**
   * Carga simultánea de los datos del Hub. Centralizado en una sola
   * función para que el efecto inicial y el intervalo de 30s compartan
   * exactamente la misma secuencia de llamadas (y evitar refetch
   * desalineados que vuelvan a parpadear los paneles).
   */
  const loadHubData = useCallback(async () => {
    // Pequeño helper para no abortar componentes desmontados.
    let cancelled = false;
    const safeSet = <T,>(setter: (v: T | null) => void, value: T | null) => {
      if (!cancelled) setter(value);
    };

    // Proyectos: limit=5 para el panel izquierdo.
    api.getProjects(0, 5)
      .then((d) => safeSet(setProjects, d ?? []))
      .catch(() => safeSet(setProjects, []));

    // Tareas: limit=5 para el panel izquierdo.
    api.getTasks(0, 5)
      .then((d) => safeSet(setTasks, d ?? []))
      .catch(() => safeSet(setTasks, []));

    // Eventos: limit=5 ordenados por start_date ASC (lo hace el backend).
    api.getEvents(0, 5)
      .then((d) => safeSet(setEvents, d ?? []))
      .catch(() => safeSet(setEvents, []));

    // Agentes: el panel los filtra por is_active=true en frontend.
    api.getAgents()
      .then((d) => safeSet(setAgents, (d as AgentItem[]) ?? []))
      .catch(() => safeSet(setAgents, []));

    // Chat reciente: limit=3 (devuelve los ultimos 3 mensajes del historial).
    api.getChatHistory(3)
      .then((d) => safeSet(setChatRecent, d ?? []))
      .catch(() => safeSet(setChatRecent, []));

    // Estado del motor de voz (estructura plana desde V0.3).
    api.getVoiceStatus()
      .then((d) =>
        safeSet<VoiceStatusInfo>(setVoiceStatus, {
          configured: d.configured,
          voices_count: d.voices_count,
          message: d.message,
          source: d.source,
        }),
      )
      .catch(() =>
        safeSet<VoiceStatusInfo>(setVoiceStatus, {
          configured: false,
          voices_count: 0,
          message: "Voz no disponible",
          source: "none",
        }),
      );

    // Tambien refresca el estado de backend e IA en el store global
    // (asi la barra inferior se actualiza junto con el resto del Hub).
    useAppStore.getState().refreshBackendStatus();
    useAppStore.getState().refreshAIStatus();

    // V0.7 extra: estado real de Email (conexion Google + propuestas).
    // V0.7.3 (Sprint 4, B7): digest diario (solo BD local, barato)
    api.getDigest()
      .then((d) => safeSet(setDigest, d))
      .catch(() => safeSet(setDigest, null));
    api.getEmailStatus()
      .then((d) => safeSet<EmailStatus>(setEmailStatus, d))
      .catch(() => safeSet<EmailStatus>(setEmailStatus, {
        connected: false, email: null, has_credentials: false, libs_available: false,
      }));
    api.listProposals()
      .then((d) => {
        const counts = { pending: 0, counter_sent: 0, confirmed: 0 };
        for (const p of d.proposals || []) {
          if (p.status === "pending") counts.pending++;
          else if (p.status === "counter_sent") counts.counter_sent++;
          else if (p.status === "confirmed") counts.confirmed++;
        }
        // safeSet exige T | null, asi que pasamos null si falla o el valor
        setProposalsCount(counts);
      })
      .catch(() => setProposalsCount({ pending: 0, counter_sent: 0, confirmed: 0 }));

    return () => {
      cancelled = true;
    };
  }, []);

  // Carga inicial + polling cada 30s
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    loadHubData().then((c) => {
      cleanup = c;
    });
    const interval = setInterval(loadHubData, HUB_POLL_INTERVAL_MS);
    return () => {
      clearInterval(interval);
      if (cleanup) cleanup();
    };
  }, [loadHubData]);

  // ----- Filtros y derivados ---------------------------------------------

  // Proyectos activos: status === 'active' (V0.3 pide "top 5 proyectos activos").
  const activeProjects = (projects ?? []).filter((p) => p.status === "active").slice(0, 5);

  // Tareas pendientes: status === 'pending' o 'in_progress'.
  const pendingTasks = (tasks ?? [])
    .filter((t) => t.status === "pending" || t.status === "in_progress")
    .slice(0, 5);

  // Agentes activos: filtrar en frontend (is_active === true).
  const activeAgents = (agents ?? []).filter((a) => a.is_active).slice(0, 5);

  // Próximos eventos: el backend ya devuelve ordenados ASC por start_date.
  const upcomingEvents = (events ?? []).slice(0, 5);

  // Últimas 3 conversaciones del chat.
  const recentChat = (chatRecent ?? []).slice(-3);

  return (
    <div
      className="hub-grid relative h-full gap-4"
      style={{
        display: "grid",
        // gridTemplateColumns se define en index.css (.hub-grid) con
        // minmax(0,...) + breakpoints para que las columnas se encojan en vez
        // de desbordar (la barra derecha ya no se sale de pantalla).
        gridTemplateRows: "1fr auto",
        minHeight: "100%",
        width: "100%",
        maxWidth: "100%",
      }}
    >
      {/* CABECERA FLOTANTE — boton discreto para cambiar el nucleo 3D.
          Posicion absoluta en la parte superior del Hub, centrado. */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20">
        <CoreSelectorButton value={coreModel} onChange={setCoreModel} />
      </div>

      {/* IZQUIERDA */}
      <div className="flex flex-col gap-4 min-h-0 overflow-y-auto pr-1">
        <HubPanel
          title="Proyectos activos"
          count={activeProjects.length}
          action={
            <button
              onClick={() => navigate("/projects")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              Ver todos →
            </button>
          }
        >
          {projects === null ? (
            <LoadingDots />
          ) : activeProjects.length === 0 ? (
            <EmptyState text="No hay proyectos activos." />
          ) : (
            <ul className="space-y-2">
              {activeProjects.map((p) => (
                <li
                  key={p.id}
                  onClick={() => navigate("/projects")}
                  className="flex items-center justify-between gap-3 cursor-pointer rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="h-1.5 w-1.5 rounded-full bg-accent/60 shrink-0" />
                    <span className="text-sm truncate text-ink">{p.name}</span>
                  </div>
                  <span
                    className={`text-[10px] font-semibold tracking-widest uppercase shrink-0 ${
                      PRIORITY_COLOR[p.priority] ?? "text-ink-dim"
                    }`}
                  >
                    {p.priority}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title="Tareas pendientes"
          count={pendingTasks.length}
          action={
            <button
              onClick={() => navigate("/tasks")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              Ver todas →
            </button>
          }
        >
          {tasks === null ? (
            <LoadingDots />
          ) : pendingTasks.length === 0 ? (
            <EmptyState text="No hay tareas pendientes." />
          ) : (
            <ul className="space-y-2">
              {pendingTasks.map((t) => (
                <li
                  key={t.id}
                  onClick={() => navigate("/tasks")}
                  className="flex items-center justify-between gap-3 cursor-pointer rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="h-1.5 w-1.5 rounded-full border border-ink-faint shrink-0" />
                    <span className="text-sm truncate text-ink">{t.title}</span>
                  </div>
                  <span
                    className={`text-[10px] font-semibold tracking-widest uppercase shrink-0 ${
                      PRIORITY_COLOR[t.priority] ?? "text-ink-dim"
                    }`}
                  >
                    {t.priority}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title="Agentes activos"
          count={activeAgents.length}
          action={
            <button
              onClick={() => navigate("/agents")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              Ver todos →
            </button>
          }
        >
          {agents === null ? (
            <LoadingDots />
          ) : activeAgents.length === 0 ? (
            <EmptyState text="No hay agentes activos." />
          ) : (
            <ul className="space-y-2">
              {activeAgents.map((a) => (
                <li
                  key={a.id}
                  onClick={() => navigate("/agents")}
                  className="flex items-center gap-3 rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 cursor-pointer transition-colors"
                >
                  <div className="h-6 w-6 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center text-accent text-[11px] font-bold shrink-0">
                    {(a.name?.[0] ?? "?").toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-ink truncate">{a.name}</p>
                    {a.description ? (
                      <p className="text-[10px] text-ink-faint truncate">{a.description}</p>
                    ) : a.agent_type ? (
                      <p className="text-[10px] text-ink-faint truncate">{a.agent_type}</p>
                    ) : null}
                  </div>
                  <span className="h-1.5 w-1.5 rounded-full bg-signal-ok shrink-0" />
                </li>
              ))}
            </ul>
          )}
        </HubPanel>
      </div>

      {/* CENTRO — Nucleo 3D seleccionable (Orbe azul / Bola de caca) */}
      <div className="flex flex-col items-center justify-center gap-3 min-h-0">
        <CoreModelView
          model={coreModel}
          size={900}
          design={currentCoreDesign}
          onNavigateToChat={() => navigate("/chat")}
        />

        <AnimatePresence mode="wait">
          <motion.div
            key={coreState}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="text-center"
          >
            <p className="text-sm font-medium text-ink">{coreStateLabel(coreState)}</p>
            <p className="text-xs text-ink-faint mt-1">
              {aiStatus?.fallback_active && aiStatus?.primary_provider
                ? `Fallback: ${aiStatus.provider} (por ${aiStatus.primary_provider} no disponible)`
                : aiStatus?.provider
                ? `${aiStatus.provider} · ${aiStatus.model ?? "sin modelo"}`
                : "Sin proveedor activo"}
            </p>
          </motion.div>
        </AnimatePresence>

        {import.meta.env.DEV && (
          <CoreDesignPanel
            model={coreModel}
            value={currentCoreDesign}
            onChange={updateCurrentCoreDesign}
            onReset={resetCurrentCoreDesign}
          />
        )}
      </div>

      {/* DERECHA */}
      <div className="flex flex-col gap-4 min-h-0 overflow-y-auto pr-1">
        <HubPanel
          title="Próximos eventos"
          count={upcomingEvents.length}
          action={
            <button
              onClick={() => navigate("/calendar")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              Ver todos →
            </button>
          }
        >
          {events === null ? (
            <LoadingDots />
          ) : upcomingEvents.length === 0 ? (
            <EmptyState text="No hay eventos próximos." />
          ) : (
            <ul className="space-y-2">
              {upcomingEvents.map((e) => (
                <li
                  key={e.id}
                  onClick={() => navigate("/calendar")}
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 cursor-pointer transition-colors"
                >
                  <div className="h-1.5 w-1.5 rounded-full bg-signal-ok/60 shrink-0" />
                  <span className="text-sm truncate text-ink flex-1">{e.title}</span>
                  <span className="text-[10px] text-ink-faint shrink-0">
                    {formatEventDate(e.start_date)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title="Chat reciente"
          count={recentChat.length}
          action={
            <button
              onClick={() => navigate("/chat")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              Abrir →
            </button>
          }
        >
          {chatRecent === null ? (
            <LoadingDots />
          ) : recentChat.length === 0 ? (
            <EmptyState text="Aún no hay conversaciones." />
          ) : (
            <ul className="space-y-2">
              {recentChat.map((m, idx) => (
                <li
                  key={`${m.created_at}-${idx}`}
                  className="rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 transition-colors"
                >
                  <p className="text-[10px] uppercase tracking-wider text-ink-faint mb-0.5">
                    {m.role === "user" ? "Tú" : "Aithera"}
                  </p>
                  <p className="text-sm text-ink line-clamp-2">{m.content}</p>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title="Email"
          action={
            <span
              className={`text-[10px] flex items-center gap-1 ${
                emailStatus?.connected
                  ? "text-signal-ok"
                  : emailStatus?.has_credentials
                  ? "text-amber-400"
                  : "text-ink-faint"
              }`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  emailStatus?.connected
                    ? "bg-signal-ok"
                    : emailStatus?.has_credentials
                    ? "bg-amber-400"
                    : "bg-ink-faint"
                }`}
              />
              V0.7
            </span>
          }
        >
          {/* V0.7 extra: estado real de Email (conexion + propuestas) */}
          {emailStatus === null ? (
            <p className="text-sm text-ink-faint">Cargando...</p>
          ) : emailStatus.connected ? (
            <>
              <p className="text-sm text-ink">
                <span className="text-signal-ok">●</span> Conectado como{" "}
                <span className="font-medium">{emailStatus.email}</span>
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">Pendientes</p>
                  <p className="text-base font-medium text-ink">{proposalsCount.pending}</p>
                </div>
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">Esperando OK</p>
                  <p className="text-base font-medium text-amber-300">{proposalsCount.counter_sent}</p>
                </div>
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">Confirmadas</p>
                  <p className="text-base font-medium text-signal-ok">{proposalsCount.confirmed}</p>
                </div>
              </div>
              {/* V0.7.3 (Sprint 4, B7): digest de hoy */}
              {digest && (
                <div className="mt-2 flex items-center justify-between text-[10px] px-2 py-1.5 rounded-lg bg-base-800/40">
                  <span className="text-ink-faint">Hoy:</span>
                  <span className="text-ink-dim">{digest.triaged_total} triados</span>
                  <span className={digest.urgent_pending > 0 ? "text-signal-error font-medium" : "text-ink-faint"}>
                    {digest.urgent_pending} urgentes
                  </span>
                  <span className={digest.drafts_awaiting > 0 ? "text-amber-300" : "text-ink-faint"}>
                    {digest.drafts_awaiting} borradores
                  </span>
                </div>
              )}
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 w-full"
              >
                Abrir Email Assistant
              </button>
            </>
          ) : emailStatus.has_credentials ? (
            <>
              <p className="text-sm text-amber-300">
                <span>●</span> Credenciales configuradas, sin OAuth activo
              </p>
              <p className="text-[10px] text-ink-faint mt-2">
                Pulsa "Conectar" en Email Assistant para abrir el browser y autorizar.
              </p>
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 w-full"
              >
                Ir a Email Assistant
              </button>
            </>
          ) : (
            <>
              <p className="text-sm text-ink-faint">
                <span className="text-ink-faint">●</span> Google no conectado
              </p>
              <p className="text-[10px] text-ink-faint mt-2">
                Necesitas client_id + client_secret de Google Cloud Console.
                Configuralo en Settings o pega las claves en el formulario de
                Email Assistant.
              </p>
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 w-full"
              >
                Configurar Email
              </button>
            </>
          )}
        </HubPanel>
      </div>

      {/* BARRA DE ESTADO INFERIOR — ocupa las 3 columnas */}
      <div
        className="glass-surface rounded-2xl px-5 py-2.5 flex items-center justify-between text-xs col-span-3"
        style={{ gridColumn: "1 / -1" }}
      >
        <SystemIndicator
          label={backendConnected ? "Backend ●" : "Backend ○"}
          color={backendConnected ? "bg-signal-ok" : "bg-signal-error"}
          pulse={!backendConnected}
          title={backendConnected ? "Backend conectado" : "Sin conexion con el backend"}
        />
        <SystemIndicator
          label={
            aiStatus?.fallback_active && aiStatus?.primary_provider
              ? `IA: ${capitalize(aiStatus.provider ?? "")} (fallback de ${capitalize(aiStatus.primary_provider)})`
              : aiStatus?.provider
              ? `IA: ${capitalize(aiStatus.provider)}`
              : "IA: —"
          }
          color={
            aiStatus?.fallback_active
              ? "bg-signal-warn"
              : aiStatus?.healthy
              ? "bg-signal-ok"
              : "bg-ink-faint"
          }
          title={
            aiStatus?.fallback_active
              ? `Sin conexion con ${aiStatus.primary_provider}; usando ${aiStatus.provider} como fallback`
              : aiStatus
              ? `${aiStatus.provider} / ${aiStatus.model ?? ""}`
              : "Sin proveedor"
          }
        />
        <SystemIndicator
          label={
            aiStatus?.model
              ? `${shortModelName(aiStatus.model)} ${aiStatus.healthy ? "✓" : "✗"}`
              : "Modelo: —"
          }
          color={
            aiStatus?.fallback_active
              ? "bg-signal-warn"
              : aiStatus?.healthy
              ? "bg-accent/60"
              : "bg-signal-warn"
          }
          title={
            aiStatus?.fallback_active
              ? `Fallback activo: ${aiStatus.provider}`
              : aiStatus?.model ?? "Sin modelo"
          }
        />
        <SystemIndicator
          label={`Voz: ${voiceStatus?.configured ? "ON" : "OFF"}`}
          color={voiceStatus?.configured ? "bg-signal-ok" : "bg-ink-faint"}
          title={voiceStatus?.message ?? "Sin informacion de voz"}
        />
        <SystemIndicator
          label={`Núcleo: ${coreStateLabel(coreState)}`}
          color={coreState === "error" ? "bg-signal-error" : "bg-accent/60"}
          pulse={coreState !== "idle"}
        />
      </div>
    </div>
  );
}

function SystemIndicator({
  label,
  color,
  pulse = false,
  title,
}: {
  label: string;
  color: string;
  pulse?: boolean;
  title?: string;
}) {
  return (
    <span
      className="flex items-center gap-1.5 text-ink-dim"
      title={title}
    >
      <span className={`relative h-1.5 w-1.5 rounded-full ${color}`}>
        {pulse && <span className={`absolute inset-0 rounded-full ${color} animate-ping opacity-60`} />}
      </span>
      {label}
    </span>
  );
}

function LoadingDots() {
  return (
    <div className="flex gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-ink-faint"
          style={{ animation: `dot-blink 1.4s ease-in-out ${i * 0.2}s infinite` }}
        />
      ))}
    </div>
  );
}

function coreStateLabel(state: string): string {
  const labels: Record<string, string> = {
    idle: "En reposo",
    listening: "Escuchando",
    thinking: "Pensando",
    speaking: "Hablando",
    processing: "Procesando",
    error: "Error",
  };
  return labels[state] ?? state;
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-ink-faint">{text}</p>;
}

/**
 * Acorta el identificador del modelo para la barra de estado (ej.
 * "MiniMax-M2.7-highspeed" -> "M2.7-hs") sin perder la informacion util.
 */
function shortModelName(model: string): string {
  if (!model) return "—";
  return model
    .replace(/^MiniMax-/i, "")
    .replace(/-highspeed$/i, "-hs")
    .replace(/^claude-/i, "claude-")
    .replace(/^gpt-/i, "gpt-");
}

function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Formatea la fecha de un evento de calendario (ISO string) a algo
 * compacto para el panel derecho (ej. "21 jun", "hoy 18:30", "mañana 09:00").
 */
function formatEventDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      return `hoy ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    if (d.toDateString() === tomorrow.toDateString()) {
      return `mañana ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    return d.toLocaleDateString([], { day: "2-digit", month: "short" });
  } catch {
    return "";
  }
}
