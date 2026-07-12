// Vertex de RENDER (ShaderMaterial normal). Tamaño y brillo POR PARTÍCULA
// (genome.b/.a), parpadeo estelar (twinkle), y atenuación/encogimiento cuando la
// partícula "viaja" lejos de su ancla (closeness) — así una partícula que se
// libera del logo se hace pequeña/tenue y al volver recupera su tamaño.

uniform sampler2D texturePosition;
uniform sampler2D uGenome;
uniform sampler2D uAnchor;
uniform float uPointSize;
uniform float uDpr;
uniform float uTime;

attribute vec2 aRef;

varying float vRole;
varying float vSeed;
varying float vBright;
varying vec2 vNdc; // posición en NDC (-1..1), para el falloff de borde (sin clipping)

void main() {
  vec4 P = texture2D(texturePosition, aRef);
  vec4 G = texture2D(uGenome, aRef);
  vec4 A = texture2D(uAnchor, aRef);
  vRole = G.g;
  vSeed = G.r;
  float sizeClass = G.b;
  float brightClass = G.a;

  // closeness: 1 en el ancla, →0 al viajar (encoge/atenúa)
  float dist = length(P.xyz - A.xyz);
  float closeness = 1.0 - smoothstep(0.06, 0.7, dist);

  // parpadeo estelar por partícula (twinkle)
  float tw = 0.6 + 0.4 * sin(uTime * (0.5 + vSeed * 2.2) + vSeed * 55.0);

  // El tamaño del núcleo lo gobierna el genoma (polvo finísimo + centro denso);
  // sin multiplicador extra — la referencia es dust diminuto, no puntos gordos.
  float sizeMul = sizeClass * mix(0.32, 1.0, closeness) * tw;

  vec4 mv = modelViewMatrix * vec4(P.xyz, 1.0);
  gl_PointSize = clamp(uPointSize * sizeMul * uDpr / max(0.1, -mv.z), 1.0, 70.0);
  vBright = brightClass * mix(0.35, 1.0, closeness) * tw;
  gl_Position = projectionMatrix * mv;
  vNdc = gl_Position.xy / max(1e-4, gl_Position.w);
}
