// components/LanguageSelector.tsx — Selector de idioma (I18N-1, doc 30 §2)
//
// Reutilizable: Ajustes → Sistema hoy; disponible para cualquier otro sitio.
// Cambia el idioma en vivo (todos los componentes que usan `useT()` se
// re-renderizan) y lo sincroniza con el backend.
import { useI18n, useT, LANGUAGES, type Lang } from "@/store/useI18n";

export default function LanguageSelector() {
  const lang = useI18n((s) => s.lang);
  const setLang = useI18n((s) => s.setLang);
  const t = useT();

  return (
    <div>
      <h3 className="text-sm font-medium text-ink mb-1">{t("language.title")}</h3>
      <p className="text-xs text-ink-dim mb-3">{t("language.subtitle")}</p>
      <div className="grid grid-cols-2 gap-2">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            onClick={() => setLang(l.code as Lang)}
            className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 border transition-colors text-left ${
              lang === l.code
                ? "border-accent bg-accent/10 text-ink"
                : "border-base-700 hover:border-base-600 text-ink-dim"
            }`}
          >
            <span className="text-xl leading-none">{l.flag}</span>
            <span className="text-sm font-medium">{l.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
