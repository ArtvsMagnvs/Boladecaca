// AVCS — FUENTE DE VERDAD de la geometría de la escena (semilla-logo + segunda
// capa de ondas de sincronía). Genera, por partícula, su GENOMA (seed, rol,
// tamaño, brillo) y su ANCLA (posición objetivo + fuerza de anclaje).
//
// LA SEMILLA ES EL LOGO DE AITHERA. Su forma está medida píxel a píxel sobre la
// imagen de referencia oficial ("semilla diseñada con partículas.png") y NO se
// reinterpreta. Coordenadas de la imagen (1254px) → proporciones normalizadas a
// la altura H del logo:
//
//   · Silueta = LÁGRIMA OJIVAL (cúpula de cebolla/llama), NO elipse:
//     aguja alta y cóncava arriba (t^a con a>1 = arranca pegada al eje),
//     panza máxima al ~62% de la altura, convergencia en tallo abajo.
//   · Contorno EXTERIOR:  半width máx = 0.31·H, ancla t*=0.62 (beta a=1.86 b=1.14)
//   · Contorno INTERIOR:  半width máx = 0.21·H, mismo vértice arriba, cierra antes
//   · ALMENDRA (vesica) alrededor del núcleo: del 34% al 70% de la altura,
//     半width 0.10·H — sus puntas mueren EN el eje (conectan); los contornos NO
//     tocan la almendra ni el núcleo (no conectan).
//   · NÚCLEO en el 53% de la altura: sol diminuto — centro blanco-cálido →
//     oro → borde ámbar profundo (profundidad por gradiente), polvo finísimo,
//     ANILLO fino nítido a r=0.084·H + arco parcial débil a r=0.103·H + radios sutiles.
//   · EJE vertical completo; tallo inferior brillante (fuente) que acaba en una
//     SALPICADURA de polvo en el suelo (montículo ancho y fino).
//   · TENDRILS tipo sauce desde los contornos (mitad inferior, caen fuera-abajo)
//     + finos arcos arriba; nodos-constelación; puntas con chispas teal.
//   · POLVO interior tenue rellenando la lágrima (no está vacía por dentro).
//
// El comportamiento (roles/anclaje/wander) NO cambia aquí: la forma se mantiene
// y la vida viene de escala global, giro del núcleo, latido, twinkle y wander.
//
// Genoma (RGBA): r=seed(0-1), g=rol, b=tamaño(0-1), a=brillo(0-1)
// Ancla  (RGBA): xyz=posición objetivo, w=fuerza de anclaje(0-1)

import { mulberry32 } from "./prng";

export interface SceneGeometry {
  genome: Float32Array<ArrayBuffer>;
  anchor: Float32Array<ArrayBuffer>;
}

// --- Roles (mismos umbrales que render.frag / fields.glsl — NO tocar) ---
export const ROLE = {
  STAR: 0.1, // partícula suelta (starfield/espacio)
  FIELD: 0.25, // nube de campo (empujada por ondas)
  RING: 0.38, // anillo concéntrico (2ª capa)
  BAND: 0.52, // banda lateral en S (2ª capa)
  SUB: 0.66, // tendril / polvo interior / salpicadura del logo
  PETAL: 0.8, // contornos + almendra + eje del logo
  CORERING: 0.9, // anillo fino del núcleo
  CORE: 1.0, // núcleo (sol)
} as const;

// ============================================================================
// MEDIDAS DEL LOGO (de la imagen de referencia; calibrables ±10%, no más —
// más allá se pierde la identidad).
// ============================================================================
const TOP_Y = 1.4; // vértice superior (aguja)
const GROUND_Y = -1.3; // suelo (salpicadura)
const CORE_Y = -0.05; // centro del núcleo (53% de altura)

// Contornos ojivales: perfil beta t^a·(1-t)^b (pico en a/(a+b)).
const OUTER = { yEnd: -0.95, W: 0.84, a: 1.86, b: 1.14 }; // 半width máx 0.31·H
const INNER = { yTop: 1.36, yEnd: -0.88, W: 0.56, a: 1.8, b: 1.2 }; // 0.21·H

// Almendra (vesica) alrededor del núcleo.
const ALMOND = { yTop: 0.47, yBot: -0.53, W: 0.27, pow: 1.35 };

// Núcleo.
const CORE_HOT_R = 0.04; // centro blanco-cálido
const CORE_GLOW_R = 0.15; // polvo del sol
const CORE_RING_R = 0.227; // anillo fino nítido
const CORE_ARC_R = 0.278; // arco parcial débil exterior

// Reparto del pool (fracciones del total). La 2ª capa (ring/band/star) NO cambia.
const FRAC = {
  outer: 0.055,
  inner: 0.042,
  almond: 0.03,
  axis: 0.026, // incluye el refuerzo del tallo
  coreHot: 0.011,
  coreGlow: 0.042,
  coreSpokes: 0.004,
  coreRing: 0.012,
  coreArc: 0.003,
  tendrils: 0.073,
  innerDust: 0.033,
  splash: 0.019,
  ring: 0.15,
  band: 0.14,
  star: 0.1,
  // field = resto (~0.26)
};

/** Perfil beta normalizado (pico = 1 en t* = a/(a+b)). Forma ojival. */
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

  // ==========================================================================
  // 1) CONTORNOS OJIVALES (exterior + interior). Comparten el vértice superior
  //    y convergen abajo hacia el tallo. Grosor y brillo varían a lo largo:
  //    más finos/tenues en las puntas, más presentes en la panza; nodos
  //    brillantes salpicados (constelación).
  // ==========================================================================
  const contour = (
    nP: number,
    yTop: number,
    yEnd: number,
    W: number,
    a: number,
    b: number,
    thickBase: number,
    brightBase: number,
  ) => {
    for (let k = 0; k < nP; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nP - 1) + jit(0.012)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = W * ogee(t, a, b);
      const bulge = ogee(t, a, b); // 0..1, 1 en la panza
      // grosor: fino en puntas, pleno en la panza
      const thick = thickBase * (0.35 + 0.75 * bulge);
      const x = side * w + jit(thick);
      const y = yTop + (yEnd - yTop) * t;
      const z = jit(thick * 2.0);
      const node = rand() < 0.055;
      const size = node ? 0.62 + 0.3 * rand() : (0.16 + 0.3 * rand()) * (0.55 + 0.55 * bulge);
      // brillo: refuerzo cerca del vértice (aguja luminosa) y panza viva
      const tipBoost = t < 0.1 ? 0.25 : 0;
      const bright = node
        ? 0.85 + 0.15 * rand()
        : brightBase * (0.5 + 0.45 * bulge) + tipBoost + 0.12 * rand();
      put(x, y, z, ROLE.PETAL, size, bright, 0.93);
    }
  };
  contour(n(FRAC.outer), TOP_Y, OUTER.yEnd, OUTER.W, OUTER.a, OUTER.b, 0.036, 0.9);
  contour(n(FRAC.inner), INNER.yTop, INNER.yEnd, INNER.W, INNER.a, INNER.b, 0.026, 0.78);

  // ==========================================================================
  // 2) ALMENDRA (vesica) alrededor del núcleo. Fina. Sus puntas mueren en el
  //    eje (conectan con él); nunca toca el anillo del núcleo.
  // ==========================================================================
  {
    const nA = n(FRAC.almond);
    for (let k = 0; k < nA; k++) {
      const t = Math.min(0.999, Math.max(0.001, k / (nA - 1) + jit(0.012)));
      const side = k % 2 === 0 ? 1 : -1;
      const w = ALMOND.W * Math.pow(Math.sin(Math.PI * t), ALMOND.pow);
      const x = side * w + jit(0.016);
      const y = ALMOND.yTop + (ALMOND.yBot - ALMOND.yTop) * t;
      const node = rand() < 0.04;
      put(
        x,
        y,
        jit(0.03),
        ROLE.PETAL,
        node ? 0.5 + 0.3 * rand() : 0.12 + 0.22 * rand(),
        node ? 0.85 + 0.15 * rand() : 0.5 + 0.3 * rand(),
        0.93,
      );
    }
  }

  // ==========================================================================
  // 3) EJE VERTICAL completo + tallo-fuente. Brillo por tramos: aguja arriba,
  //    paso por el núcleo, y tallo inferior MUY vivo que se abre en la base.
  // ==========================================================================
  {
    const nAx = n(FRAC.axis);
    for (let k = 0; k < nAx; k++) {
      const t = rand(); // 0 arriba → 1 suelo
      const y = TOP_Y + (GROUND_Y - TOP_Y) * t;
      // el tallo (último 18%) se abre ligeramente hacia la base (pie de fuente)
      const flare = t > 0.82 ? (t - 0.82) * 0.5 : 0;
      const x = jit(0.012 + flare * 0.3);
      let bright = 0.4 + 0.15 * rand();
      let size = 0.12 + 0.2 * rand();
      if (t < 0.06) bright += 0.35; // aguja
      if (Math.abs(y - CORE_Y) < 0.3) bright += 0.2; // paso por el núcleo
      if (t > 0.82) {
        bright += 0.4; // tallo-fuente brillante
        size += 0.1;
      }
      put(x, y, jit(0.02), ROLE.PETAL, size, bright, 0.93);
    }
  }

  // ==========================================================================
  // 4) NÚCLEO — el sol diminuto con profundidad.
  //    centro blanco-cálido → polvo oro → borde ámbar profundo (el gradiente
  //    lo pinta render.frag usando el brillo del genoma como "profundidad").
  // ==========================================================================
  {
    // 4a. centro blanco-cálido (denso, minúsculo)
    const nHot = n(FRAC.coreHot);
    for (let k = 0; k < nHot; k++) {
      const r = CORE_HOT_R * Math.sqrt(rand());
      const a = rand() * Math.PI * 2;
      put(Math.cos(a) * r, CORE_Y + Math.sin(a) * r, jit(0.015), ROLE.CORE, 0.24 + 0.2 * rand(), 0.96 + 0.04 * rand(), 1.0);
    }
    // 4b. polvo del sol: denso al centro, se apaga hacia el borde (profundidad)
    const nGlow = n(FRAC.coreGlow);
    for (let k = 0; k < nGlow; k++) {
      const r = CORE_GLOW_R * Math.pow(rand(), 0.45);
      const a = rand() * Math.PI * 2;
      const depth = 1 - r / CORE_GLOW_R; // 1 centro → 0 borde
      put(
        Math.cos(a) * r,
        CORE_Y + Math.sin(a) * r * 0.96,
        jit(0.05) * (1 - depth * 0.5),
        ROLE.CORE,
        0.08 + 0.16 * rand(),
        0.34 + 0.62 * depth + 0.06 * rand(), // brillo = profundidad → gradiente de color
        1.0,
      );
    }
    // 4c. radios sutiles (rosa de brújula muy tenue entre el sol y el anillo)
    const nSp = n(FRAC.coreSpokes);
    for (let k = 0; k < nSp; k++) {
      const spoke = Math.floor(rand() * 8);
      const a = (spoke / 8) * Math.PI * 2 + jit(0.06);
      const r = CORE_GLOW_R * 0.6 + (CORE_RING_R * 0.94 - CORE_GLOW_R * 0.6) * rand();
      put(Math.cos(a) * r, CORE_Y + Math.sin(a) * r, jit(0.01), ROLE.CORE, 0.07 + 0.1 * rand(), 0.3 + 0.15 * rand(), 1.0);
    }
    // 4d. ANILLO fino nítido (define el núcleo)
    const nR = n(FRAC.coreRing);
    for (let k = 0; k < nR; k++) {
      const a = (k / nR) * Math.PI * 2 + jit(0.02);
      const arcGlow = 0.6 + 0.4 * Math.sin(a * 2 + 0.7); // brillo desigual por arcos
      put(
        Math.cos(a) * (CORE_RING_R + jit(0.008)),
        CORE_Y + Math.sin(a) * (CORE_RING_R + jit(0.008)),
        jit(0.012),
        ROLE.CORERING,
        0.11 + 0.13 * rand(),
        (0.62 + 0.3 * rand()) * arcGlow,
        1.0,
      );
    }
    // 4e. arco parcial débil exterior (solo un sector, como en la referencia)
    const nArc = n(FRAC.coreArc);
    for (let k = 0; k < nArc; k++) {
      const a = -0.5 + 2.2 * (k / nArc) + jit(0.03); // sector superior-derecho
      put(
        Math.cos(a) * (CORE_ARC_R + jit(0.006)),
        CORE_Y + Math.sin(a) * (CORE_ARC_R + jit(0.006)),
        jit(0.01),
        ROLE.CORERING,
        0.08 + 0.1 * rand(),
        0.24 + 0.14 * rand(),
        1.0,
      );
    }
  }

  // ==========================================================================
  // 5) TENDRILS tipo sauce — nacen DE los contornos (mitad inferior), caen
  //    hacia fuera-abajo con vaivén y horquillas; finos arcos arriba. Nodos
  //    constelación; puntas con chispas teal (lo decide render.frag por seed).
  // ==========================================================================
  {
    const nT = n(FRAC.tendrils);
    const LOWER_T0 = [0.5, 0.57, 0.63, 0.69, 0.75, 0.8, 0.85];
    const UPPER_T0 = [0.1, 0.17, 0.25];
    const nLower = Math.floor(nT * 0.78);
    // inferiores (por lado, alternando)
    for (let k = 0; k < nLower; k++) {
      const side = k % 2 === 0 ? 1 : -1;
      const strand = Math.floor(k / 2) % LOWER_T0.length;
      const t0 = LOWER_T0[strand] + jit(0.02);
      const x0 = side * OUTER.W * ogee(t0, OUTER.a, OUTER.b);
      const y0 = TOP_Y + (OUTER.yEnd - TOP_Y) * t0;
      const ph = strand * 2.399 + sessionSeed * 0.001;
      const L = 0.55 + 0.5 * ((strand * 0.37) % 1);
      const q = Math.pow(rand(), 0.65); // denso cerca del contorno
      const fork = rand() < 0.4 && q > 0.45 ? 1 : 0; // horquilla a mitad de camino
      const x =
        x0 +
        side * (L * q + 0.1 * Math.sin(q * 6 + ph) + fork * 0.12 * Math.sin(q * 4 + ph * 3));
      const y = y0 - L * q * (0.35 + 0.85 * q) + 0.05 * Math.sin(q * 9 + ph * 2) - fork * 0.08 * q;
      const node = rand() < 0.085;
      put(
        x,
        y,
        jit(0.12 * q),
        ROLE.SUB,
        node ? 0.5 + 0.32 * rand() : (0.1 + 0.24 * rand()) * (1 - 0.3 * q),
        node ? 0.75 + 0.25 * rand() : (0.32 + 0.34 * rand()) * (1 - 0.35 * q),
        0.55,
      );
    }
    // superiores (arcos finos junto a la aguja)
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
      put(
        x,
        y,
        jit(0.08 * q),
        ROLE.SUB,
        node ? 0.45 + 0.3 * rand() : (0.07 + 0.16 * rand()) * (1 - 0.3 * q),
        node ? 0.7 + 0.25 * rand() : (0.2 + 0.26 * rand()) * (1 - 0.4 * q),
        0.55,
      );
    }
  }

  // ==========================================================================
  // 6) POLVO INTERIOR — la lágrima no está vacía: polvo finísimo y tenue,
  //    algo más denso hacia el núcleo y el eje.
  // ==========================================================================
  {
    const nD = n(FRAC.innerDust);
    for (let k = 0; k < nD; k++) {
      const t = 0.06 + 0.88 * rand();
      const w = OUTER.W * ogee(t, OUTER.a, OUTER.b) * 0.88;
      const x = (rand() * 2 - 1) * w * Math.pow(rand(), 0.35); // sesgo hacia el eje
      const y = TOP_Y + (OUTER.yEnd - TOP_Y) * t + jit(0.03);
      put(x, y, jit(0.1), ROLE.SUB, 0.05 + 0.09 * rand(), 0.1 + 0.18 * rand(), 0.42);
    }
  }

  // ==========================================================================
  // 7) SALPICADURA en el suelo — el tallo-fuente aterriza en un montículo
  //    ancho y fino de polvo ámbar tenue + chispas que saltan a los lados.
  // ==========================================================================
  {
    const nS = n(FRAC.splash);
    for (let k = 0; k < nS; k++) {
      const spark = rand() < 0.16;
      const x = spark
        ? (rand() < 0.5 ? -1 : 1) * (0.28 + 0.32 * rand())
        : (rand() + rand() + rand() - 1.5) * 0.28; // gaussiana ancha
      const y = GROUND_Y + (spark ? 0.01 + 0.05 * rand() : 0.06 * rand() * rand());
      put(x, y, jit(0.08), ROLE.SUB, spark ? 0.2 + 0.2 * rand() : 0.05 + 0.1 * rand(), spark ? 0.45 + 0.25 * rand() : 0.2 + 0.24 * rand(), 0.72);
    }
  }

  // ==========================================================================
  // 2ª CAPA (ondas de sincronía) — SIN CAMBIOS respecto a la iteración anterior.
  // ==========================================================================

  // --- ANILLOS CONCÉNTRICOS ---
  const nRing = n(FRAC.ring);
  const ringRadii = [1.55, 1.95, 2.4, 2.9, 3.45];
  for (let k = 0; k < nRing; k++) {
    const ri = k % ringRadii.length;
    const radius = ringRadii[ri] * (1 + jit(0.02));
    const a = rand() * Math.PI * 2;
    const thin = 0.55 + 0.45 * (Math.sin(a * (2 + ri) + ri) * 0.5 + 0.5);
    const node = rand() < 0.05;
    put(
      Math.cos(a) * radius,
      Math.sin(a) * radius + 0.04,
      jit(0.1),
      ROLE.RING,
      node ? 0.55 + 0.3 * rand() : 0.12 + 0.28 * rand(),
      (node ? 0.8 + 0.2 * rand() : 0.35 + 0.4 * rand()) * thin,
      0.45,
    );
  }

  // --- BANDAS LATERALES en S tumbada ---
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
    put(
      x,
      y,
      z,
      ROLE.BAND,
      node ? 0.55 + 0.35 * rand() : 0.12 + 0.28 * rand(),
      node ? 0.8 + 0.2 * rand() : 0.28 + 0.4 * rand(),
      0.47,
    );
  }

  // --- STARFIELD ---
  const nStar = n(FRAC.star);
  for (let k = 0; k < nStar; k++) {
    const x = jit(11);
    const y = jit(7.5);
    const z = jit(5) - 1.5;
    const big = rand() < 0.06;
    put(x, y, z, ROLE.STAR, big ? 0.55 + 0.4 * rand() : 0.06 + 0.18 * rand(), big ? 0.85 + 0.15 * rand() : 0.18 + 0.35 * rand(), 0.06);
  }

  // --- CAMPO: el resto, cascarón alrededor de la semilla ---
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
