// Curl noise (turbulencia orgánica SIN divergencia) — F_curl (doc 13 §5).
// Depende de snoise (noise.glsl, incluido antes).

vec3 snoiseVec3(vec3 x) {
  return vec3(
    snoise(x),
    snoise(x + vec3(19.19, 33.71, 47.53)),
    snoise(x + vec3(43.83, 11.17, 91.29))
  );
}

vec3 curlNoise(vec3 p) {
  const float e = 0.1;
  vec3 dx = vec3(e, 0.0, 0.0);
  vec3 dy = vec3(0.0, e, 0.0);
  vec3 dz = vec3(0.0, 0.0, e);

  vec3 px0 = snoiseVec3(p - dx); vec3 px1 = snoiseVec3(p + dx);
  vec3 py0 = snoiseVec3(p - dy); vec3 py1 = snoiseVec3(p + dy);
  vec3 pz0 = snoiseVec3(p - dz); vec3 pz1 = snoiseVec3(p + dz);

  float x = (py1.z - py0.z) - (pz1.y - pz0.y);
  float y = (pz1.x - pz0.x) - (px1.z - px0.z);
  float z = (px1.y - px0.y) - (py1.x - py0.x);

  return vec3(x, y, z) / (2.0 * e);
}
