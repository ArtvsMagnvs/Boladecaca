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

// Cuánto puede "viajar" una partícula según su rol (el núcleo nunca; el logo poco).
float wanderAllow(float role) {
  // role alto (logo/núcleo) → poco; role bajo (campo/estrella) → mucho
  return 1.0 - smoothstep(0.18, 0.95, role);
}

// Ancla transformada: escala de respiración (forma preservada) + giro del núcleo
// + ondulación de las bandas laterales.
vec3 targetAnchor(vec3 a, float role) {
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

  // Bandas laterales (role~0.52): ondulan en el tiempo (S viva).
  if (role > 0.45 && role < 0.6) {
    t.y += sin(t.x * 1.15 + uTime * 0.5) * 0.12;
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
  float effBind = bind * (1.0 - 0.7 * w);

  vec3 target = targetAnchor(A.xyz, role);
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
