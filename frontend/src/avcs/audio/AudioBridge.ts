// AVCS — AudioBridge: puente Web Audio real entre el <audio> de reproducción TTS
// (Chat.tsx:speak) y el AudioReactor (doc 13 §8). Mismo patrón que el VAD de
// Chat.tsx:listenOnce (AnalyserNode), aplicado a la reproducción en vez del micro.
//
// GOTCHA: createMediaElementSource() re-enruta la salida de audio del elemento
// por el grafo de Web Audio — si no se reconecta a .destination, el usuario deja
// de OÍR el audio. Y solo puede llamarse UNA VEZ por elemento (lanza si se repite,
// por eso el WeakSet). Chat.tsx crea un <audio> nuevo por cada speak(), así que
// no hay reintentos sobre el mismo elemento en el flujo normal.

let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
const attached = new WeakSet<HTMLMediaElement>();

function ensureContext(): AnalyserNode {
  if (!ctx) {
    ctx = new AudioContext();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.6;
  }
  if (ctx.state === "suspended") void ctx.resume();
  return analyser as AnalyserNode;
}

/** Conecta un <audio> de reproducción (TTS) al analizador compartido. Llamar una
 *  vez por elemento, justo tras crearlo (antes o después de play() da igual). */
export function attachVoiceAudio(el: HTMLMediaElement): void {
  if (attached.has(el)) return;
  try {
    const a = ensureContext();
    const src = (ctx as AudioContext).createMediaElementSource(el);
    src.connect(a);
    src.connect((ctx as AudioContext).destination); // sin esto, el audio se silencia
    attached.add(el);
  } catch {
    /* Navegador sin Web Audio o el contexto no pudo crearse: AudioReactor
     * simplemente sigue devolviendo silencio (degradación graceful). */
  }
}

/** Lectura cruda (dominio de tiempo, 0-255) para que AudioReactor calcule RMS.
 *  Devuelve false si todavía no hay ningún <audio> conectado. */
export function readVoiceAudioRaw(out: Uint8Array<ArrayBuffer>): boolean {
  if (!analyser) return false;
  analyser.getByteTimeDomainData(out);
  return true;
}

export function getVoiceFftSize(): number {
  return analyser?.fftSize ?? 256;
}
