import { create } from "zustand";

// [Bug real, reportado 2026-07-17] La conversación vivía en useState local de
// Chat.tsx. React Router desmonta la página al navegar a otra ruta (p.ej. a
// "Misiones" para ver un plan), así que volver al chat lo reiniciaba de cero
// — y peor: si una respuesta del TIE seguía en camino (streaming/misión
// compleja) cuando el usuario navegaba fuera, su `setMessages` apuntaba al
// componente YA desmontado: React descarta esa actualización en silencio y la
// respuesta final se perdía para siempre, aunque el backend la hubiera
// generado bien. Mismo patrón que `presenceMode` en useAppStore: el estado
// vive en el store (singleton fuera del árbol de React), así que sobrevive a
// cualquier desmontaje/remontaje de página — solo se resetea al reiniciar la app.
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  // [V1.0 T4b] Si la respuesta vino de una misión del TIE (varios pasos), su
  // id para poder abrir el plan y su estado.
  missionId?: string;
}

const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hola! Soy Aithera, tu asistente de IA. Puedo ayudarte con proyectos, tareas, calendario y más. ¿En qué puedo ayudarte hoy?",
};

interface ChatState {
  messages: ChatMessage[];
  // Guard de re-entrancia (equivalente al viejo `sendingRef`, pero como
  // singleton: sobrevive a que el componente se desmonte y remonte a mitad de
  // un envío, algo que un useRef local NO puede garantizar).
  sending: boolean;
  streamingText: string;
  tieStatus: string;
  missionId: string | null;

  appendMessage: (m: ChatMessage) => void;
  setSending: (v: boolean) => void;
  setStreamingText: (v: string) => void;
  appendStreamingText: (chunk: string) => void;
  setTieStatus: (v: string) => void;
  setMissionId: (v: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [GREETING],
  sending: false,
  streamingText: "",
  tieStatus: "",
  missionId: null,

  appendMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  setSending: (v) => set({ sending: v }),
  setStreamingText: (v) => set({ streamingText: v }),
  appendStreamingText: (chunk) => set((s) => ({ streamingText: s.streamingText + chunk })),
  setTieStatus: (v) => set({ tieStatus: v }),
  setMissionId: (v) => set({ missionId: v }),
}));
