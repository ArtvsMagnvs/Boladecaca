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
    // [doc 35 PU5] Q1 se eliminó; un valor viejo guardado migra al mínimo actual.
    if (v === "Q1") return "Q2";
    if (v === "Q2" || v === "Q3" || v === "Q4") return v;
  } catch {
    /* localStorage no disponible */
  }
  return "Q3";
}

interface AppState {
  backendConnected: boolean;
  aiStatus: AIStatus | null;
  /** [2026-07-21] "provider:model" que lleva el CHAT según la política ACTIVA
   *  del MEL (Inteligencia) — la VERDAD que muestran Sidebar/Hub/Ajustes, en
   *  vez del proveedor legacy (que podía contradecirla, bug real). */
  chatPrimary: string | null;
  /** ¿El proveedor del chat primario está fallando ahora (breaker abierto)? */
  chatPrimaryDown: boolean;
  coreState: AICoreState;
  setCoreState: (state: AICoreState) => void;
  pulseError: () => void;
  refreshBackendStatus: () => Promise<void>;
  refreshAIStatus: () => Promise<void>;
  presenceMode: boolean;
  setPresenceMode: (v: boolean) => void;
  togglePresenceMode: () => void;
  /** [PU6a-bis, doc 35 §PU6] ¿El usuario QUIERE el Modo Conversación activo?
   *  El bucle de voz real vive en Chat.tsx (necesita su <audio>, su VAD y su
   *  historial), pero la INTENCIÓN tiene que poder expresarse desde fuera:
   *  la pill del Hub, la tecla SPACE en cualquier página, o el propio botón
   *  del chat. Chat.tsx observa esta bandera y arranca/para el bucle; y la
   *  escribe de vuelta cuando el usuario usa su botón, para que las dos vías
   *  digan siempre lo mismo. Fuera del store, SPACE desde el Hub no tendría
   *  forma de llegar a un componente que ni siquiera está montado. */
  conversationRequested: boolean;
  setConversationRequested: (v: boolean) => void;
  toggleConversationRequested: () => void;
  /** [PU6a-bis v2] El chat ya no es una RUTA: es una ventana flotante montada
   *  en AppLayout que se muestra/oculta con esta bandera. Así el Modo
   *  Conversación puede correr con el chat OCULTO (SPACE desde el Hub — la
   *  conversación se graba en el chat igualmente, porque el componente sigue
   *  montado), y el AVCS queda siempre de fondo. */
  chatOpen: boolean;
  setChatOpen: (v: boolean) => void;
  avcsTier: QualityTier;
  setAvcsTier: (t: QualityTier) => void;
  /** [PU4, doc 35] El botón extra junto a Modo Presencia (y el disparo de las
   *  8:15) incrementan este contador — Chat.tsx observa el cambio (no el
   *  valor) para lanzar `runBriefing()` sin importar si el chat está montado
   *  o no todavía (mismo motivo que conversationRequested: la intención debe
   *  poder expresarse desde fuera del componente que la ejecuta). */
  briefingRequestId: number;
  requestBriefing: () => void;
  /** Evita pulsaciones dobles/carreras mientras se resuelve un briefing.
   *  [PU4b] La idempotencia del disparo automático ya no vive aquí: ahora hay
   *  N horarios configurables y cada uno guarda su clave por día en
   *  localStorage (`briefing.lastAuto.<HH:MM>`, ver Chat.tsx). */
  briefingBusy: boolean;
  setBriefingBusy: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  backendConnected: false,
  aiStatus: null,
  chatPrimary: null,
  chatPrimaryDown: false,
  coreState: "idle",

  setCoreState: (state) => set({ coreState: state }),

  presenceMode: false,
  setPresenceMode: (v) => set({ presenceMode: v }),
  togglePresenceMode: () => set((s) => ({ presenceMode: !s.presenceMode })),

  conversationRequested: false,
  setConversationRequested: (v) => set({ conversationRequested: v }),
  toggleConversationRequested: () => set((s) => ({ conversationRequested: !s.conversationRequested })),

  chatOpen: false,
  setChatOpen: (v) => set({ chatOpen: v }),

  avcsTier: readStoredTier(),
  setAvcsTier: (t) => {
    try {
      window.localStorage.setItem(AVCS_TIER_KEY, t);
    } catch {
      /* localStorage no disponible */
    }
    set({ avcsTier: t });
  },

  briefingRequestId: 0,
  requestBriefing: () => set((s) => ({ briefingRequestId: s.briefingRequestId + 1 })),
  briefingBusy: false,
  setBriefingBusy: (v) => set({ briefingBusy: v }),

  refreshBackendStatus: async () => {
    const connected = await api.health();
    set({ backendConnected: connected });
  },

  refreshAIStatus: async () => {
    try {
      // [2026-07-21] Junto al status legacy se lee la política ACTIVA del MEL:
      // su primario de CHAT es lo que la UI muestra en todas partes.
      const [status, pols, health, models] = await Promise.all([
        api.getAIStatus(),
        api.getMelPolicies().catch(() => null),
        api.getMelHealthSummary().catch(() => null),
        api.getMelModels().catch(() => null),
      ]);
      const active = pols?.find((p) => p.is_active);
      // El primario EFECTIVO: la ejecución salta los modelos no aptos para
      // chat (unfit, p.ej. Claude CLI) aunque sigan en la política guardada —
      // la UI muestra lo que de verdad responderá.
      const unfitOf = (key: string) =>
        models?.find((m) => m.key === key)?.unfit ?? [];
      const chatChain = active?.compiled?.chat ?? [];
      const chatPrimary = chatChain.find((k) => !unfitOf(k).includes("chat")) ?? null;
      const prov = chatPrimary ? chatPrimary.split(":")[0] : null;
      const chatPrimaryDown = !!prov && !!health?.providers_down?.includes(prov);
      set({ aiStatus: status, chatPrimary, chatPrimaryDown });
    } catch {
      set({ aiStatus: null, chatPrimary: null, chatPrimaryDown: false });
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
