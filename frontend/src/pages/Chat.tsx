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

  // V0.83 (voz): proveedor activo + voz principal elegidos en el Centro de Voz
  // (persistidos en Config). Por defecto EdgeTTS + Elvira (español), que es lo
  // que funciona sin key ni Docker.
  const providerRef = useRef<string>("edgetts");
  const selectedVoiceRef = useRef<string>("es-ES-ElviraNeural");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api
      .getConfig()
      .then((rows) => {
        const prov = rows.find((r) => r.key === "tts_active_provider")?.value;
        if (prov) providerRef.current = prov;
        const voice = rows.find((r) => r.key === "tts_selected_voice")?.value;
        if (voice) selectedVoiceRef.current = voice;
      })
      .catch(() => {});
  }, []);

  // Reproduce `text` con la voz seleccionada. Si ElevenLabs falla (p.ej. 402
  // del plan gratuito por uso via API/VPN), reintenta con eSpeak para que
  // Aithera responda igualmente en voz.
  const speak = useCallback(
    async (text: string) => {
      const clean = text.trim();
      if (!clean) return;
      const voiceId = selectedVoiceRef.current;
      const play = (dataUrl: string) =>
        new Promise<void>((resolve) => {
          try {
            audioRef.current?.pause();
          } catch {
            /* noop */
          }
          const audio = new Audio(dataUrl);
          audioRef.current = audio;
          setCoreState("speaking");
          audio.onended = () => { setCoreState("idle"); resolve(); };
          audio.onerror = () => { setCoreState("idle"); resolve(); };
          audio.play().catch(() => { setCoreState("idle"); resolve(); });
        });
      const provRaw = providerRef.current;
      // ElevenLabs va por el camino por defecto (sin provider); el resto explícito.
      const provider =
        provRaw === "elevenlabs" ? undefined : (provRaw as "edgetts" | "kokoro" | "espeak");
      try {
        const r = await api.synthesizeVoiceBase64(clean, voiceId, provider);
        await play(r.audio);
      } catch (e) {
        // Si el proveedor activo falla, último recurso: eSpeak offline.
        try {
          const r = await api.synthesizeVoiceBase64(clean, voiceId, "espeak");
          await play(r.audio);
        } catch (e2) {
          console.error("TTS falló (proveedor activo y eSpeak):", e, e2);
        }
      }
    },
    [setCoreState],
  );

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
  const sendMessage = useCallback(async (text: string): Promise<string | null> => {
    const userMessage = text.trim();
    if (!userMessage || loading) return null;
    if (!backendConnected) {
      setMessages(prev => [...prev, { role: "user", content: userMessage }, { role: "assistant", content: "Error: No hay conexión con el backend." }]);
      setInput("");
      pulseError();
      return null;
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
      const reply = accumulatedRef.current || "Sin respuesta";
      setMessages(prev => [...prev, { role: "assistant", content: reply }]);
      setStreamingText("");
      // V0.8.1 (Paso 2): thinking -> idle explicito antes del finally.
      setCoreState("idle");
      // El caller decide si habla la respuesta (voz / conversación).
      return reply;
    } catch (error) {
      console.error("Error en streamChat:", error);
      setMessages(prev => [...prev, { role: "assistant", content: "Lo siento, hubo un error al procesar tu mensaje." }]);
      pulseError();
      return null;
    } finally {
      setLoading(false);
    }
  }, [loading, backendConnected, setCoreState, pulseError]);

  const handleSend = () => { void sendMessage(input); };

  // V0.83: al transcribir por micro, se envía y se responde EN VOZ.
  const handleTranscript = useCallback(async (text: string) => {
    const reply = await sendMessage(text);
    if (reply) await speak(reply);
  }, [sendMessage, speak]);

  // ── V0.83: Modo Conversación (escucha continua) ─────────────────────────
  // Bucle: escuchar (con detección de silencio) → transcribir → responder en
  // voz → volver a escuchar, hasta que el usuario lo apaga.
  const [conversation, setConversation] = useState(false);
  const conversationRef = useRef(false);

  // Graba una intervención y la corta sola cuando detecta ~1.2s de silencio
  // tras haber hablado (VAD por RMS con AnalyserNode). Devuelve el blob webm.
  const listenOnce = useCallback(async (): Promise<Blob | null> => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      return null;
    }
    return new Promise<Blob | null>((resolve) => {
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks: BlobPart[] = [];
      const ac = new AudioContext();
      const analyser = ac.createAnalyser();
      analyser.fftSize = 512;
      ac.createMediaStreamSource(stream).connect(analyser);
      const buf = new Uint8Array(analyser.fftSize);

      let stopped = false;
      const cleanup = () => {
        if (stopped) return;
        stopped = true;
        try { if (recorder.state !== "inactive") recorder.stop(); } catch { /* noop */ }
      };
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        ac.close().catch(() => {});
        resolve(chunks.length ? new Blob(chunks, { type: mimeType }) : null);
      };

      const SILENCE = 0.012;      // umbral RMS de silencio
      const SILENCE_MS = 1200;    // corta tras este silencio (habiendo hablado)
      const MAX_MS = 15000;       // tope duro por intervención
      let spoke = false;
      let silentSince = 0;
      const t0 = performance.now();
      recorder.start();

      const tick = () => {
        if (stopped) return;
        if (!conversationRef.current) { cleanup(); return; }
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
        const rms = Math.sqrt(sum / buf.length);
        const now = performance.now();
        if (rms > SILENCE) { spoke = true; silentSince = 0; }
        else if (spoke) {
          if (!silentSince) silentSince = now;
          else if (now - silentSince > SILENCE_MS) { cleanup(); return; }
        }
        if (now - t0 > MAX_MS) { cleanup(); return; }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }, []);

  const conversationLoop = useCallback(async () => {
    while (conversationRef.current) {
      setCoreState("listening");
      const blob = await listenOnce();
      if (!conversationRef.current) break;
      if (!blob) { await new Promise((r) => setTimeout(r, 300)); continue; }
      let text = "";
      try {
        setCoreState("thinking");
        const r = await api.transcribeVoice(blob, "es");
        text = (r.text || "").trim();
      } catch { text = ""; }
      if (!conversationRef.current) break;
      if (!text) continue;
      const reply = await sendMessage(text);
      if (!conversationRef.current) break;
      if (reply) await speak(reply);   // espera a que termine de hablar
    }
    setCoreState("idle");
  }, [listenOnce, sendMessage, speak, setCoreState]);

  const toggleConversation = useCallback(() => {
    setConversation((prev) => {
      const next = !prev;
      conversationRef.current = next;
      if (next) {
        void conversationLoop();
      } else {
        try { audioRef.current?.pause(); } catch { /* noop */ }
        setCoreState("idle");
      }
      return next;
    });
  }, [conversationLoop, setCoreState]);

  // Al desmontar, cortar la conversación.
  useEffect(() => {
    return () => { conversationRef.current = false; };
  }, []);

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
        {/* V0.83: Modo Conversación (escucha continua). Verde = activo. */}
        <button
          type="button"
          onClick={toggleConversation}
          title={conversation ? "Conversación activa — pulsa para parar" : "Conversación continua (habla y te responde en bucle)"}
          aria-label="Modo conversación"
          className={`shrink-0 w-12 h-12 rounded-xl flex items-center justify-center border transition-all ${
            conversation
              ? "bg-signal-ok/20 text-signal-ok border-signal-ok/40 animate-pulse"
              : "bg-base-800 text-ink-dim border-base-700 hover:text-ink hover:border-base-600"
          }`}
        >
          {/* icono de conversación (dos bocadillos) */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 10h.01M12 10h.01M16 10h.01M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z" />
          </svg>
        </button>
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
