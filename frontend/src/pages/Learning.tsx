// Learning.tsx — "Aithera aprende" (V1.1 L4, doc 27 §5)
//
// LA CARA VISIBLE DEL LEARNER. Página propia y no una pestaña de Ajustes: el
// aprendizaje es una capacidad de primera clase, no una configuración.
//
// LA REGLA QUE GOBIERNA TODO ESTE ARCHIVO: aquí no se habla como habla el
// código. Nada de `blame`, `kind`, `escalera de confianza` ni `evidencia
// externa` — el backend ya devuelve las etiquetas en llano y aquí solo se
// pintan. El dato crudo vive a UN CLIC (expandir); la primera lectura es
// siempre una frase que se entiende.
//
// Pestañas como DATO (no como código): añadir "Caminos" o "Informe" en V1.2 es
// añadir una entrada al array, no refactorizar la página.
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  type LearnerHealth,
  type LearnerHistory,
  type LearnerProposal,
} from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import { useConfirm } from "@/components/ConfirmDialog";
import { useT } from "@/store/useI18n";

type Tab = "proposals" | "health" | "history";

const TABS: { id: Tab; key: string }[] = [
  { id: "proposals", key: "learning.tab.proposals" },
  { id: "health", key: "learning.tab.health" },
  { id: "history", key: "learning.tab.history" },
];

/** Color del riesgo. El texto lo pone el backend; aquí solo el tono. */
const RISK_TONE: Record<string, string> = {
  low: "text-signal-ok border-signal-ok/30 bg-signal-ok/10",
  medium: "text-signal-warn border-signal-warn/30 bg-signal-warn/10",
  high: "text-signal-error border-signal-error/30 bg-signal-error/10",
};

/** Tono de cada culpa. `unknown` en gris a propósito: no acusa a nadie. */
const BLAME_TONE: Record<string, string> = {
  external: "bg-base-500",
  config: "bg-signal-warn",
  model: "bg-accent",
  tool: "bg-signal-error",
  aithera: "bg-signal-error",
  none: "bg-base-600",
  unknown: "bg-base-700",
};

function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-base-700 px-5 py-8 text-center text-sm text-ink-dim">
      {text}
    </div>
  );
}

export default function Learning() {
  const t = useT();
  const navigate = useNavigate();
  const [confirm, confirmDialog] = useConfirm();
  const [tab, setTab] = useState<Tab>("proposals");
  const [proposals, setProposals] = useState<LearnerProposal[]>([]);
  const [waiting, setWaiting] = useState(0);
  const [health, setHealth] = useState<LearnerHealth | null>(null);
  const [history, setHistory] = useState<LearnerHistory | null>(null);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, h, hi] = await Promise.all([
        api.getLearnerProposals(),
        api.getLearnerHealth(),
        api.getLearnerHistory(),
      ]);
      setProposals(p.proposals);
      setWaiting(p.waiting_for_you);
      setHealth(h);
      setHistory(hi);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);
  // Sondeo suave: el Learner trabaja de fondo y puede aparecer algo mientras
  // la página está abierta. `usePolling` no corre con la ventana oculta (P1).
  usePolling(load, 30_000);

  const decide = async (id: string, accept: boolean) => {
    setBusy(id);
    try {
      if (accept) await api.approveLearning(id);
      else {
        const ok = await confirm({
          title: t("learning.reject.confirmTitle"),
          message: t("learning.reject.confirmBody"),
          confirmLabel: t("learning.reject.confirm"),
        });
        if (!ok) return;
        await api.rejectLearning(id);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const undo = async (id: string) => {
    setBusy(id);
    try {
      await api.undoLearning(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const analyze = async () => {
    setAnalyzing(true);
    try {
      await api.runLearnerAnalysis();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  };

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const headline = health?.report?.headline;

  return (
    <div className="h-full overflow-y-auto px-6 pb-32 pt-6">
      {confirmDialog}
      <div className="mx-auto max-w-4xl">
        {/* ── Cabecera ─────────────────────────────────────────────── */}
        <div className="glass-surface holo-frame rounded-2xl p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-ink">{t("learning.title")}</h1>
              <p className="mt-1 max-w-xl text-sm text-ink-dim">
                {t("learning.subtitle")}
              </p>
              {headline && (
                <p className="mt-3 text-sm text-accent">{headline}</p>
              )}
            </div>
            <button
              onClick={analyze}
              disabled={analyzing}
              className="shrink-0 rounded-lg border border-base-700 px-3 py-1.5 text-xs text-ink-dim transition hover:border-accent/50 hover:text-ink disabled:opacity-50"
            >
              {analyzing ? t("learning.analyzing") : t("learning.analyzeNow")}
            </button>
          </div>

          {/* Pestañas */}
          <div className="mt-5 flex gap-1 border-b border-base-800">
            {TABS.map((x) => (
              <button
                key={x.id}
                onClick={() => setTab(x.id)}
                className={`relative px-4 py-2 text-sm transition ${
                  tab === x.id
                    ? "text-ink after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-full after:bg-accent"
                    : "text-ink-dim hover:text-ink"
                }`}
              >
                {t(x.key)}
                {x.id === "proposals" && waiting > 0 && (
                  <span className="ml-2 rounded-full bg-signal-warn/20 px-1.5 py-0.5 text-[10px] text-signal-warn">
                    {waiting}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-signal-error/30 bg-signal-error/10 px-4 py-2 text-sm text-signal-error">
            {error}
          </div>
        )}

        {/* ── Propuestas ───────────────────────────────────────────── */}
        {tab === "proposals" && (
          <div className="mt-4 space-y-3">
            {proposals.length === 0 && <Empty text={t("learning.empty.proposals")} />}
            {proposals.map((p) => (
              <div key={p.id} className="glass-surface rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] uppercase tracking-wide text-ink-dim">
                        {p.kind_label}
                      </span>
                      {p.risk_label && (
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${
                            RISK_TONE[p.risk] ?? "border-base-700 text-ink-dim"
                          }`}
                        >
                          {p.risk_label}
                        </span>
                      )}
                    </div>
                    <h3 className="mt-1 truncate text-sm font-medium text-ink">
                      {p.title}
                    </h3>
                    <p className="mt-1 text-sm text-ink-dim">{p.summary}</p>
                  </div>
                </div>

                {/* La evidencia, plegada: la primera lectura es una frase. */}
                {p.evidence_count > 0 && (
                  <button
                    onClick={() => toggle(p.id)}
                    className="mt-3 text-xs text-accent hover:underline"
                  >
                    {t("learning.seenIn", { n: String(p.evidence_count) })}
                    {open.has(p.id) ? " ▴" : " ▾"}
                  </button>
                )}
                {open.has(p.id) && (
                  <div className="mt-2 space-y-2 rounded-lg bg-base-900/60 p-3">
                    {p.steps.length > 0 && (
                      <ol className="list-inside list-decimal space-y-0.5 text-xs text-ink-dim">
                        {p.steps.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ol>
                    )}
                    <div className="flex flex-wrap gap-1.5">
                      {p.mission_ids.map((m) => (
                        <button
                          key={m}
                          onClick={() => navigate("/missions", { state: { missionId: m } })}
                          className="rounded border border-base-700 px-1.5 py-0.5 font-mono text-[10px] text-ink-dim hover:border-accent/50 hover:text-ink"
                        >
                          {m.slice(0, 8)}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Los botones. Sin applier no se ofrece "Aceptar" — lo dice el
                    backend (`applicable`), no una condición inventada aquí. */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {p.applicable ? (
                    <button
                      onClick={() => decide(p.id, true)}
                      disabled={busy === p.id}
                      className="rounded-lg bg-accent/20 px-3 py-1.5 text-xs text-accent transition hover:bg-accent/30 disabled:opacity-50"
                    >
                      {t("learning.accept")}
                    </button>
                  ) : (
                    <button
                      onClick={() =>
                        navigate("/", { state: { openSettings: true, tab: p.settings_tab } })
                      }
                      className="rounded-lg bg-signal-warn/20 px-3 py-1.5 text-xs text-signal-warn transition hover:bg-signal-warn/30"
                    >
                      {t("learning.goSettings")}
                    </button>
                  )}
                  <button
                    onClick={() => decide(p.id, false)}
                    disabled={busy === p.id}
                    className="rounded-lg border border-base-700 px-3 py-1.5 text-xs text-ink-dim transition hover:border-signal-error/40 hover:text-signal-error disabled:opacity-50"
                  >
                    {t("learning.reject")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Salud ────────────────────────────────────────────────── */}
        {tab === "health" && health && (
          <div className="mt-4 space-y-3">
            {health.total_failures === 0 ? (
              <Empty text={t("learning.empty.health")} />
            ) : (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.health.why")}
                </h3>
                <div className="mt-3 space-y-2.5">
                  {health.by_blame.map((b) => {
                    const pct = Math.round((b.count / health.total_failures) * 100);
                    return (
                      <div key={b.blame}>
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="text-sm text-ink">{b.label}</span>
                          <span className="text-xs text-ink-dim">
                            {b.count} ({pct}%)
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-base-800">
                          <div
                            className={`h-full rounded-full ${BLAME_TONE[b.blame] ?? "bg-base-600"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <p className="mt-1 text-xs text-ink-dim">{b.explanation}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {health.models.length > 0 && (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.health.models")}
                </h3>
                <p className="mt-0.5 text-xs text-ink-dim">
                  {t("learning.health.modelsHint")}
                </p>
                <div className="mt-3 space-y-1.5">
                  {health.models.map((m) => (
                    <div
                      key={`${m.provider}:${m.model}`}
                      className="flex items-center justify-between gap-3 text-sm"
                    >
                      <span className="truncate text-ink-dim">{m.model}</span>
                      <span className="shrink-0 text-ink">
                        {Math.round(m.mission_success_rate * 100)}%
                        {m.missions_excused > 0 && (
                          <span className="ml-1.5 text-[10px] text-ink-dim">
                            {t("learning.health.excused", {
                              n: String(m.missions_excused),
                            })}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {health.tools.length > 0 && (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.health.tools")}
                </h3>
                <div className="mt-3 space-y-1.5">
                  {health.tools.map((x) => (
                    <div key={x.tool} className="flex justify-between gap-3 text-sm">
                      <span className="truncate text-ink-dim">{x.tool}</span>
                      <span className="shrink-0 text-signal-error">
                        {Math.round(x.error_rate * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(health.report?.findings ?? []).length > 0 && (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.health.findings")}
                </h3>
                <div className="mt-3 space-y-2">
                  {health.report.findings!.map((f, i) => (
                    <div key={i}>
                      <p className="text-sm text-ink">{f.title}</p>
                      <p className="text-xs text-ink-dim">{f.why}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Historial ────────────────────────────────────────────── */}
        {tab === "history" && history && (
          <div className="mt-4 space-y-3">
            {history.skills.length === 0 && history.decided.length === 0 && (
              <Empty text={t("learning.empty.history")} />
            )}

            {history.skills.length > 0 && (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.history.skills")}
                </h3>
                <div className="mt-3 space-y-2">
                  {history.skills.map((s) => (
                    <div key={s.id} className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-ink">{s.name}</p>
                        <p className="text-[11px] text-ink-dim">
                          {s.taught_by_user
                            ? t("learning.history.taught")
                            : t("learning.history.observed")}
                          {" · "}
                          {t(`learning.status.${s.status}`)}
                        </p>
                      </div>
                      {s.use_count > 0 && (
                        <span className="shrink-0 text-xs text-ink-dim">
                          {t("learning.history.uses", { n: String(s.use_count) })}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {history.decided.length > 0 && (
              <div className="glass-surface rounded-2xl p-4">
                <h3 className="text-sm font-medium text-ink">
                  {t("learning.history.decided")}
                </h3>
                <div className="mt-3 space-y-2.5">
                  {history.decided.map((p) => (
                    <div key={p.id} className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-ink">{p.title}</p>
                        <p className="text-[11px] text-ink-dim">
                          {t(`learning.decided.${p.state}`)}
                          {p.decision_note ? ` — “${p.decision_note}”` : ""}
                        </p>
                      </div>
                      {p.state === "consolidated" && (
                        <button
                          onClick={() => undo(p.id)}
                          disabled={busy === p.id}
                          className="shrink-0 rounded-lg border border-base-700 px-2.5 py-1 text-[11px] text-ink-dim transition hover:border-accent/50 hover:text-ink disabled:opacity-50"
                        >
                          {t("learning.undo")}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
