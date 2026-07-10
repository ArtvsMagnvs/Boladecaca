// Fragment de RENDER: glow radial por punto + color doble capa (doc 13 §7.1).
// Blending aditivo (glow por acumulación). Núcleo = Ámbar constante (uHeart);
// cáscara/pétalo = mezcla Ámbar↔aura; campo = uField.

uniform vec3 uHeart;
uniform vec3 uAura;
uniform vec3 uField;
uniform float uBreathScale;

varying float vRole;
varying float vSeed;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float glow = smoothstep(0.5, 0.0, d);

  vec3 col;
  float bright;
  float alpha;
  if (vRole > 0.75) {
    // Núcleo Ámbar cálido, pulsa con la respiración.
    col = uHeart;
    bright = 0.85 + 3.0 * (uBreathScale - 1.0);
    alpha = glow * 0.5;
  } else if (vRole > 0.25) {
    // Cáscara / pétalo: aura del ritmo con corazón cálido asomando.
    col = mix(uAura, uHeart, 0.35 + 0.25 * vSeed);
    bright = 0.75;
    alpha = glow * 0.42;
  } else {
    // Campo: color de campo, más tenue.
    col = uField;
    bright = 0.5;
    alpha = glow * 0.22;
  }

  gl_FragColor = vec4(col * bright, alpha);
}
