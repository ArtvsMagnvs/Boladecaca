// components/voice/PersonalityPicker.tsx — Personalidad de Aithera (V2, 2026-07-20)
//
// Elige CÓMO habla Aithera: la personalidad de casa (derivada de la filosofía
// del proyecto), las estándar, o una propia escrita por el usuario y mejorada
// internamente por una IA potente antes de guardarse.
//
// La personalidad es TONO, no identidad: se compone sobre el prompt base del
// sistema (ver backend/app/ai/personalities.py), así que ninguna puede saltarse
// las reglas de honestidad ni el formato de texto plano de la voz.
import { useCallback, useEffect, useState } from "react";
import { api, type PersonalityCatalog } from "@/lib/api";
import { useT } from "@/store/useI18n";

export default function PersonalityPicker() {
  const t = useT();
  const [catalog, setCatalog] = useState<PersonalityCatalog | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [showCustom, setShowCustom] = useState(false);
  const [draft, setDraft] = useState("");
  const [improving, setImproving] = useState(false);

  const load = useCallback(async () => {
    try {
      setCatalog(await api.getPersonalities());
    } catch {
      setMsg({ kind: "err", text: t("settings.voz.personality.loadError") });
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const select = async (id: string) => {
    setBusy(id);
    setMsg(null);
    try {
      setCatalog(await api.selectPersonality(id));
    } catch (e) {
      setMsg({ kind: "err", text: (e as Error).message || t("settings.voz.personality.changeError") });
    } finally {
      setBusy(null);
    }
  };

  const saveCustom = async () => {
    if (!draft.trim()) return;
    setImproving(true);
    setMsg(null);
    try {
      const r = await api.createCustomPersonality(draft.trim(), true);
      setCatalog(r);
      setDraft("");
      setShowCustom(false);
      setMsg({ kind: "ok", text: t("settings.voz.personality.created") });
    } catch (e) {
      setMsg({ kind: "err", text: (e as Error).message || t("settings.voz.personality.createError") });
    } finally {
      setImproving(false);
    }
  };

  if (!catalog) {
    return <p className="text-xs text-ink-dim">{t("settings.voz.personality.loading")}</p>;
  }

  const hasCustom = !!catalog.custom_prompt.trim();

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-ink-dim">
        {t("settings.voz.personality.intro")}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {catalog.personalities.map((p) => {
          const active = catalog.active === p.id;
          return (
            <button
              key={p.id}
              onClick={() => select(p.id)}
              disabled={busy !== null}
              className={`text-left p-3 rounded-xl border transition-colors disabled:opacity-50 ${
                active
                  ? "border-accent/50 bg-accent/10"
                  : "border-base-700 hover:border-base-600 hover:bg-base-800/40"
              }`}
            >
              <p className={`text-sm font-medium ${active ? "text-accent" : "text-ink"}`}>
                {p.name}
                {p.id === "aithera" && (
                  <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-base-700 text-ink-dim">
                    {t("settings.voz.personality.default")}
                  </span>
                )}
              </p>
              <p className="text-[11px] text-ink-faint mt-0.5 leading-snug">{p.description}</p>
            </button>
          );
        })}

        {/* Personalidad propia del usuario */}
        <button
          onClick={() => (hasCustom ? select("custom") : setShowCustom(true))}
          disabled={busy !== null}
          className={`text-left p-3 rounded-xl border transition-colors disabled:opacity-50 ${
            catalog.active === "custom"
              ? "border-accent/50 bg-accent/10"
              : "border-dashed border-base-600 hover:border-accent/40 hover:bg-base-800/40"
          }`}
        >
          <p className={`text-sm font-medium ${catalog.active === "custom" ? "text-accent" : "text-ink"}`}>
            {hasCustom ? t("settings.voz.personality.mine") : t("settings.voz.personality.createMine")}
          </p>
          <p className="text-[11px] text-ink-faint mt-0.5 leading-snug">
            {hasCustom
              ? t("settings.voz.personality.mineDesc")
              : t("settings.voz.personality.createMineDesc")}
          </p>
        </button>
      </div>

      {hasCustom && (
        <button
          onClick={() => { setDraft(""); setShowCustom((v) => !v); }}
          className="self-start text-[11px] text-ink-dim hover:text-ink underline underline-offset-2"
        >
          {showCustom ? t("settings.voz.personality.cancel") : t("settings.voz.personality.rewrite")}
        </button>
      )}

      {showCustom && (
        <div className="glass-surface rounded-xl p-3 flex flex-col gap-2">
          <label className="text-xs text-ink-dim">
            {t("settings.voz.personality.describeLabel")}
          </label>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={4}
            placeholder={t("settings.voz.personality.describePlaceholder")}
            className="form-input text-xs"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={saveCustom}
              disabled={improving || !draft.trim()}
              className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
            >
              {improving ? t("settings.voz.personality.polishing") : t("settings.voz.personality.createAndActivate")}
            </button>
            <button
              onClick={() => setShowCustom(false)}
              className="text-xs px-3 py-1.5 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600"
            >
              {t("settings.voz.personality.cancel")}
            </button>
          </div>
        </div>
      )}

      {hasCustom && catalog.active === "custom" && !showCustom && (
        <details className="text-[11px] text-ink-faint">
          <summary className="cursor-pointer hover:text-ink-dim">{t("settings.voz.personality.viewPrompt")}</summary>
          <pre className="mt-2 whitespace-pre-wrap bg-base-900/50 rounded-lg p-2 text-[10px] leading-relaxed">
            {catalog.custom_prompt}
          </pre>
        </details>
      )}

      {msg && (
        <p className={`text-xs ${msg.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
          {msg.text}
        </p>
      )}
    </div>
  );
}
