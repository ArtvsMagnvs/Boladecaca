export type CoreModelId = "aithera_seed" | "blue_orb" | "poop_sphere" | "rasengan";

export interface CoreDesignSettings {
  scale: number;
  brightness: number;
  glow: number;
  speed: number;
  energy: number;
  particles: number;
}

export type CoreDesignMap = Record<CoreModelId, CoreDesignSettings>;

export const CORE_DESIGN_STORAGE_KEY = "aithera.coreDesign.v1";

export const CORE_MODEL_IDS: CoreModelId[] = [
  "aithera_seed",
  "blue_orb",
  "poop_sphere",
  "rasengan",
];

export const CORE_MODEL_LABELS: Record<CoreModelId, string> = {
  aithera_seed: "Semilla de Aithera",
  blue_orb: "Orbe azul",
  poop_sphere: "Bola de caca",
  rasengan: "Rasengan",
};

export const DEFAULT_CORE_DESIGN: CoreDesignSettings = {
  scale: 1,
  brightness: 1,
  glow: 1,
  speed: 1,
  energy: 1,
  particles: 1,
};

const LIMITS: Record<keyof CoreDesignSettings, [number, number]> = {
  scale: [0.72, 1.28],
  brightness: [0.65, 1.45],
  glow: [0, 1.8],
  speed: [0, 2],
  energy: [0.45, 1.8],
  particles: [0, 2],
};

function clamp(key: keyof CoreDesignSettings, value: unknown) {
  const [min, max] = LIMITS[key];
  const n = typeof value === "number" && Number.isFinite(value) ? value : DEFAULT_CORE_DESIGN[key];
  return Math.min(max, Math.max(min, n));
}

export function normalizeCoreDesign(value: Partial<CoreDesignSettings> = {}): CoreDesignSettings {
  return {
    scale: clamp("scale", value.scale),
    brightness: clamp("brightness", value.brightness),
    glow: clamp("glow", value.glow),
    speed: clamp("speed", value.speed),
    energy: clamp("energy", value.energy),
    particles: clamp("particles", value.particles),
  };
}

export function createDefaultCoreDesigns(): CoreDesignMap {
  return CORE_MODEL_IDS.reduce((acc, id) => {
    acc[id] = { ...DEFAULT_CORE_DESIGN };
    return acc;
  }, {} as CoreDesignMap);
}

export function loadStoredCoreDesigns(): CoreDesignMap {
  const defaults = createDefaultCoreDesigns();
  if (typeof window === "undefined") return defaults;

  try {
    const raw = window.localStorage.getItem(CORE_DESIGN_STORAGE_KEY);
    if (!raw) return defaults;

    const parsed = JSON.parse(raw) as Partial<Record<CoreModelId, Partial<CoreDesignSettings>>>;
    return CORE_MODEL_IDS.reduce((acc, id) => {
      acc[id] = normalizeCoreDesign(parsed[id] ?? defaults[id]);
      return acc;
    }, {} as CoreDesignMap);
  } catch {
    return defaults;
  }
}

export function saveStoredCoreDesigns(designs: CoreDesignMap) {
  try {
    window.localStorage.setItem(CORE_DESIGN_STORAGE_KEY, JSON.stringify(designs));
  } catch {
    // localStorage no disponible — ignorar sin romper el Hub.
  }
}
