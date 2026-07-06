import type { CoreDesignSettings, CoreModelId } from "@/components/hub/coreDesign";
import { CORE_MODEL_LABELS, DEFAULT_CORE_DESIGN } from "@/components/hub/coreDesign";

interface CoreDesignPanelProps {
  model: CoreModelId;
  value: CoreDesignSettings;
  onChange: (patch: Partial<CoreDesignSettings>) => void;
  onReset: () => void;
}

interface SliderSpec {
  key: keyof CoreDesignSettings;
  label: string;
  min: number;
  max: number;
  step: number;
}

const SLIDERS: SliderSpec[] = [
  { key: "scale", label: "Escala", min: 0.72, max: 1.28, step: 0.01 },
  { key: "brightness", label: "Brillo", min: 0.65, max: 1.45, step: 0.01 },
  { key: "glow", label: "Glow", min: 0, max: 1.8, step: 0.01 },
  { key: "speed", label: "Velocidad", min: 0, max: 2, step: 0.01 },
  { key: "energy", label: "Energía", min: 0.45, max: 1.8, step: 0.01 },
  { key: "particles", label: "Partículas", min: 0, max: 2, step: 0.01 },
];

function formatValue(value: number) {
  return value.toFixed(2).replace(/\.00$/, "");
}

export function CoreDesignPanel({ model, value, onChange, onReset }: CoreDesignPanelProps) {
  return (
    <section
      className="w-full max-w-[520px] rounded-2xl border border-amber-300/15 bg-base-900/70 px-4 py-3 shadow-2xl backdrop-blur-md"
      aria-label="Panel interno de diseño del núcleo"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-amber-200/80">
            Design Lab · dev only
          </p>
          <p className="mt-0.5 truncate text-xs text-ink-faint">
            Ajustando: <span className="text-ink">{CORE_MODEL_LABELS[model]}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="rounded-full border border-base-700/80 px-3 py-1 text-[10px] uppercase tracking-wider text-ink-dim transition-colors hover:border-amber-300/40 hover:text-amber-100"
        >
          Reset
        </button>
      </div>

      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
        {SLIDERS.map((slider) => (
          <label key={slider.key} className="block">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-[11px] text-ink-dim">{slider.label}</span>
              <span className="font-mono text-[10px] text-amber-100/80">
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
              className="h-1.5 w-full cursor-ew-resize accent-amber-300"
            />
          </label>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 text-[10px] text-ink-faint">
        <span>Se guarda solo para este núcleo.</span>
        <code className="rounded bg-base-950/70 px-2 py-1 font-mono text-[9px] text-ink-faint">
          {JSON.stringify(value, Object.keys(DEFAULT_CORE_DESIGN))}
        </code>
      </div>
    </section>
  );
}

export default CoreDesignPanel;
