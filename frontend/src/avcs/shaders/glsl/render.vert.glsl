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

  // [PU5d] EL "APAGÓN" GLOBAL — causa y arreglo.
  // Síntoma: el AVCS entero bajaba de intensidad y luego volvía de golpe.
  // Causa: los suelos de `closeness` de abajo eran 0.35 (brillo) y 0.32
  // (tamaño), así que una partícula alejada de su ancla perdía ~65% de brillo
  // Y ~68% de tamaño — y como la luz que aporta es área × opacidad, eso es
  // caer a ~1/9 de su luz. Cada latido (`fPulse`) y cada onda de sincronía
  // desplazan MUCHAS partículas A LA VEZ, así que la caída era colectiva:
  // apagón, y al recuperar sus anclas, destello.
  // No es un bug de un caso raro: es el comportamiento normal del sistema
  // amplificado por dos gestos globales que ocurren cada pocos segundos.
  // Arreglo: suelos MUY por encima (0.82 / 0.70). La partícula que viaja sigue
  // atenuándose un poco —el efecto de "se suelta y vuelve" se conserva— pero
  // ya no puede arrastrar la luminosidad del conjunto.
  float brightFloor = 0.82;
  float sizeFloor = 0.70;

  // parpadeo estelar por partícula (twinkle)
  float tw = 0.6 + 0.4 * sin(uTime * (0.5 + vSeed * 2.2) + vSeed * 55.0);

  // El tamaño del núcleo lo gobierna el genoma (polvo finísimo + centro denso);
  // sin multiplicador extra — la referencia es dust diminuto, no puntos gordos.
  float sizeMul = sizeClass * mix(sizeFloor, 1.0, closeness) * tw;

  vec4 mv = modelViewMatrix * vec4(P.xyz, 1.0);
  gl_PointSize = clamp(uPointSize * sizeMul * uDpr / max(0.1, -mv.z), 1.0, 70.0);
  vBright = brightClass * mix(brightFloor, 1.0, closeness) * tw;
  gl_Position = projectionMatrix * mv;
  vNdc = gl_Position.xy / max(1e-4, gl_Position.w);
}
