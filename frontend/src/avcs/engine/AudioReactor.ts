// AVCS — AudioReactor: lee el AnalyserNode compartido de audio/AudioBridge.ts
// (conectado al <audio> del TTS por Chat.tsx vía attachVoiceAudio) y produce el
// AudioFrame {envelope,bands,silence} que RhythmEngine/fields.glsl consumen
// (contrato doc 13 §8, congelado desde S1 — S2 solo rellena datos reales).
import { getVoiceFftSize, readVoiceAudioRaw } from "../audio/AudioBridge";
import type { AudioFrame } from "../types";

const SILENCE: AudioFrame = { envelope: 0, bands: [0, 0, 0], silence: true };

// Envolvente suavizada ~100ms (doc 13 §8) vía filtro exponencial (frame-rate independiente).
const SMOOTH_S = 0.1;
// Ganancia: getByteTimeDomainData da RMS típicamente bajo (voz normal) → se
// amplifica para que 0-1 cubra el rango útil sin saturar en picos.
const GAIN = 3.2;
const SILENCE_THRESHOLD = 0.02;

export class AudioReactor {
  private current: AudioFrame = SILENCE;
  private buf = new Uint8Array(256);
  private envSmooth = 0;

  // eslint-disable-next-line @typescript-eslint/require-await
  async start(): Promise<void> {
    /* La conexión real ocurre por attachVoiceAudio(el) en Chat.tsx — el
     * AnalyserNode compartido ya vive en AudioBridge; no hay nada que arrancar. */
  }

  stop(): void {
    this.current = SILENCE;
    this.envSmooth = 0;
  }

  update(dt: number): void {
    const size = getVoiceFftSize();
    if (this.buf.length !== size) this.buf = new Uint8Array(size);
    if (!readVoiceAudioRaw(this.buf)) {
      this.current = SILENCE;
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
    // MVP1 separará graves/medios/agudos por FFT real; S2 aproxima con la misma
    // envolvente en los 3 canales (el contrato {bands} ya queda vivo y en uso).
    this.current = { envelope, bands: [envelope, envelope, envelope], silence: envelope < SILENCE_THRESHOLD };
  }

  get frame(): AudioFrame {
    return this.current;
  }

  dispose(): void {
    this.stop();
  }
}
