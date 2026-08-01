import { useState } from "react";
import type { CoreDesignSettings, CoreModelId } from "@/components/hub/coreDesign";
import { DEFAULT_CORE_DESIGN } from "@/components/hub/coreDesign";
import { CORE_MODEL_LABEL_KEYS } from "@/components/hub/CoreSelector";
import { useT } from "@/store/useI18n";

interface CoreDesignPanelProps {
  model: CoreModelId;
  value: CoreDesignSettings;
  onChange: (patch: Partial<CoreDesignSettings>) => void;
  onReset: () => void;
}

interface SliderSpec {
  key: keyof CoreDesignSettings;
  labelKey: string;
  min: number;
  max: number;
  step: number;
}

const SLIDERS: SliderSpec[] = [
  { key: "scale", labelKey: "hub.designLab.scale", min: 0.72, max: 1.28, step: 0.01 },
  { key: "brightness", labelKey: "hub.designLab.brightness", min: 0.65, max: 1.45, step: 0.01 },
  { key: "glow", labelKey: "hub.designLab.glow", min: 0, max: 1.8, step: 0.01 },
  { key: "speed", labelKey: "hub.designLab.speed", min: 0, max: 2, step: 0.01 },
  { key: "energy", labelKey: "hub.designLab.energy", min: 0.45, max: 1.8, step: 0.01 },
  { key: "particles", labelKey: "hub.designLab.particles", min: 0, max: 2, step: 0.01 },
];

function formatValue(value: number) {
  return value.toFixed(2).replace(/\.00$/, "");
}

export function CoreDesignPanel({ model, value, onChange, onReset }: CoreDesignPanelProps) {
  const t = useT();
  // Arranca minimizado: en el Hub solo se ve un botón pequeño y discreto; el
  // panel completo (dev-only) se despliega al pulsarlo.
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("hub.designLab.openAria")}
        title="Design Lab · dev only"
        className="rounded-full border border-amber-300/25 light:border-amber-600/40 bg-base-900/70 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-200/80 light:text-amber-800 shadow-lg backdrop-blur-md transition-colors hover:border-amber-300/50 light:hover:border-amber-700/60 hover:text-amber-100 light:hover:text-amber-900"
      >
        ⚙ Design Lab
      </button>
    );
  }

  return (
    <section
      className="w-full max-w-[520px] rounded-2xl border border-amber-300/15 light:border-amber-600/30 bg-base-900/70 px-4 py-3 shadow-2xl backdrop-blur-md"
      aria-label={t("hub.designLab.panelAria")}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-amber-200/80 light:text-amber-800">
            Design Lab · dev only
          </p>
          <p className="mt-0.5 truncate text-xs text-ink-faint">
            {t("hub.designLab.adjusting")} <span className="text-ink">{t(CORE_MODEL_LABEL_KEYS[model])}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onReset}
            className="rounded-full border border-base-700/80 px-3 py-1 text-[10px] uppercase tracking-wider text-ink-dim transition-colors hover:border-amber-300/40 light:hover:border-amber-700/50 hover:text-amber-100 light:hover:text-amber-900"
          >
            {t("hub.designLab.reset")}
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label={t("hub.designLab.minimizeAria")}
            title={t("hub.designLab.minimize")}
            className="rounded-full border border-base-700/80 px-2.5 py-1 text-sm leading-none text-ink-dim transition-colors hover:border-amber-300/40 light:hover:border-amber-700/50 hover:text-amber-100 light:hover:text-amber-900"
          >
            —
          </button>
        </div>
      </div>

      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        {SLIDERS.map((slider) => (
          <label key={slider.key} className="block">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-[11px] text-ink-dim">{t(slider.labelKey)}</span>
              <span className="font-mono text-[10px] text-amber-100/80 light:text-amber-800">
                {formatValue(value[slider.key])}
              </span>
            </div>
            <input
              type="range"
              min={slider.min}
              max={slider.max}
              step={slider.step}
              value={value[slider.key]}
              onChange={(e) => onChange({ [slider.key]: Number(e.currentTarget.value) })}
              className="h-1.5 w-full cursor-ew-resize accent-amber-300 light:accent-amber-600"
            />
          </label>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 text-[10px] text-ink-faint">
        <span>{t("hub.designLab.savedPerModel")}</span>
        <code className="rounded bg-base-950/70 px-2 py-1 font-mono text-[9px] text-ink-faint">
          {JSON.stringify(value, Object.keys(DEFAULT_CORE_DESIGN))}
        </code>
      </div>
    </section>
  );
}

export default CoreDesignPanel;
