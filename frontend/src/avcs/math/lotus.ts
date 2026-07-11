// AVCS — FUENTE DE VERDAD de la geometría de la escena (semilla-logo + segunda
// capa de ondas de sincronía). Genera, por partícula, su GENOMA (seed, rol,
// tamaño, brillo) y su ANCLA (posición objetivo + fuerza de anclaje).
//
// Filosofía (feedback del usuario): la forma EMERGE por densidad de partículas y
// se MANTIENE (no se deforma como goma). La "vida" viene de: escala global,
// giro del núcleo, pulsos, parpadeo, y partículas que viajan dentro/fuera de la
// forma cambiando tamaño/brillo según su posición — no atadas a su sitio.
//
// Referencias del usuario: pétalo de loto dorado con 3 líneas anidadas de grosor
// e intensidad variables, sub-líneas ramificadas tipo constelación, partículas
// sueltas (espacio), núcleo con profundidad + anillo fino; y una segunda capa de
// anillos concéntricos + bandas laterales en S + constelaciones (teal + oro).
//
// Genoma (RGBA): r=seed(0-1), g=rol, b=tamaño(0-1), a=brillo(0-1)
// Ancla  (RGBA): xyz=posición objetivo, w=fuerza de anclaje(0-1)

import { mulberry32 } from "./prng";

export interface SceneGeometry {
  genome: Float32Array<ArrayBuffer>;
  anchor: Float32Array<ArrayBuffer>;
}

// --- Roles (mismos umbrales que render.frag / fields.glsl) ---
export const ROLE = {
  STAR: 0.1, // partícula suelta (starfield/espacio)
  FIELD: 0.25, // nube de campo (empujada por ondas)
  RING: 0.38, // anillo concéntrico
  BAND: 0.52, // banda lateral en S
  SUB: 0.66, // sub-línea / ramificación del logo
  PETAL: 0.8, // contorno de pétalo
  CORERING: 0.9, // anillo fino del núcleo
  CORE: 1.0, // núcleo
} as const;

// Silueta del logo (calibrable ±30%, doc 13 §22). 3 pétalos anidados.
const PETALS = [
  { w: 0.66, h: 1.16, point: 0.74, thick: 1.0 }, // exterior (más grueso/brillante)
  { w: 0.46, h: 1.0, point: 0.66, thick: 0.72 }, // medio (NUEVO, la "línea de más")
  { w: 0.28, h: 0.82, point: 0.58, thick: 0.5 }, // interior (fino)
];
const Y_OFF = 0.1;
const CORE_R = 0.13;
const CORE_RING_R = 0.26;

// Reparto del pool (fracciones del total; escala con el tier).
const FRAC = {
  core: 0.06,
  corering: 0.018,
  petals: 0.16,
  axis: 0.015,
  sub: 0.045, // ramificaciones-constelación sutiles (NO raíces densas)
  ring: 0.15, // anillos concéntricos bien visibles
  band: 0.14,
  star: 0.1,
  // field = resto
};

function petalHalfWidth(u: number, W: number, point: number): number {
  return W * Math.pow(Math.max(0, 1 - u * u), point);
}

export function buildSceneGeometry(
  count: number,
  restRadius: number,
  _seedFrac: number,
  sessionSeed: number,
): SceneGeometry {
  const rand = mulberry32(sessionSeed | 0);
  const genome = new Float32Array(count * 4);
  const anchor = new Float32Array(count * 4);
  let i = 0;

  const put = (
    x: number,
    y: number,
    z: number,
    role: number,
    size: number,
    bright: number,
    bind: number,
  ) => {
    if (i >= count) return;
    const g = i * 4;
    genome[g] = rand();
    genome[g + 1] = role;
    genome[g + 2] = Math.max(0.04, Math.min(1, size));
    genome[g + 3] = Math.max(0.05, Math.min(1, bright));
    anchor[g] = x;
    anchor[g + 1] = y;
    anchor[g + 2] = z;
    anchor[g + 3] = bind;
    i++;
  };

  const n = (f: number) => Math.floor(count * f);
  const jit = (a: number) => (rand() - 0.5) * a;

  // --- NÚCLEO: cluster denso de partículas pequeñas, amorfo, con profundidad ---
  const nCore = n(FRAC.core);
  for (let k = 0; k < nCore; k++) {
    // distribución gaussiana-ish (más denso al centro), algo amorfa
    const r = CORE_R * Math.pow(rand(), 0.6) * (1 + jit(0.5));
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    const x = r * Math.sin(ph) * Math.cos(th);
    const y = r * Math.sin(ph) * Math.sin(th) + Y_OFF * 0.2;
    const z = r * Math.cos(ph) * 0.6;
    const central = 1 - r / (CORE_R * 1.5); // más brillo/pequeñez al centro
    put(x, y, z, ROLE.CORE, 0.28 + 0.35 * rand() - 0.15 * central, 0.7 + 0.3 * rand() + 0.2 * central, 1.0);
  }

  // --- ANILLO FINO del núcleo (lo define como núcleo) ---
  const nCoreRing = n(FRAC.corering);
  for (let k = 0; k < nCoreRing; k++) {
    const a = (k / nCoreRing) * Math.PI * 2 + jit(0.05);
    put(Math.cos(a) * CORE_RING_R, Math.sin(a) * CORE_RING_R + Y_OFF * 0.2, jit(0.02), ROLE.CORERING, 0.35 + 0.25 * rand(), 0.85 + 0.15 * rand(), 1.0);
  }

  // --- PÉTALOS: 3 contornos anidados, grosor/brillo por línea y por partícula ---
  const nPetalsTotal = n(FRAC.petals);
  const petalShare = [0.42, 0.33, 0.25];
  for (let p = 0; p < PETALS.length; p++) {
    const petal = PETALS[p];
    const nP = Math.floor(nPetalsTotal * petalShare[p]);
    for (let k = 0; k < nP; k++) {
      const u = -1 + 2 * (k / Math.max(1, nP - 1)) + jit(0.01);
      const side = k % 2 === 0 ? 1 : -1;
      const w = petalHalfWidth(u, petal.w, petal.point);
      // grosor de línea: jitter perpendicular proporcional al thick de la línea
      const thickJit = jit(0.06 * petal.thick);
      const x = side * w + thickJit + jit(0.008);
      const y = u * petal.h + Y_OFF;
      const z = jit(0.07 * petal.thick);
      // nodo-constelación ocasional (partícula grande y brillante)
      const node = rand() < 0.05;
      const size = node ? 0.75 + 0.25 * rand() : petal.thick * (0.4 + 0.5 * rand());
      const bright = node ? 0.9 + 0.1 * rand() : petal.thick * (0.5 + 0.45 * rand());
      put(x, y, z, ROLE.PETAL, size, bright, 0.92);
    }
  }

  // --- EJE VERTICAL de luz ---
  const nAxis = n(FRAC.axis);
  for (let k = 0; k < nAxis; k++) {
    const u = -1 + 2 * (k / Math.max(1, nAxis - 1));
    put(jit(0.012), u * PETALS[0].h * 0.94 + Y_OFF, jit(0.02), ROLE.PETAL, 0.35 + 0.4 * rand(), 0.6 + 0.4 * rand(), 0.9);
  }

  // --- RAMIFICACIONES tipo constelación (sutiles, en varias direcciones; NO raíces) ---
  // Hebras finas y tenues que nacen de puntos del pétalo y se alejan un poco,
  // sinuosas, con nodos-estrella ocasionales — como constelaciones alrededor.
  const nSub = n(FRAC.sub);
  const SUB_STRANDS = 9;
  for (let k = 0; k < nSub; k++) {
    const strand = k % SUB_STRANDS;
    // dirección de la hebra: reparto por el perímetro, sesgo suave hacia abajo
    const baseAng = (strand / SUB_STRANDS) * Math.PI * 2 - Math.PI * 0.5 + jit(0.3);
    const t = Math.pow(rand(), 0.7); // densidad decreciente hacia la punta
    // punto de partida en el contorno del pétalo exterior
    const startR = 0.5 + 0.35 * Math.abs(Math.sin(baseAng));
    const len = 0.35 + 0.5 * rand(); // hebras CORTAS
    const wobble = Math.sin(t * 7.0 + strand * 2.0) * 0.12;
    const r = startR + t * len;
    const x = Math.cos(baseAng) * r + wobble + jit(0.04);
    const y = Math.sin(baseAng) * r * 0.9 + Y_OFF + jit(0.04);
    const z = jit(0.14 * t);
    const node = rand() < 0.1;
    const size = node ? 0.5 + 0.3 * rand() : 0.1 + 0.22 * rand();
    const bright = node ? 0.7 + 0.25 * rand() : 0.2 + 0.3 * rand(); // TENUES
    put(x, y, z, ROLE.SUB, size, bright, 0.5);
  }

  // --- ANILLOS CONCÉNTRICOS (segunda capa, ondas de sincronía). Definidos y
  //     continuos como en la imagen 2, con partículas de tamaño/brillo variados
  //     y algún nodo-constelación; leve adelgazamiento angular (no rotos). ---
  const nRing = n(FRAC.ring);
  const ringRadii = [1.55, 1.95, 2.4, 2.9, 3.45];
  for (let k = 0; k < nRing; k++) {
    const ri = k % ringRadii.length;
    const radius = ringRadii[ri] * (1 + jit(0.02));
    const a = rand() * Math.PI * 2;
    // adelgazamiento angular suave (mantiene el anillo continuo, solo modula brillo)
    const thin = 0.55 + 0.45 * (Math.sin(a * (2 + ri) + ri) * 0.5 + 0.5);
    const node = rand() < 0.05;
    put(
      Math.cos(a) * radius,
      Math.sin(a) * radius + Y_OFF * 0.4,
      jit(0.1),
      ROLE.RING,
      node ? 0.55 + 0.3 * rand() : 0.12 + 0.28 * rand(),
      (node ? 0.8 + 0.2 * rand() : 0.35 + 0.4 * rand()) * thin,
      0.45,
    );
  }

  // --- BANDAS LATERALES en S tumbada (nacen del centro, expanden a los lados) ---
  const nBand = n(FRAC.band);
  for (let k = 0; k < nBand; k++) {
    const sideLeft = k % 2 === 0 ? 1 : -1;
    const t = Math.pow(rand(), 0.7); // más densidad cerca del centro
    const x = sideLeft * (0.5 + t * 3.7);
    // S tumbada: dos curvas superpuestas
    const yBase = Math.sin(x * 1.15) * 0.55 + Math.sin(x * 2.3 + 1.0) * 0.22;
    // banda con grosor + micro-ramas
    const spread = 0.12 + t * 0.35;
    const y = yBase + jit(spread);
    const z = jit(0.25 + t * 0.3);
    // constelaciones: tufts ocasionales
    const node = rand() < 0.07;
    const isGold = rand() < 0.35; // mezcla teal/oro
    put(
      x,
      y,
      z,
      ROLE.BAND,
      node ? 0.55 + 0.35 * rand() : 0.12 + 0.28 * rand(),
      node ? 0.8 + 0.2 * rand() : 0.28 + 0.4 * rand(),
      isGold ? 0.5 : 0.45, // bind ~igual; el color lo decide el seed en render
    );
  }

  // --- STARFIELD: partículas sueltas, tamaños/brillos variados (espacio) ---
  const nStar = n(FRAC.star);
  for (let k = 0; k < nStar; k++) {
    const x = jit(11);
    const y = jit(7.5);
    const z = jit(5) - 1.5;
    const big = rand() < 0.06; // pocas estrellas grandes/brillantes
    put(x, y, z, ROLE.STAR, big ? 0.55 + 0.4 * rand() : 0.06 + 0.18 * rand(), big ? 0.85 + 0.15 * rand() : 0.18 + 0.35 * rand(), 0.06);
  }

  // --- CAMPO: el resto, nube en cascarón alrededor de la semilla (empujada por ondas) ---
  while (i < count) {
    const rr = restRadius * (0.9 + 1.4 * rand());
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    put(
      rr * Math.sin(ph) * Math.cos(th),
      rr * Math.sin(ph) * Math.sin(th),
      rr * Math.cos(ph) * 0.6,
      ROLE.FIELD,
      0.1 + 0.22 * rand(),
      0.2 + 0.3 * rand(),
      0.22,
    );
  }

  return { genome, anchor };
}
