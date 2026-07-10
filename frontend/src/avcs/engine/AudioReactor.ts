// AVCS — AudioReactor: STUB en S1 (siempre silencio). API real en S2 (AnalyserNode
// sobre el <audio> del TTS + micro). El contrato {envelope,bands,silence} es el
// que RhythmEngine ya consumirá — S2 solo rellena datos reales, sin re-firmar.
import type { AudioFrame } from "../types";

const SILENCE: AudioFrame = { envelope: 0, bands: [0, 0, 0], silence: true };

export class AudioReactor {
  private current: AudioFrame = SILENCE;

  // eslint-disable-next-line @typescript-eslint/require-await
  async start(): Promise<void> {
    /* S1: no-op. S2: getUserMedia / AnalyserNode sobre el TTS. */
  }

  stop(): void {
    this.current = SILENCE;
  }

  update(_dt: number): void {
    /* S1: no-op (silencio). */
  }

  get frame(): AudioFrame {
    return this.current;
  }

  dispose(): void {
    this.stop();
  }
}
