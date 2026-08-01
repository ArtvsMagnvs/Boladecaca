// store/useBriefingShow.ts — estado del "show" visual del briefing (PU4b, doc 35)
//
// POR QUÉ UN STORE: la locución la conduce Chat.tsx (montado de forma
// persistente, dueño de speak()/TTS), pero los visuales viven en
// BriefingShow.tsx (montado en AppLayout, por encima de cualquier página).
// Están en árboles distintos y ninguno debe conocer al otro — mismo motivo
// que conversationRequested/briefingRequestId en useAppStore.
//
// Contrato: Chat.tsx llama start(onStop) → setScene(segmento) por cada
// sección → setFocus(paso) por cada frase que locuta → end(). El ✕ del show
// llama requestStop(), que corta la voz (vía el onStop registrado) y levanta
// stopRequested para que el bucle de Chat pare entre pasos.
import { create } from "zustand";
import type { SpokenSegment } from "@/lib/api";

interface BriefingShowState {
  active: boolean;
  scene: SpokenSegment | null;
  focus: string | null;
  stopRequested: boolean;
  /** Registrado por Chat.tsx al arrancar: corta la locución en curso. */
  onStop: (() => void) | null;
  start: (onStop: () => void) => void;
  setScene: (scene: SpokenSegment) => void;
  setFocus: (focus: string | null) => void;
  requestStop: () => void;
  end: () => void;
}

export const useBriefingShow = create<BriefingShowState>((set, get) => ({
  active: false,
  scene: null,
  focus: null,
  stopRequested: false,
  onStop: null,

  start: (onStop) => set({ active: true, scene: null, focus: null, stopRequested: false, onStop }),
  setScene: (scene) => set({ scene, focus: null }),
  setFocus: (focus) => set({ focus }),
  requestStop: () => {
    try {
      get().onStop?.();
    } catch {
      /* cortar la voz es best-effort */
    }
    set({ stopRequested: true });
  },
  end: () => set({ active: false, scene: null, focus: null, stopRequested: false, onStop: null }),
}));
