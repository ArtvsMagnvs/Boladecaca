import { create } from "zustand";
import { api, type AIStatus } from "@/lib/api";

export type AICoreState = "idle" | "listening" | "thinking" | "speaking" | "processing" | "error";

interface AppState {
  backendConnected: boolean;
  aiStatus: AIStatus | null;
  coreState: AICoreState;
  setCoreState: (state: AICoreState) => void;
  pulseError: () => void;
  refreshBackendStatus: () => Promise<void>;
  refreshAIStatus: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  backendConnected: false,
  aiStatus: null,
  coreState: "idle",

  setCoreState: (state) => set({ coreState: state }),

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
