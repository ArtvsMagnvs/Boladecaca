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

/** [doc 35 PU5, 2026-07-30] GIRO DE LOS ANILLOS DE SINCRONÍA (rad/s del anillo
 *  MÁS EXTERNO; los interiores multiplican por `RING_SPIN_RATIO`).
 *
 *  Los 5 anillos verdes giran cada uno EN SU PROPIO PLANO (el de la pantalla),
 *  manteniendo su posición: no bascula el círculo entero como el anillo del
 *  núcleo — que al girar sobre el eje Y se ve de canto y parece una línea — sino
 *  que rueda sobre sí mismo. Alternan sentido (el más externo hacia la derecha,
 *  el siguiente a la izquierda, y así) y los interiores giran más rápido.
 *
 *  ESTA TABLA ES EL PUNTO DE CONFIGURACIÓN POR ESTADO: cambiar el valor de un
 *  ritmo cambia la velocidad cuando Aithera entra en ese estado, y
 *  `RhythmEngine` interpola suavemente entre ellos (nunca hay saltos). Las
 *  animaciones finas de escucha/habla/pensamiento se trabajan en otra sesión;
 *  esto deja el mando puesto.
 *
 *  Referencia: 0.055 rad/s en el anillo externo = una vuelta cada ~114 s; el
 *  más interno (×3.0) da una vuelta cada ~38 s. Presente pero contemplativo. */
export const RHYTHM_RING_SPIN: Record<RhythmName, number> = {
  repose: 0.055,
  listening: 0.063,       // [PU5f] ESCUCHA: +15% sobre reposo (0.055)
  communication: 0.110,   // se anima al hablar
  comprehension: 0.080,
  action: 0.130,
  recovery: 0.030,
  error: 0.020,
};

/** Cuánto más rápido gira cada anillo respecto al inmediatamente exterior.
 *  Con 5 anillos: el interior acaba girando 1.32^4 ≈ 3.0 veces más rápido que
 *  el externo. Progresivo y sin que el más rápido resulte inquieto.
 *  REPLICADO en `fields.glsl` (comentario cruzado allí). */
export const RING_SPIN_RATIO = 1.32;

/** [PU5c] Cadencia del "bloom" de los anillos: cada cuánto (segundos, media de
 *  un proceso de Poisson) se recogen hacia el núcleo y se vuelven a expandir
 *  hasta su sitio, repitiendo la animación de entrada. Es un gesto ocasional,
 *  NO un latido constante: con 38 s de media se ve unas ~1,5 veces por minuto,
 *  suficiente para que sorprenda y no para que canse. */
export const RING_BLOOM_INTERVAL_S = 38;
/** Cuánto tarda un bloom en recuperar el radio normal (s). Suficientemente
 *  lento para que la expansión se lea como un gesto, no como un parpadeo. */
export const RING_BLOOM_RECOVER_S = 3.6;

/** [PU5d] Las ondas de sincronía nacen con un Poisson de media
 *  `RHYTHM_BREATH_PERIOD / WAVE_BIRTH_DIVISOR`. Con divisor 1 (como estaba) la
 *  media era 7 s entre nacimientos y cada onda vive ~5,4 s, así que el número
 *  MEDIO de ondas vivas a la vez era 5,4/7 ≈ 0,8: casi siempre 0 ó 1, a veces
 *  2, y prácticamente nunca 3 — justo lo que se veía. Con divisor 3 la media
 *  sube a ~2,3 simultáneas, y al ser Poisson hay ratos de 4-5 y ratos de una
 *  sola: sigue siendo un sistema vivo, no un metrónomo. El techo real lo pone
 *  `maxWaves` del tier (5-6). */
export const WAVE_BIRTH_DIVISOR = 3;

// ---------------------------------------------------------------------------
// [PU5f] ANIMACIONES DE ESCUCHA Y HABLA (doc 35 PU5f)
// ---------------------------------------------------------------------------
// Ambas se activan por RITMO (`listening` / `communication`), que es lo que ya
// traduce el estado del núcleo. `RhythmEngine` calcula una envolvente 0..1 por
// animación y la cruza suavemente al entrar y salir del estado — nunca hay
// saltos, y si Aithera cambia de estado a media animación, ésta se deshace sola.

/** ESCUCHA — cuánto se contraen los anillos hacia el centro (0.86 = 14% menos
 *  de radio). Es un gesto de recogimiento: Aithera "se concentra". */
export const LISTEN_RING_CONTRACT = 0.86;
/** Segundos de la contracción/recuperación. Lento a propósito. */
export const LISTEN_RING_TAU = 2.4;

/** HABLA — expansión base de los anillos (1.10 = 10% más de radio). */
export const SPEAK_RING_EXPAND = 1.10;
/** HABLA — amplitud de la deformación de los anillos con la voz: el radio deja
 *  de ser constante y ondula con el ángulo, como un frente de radio. Se
 *  multiplica por la envolvente de voz real, así que el volumen SE VE. */
export const SPEAK_RING_RIPPLE = 0.30;
/** Nº de lóbulos de esa ondulación (cuántas crestas da la vuelta al anillo). */
export const SPEAK_RING_LOBES = 5.0;
/** HABLA — velocidad angular base del giro de las líneas de la semilla (rad/s).
 *  El 2.º contorno gira a esta velocidad hacia la derecha; la almendra gira al
 *  revés y SPEAK_ALMOND_RATIO veces más rápido. */
export const SPEAK_PETAL_SPIN = 0.55;
/** La almendra gira ×7 respecto al anillo del núcleo (que va a la mitad del
 *  giro del propio núcleo) y en sentido contrario. */
export const SPEAK_ALMOND_RATIO = 7.0;
/** HABLA — cuánto hincha el latido de voz a la semilla (sobre `uBreathScale`).
 *  Es ADITIVO al swell que ya existía, para que el latido se note de verdad. */
export const SPEAK_SEED_PULSE = 0.10;
/** Segundos del crossfade de entrada/salida de la animación de habla. */
export const SPEAK_TAU = 0.9;

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

/** Paleta por defecto de S1 (ver ARCHITECTURE.md §10). Cambiable con setPalette.
 *  [2026-07-21] El AVCS NO cambia con el tema claro/oscuro de la UI: es la
 *  identidad visual de Aithera, la misma en cualquier tema (decisión del
 *  usuario — se probó una paleta "tinta" para claro y se descartó). */
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
  /** [doc 35 PU5] IGUAL en los 4 tiers (0.436 = el reparto histórico). Se probó
   *  darle más pool al logo en tiers bajos y el resultado fue perder los
   *  anillos/bandas, es decir medio diseño del AVCS. La diferencia entre tiers
   *  NO se compensa moviendo puntos, sino con el TAMAÑO y el BRILLO de cada uno
   *  (`pointScale`/`brightBoost`). El parámetro se conserva por si algún día
   *  hace falta, pero hoy `buildSceneGeometry` reparte igual siempre. */
  seedFraction: number;
  /** [doc 35 PU5] Compensación de LUMINOSIDAD por tier (canal alpha del
   *  fragment de render). Q4 = 1.0 EXACTO: es la referencia y multiplicar por
   *  1.0 deja el cálculo idéntico al histórico, así que Q4 no cambia nada.
   *
   *  QUÉ COMPENSA: con blending aditivo, el brillo del conjunto sale de la SUMA
   *  de todas las partículas. Q1 tiene 64× menos partículas que Q4 (4096 vs
   *  262144), así que el mismo diseño se ve apagado y disperso. Subir la
   *  opacidad de cada partícula devuelve presencia al conjunto.
   *
   *  POR QUÉ NO SE TOCA EL TAMAÑO (lección de la 1.ª versión de PU5, revertida
   *  el mismo día tras verla en pantalla): agrandar `gl_PointSize` parecía la
   *  vía obvia —y es lo que sugería el doc 35— pero es visualmente ERRÓNEA:
   *  cada partícula se dibuja como un degradado radial que ocupa todo el radio
   *  del quad, así que un punto más grande es un degradado más grande, es decir
   *  una MANCHA BORROSA. El AVCS es polvo finísimo (lo dice el propio comentario
   *  de render.vert.glsl: "la referencia es dust diminuto, no puntos gordos");
   *  ampliarlo no lo conserva, lo sustituye por otro estilo. El brillo no toca
   *  ni la geometría del punto ni el perfil del degradado: nitidez idéntica.
   *
   *  Valores conservadores a propósito (no compensan los 64× de diferencia de
   *  partículas, que sería imposible sin quemar la imagen — solo levantan lo
   *  suficiente para que el diseño se lea). Ajustables sin tocar ninguna lógica:
   *  son estos 4 números y nada más.
   */
  brightBoost: number;
  /** [doc 35 PU5] Tamaño de punto relativo a Q4 (=1.0 exacto, sin cambios).
   *
   *  CALIBRADO POR MEDICIÓN, no a ojo: con `frontend/scripts/avcs-preview/` se
   *  midió la luminosidad total (suma de energía del framebuffer) de Q4 y se
   *  buscó, por bisección, el tamaño que la iguala en cada tier. Q1 alcanza el
   *  100,0% de la luz de Q4 con ×4.00, Q2 con ×2.00, Q3 con ×1.45.
   *
   *  POR QUÉ TAN GRANDE (y por qué el brillo NO basta): la luz que aporta una
   *  partícula es área × opacidad, y la opacidad tiene TECHO 1.0 (WebGL clampa
   *  `gl_FragColor`). Medido: con un tamaño de solo ×2.0, ni subiendo el brillo
   *  ×30 se pasa del 36% de la luz de Q4 — satura y deja de sumar. Con 64× menos
   *  partículas, el tamaño es la ÚNICA palanca que puede cerrar esa diferencia.
   *
   *  Y no emborrona porque va SIEMPRE con `edgeHardness`: un disco sólido de
   *  4× es un punto grande y nítido, no una mancha. La 1.ª versión de PU5 falló
   *  justo por agrandar sin endurecer el borde. */
  pointScale: number;
  /** [doc 35 PU5] Dureza del borde del punto: es el umbral interior del
   *  `smoothstep` que dibuja cada partícula en `render.frag.glsl`.
   *  0.0 = degradado completo desde el centro (Q4, EXACTAMENTE como siempre);
   *  0.30 = núcleo sólido con un borde corto → el punto se ve NÍTIDO aunque sea
   *  algo más grande. Ésta es la pieza que permite subir el tamaño sin
   *  emborronar: sin ella, agrandar = difuminar. */
  edgeHardness: number;
}

export const TIERS: Record<QualityTier, TierSpec> = {
  Q2: { tier: "Q2", sim: 128, particles: 128 * 128, bloom: true, bloomIntensity: 0.35, dpr: 1.25, maxWaves: 5, seedFraction: 0.436, brightBoost: 1.6, pointScale: 2.0, edgeHardness: 0.42 },
  Q3: { tier: "Q3", sim: 256, particles: 256 * 256, bloom: true, bloomIntensity: 0.35, dpr: 1.5, maxWaves: 6, seedFraction: 0.436, brightBoost: 0.69, pointScale: 1.45, edgeHardness: 0.42 },
  Q4: { tier: "Q4", sim: 512, particles: 512 * 512, bloom: true, bloomIntensity: 0.32, dpr: 2.0, maxWaves: 6, seedFraction: 0.436, brightBoost: 1.0, pointScale: 1.0, edgeHardness: 0.0 },
};

export const DEFAULT_TIER: QualityTier = "Q3";

/** Tamaño de punto base — valor histórico, IGUAL para los 4 tiers (antes estaba
 *  hardcodeado en UniformBus.ts; extraído aquí solo para no dejar un literal
 *  suelto, sin ningún cambio de comportamiento). El tamaño de partícula NO
 *  depende del tier: ver la nota de `brightBoost` sobre por qué agrandar el
 *  punto en tiers bajos lo vuelve borroso. */
export const BASE_POINT_SIZE = 42;

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
// visible es la semilla + la 2ª capa (anillos hasta r≈3.10 tras [PU6a-bis v2],
// bandas hasta x≈±4.2, ver math/lotus.ts). CONTENT_HALF_HEIGHT se mantiene en
// 3.56 A PROPÓSITO aunque los anillos encogieran: reducirlo agrandaría toda la
// escena (fit) y desharía justo el ajuste pedido (anillos por encima del dock).
// El starfield cubre ahora ±9.5 en x (jit(19)) para no dejar franjas vacías en
// monitores anchos; sigue fuera del contenido garantizado a propósito.
// ---------------------------------------------------------------------------
export const CONTENT_HALF_WIDTH = 4.2;
export const CONTENT_HALF_HEIGHT = 3.56;
/** Margen extra sobre el contenido garantizado (+12%, doc 13 §13.3). */
export const FIT_MARGIN = 1.12;
