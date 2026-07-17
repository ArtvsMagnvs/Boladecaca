import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useChatStore } from "@/store/useChatStore";
import MicButton from "@/components/voice/MicButton";
import { attachVoiceAudio } from "@/avcs";

export default function Chat() {
  // [Fix bug real 2026-07-17] La conversación vive en useChatStore (singleton
  // fuera del árbol de React), no en useState local: navegar a otra página
  // (p.ej. "Misiones" para ver un plan) y volver ya no reinicia el chat, y una
  // respuesta que sigue en camino cuando el usuario navega fuera ya NO se
  // pierde (antes, su setMessages apuntaba al componente desmontado y React
  // descartaba la actualización en silencio).
  const messages = useChatStore((s) => s.messages);
  const streamingText = useChatStore((s) => s.streamingText);
  const tieStatus = useChatStore((s) => s.tieStatus);
  const sending = useChatStore((s) => s.sending);
  const [input, setInput] = useState("");
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

  // AVCS S3 (Chat limpio, doc 13 §13.5): TTS on/off. Ref porque speak() se
  // llama desde bucles async (conversationLoop) que deben leer el valor
  // actual, no el capturado en el momento en que se creó el closure.
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const ttsEnabledRef = useRef(true);
  const toggleTts = useCallback(() => {
    const next = !ttsEnabledRef.current;
    ttsEnabledRef.current = next;
    setTtsEnabled(next);
    if (!next) {
      try { audioRef.current?.pause(); } catch { /* noop */ }
    }
  }, []);

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
      if (!ttsEnabledRef.current) return; // AVCS S3: TTS silenciado — solo texto
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
          attachVoiceAudio(audio); // AVCS S2: ritmo Comunicación late con esta voz
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
  // [Fix bug real 2026-07-17] Solo fuerza "idle" si de verdad no queda nada en
  // vuelo (`chat.sending`). Antes navegar fuera con un envío en curso siempre
  // reseteaba el núcleo, aunque el envío ahora SÍ sigue vivo en el store y
  // termina de verdad — forzar "idle" aquí lo dejaría desincronizado hasta que
  // `sendMessage` corrigiera el estado igualmente al terminar.
  useEffect(() => {
    return () => {
      if (useAppStore.getState().coreState === "thinking" && !useChatStore.getState().sending) {
        setCoreState("idle");
      }
    };
  }, [setCoreState]);

  // Envío centralizado: recibe el texto explícito (no depende del estado
  // `input`, que es asíncrono). Así lo pueden llamar tanto el botón Enviar
  // como el micro (auto-envío) sin bugs de closure.
  //
  // Lee/escribe SIEMPRE vía `useChatStore.getState()` (nunca vía el hook de
  // selección) — igual que ya se hacía con `useAppStore.getState()` arriba
  // para el guard de coreState. Esto es lo que hace que el envío sobreviva a
  // que el componente se desmonte a mitad de camino (navegar a "Misiones" y
  // volver): el guard de re-entrancia y las actualizaciones de estado viven
  // en el store singleton, no en refs/useState atados a ESTA instancia del
  // componente. `getState().streamingText` al terminar el stream sustituye al
  // viejo `accumulatedRef` (FIX V0.2): ya no puede quedar obsoleto porque no
  // es un closure de render, es una lectura directa del store.
  const sendMessage = useCallback(async (text: string): Promise<string | null> => {
    const chat = useChatStore.getState();
    const userMessage = text.trim();
    if (!userMessage || chat.sending) return null;
    if (!backendConnected) {
      chat.appendMessage({ role: "user", content: userMessage });
      chat.appendMessage({ role: "assistant", content: "Error: No hay conexión con el backend." });
      setInput("");
      pulseError();
      return null;
    }

    chat.setSending(true);
    setInput("");
    chat.appendMessage({ role: "user", content: userMessage });
    chat.setStreamingText("");
    chat.setTieStatus("");
    chat.setMissionId(null);
    setCoreState("thinking");

    try {
      await api.streamChat(
        userMessage,
        (chunk) => useChatStore.getState().appendStreamingText(chunk),
        {
          // [V1.0 T4b] El TIE avisa de lo que está haciendo antes de tener
          // respuesta ("analizando" → "planificando"): feedback inmediato en vez
          // de un "Pensando..." mudo mientras clasifica y planifica.
          onStatus: (s) => useChatStore.getState().setTieStatus(s),
          onMission: (id) => useChatStore.getState().setMissionId(id),
        },
      );
      const final = useChatStore.getState();
      const reply = final.streamingText || "Sin respuesta";
      final.appendMessage({ role: "assistant", content: reply, missionId: final.missionId ?? undefined });
      final.setStreamingText("");
      final.setTieStatus("");
      // V0.8.1 (Paso 2): thinking -> idle explicito antes del finally.
      setCoreState("idle");
      // El caller decide si habla la respuesta (voz / conversación).
      return reply;
    } catch (error) {
      console.error("Error en streamChat:", error);
      useChatStore.getState().appendMessage({ role: "assistant", content: "Lo siento, hubo un error al procesar tu mensaje." });
      pulseError();
      return null;
    } finally {
      useChatStore.getState().setSending(false);
    }
  }, [backendConnected, setCoreState, pulseError]);

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

      const SILENCE = 0.012;      // umbral RMS de silencio
      const SILENCE_MS = 1200;    // corta tras este silencio (habiendo hablado)
      const MAX_MS = 15000;       // tope duro por intervención

      let stopped = false;
      const cleanup = () => {
        if (stopped) return;
        stopped = true;
        clearTimeout(hardStop);
        try { if (recorder.state !== "inactive") recorder.stop(); } catch { /* noop */ }
      };
      // FIX (audit): requestAnimationFrame se PAUSA cuando la ventana pierde
      // foco/se minimiza (comportamiento estandar del navegador/Electron).
      // Como el corte por MAX_MS solo se evaluaba dentro de tick(), si el
      // usuario minimizaba Aithera durante "Modo Conversación" el rAF dejaba
      // de dispararse y el corte de los 15s nunca llegaba: el microfono
      // podia quedarse abierto indefinidamente. setTimeout SI sigue
      // disparando en segundo plano, asi que actua de red de seguridad real
      // independiente del rAF.
      const hardStop = setTimeout(cleanup, MAX_MS);

      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        ac.close().catch(() => {});
        resolve(chunks.length ? new Blob(chunks, { type: mimeType }) : null);
      };

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

  // FIX: antes este toggle pasaba una funcion updater a setConversation con
  // efectos secundarios dentro (arrancar conversationLoop, pausar audio...).
  // React.StrictMode (activo en main.tsx) invoca los updaters DOS VECES en
  // desarrollo para detectar impurezas, asi que conversationLoop() se
  // disparaba dos veces por cada clic -> dos bucles de escucha concurrentes
  // -> Aithera respondia dos veces por cada intervencion de voz. El updater
  // de un useState debe ser puro; los efectos van fuera, en el propio
  // manejador del evento, leyendo el valor actual desde el ref (no del
  // estado, que llega con un render de retraso).
  const toggleConversation = useCallback(() => {
    const next = !conversationRef.current;
    conversationRef.current = next;
    setConversation(next);
    if (next) {
      void conversationLoop();
    } else {
      try { audioRef.current?.pause(); } catch { /* noop */ }
      setCoreState("idle");
    }
  }, [conversationLoop, setCoreState]);

  // Al desmontar, cortar la conversación.
  useEffect(() => {
    return () => { conversationRef.current = false; };
  }, []);

  // AVCS S3 (Chat limpio, doc 13 §13.5): la presencia domina el centro — el
  // AVCS ya vive detrás vía AppLayout (full-bleed), así que esta página deja
  // esa zona vacía a propósito. Solo el panel flotante lateral lleva UI.
  return (
    <div className="h-full relative">
      <aside className="avcs-panel-breathe glass-surface absolute top-4 right-4 bottom-4 w-[min(380px,calc(100%-2rem))] rounded-2xl flex flex-col overflow-hidden">
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-white/5">
          <h1 className="text-sm font-semibold text-ink">Chat con Aithera</h1>
          <span
            className={`h-1.5 w-1.5 rounded-full shrink-0 ${backendConnected ? "bg-signal-ok" : "bg-signal-error"}`}
            title={backendConnected ? "Conectado" : "Desconectado"}
          />
        </div>

        {/* Historial compacto */}
        <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 flex flex-col gap-2">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-accent/20 text-ink border border-accent/30"
                  : "bg-base-700/50 text-ink"
              }`}>
                {msg.content}
                {/* [V1.0 T4b] La respuesta vino de una misión de varios pasos:
                    enlace para ver el plan, su estado, o aprobarlo. */}
                {msg.missionId && (
                  <Link
                    to="/missions"
                    className="block mt-2 text-[10px] text-accent hover:underline"
                  >
                    Ver el plan y sus pasos →
                  </Link>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-base-700/50 px-3 py-2 rounded-xl text-xs text-ink-dim max-w-[85%]">
                {/* Mientras el TIE entiende/planifica aún no hay texto: se
                    muestra QUÉ está haciendo en vez de un "Pensando..." mudo. */}
                {streamingText || (tieStatus ? `${tieStatus}…` : "Pensando...")}
                <span className="animate-pulse">|</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Controles: input + voz. Durante Comunicación, la voz mueve la
            presencia (§8) — este panel se queda deliberadamente quieto. */}
        <div className="shrink-0 border-t border-white/5 p-3 flex flex-col gap-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Escribe tu mensaje..."
              className="flex-1 min-w-0 bg-base-800 border border-base-700 rounded-lg px-3 py-2 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/40"
              disabled={sending}
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="shrink-0 px-3 py-2 bg-accent/15 text-accent rounded-lg text-xs font-medium border border-accent/30 hover:bg-accent/25 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Enviar
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* V0.83 (Paso 4): boton de micro. FIX (audit): deshabilitado
                durante "Modo Conversación" — antes se podian usar los dos a
                la vez, abriendo dos capturas de microfono concurrentes que
                transcribian y enviaban la misma intervencion por separado. */}
            <MicButton onTranscript={handleTranscript} language="es" disabled={conversation} />
            {/* V0.83: Modo Conversación (escucha continua). Verde = activo. */}
            <button
              type="button"
              onClick={toggleConversation}
              title={conversation ? "Conversación activa — pulsa para parar" : "Conversación continua (habla y te responde en bucle)"}
              aria-label="Modo conversación"
              className={`shrink-0 w-10 h-10 rounded-lg flex items-center justify-center border transition-all ${
                conversation
                  ? "bg-signal-ok/20 text-signal-ok border-signal-ok/40 animate-pulse"
                  : "bg-base-800 text-ink-dim border-base-700 hover:text-ink hover:border-base-600"
              }`}
            >
              {/* icono de conversación (dos bocadillos) */}
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 10h.01M12 10h.01M16 10h.01M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z" />
              </svg>
            </button>
            {/* AVCS S3: TTS on/off — silencia la voz, el texto sigue llegando. */}
            <button
              type="button"
              onClick={toggleTts}
              title={ttsEnabled ? "Voz activada — pulsa para silenciar" : "Voz silenciada — pulsa para activar"}
              aria-label="Voz (texto a voz)"
              aria-pressed={ttsEnabled}
              className={`shrink-0 w-10 h-10 rounded-lg flex items-center justify-center border transition-all ${
                ttsEnabled
                  ? "bg-base-800 text-ink-dim border-base-700 hover:text-ink hover:border-base-600"
                  : "bg-signal-warn/15 text-signal-warn border-signal-warn/30"
              }`}
            >
              {ttsEnabled ? (
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              ) : (
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <line x1="23" y1="9" x2="17" y2="15" />
                  <line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
