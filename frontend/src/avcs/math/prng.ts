// AVCS — PRNG determinista + noise 1D para la respiración (CPU).
// Determinismo por sessionSeed = anti-mecanicidad §10.1 (dos arranques nunca
// idénticos, pero reproducibles dentro de una sesión).

/** mulberry32: PRNG rápido y decente sembrado por un entero de 32 bits. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Ruido 1D suave (value-noise con interpolación smootherstep). Determinista.
 *  Usado por la respiración para modular el periodo sin caer en sin(t) puro. */
export function noise1D(x: number): number {
  const xi = Math.floor(x);
  const xf = x - xi;
  const a = hash1(xi);
  const b = hash1(xi + 1);
  // smootherstep
  const t = xf * xf * xf * (xf * (xf * 6 - 15) + 10);
  return (a + (b - a) * t) * 2 - 1; // [-1, 1]
}

function hash1(n: number): number {
  // hash entero → [0,1)
  let h = Math.imul(n ^ 0x9e3779b9, 0x85ebca6b) >>> 0;
  h ^= h >>> 13;
  h = Math.imul(h, 0xc2b2ae35) >>> 0;
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

/** Intervalo de un proceso de Poisson con media `meanSeconds` (exponencial).
 *  `rand` es un generador uniforme [0,1). doc 13 §7.2 / §10.4. */
export function poissonInterval(meanSeconds: number, rand: () => number): number {
  const u = Math.max(1e-6, rand());
  return -Math.log(u) * meanSeconds;
}
