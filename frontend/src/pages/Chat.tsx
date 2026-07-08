import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import MicButton from "@/components/voice/MicButton";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hola! Soy Aithera, tu asistente de IA. Puedo ayudarte con proyectos, tareas, calendario y más. ¿En qué puedo ayudarte hoy?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  // FIX V0.2: ref para acumular el texto del stream sin depender del closure
  // de estado (que capturaría siempre el valor inicial "").
  const accumulatedRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // V0.8.1 (Paso 2): selector granular para no re-renderizar el componente
  // en cada cambio de coreState/aiStatus (pitfall #4 de aithera-hub-corestate).
  const backendConnected = useAppStore((s) => s.backendConnected);
  const setCoreState     = useAppStore((s) => s.setCoreState);
  const pulseError       = useAppStore((s) => s.pulseError);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // V0.8.1 (Paso 2): cleanup defensivo del estado del nucleo al desmontar.
  // Si el usuario navega a otra pagina mientras el stream esta en vuelo
  // (loading=true), el useEffect de cleanup de abajo lo deja en idle
  // en lugar de dejar el nucleo enganado en "thinking".
  useEffect(() => {
    return () => {
      if (useAppStore.getState().coreState === "thinking") {
        setCoreState("idle");
      }
    };
  }, [setCoreState]);

  // Envío centralizado: recibe el texto explícito (no depende del estado
  // `input`, que es asíncrono). Así lo pueden llamar tanto el botón Enviar
  // como el micro (auto-envío) sin bugs de closure.
  const sendMessage = useCallback(async (text: string) => {
    const userMessage = text.trim();
    if (!userMessage || loading) return;
    if (!backendConnected) {
      setMessages(prev => [...prev, { role: "user", content: userMessage }, { role: "assistant", content: "Error: No hay conexión con el backend." }]);
      setInput("");
      pulseError();
      return;
    }

    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setStreamingText("");
    accumulatedRef.current = "";
    setCoreState("thinking");

    try {
      await api.streamChat(userMessage, (chunk) => {
        // FIX V0.2: acumular en ref para evitar el bug de closure donde
        // streamingText siempre era "" al finalizar (valor inicial del render).
        accumulatedRef.current += chunk;
        setStreamingText(accumulatedRef.current);
      });
      setMessages(prev => [...prev, { role: "assistant", content: accumulatedRef.current || "Sin respuesta" }]);
      setStreamingText("");
      // V0.8.1 (Paso 2): thinking -> idle explicito antes del finally.
      setCoreState("idle");
    } catch (error) {
      console.error("Error en streamChat:", error);
      setMessages(prev => [...prev, { role: "assistant", content: "Lo siento, hubo un error al procesar tu mensaje." }]);
      pulseError();
    } finally {
      setLoading(false);
    }
  }, [loading, backendConnected, setCoreState, pulseError]);

  const handleSend = () => sendMessage(input);

  // V0.83: al transcribir, el texto del micro se ENVÍA automáticamente.
  // (Antes solo rellenaba el input; ahora dictar = mandar.)
  const handleTranscript = useCallback((text: string) => {
    sendMessage(text);
  }, [sendMessage]);

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-ink">Chat con Aithera</h1>
        <span className={`text-xs px-2 py-1 rounded ${backendConnected ? "bg-signal-ok/15 text-signal-ok" : "bg-signal-error/15 text-signal-error"}`}>
          {backendConnected ? "Conectado" : "Desconectado"}
        </span>
      </div>

      <div className="flex-1 glass-surface rounded-2xl p-4 overflow-y-auto flex flex-col gap-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[70%] px-4 py-3 rounded-2xl text-sm ${
              msg.role === "user" 
                ? "bg-accent/20 text-ink border border-accent/30" 
                : "bg-base-700/50 text-ink"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-base-700/50 px-4 py-3 rounded-2xl text-sm text-ink-dim max-w-[70%]">
              {streamingText || "Pensando..."}
              <span className="animate-pulse">|</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex gap-3 items-start">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Escribe tu mensaje..."
          className="flex-1 bg-base-800 border border-base-700 rounded-xl px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/40"
          disabled={loading}
        />
        {/* V0.83 (Paso 4): boton de micro al lado del input. */}
        <MicButton onTranscript={handleTranscript} language="es" />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-6 py-3 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30 hover:bg-accent/25 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
