// Biblioteca de campos de fuerza (doc 13 §5) + sumador ponderado.
// Depende de noise.glsl + curl.glsl (incluidos antes) y de los uniforms del bus
// (declarados en el preámbulo del sim shader, antes de este chunk).
//
// F_root/F_branch/F_mandala/F_channel son stubs (return vec3(0.0)) en S1: la
// FIRMA y el índice de peso ya existen; MVP1 rellena el cuerpo sin tocar nada más.

vec3 fBreath(vec3 p) {
  vec3 d = p - uSeedCenter;
  float r = length(d);
  return (d / max(r, 1e-4)) * uBreath; // radial; el signo de uBreath expande/contrae
}

vec3 fCurl(vec3 p) {
  return curlNoise(p * uCurlFreq + vec3(uSessionSeed * 13.0) + vec3(uTime * uCurlFlow));
}

vec3 fReturn(vec3 p, vec3 anchor) {
  return (anchor - p); // tira cada partícula a su ancla (SIEMPRE activo)
}

vec3 fSelf(vec3 p, float pseed) {
  return curlNoise(p * 3.1 + vec3(pseed * 97.0) + vec3(uTime * 0.12)) * 0.5;
}

vec3 fGravity() {
  return uGravityDir;
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
      // Frente NO circular: deformación angular FBM (2-3 octavas, 6-12%). doc 13 §7.2
      float deform = 0.09 * fbm3(vec3(theta * 1.5, phi * 1.5, uWaveSeed[i]));
      float frontR = uWaveR[i] * (1.0 + deform);
      float band = exp(-pow((r - frontR) / uWaveThickness, 2.0)); // cáscara gaussiana = presión
      f += uWaveAmp[i] * band;
    }
  }
  return dir * f; // empuja hacia fuera al pasar el frente
}

// --- Stubs S1 (firma real, cuerpo en MVP1) ---
vec3 fRoot(vec3 p, vec3 anchor, float role) { return vec3(0.0); }
vec3 fBranch(vec3 p, vec3 anchor, float role) { return vec3(0.0); }
vec3 fMandala(vec3 p) { return vec3(0.0); }
vec3 fChannel(vec3 p) { return vec3(0.0); }

// Suma ponderada + mezcla con el factor de sincronía S (doc 13 §5).
// G = genoma (r=seed, g=rol, b=radioAncla). uWeights en orden FIELD_ORDER.
vec3 computeForce(vec3 pos, vec4 G, vec3 anchor) {
  float pseed = G.r;
  float role = G.g;

  // OJO: 'common' es palabra RESERVADA en GLSL — usar fCommon.
  vec3 fCommon = vec3(0.0);
  fCommon += uWeights[0] * fBreath(pos);
  fCommon += uWeights[1] * fWave(pos);
  fCommon += uWeights[2] * fCurl(pos);
  fCommon += uWeights[3] * fGravity();
  fCommon += uWeights[4] * fRoot(pos, anchor, role);
  fCommon += uWeights[5] * fBranch(pos, anchor, role);
  fCommon += uWeights[6] * fMandala(pos);
  fCommon += uWeights[7] * fChannel(pos);
  fCommon += uWeights[8] * fReturn(pos, anchor);

  vec3 selfF = fSelf(pos, pseed);

  // S alto = coherencia (campo común); S bajo = cada partícula "va a su bola".
  vec3 force = mix(selfF, fCommon, uSync) + uWeights[9] * selfF * (1.0 - uSync * 0.5);

  // La semilla (role >= 0.5) se pega más a su ancla: la forma no se dispersa.
  force = mix(force, fReturn(pos, anchor) * 1.6, step(0.25, role) * 0.55);

  return force;
}
