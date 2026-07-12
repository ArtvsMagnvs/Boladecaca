// AVCS — constantes y tablas de datos (ver ARCHITECTURE.md §2, §4, §9).
import type { FieldName, FieldWeights, Palette, QualityTier, RhythmName, CoreStateId } from "./types";

/** ORDEN CANÓNICO de campos = índice en uWeights[10]. APPEND-ONLY. */
export const FIELD_ORDER: readonly FieldName[] = [
  "breath",
  "wave",
  "curl",
  "gravity",
  "root",
  "branch",
  "mandala",
  "channel",
  "return",
  "self",
] as const;

export const FIELD_COUNT = FIELD_ORDER.length; // 10
export const MAX_WAVES = 6; // frentes simultáneos (doc 13 §7.2: 4-6)

/** Convierte un FieldWeights a Float32Array en orden FIELD_ORDER. */
export function weightsToArray(w: FieldWeights, out?: Float32Array): Float32Array {
  const arr = out ?? new Float32Array(FIELD_COUNT);
  for (let i = 0; i < FIELD_COUNT; i++) arr[i] = w[FIELD_ORDER[i]] ?? 0;
  return arr;
}

const ZERO: FieldWeights = {
  breath: 0, wave: 0, curl: 0, gravity: 0, root: 0,
  branch: 0, mandala: 0, channel: 0, return: 0, self: 0,
};

/** Reposo: F_breath domina + F_return fuerte = "calma que no es quietud";
 *  F_curl/F_self bajos = deriva browniana sutil; F_wave presente (nacimiento
 *  poisson raro). doc 13 §4 Reposo. */
// Nuevo modelo (forma preservada): return DOMINA (mantiene el logo); breath es el
// latido/pulso; curl+self dan micro-vida; wave empuja la 2ª capa. Ver fields.glsl.
const REPOSE_WEIGHTS: FieldWeights = {
  ...ZERO,
  return: 1.0,
  breath: 0.8, // pulso/latido
  wave: 0.5,
  curl: 0.16,
  self: 0.08,
};

/** Escucha (S2, doc 13 §4): "el campo se INCLINA hacia abajo... nacen raíces
 *  (tendrils descendentes)... se atenúa y se asienta". F_gravity hacia abajo
 *  (dirección en RHYTHM_GRAVITY_Y) tira más de las partículas poco ancladas
 *  (tendrils/campo, bind bajo) que del logo (bind alto) → "raíces insinuadas"
 *  sin spawnear geometría nueva. Ondas menos protagonistas; latido atenuado. */
const LISTENING_WEIGHTS: FieldWeights = {
  ...ZERO,
  return: 0.92,
  breath: 0.55,
  wave: 0.3,
  curl: 0.16,
  self: 0.09,
  gravity: 0.55,
};

/** Comunicación (S2, doc 13 §4): "la energía ASCIENDE... late con la voz
 *  (audio-reactiva)". F_gravity hacia arriba; latido y ondas más vivos (el
 *  acople real a la envolvente de voz vive en fields.glsl vía uAudioEnv). */
const COMMUNICATION_WEIGHTS: FieldWeights = {
  ...ZERO,
  return: 0.95,
  breath: 0.95,
  wave: 0.7,
  curl: 0.18,
  self: 0.1,
  gravity: 0.4,
};

/** Pesos por ritmo. S1/S2: 'repose', 'listening', 'communication' reales; el
 *  resto = copia de reposo (placeholder) para que crossfade y build funcionen
 *  desde ya. MVP1 los rellena sin tocar firmas. */
export const RHYTHM_WEIGHTS: Record<RhythmName, FieldWeights> = {
  repose: REPOSE_WEIGHTS,
  listening: LISTENING_WEIGHTS,
  communication: COMMUNICATION_WEIGHTS,
  comprehension: { ...REPOSE_WEIGHTS },
  action: { ...REPOSE_WEIGHTS },
  recovery: { ...REPOSE_WEIGHTS },
  error: { ...REPOSE_WEIGHTS },
};

/** Factor de sincronía S por ritmo (salud). Reposo/Escucha/Comunicación sanos
 *  ~0.9. Error/Recuperación bajan en MVP1 (la consciencia "enferma"). */
export const RHYTHM_SYNC: Record<RhythmName, number> = {
  repose: 0.9,
  listening: 0.9,
  communication: 0.9,
  comprehension: 0.9,
  action: 0.9,
  recovery: 0.55,
  error: 0.3,
};

/** Periodo base de respiración por ritmo (s). doc 13 §6: Reposo 7s ±15%. */
export const RHYTHM_BREATH_PERIOD: Record<RhythmName, number> = {
  repose: 7.0,
  listening: 6.0,
  communication: 4.5,
  comprehension: 5.5,
  action: 3.5,
  recovery: 8.0,
  error: 5.0,
};

/** Dirección Y de F_gravity por ritmo (doc 13 §4: Escucha abajo, Comunicación
 *  arriba). RhythmEngine interpola uGravityDir hacia este valor suavemente. */
export const RHYTHM_GRAVITY_Y: Record<RhythmName, number> = {
  repose: 0,
  listening: -1,
  communication: 1,
  comprehension: 0,
  action: 0,
  recovery: 0,
  error: 0,
};

/** Offset Y aplicado al grupo de partículas completo — "se asienta" en Escucha,
 *  se eleva en Comunicación. Traslación RÍGIDA de object3D.position.y (HubEngine):
 *  mueve el logo entero sin deformarlo un ápice, así que es la palanca más segura
 *  para que el efecto se note claramente (ajustado tras feedback: los valores
 *  iniciales ±0.08/0.12 eran imperceptibles a la distancia de cámara real). */
export const RHYTHM_SETTLE_Y: Record<RhythmName, number> = {
  repose: 0,
  listening: -0.4,
  communication: 0.3,
  comprehension: 0,
  action: 0,
  recovery: -0.15,
  error: 0,
};

/** Mapa estado del store → ritmo (doc 13 §4). Editable; MVP1 lo refina sin
 *  tocar firmas. */
export const STATE_TO_RHYTHM: Record<CoreStateId, RhythmName> = {
  idle: "repose",
  listening: "listening",
  thinking: "comprehension",
  processing: "comprehension",
  speaking: "communication",
  error: "error",
  action: "action",
  recovering: "recovery",
};

// ---------------------------------------------------------------------------
// Paletas (doc 13 §3). Corazón Ámbar CONSTANTE en todas (invariante nº1).
// RGB 0-1 lineal (sRGB→lineal aproximado para los hex del doc).
// ---------------------------------------------------------------------------
function srgb2lin(hex: string): readonly [number, number, number] {
  const n = parseInt(hex.replace("#", ""), 16);
  const to = (c: number) => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return [to((n >> 16) & 255), to((n >> 8) & 255), to(n & 255)];
}

const AMBER = srgb2lin("#FFD9A0"); // Ámbar vital — corazón constante

/** doc13: aura Aliento azul (#5EA8FF), campo Savia teal atenuado. */
export const PALETTE_DOC13: Palette = {
  heart: AMBER,
  aura: srgb2lin("#5EA8FF"),
  field: srgb2lin("#7FE0C3"),
};

/** warm: aura oro cálido — honra el concept art / mockup de sistema del usuario.
 *  Núcleo Ámbar + aura dorada + campo teal Savia (como la imagen de ondas). */
export const PALETTE_WARM: Palette = {
  heart: AMBER,
  aura: srgb2lin("#FFC65E"),
  field: srgb2lin("#7FE0C3"),
};

export const PALETTES: Record<"doc13" | "warm", Palette> = {
  doc13: PALETTE_DOC13,
  warm: PALETTE_WARM,
};

/** Paleta por defecto de S1 (ver ARCHITECTURE.md §10). Cambiable con setPalette. */
export const DEFAULT_PALETTE: Palette = PALETTE_WARM;

// ---------------------------------------------------------------------------
// Tiers de calidad (doc 13 §15). PerformanceManager es el único que los aplica.
// ---------------------------------------------------------------------------
export interface TierSpec {
  tier: QualityTier;
  sim: 64 | 128 | 256 | 512; // lado de la textura FBO
  particles: number; // sim²
  bloom: boolean;
  bloomIntensity: number;
  dpr: number;
  maxWaves: number;
  /** fracción del pool asignada a la silueta de semilla (mayor en tiers bajos
   *  para que el contorno se lea aun con pocas partículas). */
  seedFraction: number;
}

export const TIERS: Record<QualityTier, TierSpec> = {
  Q1: { tier: "Q1", sim: 64, particles: 64 * 64, bloom: false, bloomIntensity: 0, dpr: 1.0, maxWaves: 4, seedFraction: 0.42 },
  Q2: { tier: "Q2", sim: 128, particles: 128 * 128, bloom: true, bloomIntensity: 0.35, dpr: 1.25, maxWaves: 5, seedFraction: 0.3 },
  Q3: { tier: "Q3", sim: 256, particles: 256 * 256, bloom: true, bloomIntensity: 0.35, dpr: 1.5, maxWaves: 6, seedFraction: 0.24 },
  Q4: { tier: "Q4", sim: 512, particles: 512 * 512, bloom: true, bloomIntensity: 0.32, dpr: 2.0, maxWaves: 6, seedFraction: 0.18 },
};

export const DEFAULT_TIER: QualityTier = "Q3";

/** Radio del cascarón de reposo (unidades de escena). */
export const REST_RADIUS = 1.55;
/** Grosor gaussiano del frente de onda. */
export const WAVE_THICKNESS = 0.14;
/** Radio máximo de una onda antes de disolverse. */
export const WAVE_MAX_RADIUS = 2.7;

/** Magnitud de F_gravity (RHYTHM_GRAVITY_Y da solo el signo/dirección -1..1).
 *  2.6 tras feedback (1.6 apenas se notaba en el campo/tendrils sueltos —
 *  el logo en sí queda a salvo: su bind alto hace que fReturn siga dominando
 *  ahí incluso con este valor, ver fields.glsl computeForce). */
export const GRAVITY_MAGNITUDE = 2.6;

// ---------------------------------------------------------------------------
// Cámara fit-contain (doc 13 §13.3, S2 "sin clipping"). El contenido GARANTIZADO
// visible es la semilla + la 2ª capa (anillos hasta r≈3.52, bandas hasta x≈±4.2,
// ver math/lotus.ts). El starfield de fondo se deja fuera a propósito (jit(11)):
// es decorativo/lejano y puede sangrar fuera de cuadro con el falloff de borde.
// ---------------------------------------------------------------------------
export const CONTENT_HALF_WIDTH = 4.2;
export const CONTENT_HALF_HEIGHT = 3.56;
/** Margen extra sobre el contenido garantizado (+12%, doc 13 §13.3). */
export const FIT_MARGIN = 1.12;
