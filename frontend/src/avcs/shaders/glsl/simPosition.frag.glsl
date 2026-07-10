// Fragment de simulación de POSICIÓN (GPUComputationRenderer, variable texturePosition).
// GOTCHA S0: texturePosition/textureVelocity auto-inyectados; resolution es #define.
// Integra pos += vel*dt. .w acumula la edad (para disolución/lifecycle, doc 13 §7.5).

uniform float uDelta;

void main() {
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec4 P = texture2D(texturePosition, uv);
  vec4 V = texture2D(textureVelocity, uv);
  vec3 pos = P.xyz + V.xyz * uDelta;
  gl_FragColor = vec4(pos, P.w + uDelta);
}
