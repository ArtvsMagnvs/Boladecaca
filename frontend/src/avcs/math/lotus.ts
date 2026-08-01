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
  // [PU5f] SUB-ROLES de la semilla. El fragment pinta TODO el tramo
  // (0.73, 0.85] con el mismo color de contorno, y dentro de ese tramo el tono
  // depende de `vSeed`, no del rol — así que separar las líneas aquí NO cambia
  // ni un píxel de color. Sirve para que la animación de habla pueda girar unas
  // líneas y otras no, que es justo lo que hacía falta y no era posible con un
  // único ROLE.PETAL para todas.
  PETAL_AXIS: 0.745,     // eje vertical — nunca gira
  PETAL_OUTER: 0.765,    // contorno exterior — nunca gira
  PETAL_INNER: 0.795,    // 2.º contorno desde fuera — gira a la derecha al hablar
  PETAL_ALMOND: 0.835,   // almendra (la de dentro) — gira a la izquierda, ×7
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

// [doc 35 PU5] Anillos de sincronía — EXPORTADOS porque `fields.glsl` replica
// estos mismos valores para identificar a qué anillo pertenece cada partícula
// (y girarlo). Fuente de verdad aquí; el shader lleva el comentario cruzado.
// [PU6a-bis v2] Radios ×0.88 (petición del usuario): el anillo externo pasaba
// por DETRÁS de los botones del dock; ahora su borde inferior queda un poco
// por encima de ellos. El encuadre (CONTENT_HALF_*) NO se toca — reducir el
// contenido garantizado habría agrandado la semilla y deshecho el ajuste.
export const RING_RADII = [1.36, 1.72, 2.11, 2.55, 3.04] as const;
export const RING_CENTER_Y = 0.04;
/** Rigidez de los anillos (0.93 = la del logo). 0.88 ≈ 95% → mantienen la
 *  forma de círculo sin quedar completamente muertos. */
export const RING_BIND = 0.88;
/** [PU5c] Brillo de los anillos ×1.5 — se veían apagados frente al logo.
 *  `put` clampa a 1, así que los más brillantes saturan (los nodos ya estaban
 *  cerca del techo); lo que sube de verdad es el cuerpo del anillo. */
export const RING_BRIGHT = 1.5;
/** [PU5d, bajado a 3% tras verificación en vivo — 7% "es demasiado"] Fracción
 *  de partículas de anillo que son FAROS: substancialmente más grandes y a
 *  brillo pleno, para que se lean como puntos de luz sueltos sin dominar el anillo. */
export const RING_BEACON_FRACTION = 0.03;
/** [PU5d2] Techo del canal `genome.b` (tamaño). Ver la nota en `put()`. */
export const MAX_SIZE_CLASS = 6;
/** [PU5c] Nodos medios (además de los faros): variedad de tamaños sin destacar. */
export const RING_NODE_FRACTION = 0.12;
/** [PU5c] Alcance lateral de las ondas de sincronía. El contenido garantizado
 *  en cuadro llega a x=±4.2 (CONTENT_HALF_WIDTH); con 7.6 las ondas SALEN de
 *  cuadro por los lados, que es justo lo pedido: que lleguen al final de la
 *  pantalla en vez de morir a media altura. El `edgeFalloff` del fragment las
 *  desvanece suavemente en el borde, así que no se ve un corte. */
export const BAND_REACH = 7.6;

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
  innerDust: 0.03,
  ring: 0.19,   // [PU5] +0.04 heredado de los tendrils eliminados
  band: 0.14,
  star: 0.14,   // [PU6a-bis v2] 0.10 → 0.14: el starfield ahora cubre ±9.5 en x
  // field = resto
};

/** smoothstep clásico (0 por debajo de e0, 1 por encima de e1, curva suave). */
function smoothstep01(e0: number, e1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

/** Perfil beta normalizado (pico=1 en a/(a+b)) → ANCHURA ojival de la silueta. */
function ogee(t: number, a: number, b: number): number {
  if (t <= 0 || t >= 1) return 0;
  const tp = a / (a + b);
  const norm = Math.pow(tp, a) * Math.pow(1 - tp, b);
  return (Math.pow(t, a) * Math.pow(1 - t, b)) / norm;
}

/** Suma de las fracciones que forman EL LOGO (semilla): contornos, almendra,
 *  eje, núcleo completo, tendrils y polvo interior. El resto de `FRAC` (ring,
 *  band, star) + el `field` implícito son la 2ª capa: decoración y fondo.
 *  Calculado a partir de FRAC, no a mano, para que no se desincronice si algún
 *  valor cambia. */
const LOGO_BASE =
  FRAC.outer + FRAC.inner + FRAC.almond + FRAC.axis + FRAC.coreHot +
  FRAC.coreGlow + FRAC.coreSpokes + FRAC.coreRing + FRAC.coreArc +
  FRAC.innerDust;

export function buildSceneGeometry(
  count: number,
  restRadius: number,
  seedFrac: number,
  sessionSeed: number,
): SceneGeometry {
  const rand = mulberry32(sessionSeed | 0);
  const genome = new Float32Array(count * 4);
  const anchor = new Float32Array(count * 4);
  let i = 0;

  // [doc 35 PU5] El reparto del pool es EL MISMO en los 4 tiers: la 2ª capa
  // (anillos, bandas, starfield) es parte del diseño del AVCS, no relleno
  // prescindible. Se probó dárselo al logo en tiers bajos y el resultado fue
  // perder medio diseño — lo que se compensa por tier es el TAMAÑO y el BRILLO
  // del punto (constants.ts), no dónde caen los puntos.
  void seedFrac;

  const put = (x: number, y: number, z: number, role: number, size: number, bright: number, bind: number) => {
    if (i >= count) return;
    const g = i * 4;
    genome[g] = rand();
    genome[g + 1] = role;
    // [PU5d2] Techo del canal de tamaño: 1 → MAX_SIZE_CLASS. Estaba a 1 y los
    // faros del anillo (que pedían 1.05) YA salían clampeados, así que pedir
    // "×3" no habría cambiado un solo píxel. El canal es un float de textura:
    // subir el techo no cuesta nada y solo afecta a quien de verdad lo pasa.
    // Único otro caso que rozaba el techo: los nodos de contorno del logo
    // (máx 1.06) — pasan de 1.00 a 1.06, un 6% imperceptible.
    genome[g + 2] = Math.max(0.04, Math.min(MAX_SIZE_CLASS, size));
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
  const contour = (role: number, nP: number, yTop: number, yEnd: number, W: number, a: number, b: number, thickBase: number, brightBase: number, topFloor: number, botFloor: number) => {
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
      put(x, y, z, role, size, bright, 0.93);
    }
  };
  contour(ROLE.PETAL_OUTER, n(FRAC.outer), TOP_Y, OUTER.yEnd, OUTER.W, OUTER.a, OUTER.b, OUTER.thick, OUTER.bright, OUTER.topFloor, OUTER.botFloor);
  contour(ROLE.PETAL_INNER, n(FRAC.inner), INNER.yTop, INNER.yEnd, INNER.W, INNER.a, INNER.b, INNER.thick, INNER.bright, INNER.topFloor, INNER.botFloor);

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
      put(x, y, tri(thick * 1.2), ROLE.PETAL_ALMOND, node ? 0.6 + 0.32 * rand() : (0.2 + 0.34 * rand()) * (0.5 + 0.7 * thickN), node ? 0.9 + 0.1 * rand() : INNER.bright * (0.55 + 0.45 * thickN), 0.93);
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
      put(x, y, jit(0.02), ROLE.PETAL_AXIS, size, bright, 0.93);
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
  // 5) [doc 35 PU5, 2026-07-30] TENDRILS/RAÍCES — ELIMINADOS por decisión del
  //    usuario: eran las líneas doradas que sobresalían del contorno del logo.
  //    Su parte del pool (`FRAC.tendrils`) se reasignó a los anillos (que ganan
  //    definición) y el resto lo absorbe el campo de fondo. El polvo interior
  //    (abajo) SÍ se mantiene: está DENTRO de la silueta, no sobresale.
  // ==========================================================================
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
  // [doc 35 PU5, 2026-07-30] Los 5 anillos de sincronía deben LEERSE COMO
  // CÍRCULOS, no como nubes: el usuario los veía demasiado deformados.
  //   · `RING_BIND` 0.45 → 0.88 = ~95% de la rigidez del logo (0.93). No es
  //     rígido del todo a propósito (siguen vivos), pero recuperan la forma.
  //   · dispersión en z 0.1 → 0.028: casi planos, para que se lean como una
  //     LÍNEA circular y no como un toro grueso visto en perspectiva.
  //   · el radio conserva su micro-jitter (±1%): un círculo perfecto de
  //     compás no pega con el resto del AVCS.
  // `RING_RADII` y `RING_CENTER_Y` los REPLICA fields.glsl para saber a qué
  // anillo pertenece cada partícula y girarlo — si cambian aquí, hay que
  // cambiarlos allí (comentario cruzado en ambos sitios).
  const nRing = n(FRAC.ring);
  const ringRadii = RING_RADII;
  for (let k = 0; k < nRing; k++) {
    const ri = k % ringRadii.length;
    const radius = ringRadii[ri] * (1 + jit(0.02));
    const a = rand() * Math.PI * 2;
    const thin = 0.55 + 0.45 * (Math.sin(a * (2 + ri) + ri) * 0.5 + 0.5);
    // [PU5d] TRES escalones de tamaño en el anillo, no dos:
    //   · FAROS (7%): claramente mayores y a brillo pleno — se leen como
    //     puntos de luz sueltos ensartados en el círculo.
    //   · nodos medios (~12%): dan textura sin destacar.
    //   · resto: el polvo fino del anillo.
    // Un solo `rand()` decide el escalón (los rangos no se solapan), así que la
    // proporción es exacta y no depende del orden de las tiradas.
    const roll = rand();
    const beacon = roll < RING_BEACON_FRACTION;
    const node = !beacon && roll < RING_BEACON_FRACTION + RING_NODE_FRACTION;
    // [PU5d2] Nodos medios −20% (0.5 → 0.40) y faros MÁS GRANDES.
    //
    // Sobre el tamaño de los faros: se pidió "×3", se implementó literal y el
    // resultado (visto en el previsualizador) se comía el diseño — los anillos
    // pasaban a ser cadenas de bolas gruesas y el logo quedaba aplastado. El
    // motivo es que lo que se estaba viendo YA salía topado a 1.0 por el clamp
    // del genoma, así que un ×3 real sobre el valor pedido (1.05→3.15) acababa
    // siendo ×3-4,6 en RADIO = ×10-20 en ÁREA, con un 7% de las partículas del
    // anillo. Aquí queda en ~×1,3 en radio (≈×1,7 en área), que es donde los
    // faros se leen como puntos de luz destacados sin robarle el papel al logo.
    // Es un número de una sola línea: subirlo o bajarlo es trivial.
    //
    // Nota: qué partícula es faro, nodo o polvo se decide UNA vez aquí, en el
    // genoma, y no cambia nunca — lo que varía en pantalla es su tamaño
    // instantáneo (twinkle) y su posición. Por eso las proporciones 7%/12% se
    // mantienen exactas por mucho que todo esté en movimiento.
    const size = beacon ? 1.30 + 0.45 * rand() : node ? 0.40 + 0.24 * rand() : 0.11 + 0.26 * rand();
    const bright = (beacon ? 1.0 : node ? 0.7 + 0.2 * rand() : 0.35 + 0.4 * rand())
      * (beacon ? 1.0 : thin)   // el faro no se atenúa con la modulación del anillo
      * RING_BRIGHT;
    put(Math.cos(a) * radius, Math.sin(a) * radius + RING_CENTER_Y, jit(0.028), ROLE.RING, size, bright, RING_BIND);
  }

  // [PU5c] ONDAS DE SINCRONÍA — ahora LARGAS: se extienden hasta BAND_REACH
  // (7.6), muy por encima del contenido garantizado en cuadro (4.2), así que
  // cruzan la pantalla de lado a lado y se desvanecen en los bordes con el
  // `edgeFalloff` del fragment en vez de terminar en seco a media pantalla.
  // La ONDULACIÓN viva (movimiento en S y el origen que sube y baja cerca del
  // núcleo) la pone `fields.glsl::targetAnchor`; aquí solo nace la forma base.
  const nBand = n(FRAC.band);
  for (let k = 0; k < nBand; k++) {
    const sideLeft = k % 2 === 0 ? 1 : -1;
    const t = Math.pow(rand(), 0.62);          // algo más de densidad lejos del centro
    const x = sideLeft * (0.45 + t * BAND_REACH);
    // [PU5d2] El perfil base es ANTISIMÉTRICO (`sin` de x), así que cerca del
    // centro un lado arrancaba por encima y el otro por debajo — se veía como
    // dos ondas descolocadas en vez de una que nace del núcleo. `grow` lo anula
    // en el centro y lo deja crecer al alejarse: ambas ramas salen del MISMO
    // punto y se abren desde ahí. El margen de vaivén arriba/abajo lo pone
    // `fields.glsl` (`originY * nearCore`), que sigue intacto.
    const grow = smoothstep01(0.0, 1.7, Math.abs(x));
    const yBase = (Math.sin(x * 0.85) * 0.5 + Math.sin(x * 1.9 + 1.0) * 0.2) * grow;
    const spread = 0.1 + t * 0.3;
    const y = yBase + jit(spread);
    const z = jit(0.22 + t * 0.28);
    const node = rand() < 0.09;
    put(x, y, z, ROLE.BAND, node ? 0.55 + 0.35 * rand() : 0.12 + 0.28 * rand(), node ? 0.8 + 0.2 * rand() : 0.28 + 0.4 * rand(), 0.47);
  }

  // [PU6a-bis v2] El starfield cubre TODA la pantalla, también en monitores
  // anchos. Con jit(11) (x=±5.5) quedaban FRANJAS laterales vacías: el
  // fit-contain garantiza la ALTURA del contenido (halfH visible ≈ 3.99), así
  // que en 16:9 el semiancho visible es ≈7.1 y en 21:9 ≈9.3 — más allá de los
  // ±5.5 donde morían las estrellas. Con jit(19) (±9.5) se cubre hasta 21:9.
  // FRAC.star subió 0.10 → 0.14 para que la densidad no caiga al repartir el
  // mismo polvo en más área (lo cede el campo implícito, que es el resto).
  const nStar = n(FRAC.star);
  for (let k = 0; k < nStar; k++) {
    const big = rand() < 0.06;
    put(jit(19), jit(9.2), jit(5) - 1.5, ROLE.STAR, big ? 0.55 + 0.4 * rand() : 0.06 + 0.18 * rand(), big ? 0.85 + 0.15 * rand() : 0.18 + 0.35 * rand(), 0.06);
  }

  while (i < count) {
    const rr = restRadius * (0.9 + 1.4 * rand());
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    put(rr * Math.sin(ph) * Math.cos(th), rr * Math.sin(ph) * Math.sin(th), rr * Math.cos(ph) * 0.6, ROLE.FIELD, 0.1 + 0.22 * rand(), 0.2 + 0.3 * rand(), 0.22);
  }

  return { genome, anchor };
}
