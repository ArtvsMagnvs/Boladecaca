// AVCS — AudioReactor: lee el AnalyserNode compartido de audio/AudioBridge.ts
// (conectado al <audio> del TTS por Chat.tsx vía attachVoiceAudio) y produce el
// AudioFrame {envelope,bands,silence} que RhythmEngine/fields.glsl consumen
// (contrato doc 13 §8, congelado desde S1 — S2 solo rellena datos reales).
import { getVoiceFftSize, readVoiceAudioRaw } from "../audio/AudioBridge";
import type { AudioFrame } from "../types";

const SILENCE: AudioFrame = { envelope: 0, bands: [0, 0, 0], silence: true, punch: 0 };

// Envolvente suavizada ~100ms (doc 13 §8) vía filtro exponencial (frame-rate independiente).
const SMOOTH_S = 0.1;
// Ganancia: getByteTimeDomainData da RMS típicamente bajo (voz normal) → se
// amplifica para que 0-1 cubra el rango útil sin saturar en picos.
const GAIN = 3.2;
const SILENCE_THRESHOLD = 0.02;

// ---------------------------------------------------------------------------
// [PU5g 2026-08-02] PUNCH POR SÍLABA — el dato que faltaba.
//
// EL PROBLEMA (reportado por el usuario: "el volumen no cambia, busca la
// manera"): `envelope` lleva 100 ms de suavizado, justo el orden de magnitud
// de una sílaba (~150-250 ms). Eso aplana precisamente lo que da carácter a la
// voz — los ataques. Y además es un valor ABSOLUTO: si el TTS habla flojo y
// parejo, se queda plano cerca de un mismo número y cualquier animación
// enganchada a él apenas se mueve. Era exactamente lo que se veía.
//
// LA SOLUCIÓN (detección de transitorios, práctica estándar de audio): dos
// seguidores de envolvente a distinta velocidad —
//   · RÁPIDO: ataque casi instantáneo (12 ms), caída media (110 ms) → sigue
//     el ataque de CADA sílaba.
//   · LENTO: 420 ms → el nivel medio al que está hablando ahora mismo.
// El PUNCH es la diferencia (rápido − lento) normalizada por el propio nivel
// medio. Al ser RELATIVO, funciona igual con voz fuerte o floja: lo que mide
// es "cuánto destaca esta sílaba sobre lo que venía", que es justo lo que hace
// que un sonido fuerte dibuje una onda más grande que uno flojo.
const FAST_ATTACK_S = 0.012;
const FAST_RELEASE_S = 0.11;
const SLOW_S = 0.42;
/** Cuánto amplifica la diferencia relativa antes de recortar a 0-1. */
const PUNCH_GAIN = 2.6;
/** Suelo del divisor: sin esto, en silencio casi total el cociente explota. */
const PUNCH_FLOOR = 0.035;

export class AudioReactor {
  private current: AudioFrame = SILENCE;
  private buf = new Uint8Array(256);
  private envSmooth = 0;
  private envFast = 0;
  private envSlow = 0;

  // eslint-disable-next-line @typescript-eslint/require-await
  async start(): Promise<void> {
    /* La conexión real ocurre por attachVoiceAudio(el) en Chat.tsx — el
     * AnalyserNode compartido ya vive en AudioBridge; no hay nada que arrancar. */
  }

  stop(): void {
    this.current = SILENCE;
    this.envSmooth = 0;
    this.envFast = 0;
    this.envSlow = 0;
  }

  update(dt: number): void {
    const size = getVoiceFftSize();
    if (this.buf.length !== size) this.buf = new Uint8Array(size);
    if (!readVoiceAudioRaw(this.buf)) {
      this.current = SILENCE;
      this.envFast = 0;
      this.envSlow = 0;
      return;
    }
    let sumSq = 0;
    for (let i = 0; i < this.buf.length; i++) {
      const v = (this.buf[i] - 128) / 128;
      sumSq += v * v;
    }
    const rms = Math.sqrt(sumSq / this.buf.length);
    const k = Math.min(1, dt / SMOOTH_S);
    this.envSmooth += (rms - this.envSmooth) * k;
    const envelope = Math.max(0, Math.min(1, this.envSmooth * GAIN));

    // [PU5g] Seguidor RÁPIDO con ataque/caída asimétricos: sube casi al
    // instante (para no perder el ataque de la sílaba) y baja despacio.
    const tauFast = rms > this.envFast ? FAST_ATTACK_S : FAST_RELEASE_S;
    this.envFast += (rms - this.envFast) * Math.min(1, dt / tauFast);
    // Seguidor LENTO: el nivel medio al que se está hablando ahora.
    this.envSlow += (rms - this.envSlow) * Math.min(1, dt / SLOW_S);
    // PUNCH relativo: cuánto sobresale esta sílaba respecto a ese nivel medio.
    const rel = (this.envFast - this.envSlow) / Math.max(PUNCH_FLOOR, this.envSlow);
    const punch = Math.max(0, Math.min(1, rel * PUNCH_GAIN));

    // MVP1 separará graves/medios/agudos por FFT real; S2 aproxima con la misma
    // envolvente en los 3 canales (el contrato {bands} ya queda vivo y en uso).
    this.current = {
      envelope,
      bands: [envelope, envelope, envelope],
      silence: envelope < SILENCE_THRESHOLD,
      punch,
    };
  }

  get frame(): AudioFrame {
    return this.current;
  }

  dispose(): void {
    this.stop();
  }
}
