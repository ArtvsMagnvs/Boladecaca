import { create } from "zustand";
import { persist } from "zustand/middleware";

// [Feature 2026-07-17] Sesiones de chat en pestañas: el usuario puede tener
// varias conversaciones abiertas a la vez, cambiar entre ellas y seguir cada
// una donde la dejó. Persistidas en localStorage (primera vez que este
// proyecto usa el middleware `persist` de zustand — mismo formato de clave
// dotted que `aithera.workspace.cardLayouts`) para que sobrevivan también a
// cerrar y reabrir la app, no solo a navegar entre páginas.
//
// [Bug real, reportado 2026-07-17] Antes la conversación vivía en useState
// local de Chat.tsx. React Router desmonta la página al navegar (p.ej. a
// "Misiones" para ver un plan), así que volver al chat lo reiniciaba de cero
// — y si una respuesta seguía en camino cuando el usuario navegaba fuera, su
// setMessages apuntaba a un componente ya desmontado: React descartaba esa
// actualización en silencio y la respuesta se perdía para siempre. El store
// vive fuera del árbol de React (singleton), así que sobrevive a cualquier
// desmontaje/remontaje — solo se resetea si el usuario cierra la pestaña.
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  // [V1.0 T4b] Si la respuesta vino de una misión del TIE (varios pasos), su
  // id para poder abrir el plan y su estado.
  missionId?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  // Guard de re-entrancia (equivalente al viejo `sendingRef`, pero como parte
  // del store: sobrevive a que el componente se desmonte/remonte a mitad de
  // un envío, algo que un useRef local NO puede garantizar) — y es POR
  // SESIÓN: enviar en una pestaña no bloquea las demás.
  sending: boolean;
  streamingText: string;
  tieStatus: string;
  missionId: string | null;
  createdAt: number;
}

const DEFAULT_TITLE = "Nueva conversación";

function newSessionId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `s${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function makeSession(): ChatSession {
  return {
    id: newSessionId(),
    title: DEFAULT_TITLE,
    messages: [
      {
        role: "assistant",
        content:
          "Hola! Soy Aithera, tu asistente de IA. Puedo ayudarte con proyectos, tareas, calendario y más. ¿En qué puedo ayudarte hoy?",
      },
    ],
    sending: false,
    streamingText: "",
    tieStatus: "",
    missionId: null,
    createdAt: Date.now(),
  };
}

function titleFrom(text: string): string {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > 32 ? `${t.slice(0, 32)}…` : t || DEFAULT_TITLE;
}

function patchSession(
  sessions: ChatSession[],
  sessionId: string,
  patch: Partial<ChatSession> | ((s: ChatSession) => Partial<ChatSession>),
): ChatSession[] {
  return sessions.map((s) =>
    s.id === sessionId ? { ...s, ...(typeof patch === "function" ? patch(s) : patch) } : s,
  );
}

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string;

  newSession: () => string;
  closeSession: (id: string) => void;
  switchSession: (id: string) => void;

  appendMessage: (sessionId: string, m: ChatMessage) => void;
  setSending: (sessionId: string, v: boolean) => void;
  setStreamingText: (sessionId: string, v: string) => void;
  appendStreamingText: (sessionId: string, chunk: string) => void;
  setTieStatus: (sessionId: string, v: string) => void;
  setMissionId: (sessionId: string, v: string | null) => void;
}

const initialSession = makeSession();

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [initialSession],
      activeSessionId: initialSession.id,

      newSession: () => {
        const s = makeSession();
        set((state) => ({ sessions: [...state.sessions, s], activeSessionId: s.id }));
        return s.id;
      },

      closeSession: (id) => {
        set((state) => {
          const remaining = state.sessions.filter((s) => s.id !== id);
          // Nunca queda la app sin ninguna pestaña: cerrar la última crea una nueva vacía.
          const sessions = remaining.length ? remaining : [makeSession()];
          const activeSessionId =
            state.activeSessionId === id ? sessions[sessions.length - 1].id : state.activeSessionId;
          return { sessions, activeSessionId };
        });
      },

      switchSession: (id) => {
        if (get().sessions.some((s) => s.id === id)) set({ activeSessionId: id });
      },

      appendMessage: (sessionId, m) =>
        set((state) => ({
          sessions: patchSession(state.sessions, sessionId, (s) => ({
            messages: [...s.messages, m],
            // El título se fija solo la primera vez, a partir del primer
            // mensaje del usuario — después no vuelve a cambiar.
            title: s.title === DEFAULT_TITLE && m.role === "user" ? titleFrom(m.content) : s.title,
          })),
        })),

      setSending: (sessionId, v) =>
        set((state) => ({ sessions: patchSession(state.sessions, sessionId, { sending: v }) })),

      setStreamingText: (sessionId, v) =>
        set((state) => ({ sessions: patchSession(state.sessions, sessionId, { streamingText: v }) })),

      appendStreamingText: (sessionId, chunk) =>
        set((state) => ({
          sessions: patchSession(state.sessions, sessionId, (s) => ({ streamingText: s.streamingText + chunk })),
        })),

      setTieStatus: (sessionId, v) =>
        set((state) => ({ sessions: patchSession(state.sessions, sessionId, { tieStatus: v }) })),

      setMissionId: (sessionId, v) =>
        set((state) => ({ sessions: patchSession(state.sessions, sessionId, { missionId: v }) })),
    }),
    {
      name: "aithera.chat.sessions",
      version: 1,
      // Lo transitorio (envío en curso, texto a medio streamear) NUNCA se
      // persiste: si el usuario cierra la app a mitad de una respuesta, al
      // reabrir no debe quedar una pestaña fantasma "enviando" para siempre.
      partialize: (state) => ({
        activeSessionId: state.activeSessionId,
        sessions: state.sessions.map((s) => ({
          ...s,
          sending: false,
          streamingText: "",
          tieStatus: "",
        })),
      }),
    },
  ),
);
