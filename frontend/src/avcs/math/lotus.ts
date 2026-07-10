// AVCS — FUENTE DE VERDAD de la FORMA de la semilla (doc 13 §7.1, imágenes de
// referencia del usuario: pétalo de loto dorado con núcleo, eje vertical y raíz
// descendente ramificada).
//
// NO dibuja nada: genera las posiciones-ancla (uAnchor) y el genoma por
// partícula (uGenome: seed/rol/radio). En el shader, F_return tira cada
// partícula hacia su ancla → la SILUETA EMERGE por densidad de partículas
// (P2 comportamiento, P6 procedural). La respiración (uBreath) la hace pulsar.
//
// Roles (uGenome.g): 0.0 = campo (nube), 0.5 = cáscara/pétalo/eje/raíz, 1.0 = núcleo.

import { mulberry32 } from "./prng";

export interface SeedGeometry {
  /** RGBA por partícula: r=seed(0-1), g=rol, b=radio del ancla, a=spare. length = count*4 */
  genome: Float32Array<ArrayBuffer>;
  /** RGBA por partícula: xyz=posición ancla, w=1. length = count*4 */
  anchor: Float32Array<ArrayBuffer>;
}

// Silueta (calibrable ±30%, doc 13 §22).
const PETAL_OUTER = { w: 0.62, h: 1.12, yOff: 0.12, point: 0.72 };
const PETAL_INNER = { w: 0.34, h: 0.9, yOff: 0.12, point: 0.62 };
const CORE_RADIUS = 0.14;
const ROOT_STRANDS = 5;

/** Ancho del pétalo a la altura normalizada u ∈ [-1,1] (extremos puntiagudos). */
function petalHalfWidth(u: number, W: number, point: number): number {
  return W * Math.pow(Math.max(0, 1 - u * u), point);
}

/**
 * Genera la geometría de la semilla + la nube de campo.
 * @param count       total de partículas (sim²)
 * @param restRadius  radio del cascarón de reposo para las partículas de campo
 * @param seedFrac    fracción del pool asignada a la semilla (contorno)
 * @param sessionSeed entero para el PRNG determinista
 */
export function buildSeedGeometry(
  count: number,
  restRadius: number,
  seedFrac: number,
  sessionSeed: number,
): SeedGeometry {
  const rand = mulberry32(sessionSeed | 0);
  const genome = new Float32Array(count * 4);
  const anchor = new Float32Array(count * 4);

  const seedCount = Math.floor(count * seedFrac);
  // Reparto de la semilla: núcleo / pétalo exterior / interior / eje / raíces.
  const nCore = Math.floor(seedCount * 0.18);
  const nOuter = Math.floor(seedCount * 0.3);
  const nInner = Math.floor(seedCount * 0.24);
  const nAxis = Math.floor(seedCount * 0.1);
  const nRoot = seedCount - nCore - nOuter - nInner - nAxis;

  let i = 0;

  const put = (idx: number, x: number, y: number, z: number, role: number) => {
    const g = idx * 4;
    anchor[g] = x;
    anchor[g + 1] = y;
    anchor[g + 2] = z;
    anchor[g + 3] = 1;
    genome[g] = rand(); // seed individual (F_self)
    genome[g + 1] = role;
    genome[g + 2] = Math.hypot(x, y, z);
    genome[g + 3] = 0;
  };

  // --- Núcleo: cluster denso cerca del centro (corazón Ámbar) ---
  for (let k = 0; k < nCore; k++, i++) {
    const r = CORE_RADIUS * Math.cbrt(rand());
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    put(i, r * Math.sin(ph) * Math.cos(th), r * Math.sin(ph) * Math.sin(th) + PETAL_OUTER.yOff * 0.3, r * Math.cos(ph) * 0.5, 1.0);
  }

  // --- Pétalo exterior (contorno, ambos lados) ---
  for (let k = 0; k < nOuter; k++, i++) {
    const u = -1 + 2 * (k / Math.max(1, nOuter - 1));
    const side = k % 2 === 0 ? 1 : -1;
    const w = petalHalfWidth(u, PETAL_OUTER.w, PETAL_OUTER.point);
    const jitter = (rand() - 0.5) * 0.02;
    put(i, side * w + jitter, u * PETAL_OUTER.h + PETAL_OUTER.yOff, (rand() - 0.5) * 0.08, 0.5);
  }

  // --- Pétalo interior ---
  for (let k = 0; k < nInner; k++, i++) {
    const u = -1 + 2 * (k / Math.max(1, nInner - 1));
    const side = k % 2 === 0 ? 1 : -1;
    const w = petalHalfWidth(u, PETAL_INNER.w, PETAL_INNER.point);
    const jitter = (rand() - 0.5) * 0.02;
    put(i, side * w + jitter, u * PETAL_INNER.h + PETAL_INNER.yOff, (rand() - 0.5) * 0.06, 0.5);
  }

  // --- Eje vertical de luz (imagen 1) ---
  for (let k = 0; k < nAxis; k++, i++) {
    const u = -1 + 2 * (k / Math.max(1, nAxis - 1));
    put(i, (rand() - 0.5) * 0.015, u * PETAL_OUTER.h * 0.92 + PETAL_OUTER.yOff, (rand() - 0.5) * 0.03, 0.5);
  }

  // --- Raíces descendentes ramificadas (imagen 2) ---
  const rootTop = -PETAL_OUTER.h + PETAL_OUTER.yOff;
  for (let k = 0; k < nRoot; k++, i++) {
    const strand = k % ROOT_STRANDS;
    const t = rand(); // profundidad 0-1 a lo largo de la raíz
    const spread = (strand / (ROOT_STRANDS - 1) - 0.5) * 0.9; // abanico lateral
    const branch = t * t; // se abre al descender
    const x = spread * branch + (rand() - 0.5) * 0.06;
    const y = rootTop - t * 0.85;
    const z = (rand() - 0.5) * 0.1 * branch;
    put(i, x, y, z, 0.5);
  }

  // --- Campo: nube en un cascarón esférico de radio restRadius ---
  for (; i < count; i++) {
    const rr = restRadius * (0.75 + 0.35 * rand());
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    put(i, rr * Math.sin(ph) * Math.cos(th), rr * Math.sin(ph) * Math.sin(th), rr * Math.cos(ph), 0.0);
  }

  return { genome, anchor };
}
