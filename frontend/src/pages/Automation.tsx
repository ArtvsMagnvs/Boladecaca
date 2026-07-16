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

const TRIGGER_LABELS: Record<string, string> = {
  schedule: "Programada",
  event: "Por evento",
  condition: "Por condición",
  pattern: "Por patrón",
  memory: "Por memoria",
  webhook: "Webhook",
};

const ACTION_LABELS: Record<string, string> = {
  telegram_message: "Mensaje de Telegram",
  email_summary: "Resumen de email",
  chat_query: "Consulta al chat",
  agent_task: "Tarea de agente",
  workspace: "Acción en el Workspace",
  skill_execution: "Ejecutar skill",
  calendar_block: "Bloque de calendario",
  chained_rule: "Regla encadenada",
  memory_update: "Actualizar memoria",
};

const STATUS_LABEL: Record<string, string> = {
  ok: "OK",
  failed: "Falló",
  skipped: "Omitida",
  waiting_approval: "Esperando aprobación",
};
const STATUS_COLOR: Record<string, string> = {
  ok: "text-signal-ok",
  failed: "text-signal-error",
  skipped: "text-ink-faint",
  waiting_approval: "text-signal-warn",
};

function triggerSummary(rule: AutomationRule): string {
  const cfg = (rule.trigger_config ?? {}) as Record<string, unknown>;
  if (rule.trigger_type === "schedule") {
    const cron = cfg.cron as { hour?: number; minute?: number } | undefined;
    if (cron) {
      const h = String(cron.hour ?? 0).padStart(2, "0");
      const m = String(cron.minute ?? 0).padStart(2, "0");
      return `Cada día a las ${h}:${m}`;
    }
    if (typeof cfg.interval_minutes === "number") return `Cada ${cfg.interval_minutes} min`;
    return "Programada";
  }
  if (rule.trigger_type === "event") {
    return `Cuando ocurre: ${String(cfg.event_name ?? "evento")}`;
  }
  return TRIGGER_LABELS[rule.trigger_type] ?? rule.trigger_type;
}

export default function Automation() {
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
      setError(e instanceof Error ? e.message : "No se pudieron cargar las automatizaciones.");
    }
  }, []);

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
  // (doc 20 A1: el gate notifica por el canal de origen, no aquí).
  useEffect(() => {
    const id = window.setInterval(() => {
      api.getApprovals().then(setApprovals).catch(() => {});
    }, 15000);
    return () => window.clearInterval(id);
  }, []);

  const toggleRule = async (rule: AutomationRule) => {
    setBusyRuleId(rule.id);
    setError(null);
    try {
      const updated = await api.toggleAutomationRule(rule.id, !rule.enabled);
      setRules((prev) => (prev ?? []).map((r) => (r.id === rule.id ? updated : r)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cambiar el estado de la regla.");
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
      setError(e instanceof Error ? e.message : "No se pudo resolver la aprobación.");
    } finally {
      setBusyGateId(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 flex flex-col gap-5 max-w-4xl mx-auto w-full">
      <div>
        <h1 className="text-xl font-semibold text-ink">Automatizaciones</h1>
        <p className="text-xs text-ink-faint mt-0.5">
          Reglas que actúan por ti — todas nacen desactivadas. Actívalas cuando quieras que Aithera actúe sin preguntar.
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
            Aprobaciones pendientes ({approvals.length})
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
                    ✓ Aprobar
                  </button>
                  <button
                    onClick={() => resolve(a.gate_id, false)}
                    disabled={busyGateId === a.gate_id}
                    className="text-xs px-2.5 py-1 rounded-lg bg-signal-error/15 text-signal-error hover:bg-signal-error/25 disabled:opacity-50"
                  >
                    ✗ Rechazar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="glass-surface rounded-2xl p-4">
        <h2 className="text-xs uppercase tracking-wider text-ink-faint mb-3">Reglas</h2>
        {rules === null ? (
          <p className="text-xs text-ink-faint px-1">Cargando…</p>
        ) : rules.length === 0 ? (
          <p className="text-xs text-ink-faint px-1">Sin reglas todavía.</p>
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
                    {triggerSummary(rule)} → {ACTION_LABELS[rule.action_type] ?? rule.action_type}
                    {rule.cooldown_s > 0 && ` · cooldown ${rule.cooldown_s}s`}
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
                  {rule.enabled ? "Activada" : "Desactivada"}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="glass-surface rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs uppercase tracking-wider text-ink-faint">
            Historial{selectedRuleId != null ? ` — ${rules?.find((r) => r.id === selectedRuleId)?.name ?? ""}` : ""}
          </h2>
          {selectedRuleId != null && (
            <button onClick={() => setSelectedRuleId(null)} className="text-[11px] text-accent hover:text-accent-soft">
              Ver todo
            </button>
          )}
        </div>
        {executions.length === 0 ? (
          <p className="text-xs text-ink-faint px-1">Sin ejecuciones todavía.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {executions.map((ex) => (
              <div key={ex.id} className="flex items-center gap-3 px-1 py-1.5 text-xs">
                <span className={`shrink-0 w-28 ${STATUS_COLOR[ex.status] ?? "text-ink-dim"}`}>
                  {STATUS_LABEL[ex.status] ?? ex.status}
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
