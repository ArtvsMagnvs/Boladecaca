import { create } from "zustand";
import { api, type AIStatus } from "@/lib/api";
import type { QualityTier } from "@/avcs";

// AVCS S1: se añaden 'action' (Acción) y 'recovering' (Recuperación) para
// completar los 7 ritmos del doc 13 §4. Los ritmos reales de esos estados
// llegan en MVP1; el store ya expone el vocabulario.
export type AICoreState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "processing"
  | "error"
  | "action"
  | "recovering";

// AVCS S3 (doc 13 §13.4): Modo Presencia pliega TODA la UI de chrome (sidebar +
// contenido de la página), dejando solo el canvas a pantalla completa. Vive en
// el store (no en localStorage) para que "persista por página": no se resetea
// al navegar entre rutas, solo al reiniciar la app.
const AVCS_TIER_KEY = "avcs.tier";
function readStoredTier(): QualityTier {
  try {
    const v = window.localStorage.getItem(AVCS_TIER_KEY);
    if (v === "Q1" || v === "Q2" || v === "Q3" || v === "Q4") return v;
  } catch {
    /* localStorage no disponible */
  }
  return "Q3";
}

interface AppState {
  backendConnected: boolean;
  aiStatus: AIStatus | null;
  coreState: AICoreState;
  setCoreState: (state: AICoreState) => void;
  pulseError: () => void;
  refreshBackendStatus: () => Promise<void>;
  refreshAIStatus: () => Promise<void>;
  presenceMode: boolean;
  setPresenceMode: (v: boolean) => void;
  togglePresenceMode: () => void;
  avcsTier: QualityTier;
  setAvcsTier: (t: QualityTier) => void;
}

export const useAppStore = create<AppState>((set) => ({
  backendConnected: false,
  aiStatus: null,
  coreState: "idle",

  setCoreState: (state) => set({ coreState: state }),

  presenceMode: false,
  setPresenceMode: (v) => set({ presenceMode: v }),
  togglePresenceMode: () => set((s) => ({ presenceMode: !s.presenceMode })),

  avcsTier: readStoredTier(),
  setAvcsTier: (t) => {
    try {
      window.localStorage.setItem(AVCS_TIER_KEY, t);
    } catch {
      /* localStorage no disponible */
    }
    set({ avcsTier: t });
  },

  refreshBackendStatus: async () => {
    const connected = await api.health();
    set({ backendConnected: connected });
  },

  refreshAIStatus: async () => {
    try {
      const status = await api.getAIStatus();
      set({ aiStatus: status });
    } catch {
      set({ aiStatus: null });
    }
  },

  /**
   * Pulso breve de error: el nucleo se pone en rojo apagado un instante y
   * vuelve solo a reposo, tal como especifica el plan de Hub Visual
   * ("Error: pulso breve... vuelve a reposo"). El componente AICore no
   * decide cuando hay un error - quien detecta el fallo llama a esto.
   */
  pulseError: () => {
    set({ coreState: "error" });
    setTimeout(() => set((s) => (s.coreState === "error" ? { coreState: "idle" } : s)), 1500);
  },
}));
