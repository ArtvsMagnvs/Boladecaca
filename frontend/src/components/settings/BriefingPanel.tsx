// components/settings/BriefingPanel.tsx — Ajustes → Briefing (PU4b, doc 35)
//
// Todo lo que el usuario pidió configurable del briefing, en una pestaña:
// · QUÉ menciona: secciones on/off (email, calendario, proyectos, tareas,
//   noticias, resumen de ayer).
// · CUÁNDO: N horarios al día (añadir/quitar; el disparo vive en Chat.tsx) y
//   cuántos minutos antes se PREPARA cada uno (noticias + locución a cache).
// · NOTICIAS: temas con su consulta (añadir/quitar), fuentes bloqueadas/
//   preferidas, el prompt libre de intereses que guía la curación, y cuántas
//   por tema se guardan / se locutan.
// El PUT re-arma los jobs de preparación en caliente (backend).
import { useEffect, useState } from "react";
import { api, type BriefingConfig } from "@/lib/api";
import { Toggle } from "@/components/Toggle";
import { useT } from "@/store/useI18n";

const SECTION_KEYS = ["email", "calendar", "projects", "tasks", "news", "yesterday"] as const;

export default function BriefingPanel() {
  const tr = useT();
  const [cfg, setCfg] = useState<BriefingConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedTick, setSavedTick] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [prepared, setPrepared] = useState<string | null>(null);
  const [newSchedule, setNewSchedule] = useState("14:00");
  const [newTopicLabel, setNewTopicLabel] = useState("");
  const [newTopicQuery, setNewTopicQuery] = useState("");
  const [newBlocked, setNewBlocked] = useState("");

  useEffect(() => {
    api
      .getBriefingConfig()
      .then(setCfg)
      .catch(() => setError(tr("settings.briefing.loadError")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error && !cfg) return <p className="text-xs text-signal-error">{error}</p>;
  if (!cfg) return <p className="text-xs text-ink-faint">…</p>;

  const patch = (p: Partial<BriefingConfig>) => setCfg({ ...cfg, ...p });
  const patchNews = (p: Partial<BriefingConfig["news"]>) =>
    setCfg({ ...cfg, news: { ...cfg.news, ...p } });

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const saved = await api.saveBriefingConfig(cfg);
      setCfg(saved);
      setSavedTick(true);
      window.setTimeout(() => setSavedTick(false), 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.briefing.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const prepareNow = async () => {
    setPreparing(true);
    setPrepared(null);
    try {
      const r = await api.prepareBriefing();
      setPrepared(
        r.status === "ok" ? tr("settings.briefing.preparedOk") : tr("settings.briefing.preparedFail"),
      );
    } catch {
      setPrepared(tr("settings.briefing.preparedFail"));
    } finally {
      setPreparing(false);
    }
  };

  const addSchedule = () => {
    const v = newSchedule.trim();
    if (!/^([01]?\d|2[0-3]):[0-5]\d$/.test(v)) return;
    const norm = v.padStart(5, "0");
    if (cfg.schedules.includes(norm) || cfg.schedules.length >= 8) return;
    patch({ schedules: [...cfg.schedules, norm].sort() });
  };

  const addTopic = () => {
    const label = newTopicLabel.trim();
    const query = newTopicQuery.trim();
    if (!label || !query || cfg.news.topics.length >= 10) return;
    patchNews({ topics: [...cfg.news.topics, { id: "", label, query, vertical: "news" }] });
    setNewTopicLabel("");
    setNewTopicQuery("");
  };

  const addBlocked = () => {
    const v = newBlocked.trim().toLowerCase();
    if (!v || cfg.news.blocked_sources.includes(v)) return;
    patchNews({ blocked_sources: [...cfg.news.blocked_sources, v] });
    setNewBlocked("");
  };

  const inputCls =
    "bg-base-800/70 border border-base-600 rounded-lg px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-accent/60";

  return (
    <div className="flex flex-col gap-4">
      {/* ── Secciones ── */}
      <section className="glass-surface rounded-2xl p-4">
        <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.briefing.sections.title")}</h3>
        <p className="text-xs text-ink-dim mb-3">{tr("settings.briefing.sections.desc")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 max-w-2xl">
          {SECTION_KEYS.map((key) => (
            <div key={key} className="flex items-center justify-between gap-3 py-1">
              <span className="text-xs text-ink">{tr(`settings.briefing.sections.${key}`)}</span>
              <Toggle
                checked={cfg.sections[key]}
                onChange={(v) => patch({ sections: { ...cfg.sections, [key]: v } })}
                label={tr(`settings.briefing.sections.${key}`)}
              />
            </div>
          ))}
        </div>
      </section>

      {/* ── Horarios ── */}
      <section className="glass-surface rounded-2xl p-4">
        <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.briefing.schedules.title")}</h3>
        <p className="text-xs text-ink-dim mb-3">{tr("settings.briefing.schedules.desc")}</p>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {cfg.schedules.map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 border border-accent/30 pl-3 pr-1.5 py-1 text-xs font-mono text-accent"
            >
              {s}
              {cfg.schedules.length > 1 && (
                <button
                  type="button"
                  onClick={() => patch({ schedules: cfg.schedules.filter((x) => x !== s) })}
                  aria-label={`${tr("settings.briefing.remove")} ${s}`}
                  className="w-4 h-4 rounded-full flex items-center justify-center hover:bg-ink/10 text-ink-dim hover:text-signal-error"
                >
                  ×
                </button>
              )}
            </span>
          ))}
          <input
            type="time"
            value={newSchedule}
            onChange={(e) => setNewSchedule(e.target.value)}
            className={inputCls}
          />
          <button
            type="button"
            onClick={addSchedule}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-accent/50"
          >
            + {tr("settings.briefing.schedules.add")}
          </button>
        </div>
        <label className="flex items-center gap-2 text-xs text-ink-dim">
          {tr("settings.briefing.prep.before")}
          <input
            type="number"
            min={5}
            max={120}
            value={cfg.prep_minutes_before}
            onChange={(e) => patch({ prep_minutes_before: Number(e.target.value) || 30 })}
            className={`${inputCls} w-16 text-center`}
          />
          {tr("settings.briefing.prep.minutes")}
        </label>
        <p className="text-[10px] text-ink-faint mt-1.5">{tr("settings.briefing.prep.hint")}</p>
      </section>

      {/* ── Noticias ── */}
      <section className="glass-surface rounded-2xl p-4">
        <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.briefing.news.title")}</h3>
        <p className="text-xs text-ink-dim mb-3">{tr("settings.briefing.news.desc")}</p>

        {/* Temas */}
        <p className="text-[11px] uppercase tracking-wider text-ink-faint mb-2">
          {tr("settings.briefing.news.topics")}
        </p>
        <div className="flex flex-col gap-1.5 mb-2 max-w-2xl">
          {cfg.news.topics.map((topic, i) => (
            <div key={topic.id || i} className="flex items-center gap-2">
              <input
                value={topic.label}
                onChange={(e) => {
                  const topics = [...cfg.news.topics];
                  topics[i] = { ...topic, label: e.target.value };
                  patchNews({ topics });
                }}
                className={`${inputCls} w-44 shrink-0`}
                placeholder={tr("settings.briefing.news.topicLabel")}
              />
              <input
                value={topic.query}
                onChange={(e) => {
                  const topics = [...cfg.news.topics];
                  topics[i] = { ...topic, query: e.target.value };
                  patchNews({ topics });
                }}
                className={`${inputCls} flex-1 min-w-0`}
                placeholder={tr("settings.briefing.news.topicQuery")}
              />
              {/* [hotfix 2026-08-02] nº de noticias DE ESTE TEMA — vacío =
                  usa el default global de más abajo (news.per_topic). */}
              <input
                type="number"
                min={1}
                max={8}
                value={topic.count ?? ""}
                onChange={(e) => {
                  const raw = e.target.value;
                  const topics = [...cfg.news.topics];
                  const { count: _drop, ...rest } = topic;
                  topics[i] = raw === "" ? rest : { ...topic, count: Number(raw) };
                  patchNews({ topics });
                }}
                placeholder={String(cfg.news.per_topic)}
                title={tr("settings.briefing.news.topicCountHint")}
                aria-label={tr("settings.briefing.news.topicCount")}
                className={`${inputCls} w-14 shrink-0 text-center`}
              />
              <button
                type="button"
                onClick={() => patchNews({ topics: cfg.news.topics.filter((_, j) => j !== i) })}
                aria-label={tr("settings.briefing.remove")}
                className="shrink-0 w-6 h-6 rounded-lg flex items-center justify-center text-ink-faint hover:text-signal-error hover:bg-ink/5"
              >
                ×
              </button>
            </div>
          ))}
          <p className="text-[10px] text-ink-faint pl-1">{tr("settings.briefing.news.topicCountDesc")}</p>
          <div className="flex items-center gap-2">
            <input
              value={newTopicLabel}
              onChange={(e) => setNewTopicLabel(e.target.value)}
              className={`${inputCls} w-44 shrink-0`}
              placeholder={tr("settings.briefing.news.topicLabel")}
            />
            <input
              value={newTopicQuery}
              onChange={(e) => setNewTopicQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTopic()}
              className={`${inputCls} flex-1 min-w-0`}
              placeholder={tr("settings.briefing.news.topicQuery")}
            />
            <button
              type="button"
              onClick={addTopic}
              className="shrink-0 text-xs px-2.5 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-accent/50"
            >
              +
            </button>
          </div>
        </div>

        {/* Fuentes bloqueadas */}
        <p className="text-[11px] uppercase tracking-wider text-ink-faint mt-4 mb-2">
          {tr("settings.briefing.news.blocked")}
        </p>
        <p className="text-[10px] text-ink-faint mb-2">{tr("settings.briefing.news.blockedDesc")}</p>
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {cfg.news.blocked_sources.map((d) => (
            <span
              key={d}
              className="inline-flex items-center gap-1.5 rounded-full bg-signal-error/10 border border-signal-error/30 pl-3 pr-1.5 py-1 text-xs text-signal-error"
            >
              {d}
              <button
                type="button"
                onClick={() =>
                  patchNews({ blocked_sources: cfg.news.blocked_sources.filter((x) => x !== d) })
                }
                aria-label={`${tr("settings.briefing.remove")} ${d}`}
                className="w-4 h-4 rounded-full flex items-center justify-center hover:bg-ink/10"
              >
                ×
              </button>
            </span>
          ))}
          <input
            value={newBlocked}
            onChange={(e) => setNewBlocked(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addBlocked()}
            className={`${inputCls} w-52`}
            placeholder="dominio.com"
          />
          <button
            type="button"
            onClick={addBlocked}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-accent/50"
          >
            +
          </button>
        </div>

        {/* Prompt de intereses */}
        <p className="text-[11px] uppercase tracking-wider text-ink-faint mt-4 mb-2">
          {tr("settings.briefing.news.prompt")}
        </p>
        <p className="text-[10px] text-ink-faint mb-2">{tr("settings.briefing.news.promptDesc")}</p>
        <textarea
          value={cfg.news.prompt}
          onChange={(e) => patchNews({ prompt: e.target.value })}
          rows={5}
          className={`${inputCls} w-full max-w-2xl resize-y leading-relaxed`}
        />

        {/* Cantidades */}
        <div className="flex flex-wrap gap-5 mt-3">
          <label className="flex items-center gap-2 text-xs text-ink-dim">
            {tr("settings.briefing.news.perTopic")}
            <input
              type="number"
              min={1}
              max={8}
              value={cfg.news.per_topic}
              onChange={(e) => patchNews({ per_topic: Number(e.target.value) || 4 })}
              className={`${inputCls} w-14 text-center`}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-ink-dim">
            {tr("settings.briefing.news.spokenPerTopic")}
            <input
              type="number"
              min={1}
              max={4}
              value={cfg.news.spoken_per_topic}
              onChange={(e) => patchNews({ spoken_per_topic: Number(e.target.value) || 2 })}
              className={`${inputCls} w-14 text-center`}
            />
          </label>
        </div>
      </section>

      {/* ── Acciones ── */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="px-4 py-2 rounded-xl text-xs font-medium bg-accent/15 text-accent border border-accent/40 hover:bg-accent/25 disabled:opacity-50"
        >
          {saving ? "…" : tr("settings.briefing.save")}
        </button>
        {savedTick && <span className="text-xs text-signal-ok">{tr("settings.briefing.saved")}</span>}
        <button
          type="button"
          onClick={prepareNow}
          disabled={preparing}
          className="px-4 py-2 rounded-xl text-xs text-ink-dim border border-base-600 hover:text-ink hover:border-accent/50 disabled:opacity-50"
          title={tr("settings.briefing.prepareNowHint")}
        >
          {preparing ? tr("settings.briefing.preparing") : tr("settings.briefing.prepareNow")}
        </button>
        {prepared && <span className="text-xs text-ink-dim">{prepared}</span>}
        {error && <span className="text-xs text-signal-error">{error}</span>}
      </div>
    </div>
  );
}
