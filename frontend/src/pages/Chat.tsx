import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, type Approval } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useChatStore } from "@/store/useChatStore";
import MicButton from "@/components/voice/MicButton";
import { attachVoiceAudio } from "@/avcs";
import { MiniMarkdown } from "@/lib/miniMarkdown";

export default function Chat() {
  // [Fix bug real 2026-07-17] La conversación vive en useChatStore (singleton
  // fuera del árbol de React), no en useState local: navegar a otra página
  // (p.ej. "Misiones" para ver un plan) y volver ya no reinicia el chat, y una
  // respuesta que sigue en camino cuando el usuario navega fuera ya NO se
  // pierde (antes, su setMessages apuntaba al componente desmontado y React
  // descartaba la actualización en silencio).
  //
  // [Feature 2026-07-17] Ahora son SESIONES en pestañas: cada una con su
  // propia conversación, envío en curso y misión asociada. `activeSession` es
  // solo para LEER/pintar; `sendMessage` captura el id de sesión al empezar y
  // lo usa durante toda la petición (si el usuario cambia de pestaña a mitad
  // de una respuesta, esa respuesta sigue escribiendo en SU sesión original,
  // nunca en la que esté activa en pantalla en ese momento).
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const newSession = useChatStore((s) => s.newSession);
  const closeSession = useChatStore((s) => s.closeSession);
  const switchSession = useChatStore((s) => s.switchSession);
  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? sessions[0];
  const messages = activeSession.messages;
  const streamingText = activeSession.streamingText;
  const tieStatus = activeSession.tieStatus;
  const sending = activeSession.sending;
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Un AbortController por sesión: parar una pestaña no corta la de al lado.
  const abortRefs = useRef<Record<string, AbortController>>({});
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
  // vuelo en NINGUNA sesión. Antes navegar fuera con un envío en curso siempre
  // reseteaba el núcleo, aunque el envío ahora SÍ sigue vivo en el store y
  // termina de verdad — forzar "idle" aquí lo dejaría desincronizado hasta que
  // `sendMessage` corrigiera el estado igualmente al terminar.
  useEffect(() => {
    return () => {
      const anySending = useChatStore.getState().sessions.some((s) => s.sending);
      if (useAppStore.getState().coreState === "thinking" && !anySending) {
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
  // componente. `getState()...streamingText` al terminar el stream sustituye
  // al viejo `accumulatedRef` (FIX V0.2): ya no puede quedar obsoleto porque
  // no es un closure de render, es una lectura directa del store.
  //
  // `sid` se resuelve UNA vez al principio y se usa en TODA la función: si el
  // usuario cambia de pestaña mientras esto sigue en vuelo, la respuesta
  // continúa escribiendo en la sesión donde se originó, nunca en la que esté
  // activa en pantalla en ese momento.
  const sendMessage = useCallback(async (text: string): Promise<string | null> => {
    const chat = useChatStore.getState();
    const sid = chat.activeSessionId;
    const session = chat.sessions.find((s) => s.id === sid);
    const userMessage = text.trim();
    if (!userMessage || !session || session.sending) return null;
    if (!backendConnected) {
      chat.appendMessage(sid, { role: "user", content: userMessage });
      chat.appendMessage(sid, { role: "assistant", content: "Error: No hay conexión con el backend." });
      setInput("");
      pulseError();
      return null;
    }

    chat.setSending(sid, true);
    setInput("");
    chat.appendMessage(sid, { role: "user", content: userMessage });
    chat.setStreamingText(sid, "");
    chat.setTieStatus(sid, "");
    chat.setMissionId(sid, null);
    setCoreState("thinking");

    // [2026-07-19] Permite PARAR la respuesta en curso desde el boton del chat.
    // Se guarda por sesion: parar una pestaña no puede cortar la de al lado.
    const controller = new AbortController();
    abortRefs.current[sid] = controller;

    try {
      await api.streamChat(
        userMessage,
        (chunk) => useChatStore.getState().appendStreamingText(sid, chunk),
        {
          // [V1.0 T4b] El TIE avisa de lo que está haciendo antes de tener
          // respuesta ("analizando" → "planificando"): feedback inmediato en vez
          // de un "Pensando..." mudo mientras clasifica y planifica.
          onStatus: (s) => useChatStore.getState().setTieStatus(sid, s),
          onMission: (id) => useChatStore.getState().setMissionId(sid, id),
          signal: controller.signal,
        },
      );
      const finalSession = useChatStore.getState().sessions.find((s) => s.id === sid);
      const reply = finalSession?.streamingText || "Sin respuesta";
      useChatStore.getState().appendMessage(sid, {
        role: "assistant", content: reply, missionId: finalSession?.missionId ?? undefined,
      });
      useChatStore.getState().setStreamingText(sid, "");
      useChatStore.getState().setTieStatus(sid, "");
      // V0.8.1 (Paso 2): thinking -> idle explicito antes del finally.
      setCoreState("idle");
      // El caller decide si habla la respuesta (voz / conversación).
      return reply;
    } catch (error) {
      // Parar NO es un fallo: es lo que el usuario ha pedido. Se conserva lo
      // que ya se habia escrito, para no tirar una respuesta a medio leer.
      if ((error as Error)?.name === "AbortError") {
        const parcial = useChatStore.getState().sessions.find((x) => x.id === sid)?.streamingText || "";
        useChatStore.getState().appendMessage(sid, {
          role: "assistant",
          content: parcial ? `${parcial}

_(parado por ti)_` : "_(parado por ti)_",
        });
        return null;
      }
      console.error("Error en streamChat:", error);
      useChatStore.getState().appendMessage(sid, { role: "assistant", content: "Lo siento, hubo un error al procesar tu mensaje." });
      pulseError();
      return null;
    } finally {
      delete abortRefs.current[sid];
      useChatStore.getState().setSending(sid, false);
    }
  }, [backendConnected, setCoreState, pulseError]);

  const handleSend = () => { void sendMessage(input); };

  // [2026-07-19] PARAR lo que esté en curso. Corta la petición de verdad
  // (AbortController), no solo la UI: sin esto, una respuesta lanzada no se
  // podía interrumpir de ninguna forma.
  const handleStop = () => {
    const sid = useChatStore.getState().activeSessionId;
    abortRefs.current[sid]?.abort();
  };

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

        {/* [Feature 2026-07-17] Pestañas de sesión: varias conversaciones a la
            vez, cada una con su propio historial y envío en curso. Franja
            compacta con scroll horizontal — el panel solo tiene 380px. */}
        <div className="shrink-0 flex items-center gap-1 px-2 py-1.5 border-b border-white/5 overflow-x-auto">
          {sessions.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              onClick={() => switchSession(s.id)}
              onKeyDown={(e) => e.key === "Enter" && switchSession(s.id)}
              title={s.title}
              className={`shrink-0 flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-md text-[11px] cursor-pointer max-w-[110px] ${
                s.id === activeSessionId
                  ? "bg-accent/20 text-ink border border-accent/30"
                  : "bg-base-800/60 text-ink-faint border border-transparent hover:text-ink-dim"
              }`}
            >
              {s.sending && <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse shrink-0" />}
              <span className="truncate">{s.title}</span>
              {sessions.length > 1 && (
                <button
                  onClick={(e) => { e.stopPropagation(); closeSession(s.id); }}
                  title="Cerrar pestaña"
                  aria-label="Cerrar pestaña"
                  className="shrink-0 w-3.5 h-3.5 flex items-center justify-center rounded hover:bg-white/10 hover:text-signal-error"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <button
            onClick={() => newSession()}
            title="Nueva conversación"
            aria-label="Nueva conversación"
            className="shrink-0 w-6 h-6 flex items-center justify-center rounded-md text-ink-faint hover:text-ink hover:bg-base-800/60"
          >
            +
          </button>
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
                {msg.role === "assistant" ? <MiniMarkdown text={msg.content} /> : msg.content}
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
                {streamingText ? <MiniMarkdown text={streamingText} /> : (tieStatus ? `${tieStatus}…` : "Pensando...")}
                <span className="animate-pulse">|</span>
              </div>
            </div>
          )}

          {/* [2026-07-19] Los permisos se piden AQUÍ, donde estás mirando.
              Antes solo salían en Misiones/Automatizaciones: para cuando los
              encontrabas y aprobabas, el bucle ya se había rendido (espera 120s
              y sigue sin esa acción), así que aprobar "no hacía nada". */}
          <PendingApprovals />
          <div ref={messagesEndRef} />
        </div>

        {/* Controles: input + voz. Durante Comunicación, la voz mueve la
            presencia (§8) — este panel se queda deliberadamente quieto. */}
        <div className="shrink-0 border-t border-white/5 p-3 flex flex-col gap-2">
          {/* [2026-07-19] `textarea`, no `input`: con un input de una sola línea
              era IMPOSIBLE escribir un segundo párrafo — Ctrl+Enter enviaba
              igual porque no había dónde meter el salto. Crece con el texto
              hasta un tope y luego hace scroll.
              Tampoco se deshabilita mientras responde: puedes ir escribiendo lo
              siguiente (el input `disabled` era, además, lo que hacía que la UI
              pareciera congelada). */}
          <div className="flex gap-2 items-end">
            <textarea
              value={input}
              rows={1}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key !== "Enter") return;
                // Ctrl/Cmd/Shift + Enter = párrafo nuevo. Enter solo = enviar.
                if (e.ctrlKey || e.metaKey || e.shiftKey) return; // el textarea mete el salto
                e.preventDefault();
                handleSend();
              }}
              placeholder="Escribe tu mensaje...  (Ctrl+Enter para otro párrafo)"
              className="flex-1 min-w-0 resize-none bg-base-800 border border-base-700 rounded-lg px-3 py-2 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/40 leading-relaxed"
            />
            {sending ? (
              <button
                onClick={handleStop}
                title="Parar"
                aria-label="Parar"
                className="shrink-0 w-9 h-9 flex items-center justify-center bg-signal-error/15 text-signal-error rounded-lg border border-signal-error/30 hover:bg-signal-error/25"
              >
                {/* Cuadrado de STOP, sin texto. */}
                <span className="block w-3 h-3 bg-current rounded-[2px]" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim()}
                className="shrink-0 px-3 py-2 bg-accent/15 text-accent rounded-lg text-xs font-medium border border-accent/30 hover:bg-accent/25 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Enviar
              </button>
            )}
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

/**
 * [2026-07-19] Aprobaciones pendientes, EN EL CHAT.
 *
 * EL PROBLEMA QUE RESUELVE: cuando el bucle de tool-use necesita permiso para
 * algo sensible (hacer clic en una página, enviar un email...), abre un
 * ApprovalGate y espera hasta 120 s. Esa petición solo se veía en
 * Misiones/Automatizaciones, así que había que darse cuenta, navegar, buscarla
 * y aprobarla contrarreloj. Pasado el plazo el bucle sigue SIN esa acción — por
 * eso aprobar más tarde parecía "no hacer nada": ya no había nadie esperando.
 *
 * Aquí se ve donde estás mirando, con el mismo endpoint genérico de A1 (no hay
 * backend nuevo).
 *
 * [Fix 2026-07-19, 2º intento] Sondea SIEMPRE que el chat esté montado, NO solo
 * mientras `sending`. El primer intento fallaba justo en el caso más común: si
 * el plan necesita aprobación, el TIE responde «necesito tu visto bueno» y
 * CIERRA el stream — `sending` pasa a false y el componente dejaba de mirar
 * exactamente cuando aparecía la aprobación. Si Aithera te está esperando,
 * tienes que verlo, haya o no una respuesta en curso.
 */
function PendingApprovals() {
  const [pending, setPending] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const appendMessage = useChatStore((s) => s.appendMessage);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const list = await api.getApprovals();
        if (!cancelled) setPending(list.filter((a) => a.status === "pending"));
      } catch {
        /* silencioso: esto es un extra, nunca puede romper el chat */
      }
    };
    void load();
    const id = window.setInterval(load, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const resolve = async (gateId: string, approved: boolean) => {
    setBusy(gateId);
    try {
      await api.resolveApproval(gateId, approved);
      setPending((prev) => prev.filter((a) => a.gate_id !== gateId));
      // El stream de esta respuesta ya se cerró, así que la continuación NO va
      // a llegar sola al chat: se dice explícitamente en vez de dejar al
      // usuario mirando una pantalla que no cambia.
      appendMessage(useChatStore.getState().activeSessionId, {
        role: "assistant",
        content: approved
          ? "Permiso concedido — sigo con ello. Puedes ver el avance paso a paso en Misiones."
          : "Entendido, no lo hago.",
      });
    } catch {
      /* si falla, el sondeo lo volverá a mostrar */
    } finally {
      setBusy(null);
    }
  };

  if (!pending.length) return null;

  return (
    <>
      {pending.map((a) => (
        <div key={a.gate_id} className="flex justify-start">
          <div className="max-w-[85%] rounded-xl border border-signal-warn/40 bg-signal-warn/10 px-3 py-2.5 space-y-2">
            <p className="text-xs font-medium text-signal-warn">Necesito tu permiso</p>
            <p className="text-xs text-ink">{a.title}</p>
            {a.summary && (
              <p className="text-[11px] text-ink-dim whitespace-pre-wrap">{a.summary}</p>
            )}
            <div className="flex gap-2 pt-0.5">
              <button
                onClick={() => resolve(a.gate_id, true)}
                disabled={busy === a.gate_id}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-signal-ok/15 text-signal-ok border border-signal-ok/30 hover:bg-signal-ok/25 disabled:opacity-50"
              >
                Permitir
              </button>
              <button
                onClick={() => resolve(a.gate_id, false)}
                disabled={busy === a.gate_id}
                className="px-3 py-1.5 rounded-lg text-xs bg-base-700/60 text-ink-dim border border-base-600 hover:text-ink disabled:opacity-50"
              >
                No
              </button>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}
