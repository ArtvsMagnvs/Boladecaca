// Modelo de fuerzas (doc 13 §5) — reescrito para que la FORMA se MANTENGA y la
// vida venga del comportamiento, no de deformar el logo (feedback del usuario).
//
// Claves:
//  - fReturn tira a un ANCLA transformada (escala de respiración + giro del núcleo
//    + ondulación de bandas), no a un empuje radial que deforma.
//  - wander: cada partícula (salvo el núcleo) se afloja y viaja hacia el campo de
//    vez en cuando, y vuelve — cambiando tamaño/brillo por el camino (render).
//  - fWave (ondas de sincronía) empuja sobre todo a las partículas poco ancladas.
//  - fPulse: vibración del núcleo que se propaga (respiración = latido).
//
// Depende de noise.glsl + curl.glsl y de los uniforms del preámbulo del sim shader.

// Rotación alrededor del eje Y.
vec3 rotY(vec3 v, float a) {
  float c = cos(a); float s = sin(a);
  return vec3(c * v.x + s * v.z, v.y, -s * v.x + c * v.z);
}

// ---------------------------------------------------------------------------
// [doc 35 PU5, 2026-07-30] GIRO DE LOS ANILLOS DE SINCRONÍA
// ---------------------------------------------------------------------------
// Los 5 anillos verdes ruedan SOBRE SÍ MISMOS en el plano de la pantalla (XY),
// manteniendo su posición. Es deliberadamente distinto del anillo del núcleo,
// que gira sobre el eje Y (`rotY`) y por eso, al alinearse con la vista, se ve
// de canto y parece una línea. Aquí se rota en Z: el círculo nunca bascula.
//
// Sentido ALTERNO (el más externo a la derecha, el siguiente a la izquierda…) y
// velocidad progresiva: los interiores giran más rápido.
//
// Estos valores REPLICAN los de `math/lotus.ts` (RING_RADII, RING_CENTER_Y) y
// `constants.ts` (RING_SPIN_RATIO). GLSL no puede importarlos; si cambian allí,
// hay que cambiarlos aquí — comentario cruzado en ambos archivos.
const float RING_CENTER_Y = 0.04;
const float RING_SPIN_RATIO = 1.32;

// [PU5f] Constantes de las animaciones de estado. REPLICAN las de constants.ts
// (GLSL no puede importarlas) — comentario cruzado allí.
const float LISTEN_RING_CONTRACT = 0.86;
const float SPEAK_RING_EXPAND = 1.10;
const float SPEAK_RING_RIPPLE = 0.30;
const float SPEAK_RING_LOBES = 5.0;
const float SPEAK_ALMOND_RATIO = 7.0;
// [PU5f] Longitud de los "relámpagos" que brotan de la semilla al hablar, en
// unidades de escena. La silueta mide ~3,5 de alto, así que 0.18 y 0.35 son
// aproximadamente el "1 cm y 2 cm" pedidos a tamaño de pantalla normal.
const float LIGHTNING_SHORT = 0.18;
const float LIGHTNING_LONG = 0.35;

// Índice del anillo (0 = el más interno … 4 = el más externo) a partir del
// radio del ancla. Los umbrales están a mitad de camino entre radios
// consecutivos de RING_RADII = [1.36, 1.72, 2.11, 2.55, 3.04] ([PU6a-bis v2]
// radios ×0.88 para que el anillo externo quede por encima del dock).
float ringIndex(float r) {
  if (r < 1.54)  return 0.0;
  if (r < 1.915) return 1.0;
  if (r < 2.33)  return 2.0;
  if (r < 2.795) return 3.0;
  return 4.0;
}

// Rotación en el plano XY alrededor del centro de los anillos + el "bloom"
// periódico (los anillos se recogen hacia el núcleo y se vuelven a expandir
// hasta su sitio, como al arrancar). `uRingBloom` va de 0 (reposo, radio
// normal) a 1 (totalmente recogidos) y lo dispara RhythmEngine de vez en
// cuando, no de continuo.
vec3 spinRing(vec3 a) {
  vec2 c = vec2(0.0, RING_CENTER_Y);
  vec2 d = a.xy - c;
  float idx = ringIndex(length(d));

  // --- giro ---
  // Alterna: índice PAR (el externo es el 4) → horario = "hacia la derecha".
  float dir = mod(idx, 2.0) < 0.5 ? -1.0 : 1.0;
  // El externo (idx 4) es el más lento (factor 1); hacia dentro se acelera.
  float speed = pow(RING_SPIN_RATIO, 4.0 - idx);
  float ang = uRingSpin * dir * speed;
  float ca = cos(ang); float sa = sin(ang);
  vec2 r = vec2(ca * d.x - sa * d.y, sa * d.x + ca * d.y);

  // --- bloom periódico: se recogen y se expanden ---
  // Desfase por anillo: los interiores recuperan su sitio antes que los de
  // fuera, así la expansión se lee como una onda que va del centro afuera en
  // vez de un salto simultáneo.
  float envK = clamp(uRingBloom - idx * 0.07, 0.0, 1.0);
  float shrink = mix(1.0, 0.16, envK);

  // --- [PU5f] ESCUCHA: los anillos se recogen hacia el centro ---
  shrink *= mix(1.0, LISTEN_RING_CONTRACT, uListenEnv);

  // --- [PU5f] HABLA: se expanden Y ondulan con la voz, como un frente de radio ---
  // La ondulación depende del ÁNGULO (lóbulos alrededor del anillo) y viaja con
  // el tiempo; su amplitud la manda `uAudioEnv`, la envolvente de voz real, así
  // que el volumen se VE. Cada anillo lleva un desfase (idx) para que no ondulen
  // los cinco al unísono, que parecería un solo objeto rígido.
  float ang2 = atan(r.y, r.x);
  float radio = sin(ang2 * SPEAK_RING_LOBES - uTime * 2.4 + idx * 1.1) * uAudioEnv;
  shrink *= mix(1.0, SPEAK_RING_EXPAND + SPEAK_RING_RIPPLE * radio, uSpeakEnv);

  return vec3(c.x + r.x * shrink, c.y + r.y * shrink, a.z * shrink);
}

// Cuánto puede "viajar" una partícula según su rol (el núcleo nunca; el logo poco).
float wanderAllow(float role) {
  // role alto (logo/núcleo) → poco; role bajo (campo/estrella) → mucho
  return 1.0 - smoothstep(0.18, 0.95, role);
}

// Ancla transformada: escala de respiración (forma preservada) + giro del núcleo
// + ondulación de las bandas laterales.
vec3 targetAnchor(vec3 a, float role, float pseed) {
  // La escala afecta al logo/estructuras cercanas, apenas al starfield lejano.
  float scaleAmt = mix(1.0, uBreathScale, smoothstep(0.2, 0.7, role));
  vec3 t = a * scaleAmt;

  // Núcleo (role~1): gira sobre su eje como un sol.
  if (role > 0.95) {
    t = rotY(t, uCoreSpin);
  } else if (role > 0.85) {
    // anillo del núcleo: gira más despacio
    t = rotY(t, uCoreSpin * 0.5);
  }

  // [doc 35 PU5] Anillos de sincronía (role 0.38): ruedan en el plano de la
  // pantalla, cada uno a su velocidad y en sentido alterno (ver spinRing).
  if (role > 0.31 && role < 0.45) {
    t = spinRing(t);
  }

  // [PU5f] HABLA — giro de las líneas de la semilla. Usan rotY (el MISMO eje
  // que el anillo del núcleo, como se pidió: "giran como gira el círculo
  // alrededor del núcleo", no como los anillos verdes que ruedan en el plano).
  // El ángulo lo pondera `uSpeakEnv`, así que arrancan y se paran suavemente y
  // en reposo no giran en absoluto.
  //   · 2.º contorno desde fuera (PETAL_INNER, 0.795): a la DERECHA.
  //   · almendra (PETAL_ALMOND, 0.835): al REVÉS y ×7 — gira como un bloque
  //     rígido alrededor del eje, "como si fuera un círculo" aunque su silueta
  //     no lo sea, porque la rotación se aplica a la posición ANCLA entera.
  if (role > 0.78 && role < 0.81) {
    t = rotY(t, uSpeakSpin * uSpeakEnv);
  } else if (role > 0.82 && role < 0.85) {
    t = rotY(t, -uSpeakSpin * SPEAK_ALMOND_RATIO * uSpeakEnv);
  }

  // [PU5f] HABLA — RELÁMPAGOS. Parte del polvo interior de la semilla (ROLE.SUB,
  // que vive DENTRO de la silueta) sale disparado en trazos cortos hacia fuera y
  // vuelve. No se crean partículas nuevas: se toman prestadas las que ya hay, que
  // es la misma disciplina del resto del AVCS (nada se spawnea, todo se reasigna).
  //   · `picked` elige un subconjunto DISTINTO en cada ventana temporal, así que
  //     los relámpagos no salen siempre de los mismos sitios.
  //   · `burst` es una envolvente corta: sale rápido y se recoge, como una chispa.
  //   · la longitud alterna entre corta y larga según la partícula.
  //   · todo escalado por `uAudioEnv`: sin voz no hay relámpagos, y cuanto más
  //     fuerte se habla, más largos.
  if (role > 0.59 && role < 0.73 && uSpeakEnv > 0.01) {
    float slot = floor(uTime * 1.6);
    float ph = fract(uTime * 1.6);
    float burst = smoothstep(0.0, 0.06, ph) * (1.0 - smoothstep(0.10, 0.45, ph));
    float picked = step(0.80, fract(pseed * 31.7 + slot * 0.618));
    float len = mix(LIGHTNING_SHORT, LIGHTNING_LONG, step(0.5, fract(pseed * 57.1)));
    vec2 dir = normalize(t.xy - vec2(0.0, -0.05) + vec2(1e-4, 1e-4));
    t.xy += dir * len * burst * picked * uSpeakEnv * (0.35 + 0.65 * uAudioEnv);
  }

  // [PU5c] ONDAS DE SINCRONÍA (role~0.52): ondean de verdad — una S lateral en
  // movimiento, no una curva fija con un temblor. Tres capas:
  //   1. onda VIAJERA principal: `- uTime` hace que el patrón se desplace hacia
  //      fuera, así la banda "corre" en vez de vibrar en el sitio.
  //   2. armónico más corto en sentido contrario → la S nunca se repite igual.
  //   3. amplitud CRECIENTE hacia los extremos: cerca del núcleo la onda nace
  //      contenida y se abre a medida que se aleja.
  if (role > 0.45 && role < 0.6) {
    float ax = abs(t.x);
    // [PU5d] Amplitud MUCHO mayor: antes el máximo era 0.44 y la onda apenas se
    // insinuaba. Con 1.25 en los extremos se lee como una cuerda agitada de
    // verdad. La VELOCIDAD temporal no cambia (0.55/0.31, las de antes): lo que
    // faltaba era recorrido vertical, no ritmo.
    float amp = 0.30 + 0.95 * smoothstep(0.4, 5.2, ax);
    // Frecuencia espacial algo más alta (0.78 → 1.15): con el alcance de 7.6
    // eso da ~1,4 ciclos por lado, así que se ven crestas y valles claros en
    // vez de una sola curva perezosa.
    t.y += sin(t.x * 1.15 - uTime * 0.55) * amp;
    t.y += sin(t.x * 2.4 + uTime * 0.31) * amp * 0.34;
    // El ORIGEN (cerca del núcleo) sube y baja de verdad: dos frecuencias
    // inconmensurables para que el arranque de la onda nunca repita el mismo
    // vaivén, y bastante más recorrido que antes (0.26 → 0.62).
    float nearCore = 1.0 - smoothstep(0.0, 2.6, ax);
    float originY = sin(uTime * 0.21 + 0.7) * 0.42 + sin(uTime * 0.135 + 2.1) * 0.20;
    t.y += originY * nearCore;
    t.x += sin(t.y * 1.5 + uTime * 0.35) * 0.06;
  }
  return t;
}

vec3 fCurl(vec3 p) {
  return curlNoise(p * uCurlFreq + vec3(uSessionSeed * 13.0) + vec3(uTime * uCurlFlow));
}

vec3 fSelf(vec3 p, float pseed) {
  return curlNoise(p * 3.1 + vec3(pseed * 97.0) + vec3(uTime * 0.12)) * 0.5;
}

vec3 fWave(vec3 p) {
  vec3 d = p - uSeedCenter;
  float r = length(d);
  vec3 dir = d / max(r, 1e-4);
  float theta = atan(dir.y, dir.x);
  float phi = acos(clamp(dir.z, -1.0, 1.0));
  float f = 0.0;
  for (int i = 0; i < 6; i++) {
    if (i < uWaveCount) {
      float deform = 0.09 * fbm3(vec3(theta * 1.5, phi * 1.5, uWaveSeed[i]));
      float frontR = uWaveR[i] * (1.0 + deform);
      float band = exp(-pow((r - frontR) / uWaveThickness, 2.0));
      f += uWaveAmp[i] * band;
    }
  }
  return dir * f;
}

// Vibración del núcleo que se propaga hacia fuera (latido). El frente viaja al
// DECAER uPulse (1→0): parte del centro y se expande mientras se desvanece.
vec3 fPulse(vec3 p) {
  vec3 d = p - uSeedCenter;
  float r = length(d);
  float travel = (1.0 - uPulse) * 2.8; // radio del frente
  float ring = exp(-pow((r - travel) / 0.4, 2.0));
  return (d / max(r, 1e-4)) * ring * uPulse;
}

// Latido audio-reactivo (Comunicación, doc 13 §8 "late con la voz"): un halo
// cerca del núcleo que respira con uAudioEnv en continuo, no un pulso Poisson
// discreto — sigue la envolvente de voz frame a frame.
vec3 fVoicePulse(vec3 p) {
  vec3 d = p - uSeedCenter;
  float r = length(d);
  float halo = exp(-pow(r / 0.55, 2.0));
  return (d / max(r, 1e-4)) * halo * uAudioEnv;
}

// Stubs S1 (firma real, cuerpo en MVP1).
vec3 fRoot(vec3 p, vec3 a, float role) { return vec3(0.0); }
vec3 fBranch(vec3 p, vec3 a, float role) { return vec3(0.0); }
vec3 fMandala(vec3 p) { return vec3(0.0); }
vec3 fChannel(vec3 p) { return vec3(0.0); }

// A = ancla (xyz=posición objetivo, w=fuerza de anclaje base).
vec3 computeForce(vec3 pos, vec4 G, vec4 A) {
  float pseed = G.r;
  float role = G.g;
  float bind = A.w;

  // wander: 0..1 lento por partícula (el núcleo nunca viaja).
  float w = 0.5 + 0.5 * sin(uTime * (0.12 + 0.14 * pseed) + pseed * 41.0);
  w *= wanderAllow(role) * step(role, 0.95);

  // [doc 35 PU5] Los ANILLOS de sincronía casi no vagan. Su `bind` alto (0.88)
  // ya los sujeta, pero el wander lo aflojaba hasta un 70% de forma periódica
  // (`effBind` de abajo) y eso era lo que los desdibujaba: dejaban de leerse
  // como círculos. Con 0.12 conservan una vida mínima sin perder la forma —
  // el usuario pidió "un 90% rígido", no rígido del todo.
  if (role > 0.31 && role < 0.45) w *= 0.12;

  float effBind = bind * (1.0 - 0.7 * w);

  vec3 target = targetAnchor(A.xyz, role, pseed);
  vec3 ret = (target - pos) * (7.0 * effBind);

  // curl: más fuerte cuando la partícula está "viajando".
  vec3 curl = fCurl(pos) * (0.25 + 1.1 * w);

  // ondas: empujan sobre todo a lo poco anclado (el logo resiste).
  vec3 wave = fWave(pos) * (1.2 - bind);

  vec3 slf = fSelf(pos, pseed);
  vec3 pulse = fPulse(pos);

  vec3 fCommon = vec3(0.0);
  fCommon += uWeights[2] * curl;
  fCommon += uWeights[1] * wave;
  fCommon += uWeights[8] * ret;
  // Gravedad (Escucha/Comunicación, doc 13 §4): tira sobre todo de lo poco
  // anclado (campo/tendrils → "raíces insinuadas"), casi nada del logo/núcleo,
  // para no deformar la identidad (misma lección que targetAnchor()).
  fCommon += uWeights[3] * uGravityDir * mix(0.2, 1.0, wanderAllow(role));
  fCommon += uWeights[4] * fRoot(pos, A.xyz, role);
  fCommon += uWeights[5] * fBranch(pos, A.xyz, role);
  fCommon += uWeights[6] * fMandala(pos);
  fCommon += uWeights[7] * fChannel(pos);

  // respiración = latido (pulso Poisson) + halo audio-reactivo continuo
  // ("late con la voz"), ambos ponderados por el peso 'breath'.
  fCommon += uWeights[0] * (pulse * 2.0 + fVoicePulse(pos) * 1.6);

  // mezcla con sincronía + ruido propio (self)
  vec3 force = mix(slf, fCommon, uSync) + uWeights[9] * slf * (1.0 - uSync * 0.5);
  return force;
}
