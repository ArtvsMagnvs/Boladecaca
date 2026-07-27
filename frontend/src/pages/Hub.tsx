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
// AVCS S1 (doc 13): el núcleo 3D del centro lo sustituye la <AitheraPresence/>,
// montada persistentemente en AppLayout (full-bleed, detrás de la UI). Los 6
// juguetes viejos (CoreSelector/AICore/AitheraSeed/PoopSphere/RasenganSphere/
// CoreDesignPanel) quedan en disco pero desconectados del árbol (recuperables
// por git; tree-shaking los excluye del bundle).
import { HubPanel } from "@/components/hub/HubPanel";
import { api, type Project, type Task, type CalendarEvent } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { shortRef } from "@/lib/modelNames";
import { useT } from "@/store/useI18n";

// V0.7 extra (Fase 4): tipos para el estado real de Email en el Hub
interface EmailStatus {
  connected: boolean;
  email: string | null;
  has_credentials: boolean;
  libs_available: boolean;
  // AUTH-1: sesión caducada/revocada se distingue de "sin OAuth".
  connection_state?: "connected" | "expired" | "revoked" | "no_token" | "no_credentials" | "libs_missing";
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
  // "none" es un estado LOCAL (backend inalcanzable) — el backend en sí ya
  // no lo emite desde A·VOZ-1 (EdgeTTS es fallback siempre disponible).
  source: "elevenlabs" | "edgetts" | "none";
}

const HUB_POLL_INTERVAL_MS = 30_000;

export default function Hub() {
  const navigate = useNavigate();
  const { backendConnected, aiStatus, chatPrimary, chatPrimaryDown, coreState } = useAppStore();
  const t = useT();

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
  // V0.85 (MOS M3): tarjeta Memoria — ultima ingesta, dias cubiertos, briefing de hoy.
  // V0.87 (WPMS W4, doc 18 §7): + señales operativas del Workspace (deadlines
  // próximos, tareas bloqueadas) — la misma consulta barata que ya hace
  // /api/memory/briefing, sin llamada extra.
  const [memoryCard, setMemoryCard] = useState<{
    summary: string;
    urgentCount: number;
    daysCovered: number;
    lastIngestAt: string | null;
    upcomingDeadlines: number;
    blockedTasks: number;
  } | null>(null);
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
          message: t("hub.voice.unavailable"),
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

    // V0.85 (MOS M3): tarjeta Memoria (briefing de hoy + ultima ingesta + dias
    // cubiertos). Tres llamadas independientes, barato y solo BD/Chroma local.
    Promise.all([
      api.getMemoryBriefing().catch(() => null),
      api.getMemoryIngestStatus().catch(() => null),
      api.getMemoryStats().catch(() => null),
    ]).then(([briefing, ingest, stats]) => {
      if (cancelled) return;
      if (!briefing && !ingest && !stats) {
        setMemoryCard(null);
        return;
      }
      const lastRuns = ingest
        ? Object.values(ingest.jobs)
            .map((j) => j.last_run?.finished_at)
            .filter((d): d is string => !!d)
        : [];
      const lastIngestAt = lastRuns.length ? lastRuns.sort().at(-1)! : null;
      setMemoryCard({
        summary: briefing?.summary ?? "",
        urgentCount: briefing?.urgent_pending.count ?? 0,
        daysCovered: stats?.mos_days_covered ?? 0,
        lastIngestAt,
        upcomingDeadlines: briefing?.workspace?.upcoming_deadlines.length ?? 0,
        blockedTasks: briefing?.workspace?.blocked.length ?? 0,
      });
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // Carga inicial + polling cada 30s.
  // [Opt v0.9.5, O3] El poll se pausa cuando la ventana NO está visible
  // (minimizada, otra pestaña): sondear el backend cada 30s sin que nadie mire
  // es carga inútil. Al volver a primer plano refresca de inmediato, así que el
  // usuario nunca ve datos rancios.
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    const refresh = () => {
      if (document.hidden) return;
      loadHubData().then((c) => { cleanup = c; });
    };
    refresh();
    const interval = setInterval(refresh, HUB_POLL_INTERVAL_MS);
    const onVisible = () => { if (!document.hidden) refresh(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
      if (cleanup) cleanup();
    };
  }, [loadHubData]);

  // ----- Filtros y derivados ---------------------------------------------

  // Proyectos activos: status === 'active' (V0.3 pide "top 5 proyectos activos").
  // V0.87 (WPMS W4): un proyecto archivado no cuenta como activo aunque su
  // status siga en "active" — archivar (archived_at) es independiente del
  // status, doc 18 §5.1.
  const activeProjects = (projects ?? []).filter((p) => p.status === "active" && !p.archived_at).slice(0, 5);

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
      {/* IZQUIERDA */}
      <div className="flex flex-col gap-4 min-h-0 overflow-y-auto pr-1">
        <HubPanel
          title={t("hub.projects.title")}
          count={activeProjects.length}
          action={
            <button
              onClick={() => navigate("/workspace")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              {t("hub.viewAll")} →
            </button>
          }
        >
          {projects === null ? (
            <LoadingDots />
          ) : activeProjects.length === 0 ? (
            <EmptyState text={t("hub.projects.empty")} />
          ) : (
            <ul className="space-y-2">
              {activeProjects.map((p) => (
                <li
                  key={p.id}
                  onClick={() => navigate("/workspace")}
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
          title={t("hub.tasks.title")}
          count={pendingTasks.length}
          action={
            <button
              onClick={() => navigate("/workspace")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              {t("hub.viewAllFem")} →
            </button>
          }
        >
          {tasks === null ? (
            <LoadingDots />
          ) : pendingTasks.length === 0 ? (
            <EmptyState text={t("hub.tasks.empty")} />
          ) : (
            <ul className="space-y-2">
              {pendingTasks.map((t) => (
                <li
                  key={t.id}
                  onClick={() => navigate("/workspace")}
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
          title={t("hub.agents.title")}
          count={activeAgents.length}
          action={
            <button
              onClick={() => navigate("/agents")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              {t("hub.viewAll")} →
            </button>
          }
        >
          {agents === null ? (
            <LoadingDots />
          ) : activeAgents.length === 0 ? (
            <EmptyState text={t("hub.agents.empty")} />
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

      {/* CENTRO — zona de la presencia (AVCS). La <AitheraPresence/> se
          renderiza full-bleed DETRAS (en AppLayout); esta columna solo deja el
          espacio libre y flota la etiqueta de estado + proveedor. Clic → chat. */}
      <div
        className="flex flex-col items-center justify-end gap-3 min-h-0 pb-6 cursor-pointer"
        onClick={() => navigate("/chat")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") navigate("/chat"); }}
        aria-label={t("hub.aria.openChat")}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={coreState}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="text-center"
          >
            {/* [2026-07-21] Tinta FIJA clara (los valores del tema oscuro):
                este texto flota directamente sobre el escenario oscuro del
                núcleo, que es idéntico en ambos temas — con text-ink normal,
                en tema claro sería tinta oscura sobre fondo oscuro. */}
            <p className="text-sm font-medium text-[#E8EAF0]">{coreStateLabel(coreState, t)}</p>
            <p className="text-xs text-[#9AA1B2] mt-1">
              {/* [2026-07-21] El modelo mostrado es el del CHAT según la
                  política ACTIVA (Inteligencia), no el proveedor legacy. */}
              {chatPrimary
                ? `${shortRef(chatPrimary)}${chatPrimaryDown ? " ⚠" : ""}`
                : aiStatus?.fallback_active && aiStatus?.primary_provider
                ? t("hub.status.fallback", { provider: aiStatus.provider, primary: aiStatus.primary_provider })
                : aiStatus?.provider
                ? `${aiStatus.provider} · ${aiStatus.model ?? "sin modelo"}`
                : t("hub.status.noProvider")}
            </p>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* DERECHA */}
      <div className="flex flex-col gap-4 min-h-0 overflow-y-auto pr-1">
        <HubPanel
          title={t("hub.events.title")}
          count={upcomingEvents.length}
          action={
            <button
              onClick={() => navigate("/calendar")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              {t("hub.viewAll")} →
            </button>
          }
        >
          {events === null ? (
            <LoadingDots />
          ) : upcomingEvents.length === 0 ? (
            <EmptyState text={t("hub.events.empty")} />
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
                    {formatEventDate(e.start_date, t)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title={t("hub.chat.title")}
          count={recentChat.length}
          action={
            <button
              onClick={() => navigate("/chat")}
              className="text-xs text-accent hover:text-accent-glow transition-colors"
            >
              {t("hub.open")} →
            </button>
          }
        >
          {chatRecent === null ? (
            <LoadingDots />
          ) : recentChat.length === 0 ? (
            <EmptyState text={t("hub.chat.empty")} />
          ) : (
            <ul className="space-y-2">
              {recentChat.map((m, idx) => (
                <li
                  key={`${m.created_at}-${idx}`}
                  className="rounded-lg px-2 py-1.5 -mx-2 hover:bg-base-800/40 transition-colors"
                >
                  <p className="text-[10px] uppercase tracking-wider text-ink-faint mb-0.5">
                    {m.role === "user" ? t("hub.chat.you") : "Aithera"}
                  </p>
                  <p className="text-sm text-ink line-clamp-2">{m.content}</p>
                </li>
              ))}
            </ul>
          )}
        </HubPanel>

        <HubPanel
          title={t("hub.email.title")}
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
            <p className="text-sm text-ink-faint">{t("hub.email.loading")}</p>
          ) : emailStatus.connected ? (
            <>
              <p className="text-sm text-ink">
                <span className="text-signal-ok">●</span> {t("hub.email.connectedAs")}{" "}
                <span className="font-medium">{emailStatus.email}</span>
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("hub.email.pending")}</p>
                  <p className="text-base font-medium text-ink">{proposalsCount.pending}</p>
                </div>
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("hub.email.awaitingOk")}</p>
                  <p className="text-base font-medium text-amber-300">{proposalsCount.counter_sent}</p>
                </div>
                <div className="rounded-lg bg-base-800/50 px-2 py-2">
                  <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("hub.email.confirmed")}</p>
                  <p className="text-base font-medium text-signal-ok">{proposalsCount.confirmed}</p>
                </div>
              </div>
              {/* V0.7.3 (Sprint 4, B7): digest de hoy */}
              {digest && (
                <div className="mt-2 flex items-center justify-between text-[10px] px-2 py-1.5 rounded-lg bg-base-800/40">
                  <span className="text-ink-faint">{t("hub.email.today")}</span>
                  <span className="text-ink-dim">{t("hub.email.triaged", { n: digest.triaged_total })}</span>
                  <span className={digest.urgent_pending > 0 ? "text-signal-error font-medium" : "text-ink-faint"}>
                    {t("hub.email.urgent", { n: digest.urgent_pending })}
                  </span>
                  <span className={digest.drafts_awaiting > 0 ? "text-amber-300" : "text-ink-faint"}>
                    {t("hub.email.drafts", { n: digest.drafts_awaiting })}
                  </span>
                </div>
              )}
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 w-full"
              >
                {t("hub.email.openAssistant")}
              </button>
            </>
          ) : (emailStatus.connection_state === "revoked" || emailStatus.connection_state === "expired") ? (
            // AUTH-1: estuvo conectado y la sesión caducó -> mensaje claro de
            // reconexión, no el genérico "credenciales sin OAuth".
            <>
              <p className="text-sm text-amber-300">
                <span>●</span> {t("hub.email.sessionExpired")}
              </p>
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 w-full"
              >
                {t("hub.email.reconnect")}
              </button>
            </>
          ) : emailStatus.has_credentials ? (
            <>
              <p className="text-sm text-amber-300">
                <span>●</span> {t("hub.email.credsNoOauth")}
              </p>
              <p className="text-[10px] text-ink-faint mt-2">
                {t("hub.email.pressConnect")}
              </p>
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 w-full"
              >
                {t("hub.email.goToAssistant")}
              </button>
            </>
          ) : (
            <>
              <p className="text-sm text-ink-faint">
                <span className="text-ink-faint">●</span> {t("hub.email.notConnected")}
              </p>
              <p className="text-[10px] text-ink-faint mt-2">
                {t("hub.email.needCreds")}
              </p>
              <button
                onClick={() => navigate("/email")}
                className="mt-3 text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 w-full"
              >
                {t("hub.email.configure")}
              </button>
            </>
          )}
        </HubPanel>

        {/* V0.85 (MOS M3): tarjeta Memoria — ultima ingesta, dias cubiertos, briefing de hoy */}
        <HubPanel
          title={t("hub.memory.title")}
          action={
            <span className="text-[10px] text-ink-faint">
              {memoryCard?.daysCovered ? t("hub.memory.days", { n: memoryCard.daysCovered }) : ""}
            </span>
          }
        >
          {memoryCard === null ? (
            <LoadingDots />
          ) : (
            <>
              <p className="text-sm text-ink line-clamp-2">
                {memoryCard.summary || t("hub.memory.noActivity")}
              </p>
              <div className="mt-2 flex items-center justify-between text-[10px] px-2 py-1.5 rounded-lg bg-base-800/40">
                <span className="text-ink-faint">
                  {memoryCard.lastIngestAt
                    ? t("hub.memory.ingestAt", { date: formatEventDate(memoryCard.lastIngestAt, t) })
                    : t("hub.memory.noIngest")}
                </span>
                <span className={memoryCard.urgentCount > 0 ? "text-signal-error font-medium" : "text-ink-faint"}>
                  {t("hub.memory.urgentCount", { n: memoryCard.urgentCount })}
                </span>
              </div>
              {/* V0.87 (WPMS W4): señales del Workspace, misma tarjeta */}
              {(memoryCard.upcomingDeadlines > 0 || memoryCard.blockedTasks > 0) && (
                <div className="mt-1.5 flex items-center gap-3 text-[10px] px-2">
                  {memoryCard.upcomingDeadlines > 0 && (
                    <span className="text-ink-faint">{t("hub.memory.deadlines", { n: memoryCard.upcomingDeadlines })}</span>
                  )}
                  {memoryCard.blockedTasks > 0 && (
                    <span className="text-signal-warn">{t("hub.memory.blocked", { n: memoryCard.blockedTasks })}</span>
                  )}
                </div>
              )}
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
          title={backendConnected ? t("hub.status.backendConnected") : t("hub.status.backendDisconnected")}
        />
        {/* [2026-07-21] La barra muestra el modelo del CHAT según la política
            ACTIVA (Inteligencia). El proveedor legacy queda solo de fallback
            si el MEL aún no tiene políticas. */}
        <SystemIndicator
          label={
            chatPrimary
              ? `${t("hub.status.iaLabel")}: ${shortRef(chatPrimary)}${chatPrimaryDown ? " ⚠" : " ✓"}`
              : aiStatus?.provider
              ? `${t("hub.status.iaLabel")}: ${capitalize(aiStatus.provider)}${aiStatus.model ? ` · ${shortModelName(aiStatus.model)}` : ""}`
              : `${t("hub.status.iaLabel")}: —`
          }
          color={
            chatPrimary
              ? (chatPrimaryDown ? "bg-signal-warn" : "bg-signal-ok")
              : aiStatus?.healthy
              ? "bg-signal-ok"
              : "bg-ink-faint"
          }
          title={
            chatPrimary
              ? (chatPrimaryDown
                  ? t("hub.status.chatFailing", { model: shortRef(chatPrimary) })
                  : t("hub.status.chatActive", { model: shortRef(chatPrimary) }))
              : aiStatus
              ? `${aiStatus.provider} / ${aiStatus.model ?? ""}`
              : t("hub.status.noProviderShort")
          }
        />
        <SystemIndicator
          label={t("hub.status.voice", { state: voiceStatus?.configured ? t("hub.status.on") : t("hub.status.off") })}
          color={voiceStatus?.configured ? "bg-signal-ok" : "bg-ink-faint"}
          title={voiceStatus?.message ?? t("hub.status.noVoiceInfo")}
        />
        <SystemIndicator
          label={t("hub.status.core", { state: coreStateLabel(coreState, t) })}
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

function coreStateLabel(state: string, t: (key: string) => string): string {
  const keys: Record<string, string> = {
    idle: "hub.core.idle",
    listening: "hub.core.listening",
    thinking: "hub.core.thinking",
    speaking: "hub.core.speaking",
    processing: "hub.core.processing",
    error: "hub.core.error",
  };
  const key = keys[state];
  return key ? t(key) : state;
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
function formatEventDate(iso: string, t: (key: string) => string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      return `${t("hub.date.today")} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    if (d.toDateString() === tomorrow.toDateString()) {
      return `${t("hub.date.tomorrow")} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    }
    return d.toLocaleDateString([], { day: "2-digit", month: "short" });
  } catch {
    return "";
  }
}
