// components/settings/MemoryQuickChat.tsx — Ajustes → Memoria: mini-chat
// directo (PU10, doc 35). Pulido visual (2026-08-02): bubbles con el mismo
// lenguaje que ChatBubble del chat principal, chips de ejemplo para que la
// frase exacta no haya que adivinarla, e indicador de "escribiendo" mientras
// se resuelve — vive DENTRO de la Section "Habla con tu memoria" de
// MemoriaPanel.tsx (el título/descripción ya los pone esa Section).
//
// "guarda que...", "¿qué sabes de...?", "olvida lo de..." se resuelven
// DIRECTO contra `POST /api/memory/quick` (app.memory.quick_memory, backend):
// SIN pasar por el pipeline completo del chat — ni clasificador, ni
// planificador, ni LLM. Guardar aquí escribe SIEMPRE en `user_context`, la
// colección que `chat_service.build_system_prompt()` ya inyecta en cada
// turno de la conversación principal — lo que se dice aquí se APLICA en la
// siguiente respuesta del chat, no queda enterrado en una búsqueda.
//
// `onChanged` avisa al padre (MemoriaPanel.tsx) tras un guardado/olvido con
// éxito, para refrescar las listas de "Lo que Aithera sabe de ti" y
// "Preferencias guardadas" — sin esto, lo guardado aquí no se vería reflejado
// arriba hasta pulsar "Refrescar" a mano.
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/store/useI18n";

interface QuickChatMsg {
  role: "user" | "aithera";
  text: string;
}

interface Props {
  onChanged?: () => void;
}

export default function MemoryQuickChat({ onChanged }: Props) {
  const tr = useT();
  const [messages, setMessages] = useState<QuickChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages, sending]);

  const send = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const res = await api.quickMemory(text);
      setMessages((m) => [...m, { role: "aithera", text: res.reply }]);
      if (res.recognized && res.ok && (res.action === "save" || res.action === "forget")) {
        onChanged?.();
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "aithera", text: tr("settings.memoria.quickchat.errSending", { msg: (e as Error).message }) },
      ]);
    } finally {
      setSending(false);
    }
  };

  const chips = [
    tr("settings.memoria.quickchat.chip1"),
    tr("settings.memoria.quickchat.chip2"),
    tr("settings.memoria.quickchat.chip3"),
  ];

  const useChip = (text: string) => {
    setInput(text);
    inputRef.current?.focus();
  };

  return (
    <div>
      {messages.length === 0 ? (
        <div className="mb-2.5">
          <p className="text-[10px] text-ink-faint mb-1.5">{tr("settings.memoria.quickchat.tryHint")}</p>
          <div className="flex flex-wrap gap-1.5">
            {chips.map((chip, i) => (
              <button
                key={i}
                type="button"
                onClick={() => useChip(chip)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-base-900/40 text-ink-dim border border-base-700/60 hover:border-accent/40 hover:text-ink transition-colors"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-1.5 max-h-48 overflow-y-auto mb-2.5 pr-1">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[88%] text-[11px] leading-relaxed rounded-xl px-2.5 py-1.5 whitespace-pre-line ${
                  m.role === "user"
                    ? "bg-accent/20 text-ink border border-accent/30"
                    : "bg-base-700/50 text-ink"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-xl px-3 py-2 bg-base-700/50">
                <span className="inline-flex gap-1">
                  <span className="w-1 h-1 rounded-full bg-ink-faint animate-bounce [animation-delay:-0.2s]" />
                  <span className="w-1 h-1 rounded-full bg-ink-faint animate-bounce [animation-delay:-0.1s]" />
                  <span className="w-1 h-1 rounded-full bg-ink-faint animate-bounce" />
                </span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}

      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder={tr("settings.memoria.quickchat.placeholder")}
          disabled={sending}
          className="flex-1 bg-base-800/70 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 disabled:opacity-60"
        />
        <button
          onClick={() => void send()}
          disabled={sending || !input.trim()}
          className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 transition-colors"
        >
          {sending ? tr("common.loading") : tr("settings.memoria.quickchat.send")}
        </button>
      </div>
    </div>
  );
}
