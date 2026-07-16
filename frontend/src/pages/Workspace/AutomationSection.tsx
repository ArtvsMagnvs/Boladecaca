// pages/Workspace/AutomationSection.tsx — reglas del proyecto (V0.9 A3, Δ10)
//
// Rellena el stub "Automatizaciones" de ProjectCard con las reglas reales
// filtradas por project_id (GET /automation/rules?project_id=). Hoy casi
// siempre estará vacía: las 5 reglas predefinidas (rules_builtin.py) nacen
// globales (project_id=None) — no hay todavía UI para crear una regla scoped
// a un proyecto (eso es trabajo futuro, fuera de A3). El toggle es el mismo
// patrón simple que /automation; el detalle completo vive ahí ("Ver todas").
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type AutomationRule } from "@/lib/api";

interface Props {
  projectId: number;
}

export function AutomationSection({ projectId }: Props) {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    api.getAutomationRules(projectId).then(setRules).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (rule: AutomationRule) => {
    setBusyId(rule.id);
    try {
      const updated = await api.toggleAutomationRule(rule.id, !rule.enabled);
      setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)));
    } catch {
      // el detalle/errores completos viven en /automation — aquí solo un vistazo
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-1.5">
        <h3 className="text-xs font-medium text-ink-dim">Automatizaciones</h3>
        <button onClick={() => navigate("/automation")} className="text-[11px] text-accent hover:text-accent-soft">
          Ver todas
        </button>
      </div>
      {rules.length === 0 ? (
        <p className="text-[11px] text-ink-faint px-1">
          Sin reglas para este proyecto todavía.
        </p>
      ) : (
        <div className="flex flex-col gap-1">
          {rules.map((r) => (
            <div key={r.id} className="flex items-center gap-2 rounded-lg px-2 py-1.5 bg-base-800/40">
              <span className="text-[11px] text-ink truncate flex-1">{r.name}</span>
              <button
                onClick={() => toggle(r)}
                disabled={busyId === r.id}
                className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 disabled:opacity-50 ${
                  r.enabled ? "border-accent/40 bg-accent/15 text-accent" : "border-base-700 text-ink-faint"
                }`}
              >
                {r.enabled ? "ON" : "OFF"}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
