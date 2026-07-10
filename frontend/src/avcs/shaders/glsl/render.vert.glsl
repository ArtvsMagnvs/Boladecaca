// Vertex de RENDER (ShaderMaterial normal, NO envuelto por GPGPU).
// AQUÍ SÍ se declara texturePosition (es la textura de salida del GPGPU que
// muestreamos por 'aRef' — el uv del texel de cada partícula).

uniform sampler2D texturePosition;
uniform sampler2D uGenome;
uniform float uPointSize;
uniform float uBreathScale;
uniform float uDpr;

attribute vec2 aRef; // uv del texel de esta partícula en la textura de simulación

varying float vRole;
varying float vSeed;

void main() {
  vec4 P = texture2D(texturePosition, aRef);
  vec4 G = texture2D(uGenome, aRef);
  vRole = G.g;
  vSeed = G.r;

  vec4 mv = modelViewMatrix * vec4(P.xyz, 1.0);
  // El núcleo (role~1) es algo más grande y pulsa con la respiración.
  float base = mix(uPointSize, uPointSize * 1.5, step(0.75, vRole));
  base *= mix(1.0, uBreathScale, step(0.25, vRole));
  gl_PointSize = clamp(base * uDpr / max(0.1, -mv.z), 1.0, 64.0);
  gl_Position = projectionMatrix * mv;
}
