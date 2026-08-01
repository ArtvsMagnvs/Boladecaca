// Automation.tsx — V0.9 (Automation Engine A3): reglas + historial + aprobaciones.
//
// Alcance de A3 (doc 20 §A3): listar reglas y activarlas/desactivarlas (HITL —
// todas nacen desactivadas), ver el historial de ejecuciones, y resolver
// aprobaciones pendientes del ApprovalGate (el Hub NO recibe push, esta pagina
// sondea GET /automation/approvals). El toggle es un boton simple a proposito:
// el interruptor deslizante azul + el selector de perfiles de autonomia son
// A3b ("Permisos & Autonomia", doc 20) — no se adelanta aqui.
import { useCallback, useEffect, useState } from "react";
import { api, type Approval, type AutomationExecution, type AutomationRule } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import { useT } from "@/store/useI18n";

const TRIGGER_KEYS: Record<string, string> = {
  schedule: "automation.trigger.schedule",
  event: "automation.trigger.event",
  condition: "automation.trigger.condition",
  pattern: "automation.trigger.pattern",
  memory: "automation.trigger.memory",
  webhook: "automation.trigger.webhook",
};

const ACTION_KEYS: Record<string, string> = {
  telegram_message: "automation.action.telegram_message",
  email_summary: "automation.action.email_summary",
  chat_query: "automation.action.chat_query",
  agent_task: "automation.action.agent_task",
  workspace: "automation.action.workspace",
  skill_execution: "automation.action.skill_execution",
  calendar_block: "automation.action.calendar_block",
  chained_rule: "automation.action.chained_rule",
  memory_update: "automation.action.memory_update",
};

const STATUS_KEY: Record<string, string> = {
  ok: "automation.status.ok",
  failed: "automation.status.failed",
  skipped: "automation.status.skipped",
  waiting_approval: "automation.status.waiting_approval",
};
const STATUS_COLOR: Record<string, string> = {
  ok: "text-signal-ok",
  failed: "text-signal-error",
  skipped: "text-ink-faint",
  waiting_approval: "text-signal-warn",
};

function triggerSummary(rule: AutomationRule, t: (key: string, vars?: Record<string, string | number>) => string): string {
  const cfg = (rule.trigger_config ?? {}) as Record<string, unknown>;
  if (rule.trigger_type === "schedule") {
    const cron = cfg.cron as { hour?: number; minute?: number } | undefined;
    if (cron) {
      const h = String(cron.hour ?? 0).padStart(2, "0");
      const m = String(cron.minute ?? 0).padStart(2, "0");
      return t("automation.trigger.dailyAt", { time: `${h}:${m}` });
    }
    if (typeof cfg.interval_minutes === "number") return t("automation.trigger.everyMin", { n: cfg.interval_minutes });
    return t("automation.trigger.schedule");
  }
  if (rule.trigger_type === "event") {
    return t("automation.trigger.onEvent", { event: String(cfg.event_name ?? "evento") });
  }
  return TRIGGER_KEYS[rule.trigger_type] ? t(TRIGGER_KEYS[rule.trigger_type]) : rule.trigger_type;
}

export default function Automation() {
  const t = useT();
  const [rules, setRules] = useState<AutomationRule[] | null>(null);
  const [executions, setExecutions] = useState<AutomationExecution[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [selectedRuleId, setSelectedRuleId] = useState<number | null>(null);
  const [busyRuleId, setBusyRuleId] = useState<number | null>(null);
  const [busyGateId, setBusyGateId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, a] = await Promise.all([api.getAutomationRules(), api.getApprovals()]);
      setRules(r);
      setApprovals(a);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("automation.loadError"));
    }
  }, [t]);

  const loadExecutions = useCallback(async (ruleId: number | null) => {
    try {
      const rows = await api.getAutomationExecutions(ruleId ?? undefined, 50);
      setExecutions(rows);
    } catch {
      // el historial es informativo — un fallo aqui no bloquea el resto de la pagina
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadExecutions(selectedRuleId);
  }, [selectedRuleId, loadExecutions]);

  // Sondeo ligero de aprobaciones pendientes — el Hub tampoco recibe push
  // (doc 20 A1: el gate notifica por el canal de origen, no aquí). [P1] pausado
  // cuando la ventana no está visible.
  usePolling(() => {
    api.getApprovals().then(setApprovals).catch(() => {});
  }, 15000);

  const toggleRule = async (rule: AutomationRule) => {
    setBusyRuleId(rule.id);
    setError(null);
    try {
      const updated = await api.toggleAutomationRule(rule.id, !rule.enabled);
      setRules((prev) => (prev ?? []).map((r) => (r.id === rule.id ? updated : r)));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("automation.toggleError"));
    } finally {
      setBusyRuleId(null);
    }
  };

  const resolve = async (gateId: string, approved: boolean) => {
    setBusyGateId(gateId);
    setError(null);
    try {
      await api.resolveApproval(gateId, approved);
      setApprovals((prev) => prev.filter((a) => a.gate_id !== gateId));
      loadExecutions(selectedRuleId);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("automation.resolveError"));
    } finally {
      setBusyGateId(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 flex flex-col gap-5 max-w-4xl mx-auto w-full">
      <div className="glass-surface rounded-xl px-4 py-2.5 w-fit">
        <h1 className="text-xl font-semibold text-ink">{t("automation.title")}</h1>
        <p className="text-xs text-ink-faint mt-0.5">
          {t("automation.subtitle")}
        </p>
      </div>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {approvals.length > 0 && (
        <section className="glass-surface rounded-2xl p-4">
          <h2 className="text-xs uppercase tracking-wider text-signal-warn mb-3">
            {t("automation.pendingApprovals", { n: approvals.length })}
          </h2>
          <div className="flex flex-col gap-2">
            {approvals.map((a) => (
              <div key={a.gate_id} className="flex items-start gap-3 rounded-xl bg-base-800/60 px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink truncate">{a.title}</p>
                  {a.summary && <p className="text-xs text-ink-faint mt-0.5">{a.summary}</p>}
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => resolve(a.gate_id, true)}
                    disabled={busyGateId === a.gate_id}
                    className="text-xs px-2.5 py-1 rounded-lg bg-signal-ok/15 text-signal-ok hover:bg-signal-ok/25 disabled:opacity-50"
                  >
                    {t("automation.approve")}
                  </button>
                  <button
                    onClick={() => resolve(a.gate_id, false)}
                    disabled={busyGateId === a.gate_id}
                    className="text-xs px-2.5 py-1 rounded-lg bg-signal-error/15 text-signal-error hover:bg-signal-error/25 disabled:opacity-50"
                  >
                    {t("automation.reject")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="glass-surface rounded-2xl p-4">
        <h2 className="text-xs uppercase tracking-wider text-ink-faint mb-3">{t("automation.rules.title")}</h2>
        {rules === null ? (
          <p className="text-xs text-ink-faint px-1">{t("automation.rules.loading")}</p>
        ) : rules.length === 0 ? (
          <p className="text-xs text-ink-faint px-1">{t("automation.rules.empty")}</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {rules.map((rule) => (
              <div
                key={rule.id}
                onClick={() => setSelectedRuleId(rule.id === selectedRuleId ? null : rule.id)}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 cursor-pointer border transition-colors ${
                  selectedRuleId === rule.id ? "border-accent/40 bg-accent/8" : "border-transparent hover:bg-base-700/40"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink">{rule.name}</p>
                  <p className="text-[11px] text-ink-faint mt-0.5">
                    {triggerSummary(rule, t)} → {ACTION_KEYS[rule.action_type] ? t(ACTION_KEYS[rule.action_type]) : rule.action_type}
                    {rule.cooldown_s > 0 && ` · ${t("automation.rules.cooldown", { s: rule.cooldown_s })}`}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleRule(rule);
                  }}
                  disabled={busyRuleId === rule.id}
                  className={`text-[11px] px-2.5 py-1 rounded-lg border shrink-0 disabled:opacity-50 ${
                    rule.enabled
                      ? "border-accent/40 bg-accent/15 text-accent"
                      : "border-base-700 text-ink-faint hover:text-ink"
                  }`}
                >
                  {rule.enabled ? t("automation.rules.enabled") : t("automation.rules.disabled")}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="glass-surface rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs uppercase tracking-wider text-ink-faint">
            {t("automation.history.title")}{selectedRuleId != null ? ` — ${rules?.find((r) => r.id === selectedRuleId)?.name ?? ""}` : ""}
          </h2>
          {selectedRuleId != null && (
            <button onClick={() => setSelectedRuleId(null)} className="text-[11px] text-accent hover:text-accent-soft">
              {t("automation.history.viewAll")}
            </button>
          )}
        </div>
        {executions.length === 0 ? (
          <p className="text-xs text-ink-faint px-1">{t("automation.history.empty")}</p>
        ) : (
          <div className="flex flex-col gap-1">
            {executions.map((ex) => (
              <div key={ex.id} className="flex items-center gap-3 px-1 py-1.5 text-xs">
                <span className={`shrink-0 w-28 ${STATUS_COLOR[ex.status] ?? "text-ink-dim"}`}>
                  {STATUS_KEY[ex.status] ? t(STATUS_KEY[ex.status]) : ex.status}
                </span>
                <span className="text-ink-faint shrink-0">{ex.trigger_source}</span>
                <span className="text-ink-dim truncate flex-1">{ex.error || ex.result || "—"}</span>
                {ex.duration_ms != null && <span className="text-ink-faint shrink-0">{ex.duration_ms}ms</span>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
