// AVCS — FUENTE DE VERDAD de la geometría de la escena (semilla-logo + segunda
// capa de ondas de sincronía). Genera, por partícula, su GENOMA (seed, rol,
// tamaño, brillo) y su ANCLA (posición objetivo + fuerza de anclaje).
//
// LA SEMILLA ES EL LOGO DE AITHERA. Silueta:
//   · Contornos SIMÉTRICOS sobre el núcleo (puntas de arriba y de abajo idénticas
//     y equidistantes del centro): anchura = W·sin(πt)^p (0 en puntas, máx en el
//     núcleo). GROSOR tipo pincel simétrico: tipFloor en ambas puntas (distinto
//     por LÍNEA — outer fino, inner medio), pleno en el centro.
//   · OJO/ALMENDRA simétrico alrededor del núcleo.
//   · NÚCLEO: sol diminuto con masa/densidad (redondo, ligeramente amorfo) +
//     profundidad de color + ANILLO fino y concentrado (partículas grandes/
//     brillantes) que gira en su plano.
//   · EJE vertical simétrico (aguja arriba, cola abajo). SIN base plana.
//   · TENDRILS tipo sauce, polvo interior, chispas teal en puntas.
//
// La SEMILLA se escala globalmente por SEED_SCALE (núcleo, anillo y líneas). La
// 2ª capa (ondas de sincronía) NO se escala ni cambia. Comportamiento intacto.
//
// Genoma (RGBA): r=seed(0-1), g=rol, b=tamaño(0-1), a=brillo(0-1)
// Ancla  (RGBA): xyz=posición objetivo, w=fuerza de anclaje(0-1)

import { mulberry32 } from "./prng";

export interface SceneGeometry {
  genome: Float32Array<ArrayBuffer>;
  anchor: Float32Array<ArrayBuffer>;
}

export const ROLE = {
  STAR: 0.1,
  FIELD: 0.25,
  RING: 0.38,
  BAND: 0.52,
  SUB: 0.66,
  PETAL: 0.8,
  CORERING: 0.9,
  CORE: 1.0,
} as const;

// ============================================================================
// MEDIDAS DEL LOGO. SEED_CY = centro de simetría (debe coincidir con CORE_CY del
// shader). SEED_SCALE = tamaño global de la semilla (×1.30).
// ============================================================================
const SEED_CY = -0.05;
const SEED_SCALE = 1.3;

// Contornos simétricos: media-altura H, anchura W·sin(πt)^p, grosor con tipFloor.
const OUTER = { H: 1.42, W: 0.86, p: 0.85, thick: 0.062, bright: 0.9, tipFloor: 0.1 };
const INNER = { H: 1.16, W: 0.56, p: 0.9, thick: 0.046, bright: 0.8, tipFloor: 0.2 };
const ALMOND = { H: 0.5, W: 0.28, p: 1.1, thick: 0.037, tipFloor: 0.16 };
const AXIS_H = 1.5;

// Núcleo (radios base; se escalan por SEED_SCALE al colocar).
const CORE_HOT_R = 0.048;
const CORE_GLOW_R = 0.16;
const CORE_RING_R = 0.235;
const CORE_ARC_R = 0.29;

const FRAC = {
  outer: 0.088,
  inner: 0.068,
  almond: 0.05,
  axis: 0.026,
  coreHot: 0.02,
  coreGlow: 0.056,
  coreSpokes: 0.004,
  coreRing: 0.024,
  coreArc: 0.004,
  tendrils: 0.07,
  innerDust: 0.03,
  ring: 0.15,
  band: 0.14,
  star: 0.1,
  // field = resto
};

/** Anchura simétrica: 0 en las puntas (t=0,1), máx en el centro (t=0.5). */
function widthProfile(t: number, p: number): number {
  return Math.pow(Math.sin(Math.PI * t), p);
}

/** Grosor tipo pincel SIMÉTRICO: tipFloor en ambas puntas, 1 en el centro. */
function thickN(t: number, tipFloor: number): number {
  const peak = Math.pow(Math.sin(Math.PI * t), 0.5);
  return tipFloor + (1 - tipFloor) * peak;
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

  const put = (x: number, y: number, z: number, role: number, size: number, bright: number, bind: number) => {
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

  // Colocación de partículas de la SEMILLA: coords relativas al núcleo, escaladas
  // por SEED_SCALE sobre el centro de simetría SEED_CY (punto 3: semilla ×1.30).
  const S = SEED_SCALE;
  const sput = (x: number, yOff: number, z: number, role: number, size: number, bright: number, bind: number) => {
    put(x * S, SEED_CY + yOff * S, z * S, role, size, bright, bind);
  };

  const n = (f: number) => Math.floor(count * f);
  const jit = (a: number) => (rand() - 0.5) * a;
  const tri = (a: number) => (rand() + rand() - 1) * a; // triangular: denso en el centro del trazo

  // ==========================================================================
  // 1) CONTORNOS SIMÉTRICOS (arriba = abajo). Grosor pincel con tipFloor por línea.
  // ==========================================================================
  const contour = (nP: number, H: number, W: number, p: number, thickBase: number, brightBase: number, tipFloor: number) => {
    for (let k = 0; k < nP; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nP - 1) + jit(0.008)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = W * widthProfile(t, p);
      const tn = thickN(t, tipFloor);
      const thick = thickBase * tn;
      const x = side * w + tri(thick);
      const yOff = H * (1 - 2 * t); // +H arriba (t=0) → -H abajo (t=1): SIMÉTRICO
      const z = tri(thick * 1.2);
      const node = rand() < 0.08;
      const size = node ? 0.72 + 0.34 * rand() : (0.26 + 0.4 * rand()) * (0.5 + 0.75 * tn);
      const tipBoost = t < 0.08 || t > 0.92 ? 0.18 : 0; // aguja y cola algo más vivas (simétrico)
      const bright = node ? 0.88 + 0.12 * rand() : brightBase * (0.55 + 0.45 * tn) + tipBoost + 0.08 * rand();
      sput(x, yOff, z, ROLE.PETAL, size, bright, 0.93);
    }
  };
  contour(n(FRAC.outer), OUTER.H, OUTER.W, OUTER.p, OUTER.thick, OUTER.bright, OUTER.tipFloor);
  contour(n(FRAC.inner), INNER.H, INNER.W, INNER.p, INNER.thick, INNER.bright, INNER.tipFloor);

  // ==========================================================================
  // 2) OJO/ALMENDRA — vesica simétrica alrededor del núcleo.
  // ==========================================================================
  {
    const nA = n(FRAC.almond);
    for (let k = 0; k < nA; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nA - 1) + jit(0.008)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = ALMOND.W * widthProfile(t, ALMOND.p);
      const tn = thickN(t, ALMOND.tipFloor);
      const thick = ALMOND.thick * tn;
      const x = side * w + tri(thick);
      const yOff = ALMOND.H * (1 - 2 * t); // simétrico
      const node = rand() < 0.06;
      sput(x, yOff, tri(thick * 1.2), ROLE.PETAL, node ? 0.6 + 0.32 * rand() : (0.2 + 0.34 * rand()) * (0.5 + 0.7 * tn), node ? 0.9 + 0.1 * rand() : INNER.bright * (0.55 + 0.45 * tn), 0.93);
    }
  }

  // ==========================================================================
  // 3) EJE VERTICAL simétrico (aguja arriba, cola abajo). SIN base plana.
  // ==========================================================================
  {
    const nAx = n(FRAC.axis);
    for (let k = 0; k < nAx; k++) {
      const t = rand();
      const yOff = AXIS_H * (1 - 2 * t);
      const dist = Math.abs(yOff);
      const x = jit(0.012);
      let bright = 0.4 + 0.15 * rand();
      let size = 0.13 + 0.2 * rand();
      if (dist > 1.32) { bright += 0.28; size *= 0.65; } // aguja/cola finas y brillantes (simétrico)
      if (dist < 0.28) bright += 0.2; // paso por el núcleo
      sput(x, yOff, jit(0.02), ROLE.PETAL, size, bright, 0.93);
    }
  }

  // ==========================================================================
  // 4) NÚCLEO — sol con masa, redondo y ligeramente amorfo, con profundidad.
  // ==========================================================================
  {
    const nHot = n(FRAC.coreHot);
    for (let k = 0; k < nHot; k++) {
      const r = CORE_HOT_R * Math.sqrt(rand());
      const a = rand() * Math.PI * 2;
      sput(Math.cos(a) * r, Math.sin(a) * r, jit(0.012), ROLE.CORE, 0.3 + 0.26 * rand(), 0.96 + 0.04 * rand(), 1.0);
    }
    const nGlow = n(FRAC.coreGlow);
    for (let k = 0; k < nGlow; k++) {
      const a = rand() * Math.PI * 2;
      let r = CORE_GLOW_R * Math.pow(rand(), 0.42);
      r *= 1 + 0.18 * Math.sin(3 * a + sessionSeed * 0.7); // amorfo (masa solar)
      const depth = Math.max(0, 1 - r / (CORE_GLOW_R * 1.18)); // 1 centro → 0 borde
      sput(Math.cos(a) * r, Math.sin(a) * r * 0.96, jit(0.045) * (1 - depth * 0.5), ROLE.CORE, 0.1 + 0.2 * rand(), 0.34 + 0.62 * depth + 0.06 * rand(), 1.0);
    }
    const nSp = n(FRAC.coreSpokes);
    for (let k = 0; k < nSp; k++) {
      const a = (Math.floor(rand() * 8) / 8) * Math.PI * 2 + jit(0.06);
      const r = CORE_GLOW_R * 0.6 + (CORE_RING_R * 0.92 - CORE_GLOW_R * 0.6) * rand();
      sput(Math.cos(a) * r, Math.sin(a) * r, jit(0.01), ROLE.CORE, 0.07 + 0.1 * rand(), 0.3 + 0.15 * rand(), 1.0);
    }
    // ANILLO fino y CONCENTRADO (banda estrecha) con partículas GRANDES/BRILLANTES.
    const nR = n(FRAC.coreRing);
    for (let k = 0; k < nR; k++) {
      const a = (k / nR) * Math.PI * 2 + jit(0.02);
      const arcGlow = 0.6 + 0.4 * Math.sin(a * 2 + 0.7); // arcos que circulan al girar
      const bigp = rand() < 0.42;
      const rr = CORE_RING_R + jit(0.004); // banda ESTRECHA (fino/concentrado)
      sput(Math.cos(a) * rr, Math.sin(a) * rr, jit(0.008), ROLE.CORERING, bigp ? 0.5 + 0.3 * rand() : 0.22 + 0.2 * rand(), (0.85 + 0.15 * rand()) * arcGlow, 1.0);
    }
    const nArc = n(FRAC.coreArc);
    for (let k = 0; k < nArc; k++) {
      const a = -0.5 + 2.2 * (k / nArc) + jit(0.03);
      const rr = CORE_ARC_R + jit(0.006);
      sput(Math.cos(a) * rr, Math.sin(a) * rr, jit(0.01), ROLE.CORERING, 0.1 + 0.12 * rand(), 0.3 + 0.16 * rand(), 1.0);
    }
  }

  // ==========================================================================
  // 5) TENDRILS tipo sauce + polvo interior.
  // ==========================================================================
  {
    const nT = n(FRAC.tendrils);
    const LOWER_T0 = [0.5, 0.57, 0.63, 0.69, 0.75, 0.8, 0.85];
    const UPPER_T0 = [0.1, 0.17, 0.25];
    const nLower = Math.floor(nT * 0.78);
    const cx = (t0: number) => OUTER.W * widthProfile(t0, OUTER.p);
    const cy = (t0: number) => OUTER.H * (1 - 2 * t0);
    for (let k = 0; k < nLower; k++) {
      const side = k % 2 === 0 ? 1 : -1;
      const strand = Math.floor(k / 2) % LOWER_T0.length;
      const t0 = LOWER_T0[strand] + jit(0.02);
      const x0 = side * cx(t0);
      const y0 = cy(t0);
      const ph = strand * 2.399 + sessionSeed * 0.001;
      const L = 0.55 + 0.5 * ((strand * 0.37) % 1);
      const q = Math.pow(rand(), 0.65);
      const fork = rand() < 0.4 && q > 0.45 ? 1 : 0;
      const x = x0 + side * (L * q + 0.1 * Math.sin(q * 6 + ph) + fork * 0.12 * Math.sin(q * 4 + ph * 3));
      const yOff = y0 - L * q * (0.35 + 0.85 * q) + 0.05 * Math.sin(q * 9 + ph * 2) - fork * 0.08 * q;
      const node = rand() < 0.085;
      sput(x, yOff, jit(0.12 * q), ROLE.SUB, node ? 0.5 + 0.32 * rand() : (0.1 + 0.24 * rand()) * (1 - 0.3 * q), node ? 0.75 + 0.25 * rand() : (0.32 + 0.34 * rand()) * (1 - 0.35 * q), 0.55);
    }
    for (let k = nLower; k < nT; k++) {
      const side = k % 2 === 0 ? 1 : -1;
      const strand = Math.floor(k / 2) % UPPER_T0.length;
      const t0 = UPPER_T0[strand] + jit(0.02);
      const x0 = side * cx(t0);
      const y0 = cy(t0);
      const ph = strand * 1.7;
      const L = 0.35 + 0.35 * ((strand * 0.61) % 1);
      const q = Math.pow(rand(), 0.7);
      const x = x0 + side * (L * q + 0.06 * Math.sin(q * 5 + ph));
      const yOff = y0 + L * q * (0.3 - 0.55 * q);
      const node = rand() < 0.07;
      sput(x, yOff, jit(0.08 * q), ROLE.SUB, node ? 0.45 + 0.3 * rand() : (0.07 + 0.16 * rand()) * (1 - 0.3 * q), node ? 0.7 + 0.25 * rand() : (0.2 + 0.26 * rand()) * (1 - 0.4 * q), 0.55);
    }
  }
  {
    const nD = n(FRAC.innerDust);
    for (let k = 0; k < nD; k++) {
      const t = 0.06 + 0.88 * rand();
      const w = OUTER.W * widthProfile(t, OUTER.p) * 0.88;
      const x = (rand() * 2 - 1) * w * Math.pow(rand(), 0.35);
      const yOff = OUTER.H * (1 - 2 * t) + jit(0.03);
      sput(x, yOff, jit(0.1), ROLE.SUB, 0.05 + 0.09 * rand(), 0.1 + 0.18 * rand(), 0.42);
    }
  }

  // ==========================================================================
  // 2ª CAPA (ondas de sincronía) — SIN escalar ni cambiar.
  // ==========================================================================
  const nRing = n(FRAC.ring);
  const ringRadii = [1.55, 1.95, 2.4, 2.9, 3.45];
  for (let k = 0; k < nRing; k++) {
    const ri = k % ringRadii.length;
    const radius = ringRadii[ri] * (1 + jit(0.02));
    const a = rand() * Math.PI * 2;
    const thin = 0.55 + 0.45 * (Math.sin(a * (2 + ri) + ri) * 0.5 + 0.5);
    const node = rand() < 0.05;
    put(Math.cos(a) * radius, Math.sin(a) * radius + 0.04, jit(0.1), ROLE.RING, node ? 0.55 + 0.3 * rand() : 0.12 + 0.28 * rand(), (node ? 0.8 + 0.2 * rand() : 0.35 + 0.4 * rand()) * thin, 0.45);
  }

  const nBand = n(FRAC.band);
  for (let k = 0; k < nBand; k++) {
    const sideLeft = k % 2 === 0 ? 1 : -1;
    const t = Math.pow(rand(), 0.7);
    const x = sideLeft * (0.5 + t * 3.7);
    const yBase = Math.sin(x * 1.15) * 0.55 + Math.sin(x * 2.3 + 1.0) * 0.22;
    const spread = 0.12 + t * 0.35;
    const y = yBase + jit(spread);
    const z = jit(0.25 + t * 0.3);
    const node = rand() < 0.07;
    put(x, y, z, ROLE.BAND, node ? 0.55 + 0.35 * rand() : 0.12 + 0.28 * rand(), node ? 0.8 + 0.2 * rand() : 0.28 + 0.4 * rand(), 0.47);
  }

  const nStar = n(FRAC.star);
  for (let k = 0; k < nStar; k++) {
    const big = rand() < 0.06;
    put(jit(11), jit(7.5), jit(5) - 1.5, ROLE.STAR, big ? 0.55 + 0.4 * rand() : 0.06 + 0.18 * rand(), big ? 0.85 + 0.15 * rand() : 0.18 + 0.35 * rand(), 0.06);
  }

  while (i < count) {
    const rr = restRadius * (0.9 + 1.4 * rand());
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    put(rr * Math.sin(ph) * Math.cos(th), rr * Math.sin(ph) * Math.sin(th), rr * Math.cos(ph) * 0.6, ROLE.FIELD, 0.1 + 0.22 * rand(), 0.2 + 0.3 * rand(), 0.22);
  }

  return { genome, anchor };
}
