// AVCS — FUENTE DE VERDAD de la geometría de la escena (semilla-logo + segunda
// capa de ondas de sincronía). Genera, por partícula, su GENOMA (seed, rol,
// tamaño, brillo) y su ANCLA (posición objetivo + fuerza de anclaje).
//
// LA SEMILLA ES EL LOGO DE AITHERA. Silueta medida sobre la referencia oficial:
//
//   · Silueta = LÁGRIMA OJIVAL (perfil beta t^a·(1-t)^b): aguja fina arriba,
//     panza al ~62% de altura, convergencia en punta abajo. NO elipse.
//   · Dos contornos (exterior + interior) que comparten el vértice superior y
//     convergen en la punta inferior. GROSOR TIPO PINCEL: fino en las dos puntas,
//     pleno en el centro de cada línea (thickBase·(0.16+1.3·sin(πt)^0.55)).
//   · OJO/ALMENDRA (vesica) SIMÉTRICO alrededor del núcleo (mismo perfil arriba
//     y abajo); sus puntas mueren en el eje.
//   · NÚCLEO: sol diminuto, redondo pero ligeramente amorfo (masa solar), con
//     profundidad (centro blanco-cálido → oro → borde ámbar), ANILLO fino y
//     nítido que gira en su plano (visible), + arco parcial débil.
//   · EJE vertical completo con cola fina abajo (SIN base plana ni salpicadura).
//   · TENDRILS tipo sauce desde los contornos (referencia de partículas), polvo
//     interior tenue, chispas teal en puntas.
//
// El comportamiento (roles/anclaje/wander/2ª capa) NO cambia.
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
// MEDIDAS DEL LOGO (calibrables ±10%). CORE_Y debe coincidir con CORE_CY del shader.
// ============================================================================
// Escala ×1.30 (punto 3): todas las medidas espaciales de la semilla escaladas
// sobre el centro CORE_Y (los valores 'y' = CORE_Y + (base-CORE_Y)*1.3; W/thick/
// radios/halfH = base*1.3). La 2ª capa (ondas de sincronía) NO se escala.
const TOP_Y = 1.835;
const CORE_Y = -0.05;
const AXIS_TOP = 1.99;
const AXIS_BOTTOM = -1.49;

// Contornos ojivales: perfil beta (pico en a/(a+b)). Grosor asimétrico
// (topFloor/botFloor): punta superior fina, inferior media.
const OUTER = { yEnd: -1.35, W: 1.092, a: 1.86, b: 1.14, thick: 0.081, bright: 0.9, topFloor: 0.1, botFloor: 0.32 };
const INNER = { yTop: 1.783, yEnd: -1.155, W: 0.728, a: 1.8, b: 1.2, thick: 0.06, bright: 0.8, topFloor: 0.13, botFloor: 0.32 };

// Ojo/almendra: SIMÉTRICO alrededor del núcleo.
const ALMOND = { halfH: 0.65, W: 0.364, pow: 1.15, thick: 0.048 };

// Núcleo.
const CORE_HOT_R = 0.0585;
const CORE_GLOW_R = 0.2015;
const CORE_RING_R = 0.299;
const CORE_ARC_R = 0.3705;

// Reparto del pool (densidad de líneas +1/3; anillo del núcleo más denso; sin salpicadura).
const FRAC = {
  outer: 0.088,
  inner: 0.068,
  almond: 0.05,
  axis: 0.026,
  coreHot: 0.02,
  coreGlow: 0.056,
  coreSpokes: 0.004,
  coreRing: 0.02,
  coreArc: 0.004,
  tendrils: 0.07,
  innerDust: 0.03,
  ring: 0.15,
  band: 0.14,
  star: 0.1,
  // field = resto
};

/** Perfil beta normalizado (pico=1 en a/(a+b)) → ANCHURA ojival de la silueta. */
function ogee(t: number, a: number, b: number): number {
  if (t <= 0 || t >= 1) return 0;
  const tp = a / (a + b);
  const norm = Math.pow(tp, a) * Math.pow(1 - tp, b);
  return (Math.pow(t, a) * Math.pow(1 - t, b)) / norm;
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

  const n = (f: number) => Math.floor(count * f);
  const jit = (a: number) => (rand() - 0.5) * a;
  const tri = (a: number) => (rand() + rand() - 1) * a; // triangular: denso en el centro del trazo

  // ==========================================================================
  // 1) CONTORNOS OJIVALES con GROSOR TIPO PINCEL (fino en puntas, pleno en medio).
  // ==========================================================================
  const contour = (nP: number, yTop: number, yEnd: number, W: number, a: number, b: number, thickBase: number, brightBase: number, topFloor: number, botFloor: number) => {
    const tp = a / (a + b); // punto de anchura máxima (panza) → grosor pleno aquí
    for (let k = 0; k < nP; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nP - 1) + jit(0.008)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = W * ogee(t, a, b);
      // grosor ASIMÉTRICO: pico en la panza (tp), floor distinto en cada punta.
      const tw = t < tp ? 0.5 * (t / tp) : 0.5 + 0.5 * ((t - tp) / (1 - tp));
      const peak = Math.pow(Math.sin(Math.PI * tw), 0.5); // 0 puntas → 1 panza
      const fl = topFloor + (botFloor - topFloor) * t; // grosor mínimo por punta
      const thickN = fl + (1 - fl) * peak; // 0..1
      const thick = thickBase * thickN;
      const x = side * w + tri(thick);
      const y = yTop + (yEnd - yTop) * t;
      const z = tri(thick * 1.2);
      const node = rand() < 0.08;
      const size = node ? 0.72 + 0.34 * rand() : (0.26 + 0.4 * rand()) * (0.5 + 0.75 * thickN);
      const tipBoost = t < 0.08 ? 0.2 : 0;
      const bright = node ? 0.88 + 0.12 * rand() : brightBase * (0.55 + 0.45 * thickN) + tipBoost + 0.08 * rand();
      put(x, y, z, ROLE.PETAL, size, bright, 0.93);
    }
  };
  contour(n(FRAC.outer), TOP_Y, OUTER.yEnd, OUTER.W, OUTER.a, OUTER.b, OUTER.thick, OUTER.bright, OUTER.topFloor, OUTER.botFloor);
  contour(n(FRAC.inner), INNER.yTop, INNER.yEnd, INNER.W, INNER.a, INNER.b, INNER.thick, INNER.bright, INNER.topFloor, INNER.botFloor);

  // ==========================================================================
  // 2) OJO/ALMENDRA — vesica SIMÉTRICA alrededor del núcleo (puntas en el eje).
  // ==========================================================================
  {
    const nA = n(FRAC.almond);
    for (let k = 0; k < nA; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nA - 1) + jit(0.008)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = ALMOND.W * Math.pow(Math.sin(Math.PI * t), ALMOND.pow);
      const peak = Math.pow(Math.sin(Math.PI * t), 0.5);
      const fl = 0.16 + 0.12 * t; // punta superior fina, inferior algo más
      const thickN = fl + (1 - fl) * peak;
      const thick = ALMOND.thick * thickN;
      const x = side * w + tri(thick);
      const y = CORE_Y + ALMOND.halfH * (1 - 2 * t); // simétrico arriba/abajo
      const node = rand() < 0.06;
      put(x, y, tri(thick * 1.2), ROLE.PETAL, node ? 0.6 + 0.32 * rand() : (0.2 + 0.34 * rand()) * (0.5 + 0.7 * thickN), node ? 0.9 + 0.1 * rand() : INNER.bright * (0.55 + 0.45 * thickN), 0.93);
    }
  }

  // ==========================================================================
  // 3) EJE VERTICAL con cola fina abajo (SIN base plana ni salpicadura).
  // ==========================================================================
  {
    const nAx = n(FRAC.axis);
    for (let k = 0; k < nAx; k++) {
      const t = rand();
      const y = AXIS_TOP + (AXIS_BOTTOM - AXIS_TOP) * t;
      const x = jit(0.012);
      let bright = 0.4 + 0.15 * rand();
      let size = 0.13 + 0.2 * rand();
      if (y > 1.28) { bright += 0.3; size *= 0.7; } // aguja fina y brillante
      if (Math.abs(y - CORE_Y) < 0.28) bright += 0.2; // paso por el núcleo
      if (y < -0.9) { size *= 0.65; bright += 0.12; } // cola fina inferior
      put(x, y, jit(0.02), ROLE.PETAL, size, bright, 0.93);
    }
  }

  // ==========================================================================
  // 4) NÚCLEO — sol diminuto, redondo pero LIGERAMENTE AMORFO, con profundidad.
  // ==========================================================================
  {
    const nHot = n(FRAC.coreHot);
    for (let k = 0; k < nHot; k++) {
      const r = CORE_HOT_R * Math.sqrt(rand());
      const a = rand() * Math.PI * 2;
      put(Math.cos(a) * r, CORE_Y + Math.sin(a) * r, jit(0.012), ROLE.CORE, 0.3 + 0.26 * rand(), 0.96 + 0.04 * rand(), 1.0);
    }
    const nGlow = n(FRAC.coreGlow);
    for (let k = 0; k < nGlow; k++) {
      const a = rand() * Math.PI * 2;
      let r = CORE_GLOW_R * Math.pow(rand(), 0.42);
      r *= 1 + 0.18 * Math.sin(3 * a + sessionSeed * 0.7); // amorfo (masa solar)
      const depth = Math.max(0, 1 - r / (CORE_GLOW_R * 1.18)); // 1 centro → 0 borde
      put(
        Math.cos(a) * r,
        CORE_Y + Math.sin(a) * r * 0.96,
        jit(0.045) * (1 - depth * 0.5),
        ROLE.CORE,
        0.1 + 0.2 * rand(),
        0.34 + 0.62 * depth + 0.06 * rand(), // brillo = profundidad → gradiente de color
        1.0,
      );
    }
    const nSp = n(FRAC.coreSpokes);
    for (let k = 0; k < nSp; k++) {
      const a = (Math.floor(rand() * 8) / 8) * Math.PI * 2 + jit(0.06);
      const r = CORE_GLOW_R * 0.6 + (CORE_RING_R * 0.92 - CORE_GLOW_R * 0.6) * rand();
      put(Math.cos(a) * r, CORE_Y + Math.sin(a) * r, jit(0.01), ROLE.CORE, 0.07 + 0.1 * rand(), 0.3 + 0.15 * rand(), 1.0);
    }
    // ANILLO fino nítido — DENSO, más brillante, tamaños variados (gira en su plano).
    const nR = n(FRAC.coreRing);
    for (let k = 0; k < nR; k++) {
      const a = (k / nR) * Math.PI * 2 + jit(0.02);
      const arcGlow = 0.6 + 0.4 * Math.sin(a * 2 + 0.7); // arcos brillantes que circulan al girar
      const bigp = rand() < 0.42; // más partículas grandes
      const rr = CORE_RING_R + jit(0.004); // banda ESTRECHA (fino/concentrado)
      put(
        Math.cos(a) * rr,
        CORE_Y + Math.sin(a) * rr,
        jit(0.008),
        ROLE.CORERING,
        bigp ? 0.5 + 0.3 * rand() : 0.22 + 0.2 * rand(),
        (0.85 + 0.15 * rand()) * arcGlow,
        1.0,
      );
    }
    // Arco parcial débil exterior (un sector).
    const nArc = n(FRAC.coreArc);
    for (let k = 0; k < nArc; k++) {
      const a = -0.5 + 2.2 * (k / nArc) + jit(0.03);
      put(Math.cos(a) * (CORE_ARC_R + jit(0.006)), CORE_Y + Math.sin(a) * (CORE_ARC_R + jit(0.006)), jit(0.01), ROLE.CORERING, 0.09 + 0.1 * rand(), 0.26 + 0.14 * rand(), 1.0);
    }
  }

  // ==========================================================================
  // 5) TENDRILS tipo sauce (referencia de partículas) + polvo interior.
  // ==========================================================================
  {
    const nT = n(FRAC.tendrils);
    const LOWER_T0 = [0.5, 0.57, 0.63, 0.69, 0.75, 0.8, 0.85];
    const UPPER_T0 = [0.1, 0.17, 0.25];
    const nLower = Math.floor(nT * 0.78);
    for (let k = 0; k < nLower; k++) {
      const side = k % 2 === 0 ? 1 : -1;
      const strand = Math.floor(k / 2) % LOWER_T0.length;
      const t0 = LOWER_T0[strand] + jit(0.02);
      const x0 = side * OUTER.W * ogee(t0, OUTER.a, OUTER.b);
      const y0 = TOP_Y + (OUTER.yEnd - TOP_Y) * t0;
      const ph = strand * 2.399 + sessionSeed * 0.001;
      const L = 0.55 + 0.5 * ((strand * 0.37) % 1);
      const q = Math.pow(rand(), 0.65);
      const fork = rand() < 0.4 && q > 0.45 ? 1 : 0;
      const x = x0 + side * (L * q + 0.1 * Math.sin(q * 6 + ph) + fork * 0.12 * Math.sin(q * 4 + ph * 3));
      const y = y0 - L * q * (0.35 + 0.85 * q) + 0.05 * Math.sin(q * 9 + ph * 2) - fork * 0.08 * q;
      const node = rand() < 0.085;
      put(x, y, jit(0.12 * q), ROLE.SUB, node ? 0.5 + 0.32 * rand() : (0.1 + 0.24 * rand()) * (1 - 0.3 * q), node ? 0.75 + 0.25 * rand() : (0.32 + 0.34 * rand()) * (1 - 0.35 * q), 0.55);
    }
    for (let k = nLower; k < nT; k++) {
      const side = k % 2 === 0 ? 1 : -1;
      const strand = Math.floor(k / 2) % UPPER_T0.length;
      const t0 = UPPER_T0[strand] + jit(0.02);
      const x0 = side * OUTER.W * ogee(t0, OUTER.a, OUTER.b);
      const y0 = TOP_Y + (OUTER.yEnd - TOP_Y) * t0;
      const ph = strand * 1.7;
      const L = 0.35 + 0.35 * ((strand * 0.61) % 1);
      const q = Math.pow(rand(), 0.7);
      const x = x0 + side * (L * q + 0.06 * Math.sin(q * 5 + ph));
      const y = y0 + L * q * (0.3 - 0.55 * q);
      const node = rand() < 0.07;
      put(x, y, jit(0.08 * q), ROLE.SUB, node ? 0.45 + 0.3 * rand() : (0.07 + 0.16 * rand()) * (1 - 0.3 * q), node ? 0.7 + 0.25 * rand() : (0.2 + 0.26 * rand()) * (1 - 0.4 * q), 0.55);
    }
  }
  {
    const nD = n(FRAC.innerDust);
    for (let k = 0; k < nD; k++) {
      const t = 0.06 + 0.88 * rand();
      const w = OUTER.W * ogee(t, OUTER.a, OUTER.b) * 0.88;
      const x = (rand() * 2 - 1) * w * Math.pow(rand(), 0.35);
      const y = TOP_Y + (OUTER.yEnd - TOP_Y) * t + jit(0.03);
      put(x, y, jit(0.1), ROLE.SUB, 0.05 + 0.09 * rand(), 0.1 + 0.18 * rand(), 0.42);
    }
  }

  // ==========================================================================
  // 2ª CAPA (ondas de sincronía) — SIN CAMBIOS.
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
