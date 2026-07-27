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
import { useT, useI18n, LOCALE_TAG } from "@/store/useI18n";

// [I18N-8] Constantes a nivel de módulo: guardan la CLAVE i18n, no el texto.
// Se resuelven con t()/tr() dentro del componente (mismo patrón que TIER_INFO
// en Settings.tsx, I18N-7).
const MATCHING_LABEL_KEYS: Record<string, string> = {
  sender_contains: "email.rule.matching.senderContains",
  subject_contains: "email.rule.matching.subjectContains",
  sender_domain: "email.rule.matching.senderDomain",
};

const ACTION_LABEL_KEYS: Record<string, string> = {
  auto_send: "email.rule.action.autoSend",
  create_draft: "email.rule.action.createDraft",
  alert_only: "email.rule.action.alertOnly",
};

// V0.7 extra: visual config para los tipos de actividad del dashboard
const ACTIVITY_VISUAL: Record<string, { bg: string; ring: string; text: string; icon: string; labelKey: string }> = {
  sent:               { bg: "bg-emerald-500/10",  ring: "ring-emerald-500/30", text: "text-emerald-300", icon: "✉",  labelKey: "email.activity.type.sent" },
  draft:              { bg: "bg-amber-500/10",    ring: "ring-amber-500/30",   text: "text-amber-300",   icon: "📝", labelKey: "email.activity.type.draft" },
  alert:              { bg: "bg-rose-500/15",     ring: "ring-rose-500/40",    text: "text-rose-300",    icon: "🔔", labelKey: "email.activity.type.alert" },
  urgent:             { bg: "bg-orange-500/10",   ring: "ring-orange-500/30",  text: "text-orange-300",  icon: "!",  labelKey: "email.activity.type.urgent" },
  meeting_proposal:   { bg: "bg-violet-500/10",   ring: "ring-violet-500/30",  text: "text-violet-300",  icon: "📅", labelKey: "email.activity.type.meetingProposal" },
  meeting_confirmed:  { bg: "bg-signal-ok/15",    ring: "ring-signal-ok/40",   text: "text-signal-ok",   icon: "✓",  labelKey: "email.activity.type.meetingConfirmed" },
  skipped:            { bg: "bg-base-800/30",     ring: "ring-base-700/20",    text: "text-ink-faint",   icon: "⊘",  labelKey: "email.activity.type.skipped" },
  error:              { bg: "bg-red-500/15",      ring: "ring-red-500/40",     text: "text-red-300",     icon: "⚠",  labelKey: "email.activity.type.error" },
};

// V0.7 extra: filtros disponibles para el dashboard
const ACTIVITY_FILTERS = [
  { id: "all",                    labelKey: "email.filter.all",              color: "ink" },
  { id: "sent",                   labelKey: "email.filter.sent",             color: "emerald" },
  { id: "draft",                  labelKey: "email.filter.draft",            color: "amber" },
  { id: "alert",                  labelKey: "email.filter.alert",            color: "rose" },
  { id: "urgent",                 labelKey: "email.filter.urgent",           color: "orange" },
  { id: "meeting_proposal",       labelKey: "email.filter.meetingProposal",  color: "violet" },
  { id: "meeting_confirmed",      labelKey: "email.filter.meetingConfirmed", color: "green" },
  { id: "error",                  labelKey: "email.filter.error",            color: "red" },
];

const STATUS_LABEL_KEYS: Record<string, string> = {
  pending: "email.execStatus.pending",
  running: "email.execStatus.running",
  completed: "email.execStatus.completed",
  failed: "email.execStatus.failed",
  cancelled: "email.execStatus.cancelled",
};

const PROPOSAL_STATUS_COLORS: Record<string, { bg: string; text: string; labelKey: string }> = {
  pending:      { bg: "bg-base-700/40",   text: "text-ink-dim",     labelKey: "email.proposalStatus.pending" },
  counter_sent: { bg: "bg-amber-500/15",  text: "text-amber-300",   labelKey: "email.proposalStatus.counterSent" },
  confirmed:    { bg: "bg-signal-ok/15",  text: "text-signal-ok",   labelKey: "email.proposalStatus.confirmed" },
  rejected:     { bg: "bg-signal-error/15", text: "text-signal-error", labelKey: "email.proposalStatus.rejected" },
  expired:      { bg: "bg-base-700/40",   text: "text-ink-faint",   labelKey: "email.proposalStatus.expired" },
};

// 2026-07-02: link al email real en Gmail web (por message id)
const gmailLink = (emailId?: string | null) =>
  emailId ? `https://mail.google.com/mail/u/0/#all/${emailId}` : null;

// V0.7.3 (Sprint 3): color de badge por categoria de triaje
const TRIAGE_STYLES: Record<string, string> = {
  urgente: "bg-red-500/20 text-red-400",
  responder: "bg-amber-500/20 text-amber-400",
  reunion: "bg-blue-500/20 text-blue-400",
  newsletter: "bg-base-700/60 text-ink-faint",
  factura: "bg-emerald-500/20 text-emerald-400",
  "spam-social": "bg-fuchsia-500/20 text-fuchsia-400",
  fyi: "bg-base-700/60 text-ink-dim",
};

export default function EmailAssistant() {
  const t = useT();
  const lang = useI18n((s) => s.lang);
  const dateLocale = LOCALE_TAG[lang];
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
  // V0.7.3 (Sprint 3): triaje del inbox
  const [triageLoading, setTriageLoading] = useState(false);
  // V0.7.3b (Sprint 4b): formulario — autonomia directa + prompt de IA
  const [formAutonomy, setFormAutonomy] = useState<"propose" | "auto">("propose");
  const [formAiPrompt, setFormAiPrompt] = useState("");

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
      setMsg({ kind: "err", text: t("email.errLoading", { msg: (e as Error).message }) });
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

  // V0.7.3 (Sprint 3): clasifica el inbox (heuristica -> LLM) y recarga.
  const handleRunTriage = async () => {
    if (!status?.connected) return;
    setTriageLoading(true);
    try {
      await api.runTriage(30);
      await loadInbox();
    } catch (e) {
      console.error("Error en triaje:", e);
    } finally {
      setTriageLoading(false);
    }
  };

  // V0.7.3 (Sprint 4, B6): feedback -> contadores de la regla; si la regla
  // ya se gano la confianza, ofrecemos promocionarla.
  const handleRuleFeedback = async (ruleId: number, result: "approved" | "edited" | "rejected") => {
    try {
      const r = await api.ruleFeedback(ruleId, result);
      if (r.can_promote) {
        setMsg({
          kind: "ok",
          text: t("email.feedback.registeredCanPromote", { n: r.approved_count }),
        });
      } else {
        setMsg({ kind: "ok", text: t("email.feedback.registered") });
      }
      await refresh();
    } catch (e: any) {
      setMsg({ kind: "err", text: t("email.feedback.errRegistering", { msg: e.message }) });
    }
  };

  // 2026-07-02: responder desde una alerta del dashboard
  const [respondingId, setRespondingId] = useState<number | null>(null);
  const handleRespondFromAlert = async (entryId: number, mode: "draft" | "send") => {
    setRespondingId(entryId);
    try {
      const r = await api.respondFromActivity(entryId, mode);
      const extra = r.meeting
        ? r.calendar_status === "ocupado"
          ? ` (${t("email.respond.meetingBusy")}${r.new_date_proposed ? `, ${t("email.respond.proposed")}: ${new Date(r.new_date_proposed).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" })}` : ""})`
          : ` (${t("email.respond.meetingFreeAccepted")})`
        : "";
      setMsg({
        kind: "ok",
        text: `${r.action === "borrador_creado" ? t("email.respond.draftCreated") : t("email.respond.sent")} → ${r.sent_to}${extra}: "${r.reply_preview.slice(0, 120)}..."`,
      });
      await refresh();
      await refreshActivity();
    } catch (e: any) {
      setMsg({ kind: "err", text: t("email.respond.errResponding", { msg: e.message }) });
    } finally {
      setRespondingId(null);
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
    if (!confirm(t("email.confirmClearActivity"))) return;
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
        text: t("email.errNoCredentials"),
      });
      return;
    }
    setConnecting(true);
    setMsg(null);
    try {
      const r = await api.startEmailOAuth();
      setMsg({ kind: "ok", text: t("email.connectedAs", { email: r.email || t("email.googleAccount") }) });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errConnecting", { msg: (e as Error).message }) });
    } finally {
      setConnecting(false);
    }
  };

  const disconnectGoogle = async () => {
    if (!confirm(t("email.confirmDisconnect"))) return;
    try {
      await api.disconnectEmail();
      setMsg({ kind: "ok", text: t("email.disconnected") });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errDisconnecting", { msg: (e as Error).message }) });
    }
  };

  // ------------------------------------------------------------------
  // CRUD reglas
  // ------------------------------------------------------------------

  const addRule = async () => {
    if (!formName.trim()) {
      setMsg({ kind: "err", text: t("email.errNameRequired") });
      return;
    }
    // V0.7 extra (FIX): la plantilla es OPCIONAL si detect_meeting_with_ia=True
    // porque la IA genera la respuesta completa para reuniones.
    // Solo es obligatoria si NO detecta reuniones con IA.
    if (!formDetectMeeting && !formReplyTemplate.trim() && !formAiPrompt.trim()) {
      setMsg({
        kind: "err",
        text: t("email.errNeedTemplateOrPrompt"),
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
      setMsg({ kind: "err", text: t("email.errNeedEmailOrDomain") });
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
        ai_prompt: formAiPrompt.trim() || null,  // V0.7.3b: respuesta generada por IA
        autonomy: formAutonomy,  // V0.7.3: eleccion directa propose/auto
        enabled: formEnabled,
      });
      setMsg({ kind: "ok", text: t("email.ruleCreated", { name: formName }) });
      setFormName("");
      setFormSenderEmailsText("");
      setFormSenderDomainsText("");
      setFormReplyTemplate("");
      setFormEnabled(true);
      setFormAction("auto_send");
      setFormDetectMeeting(true);
      setFormAutonomy("propose");
      setFormAiPrompt("");
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errCreatingRule", { msg: (e as Error).message }) });
    }
  };

  // V0.7.3 (Sprint 4, B6): cambia la autonomia de una regla
  const promoteRule = async (rule: AutoReplyRule, autonomy: "propose" | "auto") => {
    try {
      await api.updateAutoReplyRule(rule.id, { autonomy });
      setMsg({
        kind: "ok",
        text:
          autonomy === "auto"
            ? t("email.ruleNowAuto", { name: rule.name })
            : t("email.ruleNowPropose", { name: rule.name }),
      });
      await refresh();
    } catch (e: any) {
      setMsg({ kind: "err", text: t("email.errChangingAutonomy", { msg: e.message }) });
    }
  };

  const toggleRule = async (rule: AutoReplyRule) => {
    try {
      await api.updateAutoReplyRule(rule.id, { enabled: !rule.enabled });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errUpdating", { msg: (e as Error).message }) });
    }
  };

  const deleteRule = async (id: number, name: string) => {
    if (!confirm(t("email.confirmDeleteRule", { name }))) return;
    try {
      await api.deleteAutoReplyRule(id);
      setMsg({ kind: "ok", text: t("email.ruleDeleted", { name }) });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errDeleting", { msg: (e as Error).message }) });
    }
  };

  // ------------------------------------------------------------------
  // Test
  // ------------------------------------------------------------------

  const testRule = async () => {
    if (!testSender.trim()) {
      setMsg({ kind: "err", text: t("email.errSenderRequired") });
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
      setMsg({ kind: "err", text: t("email.errTest", { msg: (e as Error).message }) });
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

      let toastText = t("email.toast.processed", { n: r.count });
      if (sentItems.length > 0) toastText += ` ${t("email.toast.sentCount", { n: sentItems.length })}`;
      if (draftItems.length > 0) toastText += ` ${t("email.toast.draftsCount", { n: draftItems.length })}`;
      if (urgentItems.length > 0) toastText += ` ${t("email.toast.urgentCount", { n: urgentItems.length, subjects: subjectsOf(urgentItems) })}`;
      if (alertItems.length > 0) toastText += ` ${t("email.toast.alertsCount", { n: alertItems.length, subjects: subjectsOf(alertItems) })}`;
      if (meetingItems.length > 0) toastText += ` ${t("email.toast.meetingsCount", { n: meetingItems.length, subjects: subjectsOf(meetingItems) })}`;
      // FIX BUG (Tarea 1.4): call-to-action al dashboard cuando hay algo que revisar.
      if (urgentItems.length > 0 || alertItems.length > 0 || meetingItems.length > 0) {
        toastText += ` ${t("email.toast.reviewDashboard")}`;
      }
      setMsg({ kind: "ok", text: toastText });
      // FIX BUG 1: Esperamos un poquito a que el backend termine de hacer
      // commit de TODAS las entradas EmailActivityLog, luego refrescamos
      // el dashboard y las propuestas explicitamente.
      await new Promise((res) => setTimeout(res, 500));
      await Promise.all([refreshActivity(), refresh(), loadInbox()]);
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errProcessingInbox", { msg: (e as Error).message }) });
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
        text: t("email.toast.confirmationsChecked", { checked: r.checked, n: r.count }),
      });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: t("email.errCheckingConfirmations", { msg: (e as Error).message }) });
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
          <h1 className="text-xl font-semibold text-ink">{t("email.title")}</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            {t("email.subtitle")}
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
              {t("email.connectedAs")}{" "}
              <span className="text-ink font-medium">{status.email || t("email.googleAccount")}</span>
            </p>
            <button
              onClick={disconnectGoogle}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              {t("email.disconnect")}
            </button>
          </div>
        )}
        {!status?.connected && (
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-medium text-ink">{t("email.googleStatus.title")}</h2>
              <p className="text-xs text-ink-faint mt-1">
                {status?.connected ? (
                  <>
                    {t("email.connectedAs")}{" "}
                    <span className="text-ink">{status.email || t("email.googleAccount")}</span>
                  </>
                ) : status?.has_credentials ? (
                  <>{t("email.credentialsReady", { source: (status as any).credentials_source || "db" })}</>
                ) : (
                  <>{t("email.noCredentials")} <code className="bg-base-950/50 px-1 rounded">backend/.env</code>.</>
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
                      ? t("email.titleConfigureCredentialsFirst")
                      : t("email.titleOpenBrowserAuthorize")
                  }
                  className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connecting ? t("email.connecting") : t("email.connect")}
                </button>
              )}
              {status?.connected && (
                <button
                  onClick={disconnectGoogle}
                  className="text-xs px-4 py-2 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
                >
                  {t("email.disconnect")}
                </button>
              )}
            </div>
          </div>

          {!status?.has_credentials && (
            <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 space-y-2">
              <p>
                {t("email.creds.intro")}
              </p>
              <p>
                <strong className="text-amber-200">{t("email.creds.connectDisabledStrong")}</strong>{" "}
                {t("email.creds.connectDisabledRest")}
              </p>
              <ul className="list-disc list-inside text-ink-faint">
                <li>
                  <strong className="text-amber-200">{t("email.creds.option1")}</strong> {t("email.creds.option1Rest")}{" "}
                  <code className="bg-base-950/50 px-1 rounded">backend/.env</code> {t("email.creds.option1Add")}
                  <br />
                  <code className="bg-base-950/50 px-1 rounded inline-block mt-1">
                    GOOGLE_CLIENT_ID=tu_client_id
                    <br />
                    GOOGLE_CLIENT_SECRET=tu_client_secret
                  </code>
                  <br />
                  <span className="text-[10px]">{t("email.creds.restartHint")}</span>
                </li>
                <li>
                  <strong className="text-amber-200">{t("email.creds.option2")}</strong> {t("email.creds.option2Rest")}{" "}
                  <strong className="text-amber-200">Settings → Google</strong> {t("email.creds.option2End")}
                </li>
              </ul>
              <p className="text-ink-faint text-[10px] italic">
                {t("email.creds.worksWithoutGoogle")}
              </p>
            </div>
          )}
        </div>
        )}

        {/* Procesar inbox con IA (Tarea 1.5 Fase 4b): CTA principal, antes del dashboard */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-ink">
              {t("email.processInbox.title")}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={processInbox}
                disabled={!status?.connected || processing}
                title={!status?.connected ? t("email.titleConnectFirst") : t("email.titleScanApplyRules")}
                className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? t("email.processInbox.processing") : t("email.processInbox.run")}
              </button>
              <button
                onClick={checkConfirmations}
                disabled={!status?.connected || checking}
                title={t("email.titleCheckConfirmations")}
                className="text-xs px-3 py-1.5 rounded-lg bg-base-800 text-ink border border-base-700 hover:bg-base-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {checking ? t("email.processInbox.checking") : t("email.processInbox.checkConfirm")}
              </button>
            </div>
          </div>

          <p className="text-[10px] text-ink-faint mb-3">
            <strong className="text-ink-dim">{t("email.processInbox.calloutStrong")}</strong> {t("email.processInbox.calloutRest")}
          </p>
        </div>

        {/* V0.7.1 (Fase 4b): Bandeja de entrada de Gmail (ultimos emails; no leidos resaltados) */}
        <div className="glass-surface rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-medium text-ink">{t("email.inbox.title")}</h2>
              <p className="text-[10px] text-ink-faint mt-0.5">
                {t("email.inbox.desc")}
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleRunTriage}
                disabled={!status?.connected || triageLoading || inboxLoading}
                className="text-[10px] px-2 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30 disabled:opacity-50 disabled:cursor-not-allowed"
                title={t("email.titleTriage")}
              >
                {triageLoading ? t("email.inbox.triaging") : t("email.inbox.triage")}
              </button>
              <button
                onClick={loadInbox}
                disabled={!status?.connected || inboxLoading}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {inboxLoading ? t("common.loading") : t("email.inbox.refresh")}
              </button>
            </div>
          </div>

          {!status?.connected ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              {t("email.inbox.connectFirst")}
            </p>
          ) : inbox.length === 0 ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              {inboxLoading ? t("email.inbox.loading") : t("email.inbox.empty")}
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
                    title={m.unread ? t("email.inbox.unread") : t("email.inbox.read")}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs truncate ${m.unread ? "text-ink font-medium" : "text-ink-dim"}`}>
                        {m.from || "?"}
                      </span>
                      {m.unread && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-accent/20 text-accent">
                          {t("email.inbox.unreadBadge")}
                        </span>
                      )}
                      {m.category && (
                        <span
                          className={`text-[9px] px-1 py-0.5 rounded uppercase ${
                            TRIAGE_STYLES[m.category] || "bg-base-700/60 text-ink-dim"
                          }`}
                        >
                          {m.category}
                        </span>
                      )}
                    </div>
                    <a
                      href={gmailLink(m.id) || undefined}
                      target="_blank"
                      rel="noreferrer"
                      className={`block text-xs truncate hover:text-accent ${m.unread ? "text-ink" : "text-ink-dim"}`}
                      title={t("email.activity.openInGmail")}
                    >
                      {m.subject || t("email.proposals.noSubject")}
                    </a>
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
              <h2 className="text-sm font-medium text-ink">{t("email.dashboard.title")}</h2>
              <p className="text-[10px] text-ink-faint mt-0.5">
                {t("email.dashboard.desc")}
              </p>
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={refreshActivity}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700"
              >
                {t("email.dashboard.refresh")}
              </button>
              <button
                onClick={handleMarkAllRead}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-dim hover:bg-base-700"
              >
                {t("email.dashboard.markAllRead")}
              </button>
              <button
                onClick={handleClearAll}
                className="text-[10px] px-2 py-1 rounded bg-base-800 text-ink-faint hover:bg-signal-error/20 hover:text-signal-error"
              >
                {t("email.dashboard.clear")}
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
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("email.stats.sent")}</p>
                <p className="text-base font-semibold text-emerald-300">
                  {activityStats.sent?.total || 0}
                </p>
                {(activityStats.sent?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{t("email.stats.unreadCount", { n: activityStats.sent.unread })}</p>
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
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("email.stats.drafts")}</p>
                <p className="text-base font-semibold text-amber-300">
                  {activityStats.draft?.total || 0}
                </p>
                {(activityStats.draft?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{t("email.stats.unreadCount", { n: activityStats.draft.unread })}</p>
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
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("email.stats.alerts")}</p>
                <p className="text-base font-semibold text-rose-300">
                  {activityStats.alert?.total || 0}
                </p>
                {(activityStats.alert?.unread || 0) > 0 && (
                  <p className="text-[9px] text-rose-300 font-medium">
                    {t("email.stats.needsAttention", { n: activityStats.alert.unread })}
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
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("email.stats.urgent")}</p>
                <p className="text-base font-semibold text-orange-300">
                  {activityStats.urgent?.total || 0}
                </p>
                {(activityStats.urgent?.unread || 0) > 0 && (
                  <p className="text-[9px] text-orange-300 font-medium">
                    {t("email.stats.unreadCount", { n: activityStats.urgent.unread })}
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
                <p className="text-[9px] text-ink-faint uppercase tracking-wider">{t("email.stats.meetings")}</p>
                <p className="text-base font-semibold text-violet-300">
                  {(activityStats.meeting_proposal?.total || 0) + (activityStats.meeting_confirmed?.total || 0)}
                </p>
                {(activityStats.meeting_proposal?.unread || 0) > 0 && (
                  <p className="text-[9px] text-ink-faint">{t("email.stats.proposalsCount", { n: activityStats.meeting_proposal.unread })}</p>
                )}
              </button>
            </div>
          )}

          {/* Filter chip "solo no leidos" */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] text-ink-faint">
              {activityFilter === "all"
                ? t("email.activity.showingAll")
                : t("email.activity.filtering", {
                    label: t(ACTIVITY_FILTERS.find((f) => f.id === activityFilter)?.labelKey ?? "email.filter.all"),
                  })}
              {showUnreadOnly && ` ${t("email.activity.unreadOnlySuffix")}`}
            </p>
            <label className="flex items-center gap-1.5 text-[10px] text-ink-dim cursor-pointer">
              <input
                type="checkbox"
                checked={showUnreadOnly}
                onChange={(e) => setShowUnreadOnly(e.target.checked)}
                className="h-3 w-3 accent-accent"
              />
              {t("email.activity.unreadOnly")}
            </label>
          </div>

          {/* Activity feed */}
          {activity.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-3xl mb-2">📭</p>
              <p className="text-xs text-ink-faint">
                {t("email.activity.empty")}
              </p>
              <p className="text-[10px] text-ink-faint mt-1">
                {t("email.activity.emptyHint")}
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
                          {t(vis.labelKey)}
                        </span>
                        {!entry.read && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-accent/20 text-accent">
                            {t("email.activity.new")}
                          </span>
                        )}
                        {entry.timestamp && (
                          <span className="text-[10px] text-ink-faint">
                            {new Date(entry.timestamp).toLocaleString(dateLocale, {
                              day: "2-digit",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-ink mt-1 truncate">
                        <span className="text-ink-faint">{t("email.activity.from")}</span>{" "}
                        <span className="text-ink-dim">{entry.sender_email || entry.sender || "?"}</span>
                        {entry.subject && (
                          <>
                            <span className="text-ink-faint"> · </span>
                            {gmailLink(entry.email_id) ? (
                              <a
                                href={gmailLink(entry.email_id)!}
                                target="_blank"
                                rel="noreferrer"
                                className="text-ink underline decoration-dotted underline-offset-2 hover:text-accent"
                                title={t("email.activity.openInGmail")}
                              >
                                {entry.subject} ↗
                              </a>
                            ) : (
                              <span className="text-ink">{entry.subject}</span>
                            )}
                          </>
                        )}
                      </p>
                      {/* Detalles especificos segun action_type */}
                      {entry.action_type === "sent" && details.is_meeting && (
                        <p className="text-[11px] text-emerald-300/80 mt-0.5">
                          {details.calendar_status === "libre" ? t("email.activity.meetingConfirmed") : t("email.activity.counterProposalSent")}
                          {details.proposed_new_date && (
                            <> {t("email.activity.forDate")} {new Date(details.proposed_new_date).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" })}</>
                          )}
                          {details.accepted_date && (
                            <> {t("email.activity.forDate")} {new Date(details.accepted_date).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" })}</>
                          )}
                        </p>
                      )}
                      {entry.action_type === "draft" && details.is_meeting && (
                        <p className="text-[11px] text-amber-300/80 mt-0.5">
                          {t("email.activity.aiDraftMeeting")}{" "}
                          {details.proposed_new_date ? t("email.activity.withNewDate") : t("email.activity.confirmsDate")}
                        </p>
                      )}
                      {entry.action_type === "alert" && details.is_meeting && (
                        <p className="text-[11px] text-rose-300/90 mt-0.5 font-medium">
                          {details.calendar_status === "ocupado"
                            ? t("email.activity.youAreBusy", { date: details.original_date || "?", suggestion: details.proposed_new_date || "?" })
                            : t("email.activity.meetingProposedFor", { date: details.proposed_date || details.original_date || "?" })}
                        </p>
                      )}
                      {entry.action_type === "alert" && !details.is_meeting && (
                        <p className="text-[11px] text-rose-300/90 mt-0.5">
                          {details.reason || t("email.activity.importantEmail")}
                        </p>
                      )}
                      {entry.action_type === "meeting_proposal" && (
                        <p className="text-[11px] text-violet-300/90 mt-0.5">
                          {t("email.activity.original")}: {details.original_date ? new Date(details.original_date).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" }) : "?"} →
                          {t("email.activity.suggestion")}: {details.proposed_new_date ? new Date(details.proposed_new_date).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" }) : "?"}
                        </p>
                      )}
                      {entry.action_type === "meeting_confirmed" && (
                        <p className="text-[11px] text-signal-ok mt-0.5">
                          {t("email.activity.meetingConfirmedFor")} {details.confirmed_datetime ? new Date(details.confirmed_datetime).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" }) : "?"}
                        </p>
                      )}
                      {details.preview_reply && entry.action_type === "alert" && (
                        <details className="mt-1">
                          <summary className="text-[10px] text-ink-faint cursor-pointer hover:text-ink">
                            {t("email.activity.viewSuggestedReply")}
                          </summary>
                          <p className="text-[10px] text-ink-dim mt-1 italic whitespace-pre-wrap">
                            {details.preview_reply}
                          </p>
                        </details>
                      )}
                      {/* 2026-07-02: actuar desde la alerta (peticion usuario) */}
                      {entry.action_type === "alert" && entry.email_id && (
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <button
                            onClick={() => handleRespondFromAlert(entry.id, "draft")}
                            disabled={respondingId === entry.id}
                            className="text-[10px] px-2 py-1 rounded bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 disabled:opacity-50"
                            title={t("email.activity.generateDraftTitle")}
                          >
                            {respondingId === entry.id ? t("email.activity.generating") : t("email.activity.generateProposal")}
                          </button>
                          <button
                            onClick={() => handleRespondFromAlert(entry.id, "send")}
                            disabled={respondingId === entry.id}
                            className="text-[10px] px-2 py-1 rounded bg-signal-ok/15 text-signal-ok hover:bg-signal-ok/25 disabled:opacity-50"
                            title={t("email.activity.generateSendTitle")}
                          >
                            {respondingId === entry.id ? t("email.activity.sending") : t("email.activity.respondAuto")}
                          </button>
                        </div>
                      )}
                      {/* V0.7.3 (Sprint 4, B6): feedback sobre borradores propuestos */}
                      {entry.action_type === "draft" && entry.rule_id && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <span className="text-[9px] text-ink-faint">{t("email.activity.thisDraft")}</span>
                          <button
                            onClick={() => handleRuleFeedback(entry.rule_id!, "approved")}
                            className="text-[9px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok hover:bg-signal-ok/25"
                            title={t("email.activity.feedbackApprovedTitle")}
                          >
                            ✓ {t("email.activity.feedbackApproved")}
                          </button>
                          <button
                            onClick={() => handleRuleFeedback(entry.rule_id!, "edited")}
                            className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 hover:bg-amber-500/25"
                            title={t("email.activity.feedbackEditedTitle")}
                          >
                            ✎ {t("email.activity.feedbackEdited")}
                          </button>
                          <button
                            onClick={() => handleRuleFeedback(entry.rule_id!, "rejected")}
                            className="text-[9px] px-1.5 py-0.5 rounded bg-signal-error/15 text-signal-error hover:bg-signal-error/25"
                            title={t("email.activity.feedbackRejectedTitle")}
                          >
                            ✗ {t("email.activity.feedbackRejected")}
                          </button>
                        </div>
                      )}
                      {entry.rule_name && (
                        <p className="text-[10px] text-ink-faint mt-1">
                          {t("email.activity.ruleApplied")}: <span className="text-ink-dim">{entry.rule_name}</span>
                        </p>
                      )}
                    </div>
                    {/* Boton descartar */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismissEntry(entry.id);
                      }}
                      title={t("email.activity.dismissEntry")}
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
              {t("email.proposals.title", { n: proposals.length })}
            </h2>
          </div>

          {proposals.length === 0 ? (
            <p className="text-xs text-ink-faint py-3 text-center">
              {t("email.proposals.empty")}
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
                          {p.subject || t("email.proposals.noSubject")}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${sc.bg} ${sc.text}`}>
                          {t(sc.labelKey)}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-faint mt-0.5">
                        {t("email.activity.from")} <span className="text-ink-dim">{p.sender}</span>
                      </p>
                      <div className="text-[11px] text-ink-dim mt-1 grid grid-cols-2 gap-x-3">
                        <div>
                          <span className="text-ink-faint">{t("email.proposals.theyProposed")}:</span>{" "}
                          {p.original_proposed_datetime
                            ? new Date(p.original_proposed_datetime).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" })
                            : "—"}
                        </div>
                        {p.counter_proposed_datetime && (
                          <div>
                            <span className="text-ink-faint">{t("email.proposals.iProposed")}:</span>{" "}
                            {new Date(p.counter_proposed_datetime).toLocaleString(dateLocale, { dateStyle: "short", timeStyle: "short" })}
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
                        if (confirm(t("email.proposals.confirmDelete", { id: p.id }))) {
                          api.deleteProposal(p.id).then(refresh).catch((e) =>
                            setMsg({ kind: "err", text: t("email.errDeleting", { msg: e.message }) })
                          );
                        }
                      }}
                      className="text-[10px] px-2 py-1 rounded bg-base-700/50 text-ink-faint hover:bg-signal-error/20 hover:text-signal-error shrink-0"
                    >
                      {t("email.proposals.delete")}
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
              {t("email.rules.title", { n: rules.length })}
            </h2>
            <p className="text-[10px] text-ink-faint">
              {t("email.rules.desc")}
            </p>
          </div>

          {loading ? (
            <p className="text-xs text-ink-faint">{t("email.rules.loading")}</p>
          ) : rules.length === 0 ? (
            <p className="text-xs text-ink-faint py-3">
              {t("email.rules.empty")}{" "}
              <em>{t("email.rules.emptyExample")}</em>.
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
                        {rule.enabled ? t("email.rules.active") : t("email.rules.inactive")}
                      </span>
                      {/* V0.7.3 (Sprint 4, B6): autonomia gradual */}
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          rule.autonomy === "auto"
                            ? "bg-signal-ok/20 text-signal-ok"
                            : "bg-amber-500/20 text-amber-400"
                        }`}
                        title={
                          rule.autonomy === "auto"
                            ? t("email.rules.autoTitle")
                            : t("email.rules.proposeTitle")
                        }
                      >
                        {rule.autonomy === "auto" ? t("email.rules.auto") : t("email.rules.propose")}
                      </span>
                      {(rule.approved_count || 0) + (rule.rejected_count || 0) + (rule.edited_count || 0) > 0 && (
                        <span className="text-[9px] text-ink-faint" title={t("email.rules.countsTitle")}>
                          ✓{rule.approved_count || 0} ✎{rule.edited_count || 0} ✗{rule.rejected_count || 0}
                        </span>
                      )}
                    </div>
                    {/* FIX (Tarea 1.3 Fase 4b): mostrar los campos reales
                        (sender_emails / sender_domains), no los legacy matching/pattern. */}
                    {(() => {
                      const emailsStr = (rule.sender_emails || []).join(", ");
                      const domainsStr = (rule.sender_domains || []).join(", ");
                      return (
                        <p className="text-[11px] text-ink-dim mt-0.5">
                          {emailsStr && <span>{t("email.rules.emails")}: <code className="bg-base-950/50 px-1 rounded">{emailsStr}</code></span>}
                          {domainsStr && <span> | {t("email.rules.domains")}: <code className="bg-base-950/50 px-1 rounded">{domainsStr}</code></span>}
                          {!emailsStr && !domainsStr && rule.pattern && (
                            <span>
                              {rule.matching ? t(MATCHING_LABEL_KEYS[rule.matching]) : ""}{" "}
                              <code className="bg-base-950/50 px-1 rounded">{rule.pattern}</code>
                            </span>
                          )}
                        </p>
                      );
                    })()}
                    <p className="text-[11px] text-ink-faint mt-1 italic truncate">
                      {rule.ai_prompt ? (
                        <>
                          <span className="text-accent not-italic">{t("email.rules.ai")}:</span> {rule.ai_prompt}
                          {rule.reply_template && <span className="text-ink-faint"> {t("email.rules.fallbackTemplate")}</span>}
                        </>
                      ) : (
                        <>{t("email.rules.response")}: {rule.reply_template || t("email.rules.onlyMeetingsAI")}</>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {rule.can_promote && (
                      <button
                        onClick={() => promoteRule(rule, "auto")}
                        className="text-[10px] px-2 py-1 rounded bg-signal-ok/15 text-signal-ok hover:bg-signal-ok/25 border border-signal-ok/30"
                        title={t("email.rules.canPromoteTitle")}
                      >
                        {t("email.rules.promoteToAuto")}
                      </button>
                    )}
                    {rule.autonomy === "auto" && (
                      <button
                        onClick={() => promoteRule(rule, "propose")}
                        className="text-[10px] px-2 py-1 rounded bg-base-700/50 text-ink-faint hover:bg-base-700"
                        title={t("email.rules.demoteTitle")}
                      >
                        {t("email.rules.demoteToPropose")}
                      </button>
                    )}
                    <button
                      onClick={() => toggleRule(rule)}
                      className="text-[10px] px-2 py-1 rounded bg-base-700/50 text-ink-dim hover:bg-base-700"
                    >
                      {rule.enabled ? t("email.rules.disable") : t("email.rules.enable")}
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id, rule.name)}
                      className="text-[10px] px-2 py-1 rounded bg-signal-error/10 text-signal-error hover:bg-signal-error/20"
                    >
                      {t("email.proposals.delete")}
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
            {t("email.addRule.title")}
          </h2>
          <p className="text-[10px] text-ink-faint mb-4">
            {t("email.addRule.desc")}
          </p>

          {/* Paso 1: Nombre */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              {t("email.addRule.step1")}
            </label>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder={t("email.addRule.namePlaceholder")}
              className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
            />
          </div>

          {/* Paso 2: Emails / dominios */}
          <div className="mb-3 grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                {t("email.addRule.step2a")}
                <span className="text-ink-faint normal-case tracking-normal ml-1">{t("email.addRule.commaSeparated")}</span>
              </label>
              <input
                value={formSenderEmailsText}
                onChange={(e) => setFormSenderEmailsText(e.target.value)}
                placeholder="losmagnoviajes@gmail.com, jefe@empresa.com"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
              <p className="text-[9px] text-ink-faint mt-1">
                {t("email.addRule.exactMatch")}
              </p>
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                {t("email.addRule.step2b")}
                <span className="text-ink-faint normal-case tracking-normal ml-1">{t("email.addRule.commaSeparated")}</span>
              </label>
              <input
                value={formSenderDomainsText}
                onChange={(e) => setFormSenderDomainsText(e.target.value)}
                placeholder="empresa.com, cliente.com"
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
              <p className="text-[9px] text-ink-faint mt-1">
                {t("email.addRule.exactDomainMatch")}
              </p>
            </div>
          </div>

          {/* Paso 3: Accion */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              {t("email.addRule.step3")}
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
                  <strong className="block text-ink">{t(ACTION_LABEL_KEYS[a])}</strong>
                  <span className="text-[10px] text-ink-faint">
                    {a === "auto_send" && t("email.addRule.actionAutoSendDesc")}
                    {a === "create_draft" && t("email.addRule.actionCreateDraftDesc")}
                    {a === "alert_only" && t("email.addRule.actionAlertOnlyDesc")}
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
                {t("email.addRule.detectMeeting")}
              </label>
            </div>
            <p className="text-[10px] text-ink-faint mt-1 ml-6">
              {t("email.addRule.detectMeetingDesc")}
            </p>
          </div>

          {/* Paso 4: Plantilla */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              {t("email.addRule.step4")}
              <span className="text-ink-faint normal-case tracking-normal ml-1">
                ({formDetectMeeting ? t("email.addRule.optional") : t("email.addRule.mandatory")}) {t("email.addRule.step4Suffix")}
              </span>
            </label>
            <textarea
              value={formReplyTemplate}
              onChange={(e) => setFormReplyTemplate(e.target.value)}
              placeholder={
                formDetectMeeting
                  ? t("email.addRule.templatePlaceholderMeeting")
                  : t("email.addRule.templatePlaceholder")
              }
              rows={3}
              className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 resize-y"
            />
            <p className="text-[9px] text-ink-faint mt-1">
              {t("email.addRule.variablesAvailable")}: {"{sender}"}, {"{subject}"}, {"{body}"}
            </p>
            {formDetectMeeting && !formReplyTemplate.trim() && (
              <p className="text-[10px] text-emerald-400 mt-1">
                {t("email.addRule.noTemplateHint")}
              </p>
            )}
          </div>

          {/* V0.7.3b (Sprint 4b): Paso 4b — Respuesta generada por IA */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              {t("email.addRule.step4b")}
              <span className="text-ink-faint normal-case tracking-normal ml-1">
                {t("email.addRule.step4bHint")}
              </span>
            </label>
            <textarea
              value={formAiPrompt}
              onChange={(e) => setFormAiPrompt(e.target.value)}
              placeholder={t("email.addRule.aiPromptPlaceholder")}
              rows={2}
              className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 resize-y"
            />
            <p className="text-[9px] text-ink-faint mt-1">
              {t("email.addRule.aiPromptDesc")}
            </p>
          </div>

          {/* V0.7.3 (Sprint 4, B6): Paso 5 — Autonomia (eleccion directa) */}
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
              {t("email.addRule.step5")}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setFormAutonomy("propose")}
                className={`text-xs px-3 py-2 rounded-lg border text-left ${
                  formAutonomy === "propose"
                    ? "bg-amber-500/20 border-amber-500/50 text-amber-300"
                    : "bg-base-700/50 border-base-600 text-ink-dim hover:bg-base-700"
                }`}
              >
                <strong className="block text-ink">{t("email.addRule.autonomyProposeTitle")}</strong>
                <span className="text-[10px] text-ink-faint">
                  {t("email.addRule.autonomyProposeDesc")}
                </span>
              </button>
              <button
                type="button"
                onClick={() => setFormAutonomy("auto")}
                className={`text-xs px-3 py-2 rounded-lg border text-left ${
                  formAutonomy === "auto"
                    ? "bg-signal-ok/20 border-signal-ok/50 text-signal-ok"
                    : "bg-base-700/50 border-base-600 text-ink-dim hover:bg-base-700"
                }`}
              >
                <strong className="block text-ink">{t("email.addRule.autonomyAutoTitle")}</strong>
                <span className="text-[10px] text-ink-faint">
                  {t("email.addRule.autonomyAutoDesc")}
                </span>
              </button>
            </div>
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
                {t("email.addRule.enableImmediately")}
              </label>
            </div>
            <button
              onClick={addRule}
              className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow transition-colors"
            >
              {t("email.addRule.create")}
            </button>
          </div>
        </div>

        {/* Test de regla */}
        <div className="glass-surface rounded-2xl p-5">
          <h2 className="text-sm font-medium text-ink mb-3">
            {t("email.testRule.title")}
          </h2>
          <p className="text-[10px] text-ink-faint mb-3">
            {t("email.testRule.desc")}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                {t("email.testRule.sender")}
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
                {t("email.testRule.subject")}
              </label>
              <input
                value={testSubject}
                onChange={(e) => setTestSubject(e.target.value)}
                placeholder={t("email.testRule.subjectPlaceholder")}
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                {t("email.testRule.body")}
              </label>
              <input
                value={testBody}
                onChange={(e) => setTestBody(e.target.value)}
                placeholder={t("email.testRule.bodyPlaceholder")}
                className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <button
              onClick={testRule}
              className="text-xs px-4 py-2 rounded-lg bg-base-800 text-ink border border-base-700 hover:bg-base-700"
            >
              {t("email.testRule.run")}
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
                    {t("email.testRule.activated", { n: testResult.matches.length })}
                  </p>
                  {testResult.matches.map((m, i) => (
                    <div key={i} className="mt-2 text-xs">
                      <p className="text-ink-dim">
                        {t("email.testRule.rule")}: <span className="text-ink">{m.name}</span>
                      </p>
                      <p className="text-ink-faint italic mt-0.5">
                        "{m.reply_text}"
                      </p>
                    </div>
                  ))}
                </>
              ) : (
                <p className="text-xs text-ink-dim">
                  {t("email.testRule.noMatch")}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}