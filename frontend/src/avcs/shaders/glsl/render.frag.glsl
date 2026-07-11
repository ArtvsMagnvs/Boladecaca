// Fragment de RENDER: glow radial + color por ROL (doc 13 §7.1 + feedback).
// Blending aditivo (glow por acumulación). Núcleo = Ámbar; pétalos = oro cálido;
// sub-líneas = oro; bandas/anillos = teal (con nodos oro); starfield = teal→blanco.

uniform vec3 uHeart; // Ámbar (núcleo)
uniform vec3 uAura;  // oro cálido (aura/pétalos)
uniform vec3 uField; // teal (Savia)

varying float vRole;
varying float vSeed;
varying float vBright;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float glow = smoothstep(0.5, 0.0, d);

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

  gl_FragColor = vec4(col * (0.35 + 0.9 * vBright), glow * vBright * 0.85);
}
