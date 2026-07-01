import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

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
  const { backendConnected } = useAppStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    if (!backendConnected) {
      setMessages(prev => [...prev, { role: "user", content: input }, { role: "assistant", content: "Error: No hay conexión con el backend." }]);
      setInput("");
      return;
    }

    const userMessage = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setStreamingText("");
    accumulatedRef.current = "";

    try {
      await api.streamChat(userMessage, (chunk) => {
        // FIX V0.2: acumular en ref para evitar el bug de closure donde
        // streamingText siempre era "" al finalizar (valor inicial del render).
        accumulatedRef.current += chunk;
        setStreamingText(accumulatedRef.current);
      });
      setMessages(prev => [...prev, { role: "assistant", content: accumulatedRef.current || "Sin respuesta" }]);
      setStreamingText("");
    } catch (error) {
      console.error("Error en streamChat:", error);
      setMessages(prev => [...prev, { role: "assistant", content: "Lo siento, hubo un error al procesar tu mensaje." }]);
    } finally {
      setLoading(false);
    }
  };

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

      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Escribe tu mensaje..."
          className="flex-1 bg-base-800 border border-base-700 rounded-xl px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/40"
          disabled={loading}
        />
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
