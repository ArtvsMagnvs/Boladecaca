// EmailAssistant.tsx - Email + Auto-reply (V0.7 Fase 4)
//
// Caracteristicas V0.7:
// - Estado de conexion Google (connected/disconnected)
// - Boton para conectar Google OAuth (requiere client_id/client_secret en Settings)
// - Lista de reglas de auto-respuesta configurables (no requieren OAuth)
// - Formulario para anadir reglas (sender_contains, subject_contains, sender_domain)
// - Test de regla antes de activarla (dry-run)
// - Activar/desactivar reglas existentes
// - Seccion "Configurar Google" con link a Settings

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, type AutoReplyRule, type MeetingProposal, type ActivityEntry, type ActivityStats, type InboxEmail } from "@/lib/api";

const MATCHING_LABELS: Record<string, string> = {
  sender_contains: "Remitente contiene",
  subject_contains: "Asunto contiene",
  sender_domain: "Dominio del remitente",
};

const ACTION_LABELS: Record<string, string> = {
  auto_send: "Enviar automaticamente",
  create_draft: "Crear borrador (revision manual)",
  alert_only: "Solo avisar (no responder)",
};

// V0.7 extra: visual config para los tipos de actividad del dashboard
const ACTIVITY_VISUAL: Record<string, { bg: string; ring: string; text: string; icon: string; label: string }> = {
  sent:               { bg: "bg-emerald-500/10",  ring: "ring-emerald-500/30", text: "text-emerald-300", icon: "✉",  label: "Enviado" },
  draft:              { bg: "bg-amber-500/10",    ring: "ring-amber-500/30",   text: "text-amber-300",   icon: "📝", label: "Borrador" },
  alert:              { bg: "bg-rose-500/15",     ring: "ring-rose-500/40",    text: "text-rose-300",    icon: "🔔", label: "Alerta" },
  urgent:             { bg: "bg-orange-500/10",   ring: "ring-orange-500/30",  text: "text-orange-300",  icon: "!",  label: "Urgente" },
  meeting_proposal:   { bg: "bg-violet-500/10",   ring: "ring-violet-500/30",  text: "text-violet-300",  icon: "📅", label: "Propuesta reunion" },
  meeting_confirmed:  { bg: "bg-signal-ok/15",    ring: "ring-signal-ok/40",   text: "text-signal-ok",   icon: "✓",  label: "Reunion confirmada" },
  skipped:            { bg: "bg-base-800/30",     ring: "ring-base-700/20",    text: "text-ink-faint",   icon: "⊘",  label: "Omitido" },
  error:              { bg: "bg-red-500/15",      ring: "ring-red-500/40",     text: "text-red-300",     icon: "⚠",  label: "Error" },
};

// V0.7 extra: filtros disponibles para el dashboard
const ACTIVITY_FILTERS = [
  { id: "all",                    label: "Todas",                  color: "ink" },
  { id: "sent",                   label: "Enviados",               color: "emerald" },
  { id: "draft",                  label: "Borradores",             color: "amber" },
  { id: "alert",                  label: "Alertas",                color: "rose" },
  { id: "urgent",                 label: "Urgentes",               color: "orange" },
  { id: "meeting_proposal",       label: "Reuniones",              color: "violet" },
  { id: "meeting_confirmed",      label: "Confirmadas",            color: "green" },
  { id: "error",                  label: "Errores",                color: "red" },
];

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

const PROPOSAL_STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  pending:      { bg: "bg-base-700/40",   text: "text-ink-dim",     label: "Pendiente" },
  counter_sent: { bg: "bg-amber-500/15",  text: "text-amber-300",   label: "Esperando confirmacion" },
  confirmed:    { bg: "bg-signal-ok/15",  text: "text-signal-ok",   label: "Confirmada" },
  rejected:     { bg: "bg-signal-error/15", text: "text-signal-error", label: "Rechazada" },
  expired:      { bg: "bg-base-700/40",   text: "text-ink-faint",   label: "Caducada" },
};

export default function EmailAssistant() {
  const [status, setStatus] = useState<{
    connected: boolean;
    email: string | null;
    has_credentials: boolean;
    libs_available: boolean;
  } | null>(null);

  const [rules, setRules] = useState<AutoReplyRule[]>([]);
  const [proposals, setProposals] = useState<MeetingProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [checking, setChecking] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // V0.7 extra: dashboard persistente de actividad
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [activityStats, setActivityStats] = useState<ActivityStats | null>(null);
  const [activityFilter, setActivityFilter] = useState<string>("all");
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  // V0.7.1 (Fase 4b): bandeja de entrada de Gmail (ultimos emails, no leidos)
  const [inbox, setInbox] = useState<InboxEmail[]>([]);
  const [inboxLoading, setInboxLoading] = useState(false);

  // Form
  const [formName, setFormName] = useState("");
  const [formSenderEmailsText, setFormSenderEmailsText] = useState("");
  const [formSenderDomainsText, setFormSenderDomainsText] = useState("");
  const [formAction, setFormAction] = useState<"auto_send" | "create_draft" | "alert_only">("auto_send");
  const [formDetectMeeting, setFormDetectMeeting] = useState(true);
  const [formReplyTemplate, setFormReplyTemplate] = useState("");
  const [formEnabled, setFormEnabled] = useState(true);

  // Test
  const [testSender, setTestSender] = useState("");
  const [testSubject, setTestSubject] = useState("");
  const [testBody, setTestBody] = useState("");
  const [testResult, setTestResult] = useState<{
    would_auto_reply: boolean;
    matches: Array<{ name: string; reply_text: string }>;
  } | null>(null);

  // ------------------------------------------------------------------
  // Carga
  // ------------------------------------------------------------------

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, r, p, a, stats] = await Promise.all([
        api.getEmailStatus(),
        api.listAutoReplyRules(),
        api.listProposals(),
        api.getActivity({ limit: 50 }),
        api.getActivityStats(),
      ]);
      setStatus(s);
      setRules(r.rules || []);
      setProposals(p.proposals || []);
      setActivity(a.items || []);
      setActivityStats(stats);
    } catch (e) {
      setMsg({ kind: "err", text: `Error cargando: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const refreshActivity = async () => {
    try {
      const params: { action_type?: string; only_unread?: boolean; limit?: number } = { limit: 50 };
      if (activityFilter !== "all") params.action_type = activityFilter;
      if (showUnreadOnly) params.only_unread = true;
      const [a, stats] = await Promise.all([
        api.getActivity(params),
        api.getActivityStats(),
      ]);
      setActivity(a.items || []);
      setActivityStats(stats);
    } catch (e) {
      console.error("Error refrescando actividad:", e);
    }
  };

  // V0.7.1 (Fase 4b): carga la bandeja de entrada enriquecida (solo lectura).
  const loadInbox = async () => {
    if (!status?.connected) return;
    setInboxLoading(true);
    try {
      const r = await api.getInboxPreview(15);
      setInbox(r.items || []);
    } catch (e) {
      console.error("Error cargando bandeja:", e);
    } finally {
      setInboxLoading(false);
    }
  };

  const handleDismissEntry = async (id: number) => {
    try {
      await api.deleteActivityEntry(id);
      setActivity((prev) => prev.filter((e) => e.id !== id));
      const stats = await api.getActivityStats();
      setActivityStats(stats);
    } catch (e) {
      console.error("Error borrando entrada:", e);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await api.markActivityRead(id);
      setActivity((prev) =>
        prev.map((e) => (e.id === id ? { ...e, read: true } : e))
      );
    } catch (e) {
      console.error("Error marcando como leido:", e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllActivityRead();
      setActivity((prev) => prev.map((e) => ({ ...e, read: true })));
      setActivityStats((prev) => {
        if (!prev) return prev;
        const out: ActivityStats = { ...prev };
        for (const k of Object.keys(out)) {
          out[k] = { ...out[k], unread: 0 };
        }
        return out;
      });
    } catch (e) {
      console.error("Error marcando todas como leidas:", e);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Borrar todo el historial de actividad?")) return;
    try {
      await api.clearAllActivity();
      setActivity([]);
      setActivityStats(null);
    } catch (e) {
      console.error("Error limpiando:", e);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  // V0.7.1 (Fase 4b): cuando Google queda conectado, cargamos la bandeja.
  useEffect(() => {
    if (status?.connected) loadInbox();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.connected]);

  // ------------------------------------------------------------------
  // Conexion Google
  // ------------------------------------------------------------------

  const connectGoogle = async () => {
    if (!status?.has_credentials) {
      setMsg({
        kind: "err",
        text: "Antes de conectar, configura client_id y client_secret en Settings > Google.",
      });
      return;
    }
    setConnecting(true);
    setMsg(null);
    try {
      const r = await api.startEmailOAuth();
      setMsg({ kind: "ok", text: `Conectado como ${r.email || "Google account"}` });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error conectando: ${(e as Error).message}` });
    } finally {
      setConnecting(false);
    }
  };

  const disconnectGoogle = async () => {
    if (!confirm("Desconectar Google? Se borrara el token local.")) return;
    try {
      await api.disconnectEmail();
      setMsg({ kind: "ok", text: "Google desconectado" });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error desconectando: ${(e as Error).message}` });
    }
  };

  // ------------------------------------------------------------------
  // CRUD reglas
  // ------------------------------------------------------------------

  const addRule = async () => {
    if (!formName.trim()) {
      setMsg({ kind: "err", text: "El nombre es obligatorio" });
      return;
    }
    // V0.7 extra (FIX): la plantilla es OPCIONAL si detect_meeting_with_ia=True
    // porque la IA genera la respuesta completa para reuniones.
    // Solo es obligatoria si NO detecta reuniones con IA.
    if (!formDetectMeeting && !formReplyTemplate.trim()) {
      setMsg({
        kind: "err",
        text: "Si desactivas 'detectar reuniones con IA', la plantilla es obligatoria",
      });
      return;
    }
    const emails = formSenderEmailsText
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s);
    const domains = formSenderDomainsText
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s);
    if (emails.length === 0 && domains.length === 0) {
      setMsg({ kind: "err", text: "Anade al menos un email o un dominio" });
      return;
    }
    try {
      await api.addAutoReplyRule({
        name: formName.trim(),
        sender_emails: emails,
        sender_domains: domains,
        action: formAction,
        detect_meeting_with_ia: formDetectMeeting,
        reply_template: formReplyTemplate.trim() || "",  // V0.7 extra: opcional
        enabled: formEnabled,
      });
      setMsg({ kind: "ok", text: `Regla '${formName}' creada` });
      setFormName("");
      setFormSenderEmailsText("");
      setFormSenderDomainsText("");
      setFormReplyTemplate("");
      setFormEnabled(true);
      setFormAction("auto_send");
      setFormDetectMeeting(true);
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error creando regla: ${(e as Error).message}` });
    }
  };

  const toggleRule = async (rule: AutoReplyRule) => {
    try {
      await api.updateAutoReplyRule(rule.id, { enabled: !rule.enabled });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error actualizando: ${(e as Error).message}` });
    }
  };

  const deleteRule = async (id: number, name: string) => {
    if (!confirm(`Eliminar regla '${name}'?`)) return;
    try {
      await api.deleteAutoReplyRule(id);
      setMsg({ kind: "ok", text: `Regla '${name}' eliminada` });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error eliminando: ${(e as Error).message}` });
    }
  };

  // ------------------------------------------------------------------
  // Test
  // ------------------------------------------------------------------

  const testRule = async () => {
    if (!testSender.trim()) {
      setMsg({ kind: "err", text: "El remitente es obligatorio para el test" });
      return;
    }
    try {
      const r = await api.testAutoReply({
        sender: testSender.trim(),
        subject: testSubject,
        body: testBody,
      });
      setTestResult({
        would_auto_reply: r.would_auto_reply,
        matches: r.matches.map((m) => ({ name: m.name, reply_text: m.reply_text })),
      });
    } catch (e) {
      setMsg({ kind: "err", text: `Error en test: ${(e as Error).message}` });
    }
  };

  // V0.7 extra (FIX): nuevo endpoint unificado que SI funciona
  const processInbox = async () => {
    setProcessing(true);
    setMsg(null);
    try {
      const r = await api.processInbox(10);
      // FIX BUG 1 (Fase 4b): toast contextual con subjects, no solo contadores.
      // Los urgentes (Oleada 2) se marcan con action_taken === "urgent_logged";
      // los distinguimos de las alertas normales.
      const urgentItems = r.processed.filter((p) => p.action_taken === "urgent_logged");
      const alertItems = r.processed.filter((p) => p.alert && p.action_taken !== "urgent_logged");
      const meetingItems = r.processed.filter((p) => p.is_meeting);
      const sentItems = r.processed.filter((p) => p.sent);
      const draftItems = r.processed.filter((p) => p.draft_id);

      const subjectsOf = (items: typeof r.processed) =>
        items.slice(0, 2).map((i) => `"${i.subject || "?"}"`).join(", ");

      let toastText = `Procesados ${r.count} emails.`;
      if (sentItems.length > 0) toastText += ` ${sentItems.length} enviados.`;
      if (draftItems.length > 0) toastText += ` ${draftItems.length} borradores.`;
      if (urgentItems.length > 0) toastText += ` ${urgentItems.length} urgente(s): ${subjectsOf(urgentItems)}.`;
      if (alertItems.length > 0) toastText += ` ${alertItems.length} alerta(s): ${subjectsOf(alertItems)}.`;
      if (meetingItems.length > 0) toastText += ` ${meetingItems.length} reunion(es): ${subjectsOf(meetingItems)}.`;
      // FIX BUG (Tarea 1.4): call-to-action al dashboard cuando hay algo que revisar.
      if (urgentItems.length > 0 || alertItems.length > 0 || meetingItems.length > 0) {
        toastText += " → Revisa el dashboard.";
      }
      setMsg({ kind: "ok", text: toastText });
      // FIX BUG 1: Esperamos un poquito a que el backend termine de hacer
      // commit de TODAS las entradas EmailActivityLog, luego refrescamos
      // el dashboard y las propuestas explicitamente.
      await new Promise((res) => setTimeout(res, 500));
      await Promise.all([refreshActivity(), refresh(), loadInbox()]);
    } catch (e) {
      setMsg({ kind: "err", text: `Error procesando inbox: ${(e as Error).message}` });
    } finally {
      setProcessing(false);
    }
  };

  const checkConfirmations = async () => {
    setChecking(true);
    setMsg(null);
    try {
      const r = await api.checkConfirmations(20);
      setMsg({
        kind: "ok",
        text: `Revisados ${r.checked} emails: ${r.count} confirmaciones detectadas.`,
      });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error verificando confirmaciones: ${(e as Error).message}` });
    } finally {
      setChecking(false);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="h-full p-4 overflow-y-auto">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Cabecera */}
        <div>
          <h1 className="text-xl font-semibold text-ink">Email Assistant</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            Gestiona Gmail y configura reglas de auto-respuesta
          </p>
        </div>

        {msg && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`text-xs p-3 rounded-lg ${
              msg.kind === "ok"
                ? "bg-signal-ok/10 text-signal-ok border border-signal-ok/30"
                : "bg-signal-error/10 text-signal-error border border-signal-error/30"
            }`}
          >
            {msg.text}
          </motion.div>
        )}

        {/* Estado de conexion (Tarea 1.5 Fase 4b): cuando Google esta conectado
            colapsa a un banner compacto de 1 linea para no dominar la vista. */}
        {status?.connected && (
          <div className="glass-surface rounded-2xl px-4 py-3 flex items-center justify-between">
            <p className="text-xs text-ink-dim">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-signal-ok mr-2 align-middle" />
              Conectado como{" "}
              <span className="text-ink font-medium">{status.email || "Google account"}</span>
            </p>
            <button
              onClick={disconnectGoogle}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              Desconectar
            </button>
          </div>
        )}
        {!status?.connected && (
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-medium text-ink">Estado de Google</h2>
              <p className="text-xs text-ink-faint mt-1">
                {status?.connected ? (
                  <>
                    Conectado como{" "}
                    <span className="text-ink">{status.email || "Google account"}</span>
                  </>
                ) : status?.has_credentials ? (
                  <>Credenciales listas (fuente: {(status as any).credentials_source || "db"}). Pulsa "Conectar con Google".</>
                ) : (
                  <>No hay credenciales. Configuralas en Settings → Google, o en <code className="bg-base-950/50 px-1 rounded">backend/.env</code>.</>
                )}
              </p>
            </div>
            <div className="flex gap-2">
              {/* V0.7 extra: Conectar SOLO si hay credenciales.
                  Si no, el usuario ve claramente que debe ir a Settings primero. */}
              {!status?.connected && (
                <button
                  onClick={connectGoogle}
                  disabled={connecting || !status?.has_credentials}
                  title={
                    !status?.has_credentials
                      ? "Configura credenciales primero (ver Settings)"
                      : "Abrir el browser para autorizar a Aithera"
                  }
                  className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connecting ? "Conectando..." : "Conectar con Google"}
                </button>
              )}
              {status?.connected && (
                <button
                  onClick={disconnectGoogle}
                  className="text-xs px-4 py-2 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
                >
                  Desconectar
                </button>
              )}
            </div>
          </div>

          {!status?.has_credentials && (
            <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 space-y-2">
              <p>
                Para usar Gmail necesitas obtener credenciales OAuth desde Google Cloud Console.
              </p>
              <p>
                <strong className="text-amber-200">El boton "Conectar" esta desactivado</strong>{" "}
                porque aun no hay credenciales. Configuralas en:
              </p>
              <ul className="list-disc list-inside text-ink-faint">
                <li>
                  <strong className="text-amber-200">Opcion 1 (recomendada):</strong> edita{" "}
                  <code className="bg-base-950/50 px-1 rounded">backend/.env</code> y anade:
                  <br />
                  <code className="bg-base-950/50 px-1 rounded inline-block mt-1">
                    GOOGLE_CLIENT_ID=tu_client_id
                    <br />
                    GOOGLE_CLIENT_SECRET=tu_client_secret
                  </code>
                  <br />
                  <span className="text-[10px]">(luego reinicia el backend con Ctrl+C y vuelve a arrancarlo)</span>
                </li>
                <li>
                  <strong className="text-amber-200">Opcion 2:</strong> ve a{" "}
                  <strong className="text-amber-200">Settings → Google</strong> y pegalas
                  en el formulario. Quedan guardadas en la BD.
                </li>
              </ul>
              <p className="text-ink-faint text-[10px] italic">
                Las reglas de auto-respuesta y la gestion manual del calendario funcionan
                SIN necesidad de conectar Google.
              </p>
            </div>
          )}
        </div>
        )}

        {/* Procesar inbox con IA (Tarea 1.5 Fase 4b): CTA principal, antes del dashboard */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-ink">
              Procesar inbox con IA
            </h2>
            <div className="flex gap-2">
              <button
                onClick={processInbox}
                disabled={!status?.connected || processing}
                title={!status?.connected ? "Conecta Google primero" : "Escanea los ultimos emails y aplica tus reglas"}
                className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? "Procesando..." : "Procesar inbox ahora"}
              </button>
              <button
                onClick={checkConfirmations}
                disabled={!status?.connected || checking}
                title="Buscar emails que confirman propuestas pendientes"
                className="text-xs px-3 py-1.5 rounded-lg bg-base-800 text-ink border border-base-700 hover:bg-base-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {checking ? "Buscando..." : "Verificar confirmaciones"}
              </button>
            </div>
          </div>

          <p className="text-[10px] text-ink-faint mb-3">
            <strong className="text-ink-dim">Procesar inbox</strong> escanea tus
            ultimos emails y aplica tus reglas: si algun email matchea una regla
            y propone una reunion (detectado por IA, no por palabras clave), se
            consulta tu calendario. Si estas libre, se acepta. Si estas ocupado,
            se propone automaticamente una nueva fecha disponible.
          </p>
        </div>

        {/* V0.7.1 (Fase 4b): Bandeja de entrada de Gmail (ultimos emails; no leidos resaltados) */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-medium text-ink">Bandeja de entrada</h2>
              <p className="text-[10px] text-ink-faint mt-0.5">
                Tus ultimos emails de Gmail. Los no leidos aparecen resaltados.
              </p>
            </div>
            <button
              onClick={loadInbox}
              disabled={!status?.connected || inboxLoading}
              className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {inboxLoading ? "Cargando..." : "Refrescar"}
            </button>
          </div>

          {!status?.connected ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              Conecta Google para ver tu bandeja de entrada.
            </p>
          ) : inbox.length === 0 ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              {inboxLoading ? "Cargando bandeja..." : "No hay emails para mostrar."}
            </p>
          ) : (
            <div className="space-y-1.5 max-h-[360px] overflow-y-auto">
              {inbox.map((m) => (
                <div
                  key={m.id}
                  className={`flex items-start gap-3 p-2.5 rounded-lg ${
                    m.unread ? "bg-base-800/60 ring-1 ring-accent/20" : "bg-base-900/30"
                  }`}
                >
                  <div
                    className={`shrink-0 w-2 h-2 mt-1.5 rounded-full ${
                      m.unread ? "bg-accent" : "bg-base-600"
                    }`}
                    title={m.unread ? "No leido" : "Leido"}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs truncate ${m.unread ? "text-ink font-medium" : "text-ink-dim"}`}>
                        {m.from || "?"}
                      </span>
                      {m.unread && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-accent/20 text-accent">
                          NO LEIDO
                        </span>
                      )}
                    </div>
                    <p className={`text-xs truncate ${m.unread ? "text-ink" : "text-ink-dim"}`}>
                      {m.subject || "(sin asunto)"}
                    </p>
                    {m.snippet && (
                      <p className="text-[10px] text-ink-faint truncate mt-0.5">{m.snippet}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* V0.7 extra (FIX): Dashboard de actividad - lo primero que el usuario ve */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-medium text-ink">Dashboard de actividad</h2>
              <p className="text-[10px] text-ink-faint mt-0.5">
                Aqui ves todo lo que Aithera hizo con tus emails: respuestas enviadas,
                borradores creados, alertas, propuestas de reunion, errores.
              </p>
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={refreshActivity}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700"
              >
                Refrescar
              </button>
              <button
                onClick={handleMarkAllRead}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700"
              >
                Marcar todo leido
              </button>
              <button
                onClick={handleClearAll}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-faint hover:bg-signal-error/20 hover:text-signal-error"
              >
                Limpiar
              </button>
            </div>
          </div>

          {/* Stats cards */}
          {activityStats && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
              <button
                onClick={() => setActivityFilter(activityFilter === "sent" ? "all" : "sent")}
                className={`rounded-lg p-2.5 text-left transition-all ${
                  activityFilter === "sent"
                    ? "bg-emerald-500/20 ring-2 ring-emerald-500/40"
                    : "bg-base-900/40 hover:bg-base-900/60"
                }`}
              >
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">Enviados</p>
                <p className="text-base font-semibold text-emerald-300">
                  {activityStats.sent?.total || 0}
                </p>
                {(activityStats.sent?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{activityStats.sent.unread} sin leer</p>
                )}
              </button>
              <button
                onClick={() => setActivityFilter(activityFilter === "draft" ? "all" : "draft")}
                className={`rounded-lg p-2.5 text-left transition-all ${
                  activityFilter === "draft"
                    ? "bg-amber-500/20 ring-2 ring-amber-500/40"
                    : "bg-base-900/40 hover:bg-base-900/60"
                }`}
              >
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">Borradores</p>
                <p className="text-base font-semibold text-amber-300">
                  {activityStats.draft?.total || 0}
                </p>
                {(activityStats.draft?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{activityStats.draft.unread} sin leer</p>
                )}
              </button>
              <button
                onClick={() => setActivityFilter(activityFilter === "alert" ? "all" : "alert")}
                className={`rounded-lg p-2.5 text-left transition-all ${
                  activityFilter === "alert"
                    ? "bg-rose-500/25 ring-2 ring-rose-500/40"
                    : "bg-base-900/40 hover:bg-base-900/60"
                }`}
              >
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">Alertas</p>
                <p className="text-base font-semibold text-rose-300">
                  {activityStats.alert?.total || 0}
                </p>
                {(activityStats.alert?.unread || 0) > 0 && (
                  <p className="text-[9px] text-rose-300 font-medium">
                    {activityStats.alert.unread} requieren atencion
                  </p>
                )}
              </button>
              <button
                onClick={() => setActivityFilter(activityFilter === "urgent" ? "all" : "urgent")}
                className={`rounded-lg p-2.5 text-left transition-all ${
                  activityFilter === "urgent"
                    ? "bg-orange-500/20 ring-2 ring-orange-500/40"
                    : "bg-base-900/40 hover:bg-base-900/60"
                }`}
              >
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">Urgentes</p>
                <p className="text-base font-semibold text-orange-300">
                  {activityStats.urgent?.total || 0}
                </p>
                {(activityStats.urgent?.unread || 0) > 0 && (
                  <p className="text-[9px] text-orange-300 font-medium">
                    {activityStats.urgent.unread} sin leer
                  </p>
                )}
              </button>
              <button
                onClick={() => setActivityFilter(activityFilter === "meeting_proposal" ? "all" : "meeting_proposal")}
                className={`rounded-lg p-2.5 text-left transition-all ${
                  activityFilter === "meeting_proposal"
                    ? "bg-violet-500/20 ring-2 ring-violet-500/40"
                    : "bg-base-900/40 hover:bg-base-900/60"
                }`}
              >
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">Reuniones</p>
                <p className="text-base font-semibold text-violet-300">
                  {(activityStats.meeting_proposal?.total || 0) + (activityStats.meeting_confirmed?.total || 0)}
                </p>
                {(activityStats.meeting_proposal?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{activityStats.meeting_proposal.unread} propuestas</p>
                )}
              </button>
            </div>
          )}

          {/* Filter chip "solo no leidos" */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] text-ink-faint">
              {activityFilter === "all" ? "Mostrando todo" : `Filtrando: ${activityFilter}`}
              {showUnreadOnly && " (solo no leidos)"}
            </p>
            <label className="flex items-center gap-1.5 text-[10px] text-ink-dim cursor-pointer">
              <input
                type="checkbox"
                checked={showUnreadOnly}
                onChange={(e) => setShowUnreadOnly(e.target.checked)}
                className="h-3 w-3 accent-accent"
              />
              Solo no leidos
            </label>
          </div>

          {/* Activity feed */}
          {activity.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-3xl mb-2">📭</p>
              <p className="text-xs text-ink-faint">
                No hay actividad registrada.
              </p>
              <p className="text-[10px] text-ink-faint mt-1">
                Pulsa "Procesar inbox ahora" para empezar.
              </p>
            </div>
          ) : (
            <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
              {activity.map((entry) => {
                const vis = ACTIVITY_VISUAL[entry.action_type] || ACTIVITY_VISUAL.skipped;
                const details = entry.details || {};
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`flex items-start gap-3 p-2.5 rounded-lg ${
                      entry.read ? "bg-base-900/30" : "bg-base-800/60 ring-1 ring-accent/20"
                    } ${vis.bg}`}
                    onClick={() => !entry.read && handleMarkRead(entry.id)}
                  >
                    {/* Icono */}
                    <div className={`shrink-0 w-8 h-8 rounded-lg ${vis.bg} ring-1 ${vis.ring} flex items-center justify-center text-base ${vis.text}`}>
                      {vis.icon}
                    </div>
                    {/* Contenido */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${vis.bg} ${vis.text} ring-1 ${vis.ring}`}>
                          {vis.label}
                        </span>
                        {!entry.read && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-accent/20 text-accent">
                            NUEVO
                          </span>
                        )}
                        {entry.timestamp && (
                          <span className="text-[10px] text-ink-faint">
                            {new Date(entry.timestamp).toLocaleString("es-ES", {
                              day: "2-digit",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-ink mt-1 truncate">
                        <span className="text-ink-faint">De:</span>{" "}
                        <span className="text-ink-dim">{entry.sender_email || entry.sender || "?"}</span>
                        {entry.subject && (
                          <>
                            <span className="text-ink-faint"> · </span>
                            <span className="text-ink">{entry.subject}</span>
                          </>
                        )}
                      </p>
                      {/* Detalles especificos segun action_type */}
                      {entry.action_type === "sent" && details.is_meeting && (
                        <p className="text-[11px] text-emerald-300/80 mt-0.5">
                          Reunion {details.calendar_status === "libre" ? "confirmada" : "contrapropuesta enviada"}
                          {details.proposed_new_date && (
                            <> para {new Date(details.proposed_new_date).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })}</>
                          )}
                          {details.accepted_date && (
                            <> para {new Date(details.accepted_date).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })}</>
                          )}
                        </p>
                      )}
                      {entry.action_type === "draft" && details.is_meeting && (
                        <p className="text-[11px] text-amber-300/80 mt-0.5">
                          Borrador IA sobre reunion{" "}
                          {details.proposed_new_date ? "con nueva fecha propuesta" : "que confirma fecha"}
                        </p>
                      )}
                      {entry.action_type === "alert" && details.is_meeting && (
                        <p className="text-[11px] text-rose-300/90 mt-0.5 font-medium">
                          {details.calendar_status === "ocupado"
                            ? `ESTAS OCUPADO el ${details.original_date || "?"}. Sugerencia: ${details.proposed_new_date || "?"}`
                            : `Reunion propuesta para ${details.proposed_date || details.original_date || "?"}`}
                        </p>
                      )}
                      {entry.action_type === "alert" && !details.is_meeting && (
                        <p className="text-[11px] text-rose-300/90 mt-0.5">
                          {details.reason || "Email importante que requiere tu atencion"}
                        </p>
                      )}
                      {entry.action_type === "meeting_proposal" && (
                        <p className="text-[11px] text-violet-300/90 mt-0.5">
                          Original: {details.original_date ? new Date(details.original_date).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" }) : "?"} →
                          Sugerencia: {details.proposed_new_date ? new Date(details.proposed_new_date).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" }) : "?"}
                        </p>
                      )}
                      {entry.action_type === "meeting_confirmed" && (
                        <p className="text-[11px] text-signal-ok mt-0.5">
                          Reunion confirmada para {details.confirmed_datetime ? new Date(details.confirmed_datetime).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" }) : "?"}
                        </p>
                      )}
                      {details.preview_reply && entry.action_type === "alert" && (
                        <details className="mt-1">
                          <summary className="text-[10px] text-ink-faint cursor-pointer hover:text-ink">
                            Ver respuesta sugerida
                          </summary>
                          <p className="text-[10px] text-ink-dim mt-1 italic whitespace-pre-wrap">
                            {details.preview_reply}
                          </p>
                        </details>
                      )}
                      {entry.rule_name && (
                        <p className="text-[10px] text-ink-faint mt-1">
                          Regla aplicada: <span className="text-ink-dim">{entry.rule_name}</span>
                        </p>
                      )}
                    </div>
                    {/* Boton descartar */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismissEntry(entry.id);
                      }}
                      title="Descartar entrada"
                      className="shrink-0 text-ink-faint hover:text-signal-error text-lg px-1"
                    >
                      ×
                    </button>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* Propuestas de reunion (Tarea 1.5 Fase 4b): estado de las reuniones detectadas */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-ink">
              Propuestas de reunion ({proposals.length})
            </h2>
          </div>

          {proposals.length === 0 ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              No hay propuestas registradas. Pulsa "Procesar inbox ahora" para
              empezar.
            </p>
          ) : (
            <div className="space-y-2">
              {proposals.map((p) => {
                const sc = PROPOSAL_STATUS_COLORS[p.status] || PROPOSAL_STATUS_COLORS.pending;
                return (
                  <div
                    key={p.id}
                    className={`flex items-start justify-between gap-3 p-3 rounded-lg ${sc.bg}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-ink truncate">
                          {p.subject || "(sin asunto)"}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${sc.bg} ${sc.text}`}>
                          {sc.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-faint mt-0.5">
                        De: <span className="text-ink-dim">{p.sender}</span>
                      </p>
                      <div className="text-[11px] text-ink-dim mt-1 grid grid-cols-2 gap-x-3">
                        <div>
                          <span className="text-ink-faint">Propuso:</span>{" "}
                          {p.original_proposed_datetime
                            ? new Date(p.original_proposed_datetime).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })
                            : "—"}
                        </div>
                        {p.counter_proposed_datetime && (
                          <div>
                            <span className="text-ink-faint">Propuse:</span>{" "}
                            {new Date(p.counter_proposed_datetime).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })}
                          </div>
                        )}
                      </div>
                      {p.notes && (
                        <p className="text-[10px] text-ink-faint mt-1 italic">
                          {p.notes}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => {
                        if (confirm(`Eliminar propuesta #${p.id}?`)) {
                          api.deleteProposal(p.id).then(refresh).catch((e) =>
                            setMsg({ kind: "err", text: `Error eliminando: ${e.message}` })
                          );
                        }
                      }}
                      className="text-[10px] px-2 py-1 rounded bg-base-700/50 text-ink-faint hover:bg-signal-error/20 hover:text-signal-error shrink-0"
                    >
                      Eliminar
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Reglas de auto-respuesta */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-ink">
              Reglas de auto-respuesta ({rules.length})
            </h2>
            <p className="text-[10px] text-ink-faint">
              Estas reglas funcionan sin OAuth de Google. Activalas aqui y el chat
              las respetara al responder emails.
            </p>
          </div>

          {loading ? (
            <p className="text-xs text-ink-faint">Cargando reglas...</p>
          ) : rules.length === 0 ? (
            <p className="text-xs text-ink-faint py-3">
              No tienes reglas configuradas. Crea una abajo o desde el chat con{" "}
              <em>"siempre responde a los emails de mi jefe con 'Recibido, gracias'"</em>.
            </p>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className={`flex items-start justify-between gap-3 p-3 rounded-lg ${
                    rule.enabled ? "bg-accent/5 border border-accent/20" : "bg-base-900/40 border border-base-700/30"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-ink">{rule.name}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        rule.enabled
                          ? "bg-signal-ok/20 text-signal-ok"
                          : "bg-base-700/50 text-ink-faint"
                      }`}>
                        {rule.enabled ? "ACTIVA" : "INACTIVA"}
                      </span>
                    </div>
                    {/* FIX (Tarea 1.3 Fase 4b): mostrar los campos reales
                        (sender_emails / sender_domains), no los legacy matching/pattern. */}
                    {(() => {
                      const emailsStr = (rule.sender_emails || []).join(", ");
                      const domainsStr = (rule.sender_domains || []).join(", ");
                      return (
                        <p className="text-[11px] text-ink-dim mt-0.5">
                          {emailsStr && <span>Emails: <code className="bg-base-950/50 px-1 rounded">{emailsStr}</code></span>}
                          {domainsStr && <span> | Dominios: <code className="bg-base-950/50 px-1 rounded">{domainsStr}</code></span>}
                          {!emailsStr && !domainsStr && rule.pattern && (
                            <span>
                              {rule.matching ? MATCHING_LABELS[rule.matching] : ""}{" "}
                              <code className="bg-base-950/50 px-1 rounded">{rule.pattern}</code>
                            </span>
                          )}
                        </p>
                      );
                    })()}
                    <p className="text-[11px] text-ink-faint mt-1 italic truncate">
                      Respuesta: {rule.reply_template}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => toggleRule(rule)}
                      className="text-[10px] px-2 py-1 rounded bg-base-700/50 text-ink-dim hover:bg-base-700"
                    >
                      {rule.enabled ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id, rule.name)}
                      className="text-[10px] px-2 py-1 rounded bg-signal-error/10 text-signal-error hover:bg-signal-error/20"
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* V0.7 extra (FIX): Formulario rediseñado - simple y claro */}
        <div className="glass-surface rounded-2xl p-5">
          <h2 className="text-sm font-medium text-ink mb-3">
            Anadir regla de auto-respuesta
          </h2>
          <p className="text-[10px] text-ink-faint mb-4">
            Crea una regla en 4 pasos simples: 1) nombre, 2) emails o dominios,
            3) accion, 4) plantilla. La IA detectara automaticamente si los emails
            proponen una reunion y actuara en consecuencia.
          </p>

          {/* Paso 1: Nombre */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              1. Nombre
            </label>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="ej. Respuesta a MagnoViajes"
              className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
            />
          </div>

          {/* Paso 2: Emails / dominios */}
          <div className="mb-3 grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                2a. Emails exactos
                <span className="text-ink-faint normal-case tracking-normal ml-1">(separados por coma)</span>
              </label>
              <input
                value={formSenderEmailsText}
                onChange={(e) => setFormSenderEmailsText(e.target.value)}
                placeholder="losmagnoviajes@gmail.com, jefe@empresa.com"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
              <p className="text-[9px] text-ink-faint mt-1">
                Match exacto (case-insensitive)
              </p>
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                2b. Dominios
                <span className="text-ink-faint normal-case tracking-normal ml-1">(separados por coma)</span>
              </label>
              <input
                value={formSenderDomainsText}
                onChange={(e) => setFormSenderDomainsText(e.target.value)}
                placeholder="empresa.com, cliente.com"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
              <p className="text-[9px] text-ink-faint mt-1">
                Match exacto del dominio
              </p>
            </div>
          </div>

          {/* Paso 3: Accion */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              3. Que hacer cuando llega un email que matchea
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(["auto_send", "create_draft", "alert_only"] as const).map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => setFormAction(a)}
                  className={`text-xs px-3 py-2 rounded-lg border text-left ${
                    formAction === a
                      ? "bg-accent/20 border-accent/50 text-accent"
                      : "bg-base-700/50 border-base-600 text-ink-dim hover:bg-base-700"
                  }`}
                >
                  <strong className="block text-ink">{ACTION_LABELS[a].split(" (")[0]}</strong>
                  <span className="text-[10px] text-ink-faint">
                    {a === "auto_send" && "Envia email automaticamente"}
                    {a === "create_draft" && "Lo deja en Borradores para revision manual"}
                    {a === "alert_only" && "Solo te avisa, no envia nada"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Toggle: deteccion IA de reuniones */}
          <div className="mb-3 p-3 rounded-lg bg-base-900/40 border border-base-700/30">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="form-detect-meeting"
                checked={formDetectMeeting}
                onChange={(e) => setFormDetectMeeting(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
              <label htmlFor="form-detect-meeting" className="text-xs text-ink">
                La IA detecta si el email propone una reunion
              </label>
            </div>
            <p className="text-[10px] text-ink-faint mt-1 ml-6">
              Si el email es una reunion y estas ocupado, Aithera consulta tu
              calendario y propone una nueva fecha automaticamente. Si no detecta
              ninguna reunion, usa la plantilla de abajo.
            </p>
          </div>

          {/* Paso 4: Plantilla */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              4. Plantilla de respuesta
              <span className="text-ink-faint normal-case tracking-normal ml-1">
                ({formDetectMeeting ? "OPCIONAL" : "obligatoria"}) - solo para emails que NO son reuniones
              </span>
            </label>
            <textarea
              value={formReplyTemplate}
              onChange={(e) => setFormReplyTemplate(e.target.value)}
              placeholder={
                formDetectMeeting
                  ? "Opcional. La IA genera la respuesta cuando detecta reuniones."
                  : "ej. Recibido {sender}. Te respondo pronto."
              }
              rows={3}
              className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 resize-y"
            />
            <p className="text-[9px] text-ink-faint mt-1">
              Variables disponibles: {"{sender}"}, {"{subject}"}, {"{body}"}
            </p>
            {formDetectMeeting && !formReplyTemplate.trim() && (
              <p className="text-[10px] text-emerald-400 mt-1">
                ✓ Sin plantilla: la IA generara todas las respuestas
                automaticamente (incluso las de no-reunion).
              </p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="form-enabled"
                checked={formEnabled}
                onChange={(e) => setFormEnabled(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
              <label htmlFor="form-enabled" className="text-xs text-ink">
                Activar inmediatamente
              </label>
            </div>
            <button
              onClick={addRule}
              className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow transition-colors"
            >
              Crear regla
            </button>
          </div>
        </div>

        {/* Test de regla */}
        <div className="glass-surface rounded-2xl p-5">
          <h2 className="text-sm font-medium text-ink mb-3">
            Probar reglas (dry-run, NO envia nada)
          </h2>
          <p className="text-[10px] text-ink-faint mb-3">
            Comprueba si un email matchearia alguna regla sin enviar respuesta.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                Remitente (header From)
              </label>
              <input
                value={testSender}
                onChange={(e) => setTestSender(e.target.value)}
                placeholder="Jefe <jefe@empresa.com>"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                Asunto
              </label>
              <input
                value={testSubject}
                onChange={(e) => setTestSubject(e.target.value)}
                placeholder="Reunion manana"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                Cuerpo (opcional)
              </label>
              <input
                value={testBody}
                onChange={(e) => setTestBody(e.target.value)}
                placeholder="primeras palabras del email"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <button
              onClick={testRule}
              className="text-xs px-4 py-2 rounded-lg bg-base-800 text-ink border border-base-700 hover:bg-base-700"
            >
              Probar
            </button>
          </div>

          {testResult && (
            <div className={`mt-3 p-3 rounded-lg ${
              testResult.would_auto_reply
                ? "bg-signal-ok/10 border border-signal-ok/30"
                : "bg-base-800/40 border border-base-700/30"
            }`}>
              {testResult.would_auto_reply ? (
                <>
                  <p className="text-xs text-signal-ok font-medium">
                    ✓ Auto-respuesta activada ({testResult.matches.length} regla(s))
                  </p>
                  {testResult.matches.map((m, i) => (
                    <div key={i} className="mt-2 text-xs">
                      <p className="text-ink-dim">
                        Regla: <span className="text-ink">{m.name}</span>
                      </p>
                      <p className="text-ink-faint italic mt-0.5">
                        "{m.reply_text}"
                      </p>
                    </div>
                  ))}
                </>
              ) : (
                <p className="text-xs text-ink-dim">
                  Ninguna regla matchea este email.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}