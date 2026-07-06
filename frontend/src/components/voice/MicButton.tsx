// MicButton.tsx — Boton de micro reutilizable (V0.83, Paso 4 STT).
//
// Captura audio del microfono con MediaRecorder (audio/webm;codecs=opus en
// Electron/Chromium 122), lo envia a POST /api/voice/transcribe y entrega
// la transcripcion por callback. Tambien anima el nucleo 3D segun la
// skill aithera-hub-corestate:
//   recording     -> coreState = "listening"
//   transcribing  -> coreState = "thinking"
//   idle/cleanup  -> coreState = "idle"  (con guard de 80ms breath, R2)
//
// Notas de pitfalls (de la skill aithera-voice-stt):
//   1. MIME type SIEMPRE explicito, sino Chromium elige uno raro.
//   2. stream.getTracks().stop() en onstop, sino el LED del micro queda
//      encendido y el OS muestra "app is using microphone".
//   3. Modelo Whisper se carga LAZY en el backend; el primer click puede
//      tardar 5-10s. feedback visual via transcribing state.
//   4. language="es" forzado, no autodetect (clip corto -> falso idioma).
//   7. Boton disabled mientras transcribing para no enqueuear.
//   8. cleanup en unmount: si el componente desaparece mid-recording,
//      devolvemos el nucleo a idle y soltamos el micro.

import { useState, useRef, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

interface MicButtonProps {
  /** Callback al recibir la transcripcion limpia. */
  onTranscript: (text: string) => void;
  /** Idioma para forzar en Whisper. Default "es" (skill pitfall #4). */
  language?: string;
  /** Tamano del icono en px. Default 18. */
  size?: number;
  /** Clase extra para el boton (alinear con el input). */
  className?: string;
  /** Tooltip custom. */
  title?: string;
}

export default function MicButton({
  onTranscript,
  language = "es",
  size = 18,
  className = "",
  title,
}: MicButtonProps) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Refs (no state) para evitar re-renders durante la grabacion.
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Granular selector (pitfall #4 skill aithera-hub-corestate).
  const setCoreState = useAppStore((s) => s.setCoreState);
  const pulseError = useAppStore((s) => s.pulseError);

  // Cleanup defensivo al desmontar el componente mid-grabacion.
  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        try {
          recorderRef.current.stop();
        } catch {
          /* ya estaba parando */
        }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      // Si el nucleo estaba en "listening" o "thinking" por nuestra culpa,
      // lo devolvemos a idle. Si lo puso otro componente (chat, voice
      // preview), no lo tocamos.
      const cur = useAppStore.getState().coreState;
      if (cur === "listening" || cur === "thinking") {
        setCoreState("idle");
      }
    };
  }, [setCoreState]);

  const start = useCallback(async () => {
    setError(null);
    // Reset defensivo por si quedo algo a medias.
    if (recorderRef.current) {
      try {
        recorderRef.current.stop();
      } catch {
        /* ignore */
      }
      recorderRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // MIME type SIEMPRE explicito (skill pitfall #1).
      // Chromium 122 (Electron 29) soporta audio/webm;codecs=opus nativamente.
      const mimeType = "audio/webm;codecs=opus";
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        throw new Error(
          `Tu navegador no soporta ${mimeType}. Usa una version mas reciente de Electron.`,
        );
      }
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onerror = (e) => {
        // skill pitfall #6: error durante la grabacion
        console.error("MediaRecorder error:", e);
        pulseError();
        setRecording(false);
        setCoreState("idle");
      };

      recorder.onstop = async () => {
        // skill pitfall #2: liberar el micro SIEMPRE.
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        recorderRef.current = null;
        if (blob.size === 0) {
          // grabacion vacia (micro cerrado muy rapido). No transcribimos.
          setRecording(false);
          setCoreState("idle");
          return;
        }
        await transcribe(blob);
      };

      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      // No "thinking" -> "listening" directo: va por la R2 (idle breath)
      // solo cuando vengamos de otro estado. Aqui asumimos que el componente
      // esta limpio al inicio, asi que "listening" directo es correcto.
      setCoreState("listening");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error("Mic access failed:", msg);
      setError(msg);
      pulseError();
      setRecording(false);
      setCoreState("idle");
    }
  }, [language, pulseError, setCoreState]);

  const stop = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      try {
        recorderRef.current.stop();
      } catch (e) {
        console.error("Error stopping recorder:", e);
        // Aun asi dejamos el micro
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        setRecording(false);
        setCoreState("idle");
      }
    }
    // No seteamos idle aqui: onstop -> transcribe() lo hara cuando termine.
  }, [setCoreState]);

  const transcribe = useCallback(
    async (blob: Blob) => {
      setTranscribing(true);
      // Breve transicion listening -> thinking (regla R2: 80ms breath).
      setCoreState("idle");
      setTimeout(() => setCoreState("thinking"), 80);

      try {
        const result = await api.transcribeVoice(blob, language);
        if (result.text && result.text.trim()) {
          onTranscript(result.text.trim());
        } else {
          setError("No se detecto habla. Intentalo de nuevo.");
        }
        setCoreState("idle");
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.error("Transcription failed:", msg);
        setError(msg);
        pulseError();
        setCoreState("idle");
      } finally {
        setTranscribing(false);
        setRecording(false);
      }
    },
    [language, onTranscript, pulseError, setCoreState],
  );

  // Visual: tres estados con estilo distinto.
  const stateClass = recording
    ? "bg-signal-error/15 border-signal-error/40 text-signal-error animate-pulse"
    : transcribing
      ? "bg-signal-warn/15 border-signal-warn/40 text-signal-warn"
      : "bg-base-800 border-base-700 text-ink-dim hover:border-accent/40 hover:text-ink";

  const label = recording
    ? "Detener grabacion"
    : transcribing
      ? "Transcribiendo..."
      : title ?? "Dictar al chat";

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={recording ? stop : start}
        disabled={transcribing}
        title={label}
        aria-label={label}
        className={`p-3 rounded-xl border transition-all disabled:opacity-50 ${stateClass} ${className}`}
      >
        {/* Icono inline. No usamos lucide porque el repo aun no lo tiene. */}
        {recording ? (
          <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : transcribing ? (
          <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="4">
              <animate
                attributeName="r"
                values="4;7;4"
                dur="1.2s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="1;0.3;1"
                dur="1.2s"
                repeatCount="indefinite"
              />
            </circle>
          </svg>
        ) : (
          <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="9" y="2" width="6" height="12" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
        )}
      </button>
      {error && (
        <span
          className="text-[10px] text-signal-error max-w-[180px] text-right"
          role="alert"
        >
          {error}
        </span>
      )}
    </div>
  );
}
