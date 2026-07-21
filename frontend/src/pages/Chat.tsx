import { useState, useRef, useEffect, useCallback, memo } from "react";
import { Link } from "react-router-dom";
import { api, type Approval } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useChatStore } from "@/store/useChatStore";
import MicButton from "@/components/voice/MicButton";
import { attachVoiceAudio } from "@/avcs";
import { MiniMarkdown } from "@/lib/miniMarkdown";
import { usePolling } from "@/hooks/usePolling";

// [O1] Trocea la respuesta en fragmentos hablables para el TTS por frases. La
// clave del turn-taking fluido: agrupa por frases (. ! ? … saltos de línea)
// pero fusiona las muy cortas para no fragmentar en exceso (síntesis de "Sí."
// suelta cuesta más overhead que valor). Máx ~180 chars por fragmento para que
// la primera frase suene rápido pero no se parta una idea larga a la mitad.
function splitIntoSpeechChunks(text: string): string[] {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return [];
  const sentences = clean.match(/[^.!?…\n]+[.!?…]*\s*/g) || [clean];
  const out: string[] = [];
  let buf = "";
  for (const s of sentences) {
    const piece = s.trim();
    if (!piece) continue;
    if (buf && (buf.length + piece.length > 180)) {
      out.push(buf.trim());
      buf = piece;
    } else {
      buf = buf ? `${buf} ${piece}` : piece;
      // Corta ya si el buffer tiene una frase completa de tamaño razonable:
      // así la PRIMERA suena cuanto antes.
      if (buf.length >= 60 && /[.!?…]$/.test(piece)) {
        out.push(buf.trim());
        buf = "";
      }
    }
  }
  if (buf.trim()) out.push(buf.trim());
  return out.length ? out : [clean];
}

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
  // [V1 barge-in] Token de cancelación de la locución en curso, texto ya dicho
  // en voz alta, y contexto pendiente de la última interrupción (se le pasa al
  // modelo en el siguiente turno para que reformule sin repetirse).
  const speakTokenRef = useRef<{ cancelled: boolean } | null>(null);
  const spokenSoFarRef = useRef<string>("");
  const interruptedCtxRef = useRef<string | null>(null);
  // [VZ5] Profiling del pipeline de voz: marcas de tiempo de cada etapa del
  // turno actual (fin de escucha → STT → primer token del LLM → primer audio).
  // Se vuelca a consola al final de cada turno de voz — es lo que permite ver
  // en QUÉ etapa se pierde el tiempo en ESTA máquina en vez de suponerlo.
  const voiceProfileRef = useRef<Record<string, number>>({});

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

  // [V3] Voz GARANTIZADA al arrancar. Antes se leía la Config a pelo: si el
  // usuario nunca había pasado por el Centro de Voz no había voz guardada y
  // Aithera respondía MUDA en el chat (bug real reportado). `/voice/defaults`
  // devuelve siempre una voz —la elegida por el usuario, o la mejor del idioma
  // configurado, que además persiste— así que el chat habla desde el primer
  // mensaje sin que nadie configure nada.
  useEffect(() => {
    api
      .getVoiceDefaults()
      .then((d) => {
        providerRef.current = d.provider;
        selectedVoiceRef.current = d.voice_id;
      })
      .catch(() => {
        // Sin backend, los defaults de los refs (EdgeTTS + Elvira) ya sirven.
      });
  }, []);

  // [O1] Síntesis con fallback a eSpeak, devuelve el data-URL del audio.
  const synthChunk = useCallback(async (chunk: string): Promise<string | null> => {
    const voiceId = selectedVoiceRef.current;
    const provRaw = providerRef.current;
    // ElevenLabs va por el camino por defecto (sin provider); el resto explícito.
    const provider =
      provRaw === "elevenlabs" ? undefined : (provRaw as "edgetts" | "kokoro" | "espeak");
    try {
      return (await api.synthesizeVoiceBase64(chunk, voiceId, provider)).audio;
    } catch (e) {
      try {
        return (await api.synthesizeVoiceBase64(chunk, voiceId, "espeak")).audio;
      } catch (e2) {
        console.error("TTS falló (proveedor activo y eSpeak):", e, e2);
        return null;
      }
    }
  }, []);

  // [V1 barge-in] `onpause` resuelve igual que `onended`: cuando el usuario
  // interrumpe, `stopSpeaking()` pausa el audio y el bucle de frases debe
  // salir YA, no quedarse esperando un `ended` que nunca llegará.
  const playUrl = useCallback((dataUrl: string) =>
    new Promise<void>((resolve) => {
      let done = false;
      const finish = () => { if (!done) { done = true; resolve(); } };
      try { audioRef.current?.pause(); } catch { /* noop */ }
      const audio = new Audio(dataUrl);
      audioRef.current = audio;
      attachVoiceAudio(audio); // AVCS S2: ritmo Comunicación late con esta voz
      setCoreState("speaking");
      audio.onended = finish;
      audio.onerror = finish;
      audio.onpause = finish;
      audio.play().catch(finish);
    }), [setCoreState]);

  // [VZ1] STREAMING LLM→TTS — la voz arranca mientras el modelo AÚN ESCRIBE.
  //
  // Antes (O1) el TTS troceaba por frases pero solo cuando la respuesta estaba
  // COMPLETA: se pagaba el tiempo entero de generación del LLM en silencio.
  // `beginSpeechStream()` devuelve una cola viva: `feed(chunk)` recibe los
  // tokens del stream del chat según llegan, extrae frases completas (con el
  // MISMO agrupador splitIntoSpeechChunks) y las encola; cada frase lanza su
  // síntesis DE INMEDIATO (prefetch natural) y la reproducción va en orden.
  // `finish()` vacía lo que quede y resuelve cuando la voz termina de verdad.
  //
  // El barge-in vive aquí (token + spokenSoFar): interrumpir cancela la cola
  // entera y deja registrado hasta dónde llegó a oírse.
  type SpeechStream = {
    feed: (chunk: string) => void;
    finish: () => Promise<void>;
    hasSpokenAnything: () => boolean;
  };

  const beginSpeechStream = useCallback((): SpeechStream => {
    const token = { cancelled: false };
    speakTokenRef.current = token;
    spokenSoFarRef.current = "";
    let buffer = "";
    let tail: Promise<void> = Promise.resolve();
    let anything = false;
    // [VZ5 profiling] primera vez que suena audio de esta locución.
    let firstAudioAt = 0;

    const enqueue = (sentence: string) => {
      if (token.cancelled || !ttsEnabledRef.current) return;
      anything = true;
      const urlPromise = synthChunk(sentence);      // la síntesis arranca YA
      tail = tail.then(async () => {
        if (token.cancelled || !ttsEnabledRef.current) return;
        const url = await urlPromise;
        if (token.cancelled || !url) return;
        if (!firstAudioAt) {
          firstAudioAt = performance.now();
          voiceProfileRef.current.tts_first_audio = firstAudioAt;
        }
        await playUrl(url);
        if (!token.cancelled) {
          spokenSoFarRef.current += (spokenSoFarRef.current ? " " : "") + sentence;
        }
      });
    };

    return {
      feed: (chunk: string) => {
        if (token.cancelled || !ttsEnabledRef.current || !chunk) return;
        buffer += chunk;
        // Extrae las frases COMPLETAS y deja la última (posiblemente a medias)
        // en el buffer. Reusa el agrupador de O1: mismas reglas de tamaño.
        const parts = splitIntoSpeechChunks(buffer);
        if (parts.length > 1) {
          for (const p of parts.slice(0, -1)) enqueue(p);
          buffer = parts[parts.length - 1];
        }
      },
      finish: async () => {
        const rest = buffer.trim();
        buffer = "";
        if (rest) enqueue(rest);
        try {
          await tail;
        } finally {
          if (speakTokenRef.current === token) speakTokenRef.current = null;
          setCoreState("idle");
        }
      },
      hasSpokenAnything: () => anything,
    };
  }, [synthChunk, playUrl, setCoreState]);

  // Reproduce `text` completo (respuesta ya terminada). Envuelve el mismo
  // stream de habla: un solo camino de código para hablar, con barge-in.
  const speak = useCallback(
    async (text: string) => {
      if (!ttsEnabledRef.current) return; // AVCS S3: TTS silenciado — solo texto
      const clean = text.trim();
      if (!clean) return;
      const stream = beginSpeechStream();
      stream.feed(clean);
      await stream.finish();
    },
    [beginSpeechStream],
  );

  // [V1 barge-in] Corta la voz AHORA. La usan la interrupción por voz (modo
  // conversación) y el botón del micro: si Aithera está hablando y el usuario
  // arranca, Aithera se calla — como haría una persona.
  const stopSpeaking = useCallback(() => {
    if (speakTokenRef.current) speakTokenRef.current.cancelled = true;
    try { audioRef.current?.pause(); } catch { /* noop */ }
    audioRef.current = null;
    setCoreState("idle");
  }, [setCoreState]);

  /** ¿Está Aithera hablando ahora mismo? */
  const isSpeaking = () => speakTokenRef.current !== null && !speakTokenRef.current.cancelled;

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
  // `opts.prefix` [V1 barge-in]: contexto que se le envía al modelo pero NO se
  // muestra en el chat. Lo usa la interrupción por voz para decirle "te han
  // cortado mientras decías X" sin ensuciar la conversación del usuario.
  // `opts.speech` [VZ1]: cola de habla viva — cada token del stream se le pasa
  // según llega, así la voz arranca mientras el modelo AÚN escribe.
  const sendMessage = useCallback(async (
    text: string,
    opts?: { prefix?: string; speech?: { feed: (c: string) => void } },
  ): Promise<string | null> => {
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
        // El chat muestra `userMessage`; al modelo le llega además el contexto
        // de interrupción cuando lo hay (nunca visible para el usuario).
        opts?.prefix ? `${opts.prefix}\n\n${userMessage}` : userMessage,
        (chunk) => {
          // [VZ5] primer token del LLM = fin del "pensando" percibido.
          if (!voiceProfileRef.current.llm_first_token) {
            voiceProfileRef.current.llm_first_token = performance.now();
          }
          useChatStore.getState().appendStreamingText(sid, chunk);
          // [VZ1] la voz consume el stream EN VIVO, no la respuesta terminada.
          opts?.speech?.feed(chunk);
        },
        {
          // [V1.0 T4b] El TIE avisa de lo que está haciendo antes de tener
          // respuesta ("analizando" → "planificando"): feedback inmediato en vez
          // de un "Pensando..." mudo mientras clasifica y planifica.
          onStatus: (s) => useChatStore.getState().setTieStatus(sid, s),
          onMission: (id) => useChatStore.getState().setMissionId(sid, id),
          signal: controller.signal,
          // [R6.5b] La pestaña ya tenía identidad en localStorage desde el
          // sprint de sesiones; hasta ahora nunca salía del navegador. Con esto
          // el backend puede recuperar el hilo de ESTA conversación.
          sessionId: sid,
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
    // [V1 barge-in] Si el usuario pulsó el micro MIENTRAS Aithera hablaba,
    // `stopSpeaking` ya la calló (onStartRecording) y aquí se le pasa al modelo
    // hasta dónde llegó a oírse, para que no repita lo ya dicho.
    let prefix: string | undefined;
    const dicho = spokenSoFarRef.current.trim();
    if (interruptedCtxRef.current) {
      prefix = interruptedCtxRef.current;
      interruptedCtxRef.current = null;
    } else if (dicho && speakTokenRef.current?.cancelled) {
      prefix =
        `[Contexto interno: el usuario te ha INTERRUMPIDO mientras hablabas. ` +
        `Solo llegó a oír: "${dicho.slice(-400)}". No repitas lo que ya dijiste; ` +
        `atiende directamente a lo que te dice ahora, teniéndolo en cuenta.]`;
      spokenSoFarRef.current = "";
    }
    // [VZ1] También desde el botón del micro: la voz consume el stream en vivo.
    // (El STT ya ocurrió dentro de MicButton; aquí t0 = texto listo.)
    voiceProfileRef.current = { t0: performance.now(), stt_done: performance.now() };
    const speech = beginSpeechStream();
    await sendMessage(text, { prefix, speech });
    await speech.finish();
    _logVoiceProfile();
  }, [sendMessage, beginSpeechStream]);

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
      // [O1] 700ms (antes 1200): turn-taking más ágil, como Alexa/GPT voz. El
      // usuario no espera un segundo y pico tras callarse para que Aithera
      // arranque. 700ms es suficiente para no cortar entre frases naturales.
      const SILENCE_MS = 700;     // corta tras este silencio (habiendo hablado)
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

  // [V1 barge-in] Escucha el micro MIENTRAS Aithera habla. Si detecta voz
  // sostenida del usuario (~250ms por encima del umbral), corta la locución.
  // `echoCancellation` es lo que impide que Aithera se interrumpa a sí misma al
  // oírse por los altavoces; el umbral es más alto que el del silencio normal
  // por el mismo motivo (defensa en profundidad frente al eco residual).
  const watchForBargeIn = useCallback(async (): Promise<boolean> => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch {
      return false;   // sin micro no hay barge-in; la voz sigue normal
    }
    const ac = new AudioContext();
    const analyser = ac.createAnalyser();
    analyser.fftSize = 512;
    ac.createMediaStreamSource(stream).connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);

    const BARGE_RMS = 0.06;     // bastante por encima del eco residual
    const BARGE_MS = 250;       // voz sostenida, no un golpe de mesa

    return new Promise<boolean>((resolve) => {
      let speakingSince = 0;
      let finished = false;
      const cleanup = (result: boolean) => {
        if (finished) return;
        finished = true;
        stream.getTracks().forEach((t) => t.stop());
        ac.close().catch(() => {});
        resolve(result);
      };
      const tick = () => {
        if (finished) return;
        // Si ya terminó de hablar (o se salió del modo conversación), fuera.
        if (!speakTokenRef.current || speakTokenRef.current.cancelled || !conversationRef.current) {
          cleanup(false);
          return;
        }
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
        const rms = Math.sqrt(sum / buf.length);
        const now = performance.now();
        if (rms > BARGE_RMS) {
          if (!speakingSince) speakingSince = now;
          else if (now - speakingSince > BARGE_MS) { cleanup(true); return; }
        } else {
          speakingSince = 0;
        }
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
        // [VZ5] t0 del turno: el instante en que terminaste de hablar.
        voiceProfileRef.current = { t0: performance.now() };
        // [O1] Modo conversación: STT rápido (modelo base + beam voraz) para
        // que Aithera responda con fluidez, no tras varios segundos.
        const r = await api.transcribeVoice(blob, "es", true);
        voiceProfileRef.current.stt_done = performance.now();
        text = (r.text || "").trim();
      } catch { text = ""; }
      if (!conversationRef.current) break;
      if (!text) continue;

      // Si el turno anterior se cortó, el modelo recibe ese contexto (oculto
      // para el usuario) y reformula sin repetir lo que ya se oyó.
      const prefix = interruptedCtxRef.current || undefined;
      interruptedCtxRef.current = null;

      // [VZ1] La cola de habla se abre ANTES de enviar: cada token del stream
      // alimenta la voz según llega — Aithera empieza a hablar mientras el
      // modelo aún está escribiendo, no cuando termina.
      const speech = beginSpeechStream();
      // [V1] Vigilar el micro desde ya: se puede interrumpir desde la 1.ª frase.
      const watcher = watchForBargeIn();

      const replyPromise = sendMessage(text, { prefix, speech });
      const speakingDone = replyPromise.then(async () => {
        await speech.finish();
        _logVoiceProfile();
        return false as const;
      });

      const interrupted = await Promise.race([watcher, speakingDone]);
      if (interrupted) {
        const dicho = spokenSoFarRef.current.trim();
        stopSpeaking();
        interruptedCtxRef.current =
          `[Contexto interno: el usuario te ha INTERRUMPIDO mientras hablabas. ` +
          `Solo llegó a oír: "${dicho.slice(-400)}". No repitas lo que ya dijiste; ` +
          `atiende directamente a lo que te dice ahora, teniéndolo en cuenta.]`;
      }
      await speakingDone.catch(() => {});   // la cola queda siempre cerrada
      await replyPromise.catch(() => {});
    }
    setCoreState("idle");
  }, [listenOnce, sendMessage, beginSpeechStream, setCoreState, watchForBargeIn, stopSpeaking]);

  // [VZ5] Vuelca el perfil del turno de voz a consola, legible de un vistazo.
  // Todas las cifras en ms desde el fin de la escucha (t0). Es la herramienta
  // para saber qué etapa domina en ESTA máquina: stt, el modelo o el tts.
  const _logVoiceProfile = () => {
    const p = voiceProfileRef.current;
    if (!p.t0) return;
    const rel = (k: string) => (p[k] ? Math.round(p[k] - p.t0) : null);
    const parts = [
      `stt=${rel("stt_done") ?? "—"}ms`,
      `llm_1er_token=${rel("llm_first_token") ?? "—"}ms`,
      `voz_suena=${rel("tts_first_audio") ?? "—"}ms`,
    ];
    console.info(`[voz-perfil] ${parts.join("  ")}  (t0 = fin de tu frase)`);
    voiceProfileRef.current = {};
  };

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
                  className="shrink-0 w-3.5 h-3.5 flex items-center justify-center rounded hover:bg-ink/10 hover:text-signal-error"
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
            <ChatBubble key={i} role={msg.role} content={msg.content} missionId={msg.missionId} />
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
            <MicButton
              onTranscript={handleTranscript}
              language="es"
              disabled={conversation}
              onStartRecording={stopSpeaking}
            />
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
// [P3] Burbuja MEMOIZADA: durante el streaming, cada token re-renderiza la
// página entera y, sin esto, se re-parseaba el MiniMarkdown de TODOS los
// mensajes anteriores en cada chunk — coste que crece con la conversación.
// Con memo, un mensaje ya escrito no vuelve a parsearse jamás.
const ChatBubble = memo(function ChatBubble({ role, content, missionId }: {
  role: string;
  content: string;
  missionId?: string;
}) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
        role === "user"
          ? "bg-accent/20 text-ink border border-accent/30"
          : "bg-base-700/50 text-ink"
      }`}>
        {role === "assistant" ? <MiniMarkdown text={content} /> : content}
        {/* [V1.0 T4b] La respuesta vino de una misión de varios pasos:
            enlace para ver el plan, su estado, o aprobarlo. */}
        {missionId && (
          <Link
            to="/missions"
            className="block mt-2 text-[10px] text-accent hover:underline"
          >
            Ver el plan y sus pasos →
          </Link>
        )}
      </div>
    </div>
  );
});

function PendingApprovals() {
  const [pending, setPending] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const appendMessage = useChatStore((s) => s.appendMessage);

  // [P1] Poll visibility-aware: 2s es el sondeo más agresivo de la app y no
  // tiene sentido pagarlo con la ventana minimizada.
  usePolling(() => {
    api
      .getApprovals()
      .then((list) => setPending(list.filter((a) => a.status === "pending")))
      .catch(() => { /* silencioso: esto es un extra, nunca puede romper el chat */ });
  }, 2000);

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
