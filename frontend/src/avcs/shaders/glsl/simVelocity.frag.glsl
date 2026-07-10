// Fragment de simulación de VELOCIDAD (GPUComputationRenderer, variable textureVelocity).
// GOTCHA S0: texturePosition y textureVelocity los antepone init() automáticamente
// (uno por variable/dependencia). NO declararlos aquí. resolution es #define.
// uGenome/uAnchor SÍ se declaran (uniforms propios; nombres no-colisionantes).
// Las declaraciones de uniforms van ANTES de los includes de campos (que las usan).

uniform float uTime;
uniform float uDelta;
uniform float uSessionSeed;
uniform float uSync;
uniform float uDamping;
uniform vec3  uSeedCenter;
uniform vec3  uGravityDir;
uniform float uWeights[10];
uniform float uBreath;
uniform float uCurlFreq;
uniform float uCurlFlow;
uniform int   uWaveCount;
uniform float uWaveR[6];
uniform float uWaveAmp[6];
uniform float uWaveSeed[6];
uniform float uWaveThickness;
uniform sampler2D uGenome;
uniform sampler2D uAnchor;

#include "noise"
#include "curl"
#include "fields"

void main() {
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec4 P = texture2D(texturePosition, uv);
  vec4 V = texture2D(textureVelocity, uv);
  vec4 G = texture2D(uGenome, uv);
  vec3 anchor = texture2D(uAnchor, uv).xyz;

  vec3 force = computeForce(P.xyz, G, anchor);
  vec3 vel = V.xyz + force * uDelta;
  vel *= uDamping;                 // amortiguación (evita explosión numérica)
  vel = clamp(vel, -8.0, 8.0);
  gl_FragColor = vec4(vel, V.w);
}
