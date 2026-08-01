// Fragment de RENDER: glow radial + color por ROL (doc 13 §7.1 + feedback).
// Blending aditivo (glow por acumulación). Núcleo = Ámbar; pétalos = oro cálido;
// sub-líneas = oro; bandas/anillos = teal (con nodos oro); starfield = teal→blanco.
//
// [2026-07-21] NOTA DE IDENTIDAD (decisión del usuario): el AVCS NO cambia con
// el tema claro/oscuro de la UI. Es la identidad visual de Aithera — se
// mantiene 100% el original en cualquier tema. (Se probó una variante "tinta"
// para tema claro y se descartó explícitamente.)

uniform vec3 uHeart; // Ámbar (núcleo)
uniform vec3 uAura;  // oro cálido (aura/pétalos)
uniform vec3 uField; // teal (Savia)

// [doc 35 PU5] Compensación de luminosidad por tier. Q4 = 1.0 EXACTO (la
// referencia: multiplicar por 1.0 deja el cálculo idéntico al original, así que
// Q4 es bit a bit el de siempre). En tiers bajos hay menos partículas sumando
// luz con el blending aditivo, así que el conjunto se apaga; esto lo compensa
// subiendo la OPACIDAD de cada partícula.
//
// POR QUÉ AQUÍ Y NO EN EL TAMAÑO (lección de la primera versión de PU5, que se
// revirtió): agrandar gl_PointSize NO conserva el diseño — cada partícula se
// dibuja como un degradado radial (`glow`, abajo) que ocupa TODO el radio del
// quad, así que un punto más grande es literalmente un degradado más grande =
// una mancha difusa. El AVCS es polvo finísimo (ver render.vert.glsl); ampliarlo
// lo convierte en otra cosa. El brillo, en cambio, no toca ni la geometría del
// punto ni el perfil del degradado: misma nitidez exacta, más presencia.
//
// SOLO se aplica al canal ALPHA, nunca al color: `vBright` también gobierna la
// mezcla ámbar→blanco del núcleo (abajo), así que tocarlo ahí volvería el núcleo
// más blanco en tiers bajos — otro cambio de identidad. Con el boost solo en
// alpha, el TONO es idéntico en los 4 tiers y solo cambia cuánta luz aporta cada
// partícula.
uniform float uBrightBoost;

// [doc 35 PU5] Dureza del borde del punto (umbral interior del smoothstep de
// abajo). 0.0 = degradado desde el mismísimo centro → Q4, EXACTAMENTE como
// siempre. En tiers bajos sube (~0.30) y el punto pasa a tener un núcleo sólido
// con un borde corto: se ve NÍTIDO aunque sea algo más grande.
//
// Es la pieza que hace viable subir `pointScale` sin emborronar. La 1.ª versión
// de PU5 agrandó el punto SIN esto y el resultado fueron manchas difusas: con el
// degradado ocupando todo el radio, más tamaño es literalmente más desenfoque.
uniform float uEdgeHardness;

varying float vRole;
varying float vSeed;
varying float vBright;
varying vec2 vNdc;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float glow = smoothstep(0.5, uEdgeHardness, d);

  vec3 col;
  if (vRole > 0.95) {
    // Núcleo con PROFUNDIDAD (referencia: sol diminuto): el brillo del genoma
    // codifica la profundidad radial → centro blanco-cálido, borde ámbar hondo.
    vec3 deepAmber = uHeart * vec3(0.95, 0.52, 0.24);
    vec3 hotWhite = mix(uHeart, vec3(1.0), 0.55);
    col = mix(deepAmber, hotWhite, smoothstep(0.2, 0.95, vBright));
  } else if (vRole > 0.85) {
    col = mix(uHeart, uAura, 0.45); // anillo fino del núcleo (oro nítido)
  } else if (vRole > 0.73) {
    col = mix(uAura, uHeart, 0.3 + 0.25 * vSeed); // contornos/almendra/eje (oro cálido)
  } else if (vRole > 0.59) {
    // tendrils/polvo: oro, con chispas teal ocasionales en las puntas (constelación)
    col = mix(uAura * 0.92, uField, step(0.82, vSeed) * 0.55);
  } else if (vRole > 0.45) {
    col = mix(uField, uAura, step(0.65, vSeed)); // banda: mayoría teal, algunas oro
  } else if (vRole > 0.31) {
    col = uField; // anillo (teal)
  } else if (vRole > 0.18) {
    col = uField * 0.9; // campo (teal tenue)
  } else {
    col = mix(uField, vec3(1.0), 0.35 * vSeed); // estrella: teal→blanca
  }

  // Falloff de borde (doc 13 §13.3, "sin clipping"): se desvanece suave en el
  // ~8% exterior del frustum en vez de recortarse en seco al salir de cuadro.
  float edge = max(abs(vNdc.x), abs(vNdc.y));
  float edgeFalloff = 1.0 - smoothstep(0.92, 1.0, edge);

  // El color (primer argumento) NO lleva el boost — ver la nota de uBrightBoost:
  // el tono debe ser idéntico en los 4 tiers. Solo el alpha compensa.
  gl_FragColor = vec4(col * (0.35 + 0.9 * vBright), glow * vBright * uBrightBoost * 0.85 * edgeFalloff);
}
