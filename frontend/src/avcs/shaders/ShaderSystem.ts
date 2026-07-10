// AVCS — ShaderSystem: registro y composición de chunks GLSL (ARCHITECTURE.md §6).
// UN solo lugar por función matemática. Resuelve `#include "chunk"` y valida los
// gotchas de GPUComputationRenderer del spike S0.

import noiseChunk from "./glsl/noise.glsl?raw";
import curlChunk from "./glsl/curl.glsl?raw";
import fieldsChunk from "./glsl/fields.glsl?raw";
import simVelocitySrc from "./glsl/simVelocity.frag.glsl?raw";
import simPositionSrc from "./glsl/simPosition.frag.glsl?raw";
import renderVertexSrc from "./glsl/render.vert.glsl?raw";
import renderFragmentSrc from "./glsl/render.frag.glsl?raw";

const CHUNKS: Record<string, string> = {
  noise: noiseChunk,
  curl: curlChunk,
  fields: fieldsChunk,
};

/** Nombres que GPUComputationRenderer.init() antepone automáticamente
 *  (uniform sampler2D <var>;). NUNCA declararlos en un fragment de simulación. */
const GPGPU_RESERVED = ["texturePosition", "textureVelocity"] as const;

// IMPORTANTE: un regex con flag `g` es STATEFUL (lastIndex). Reutilizar el mismo
// objeto en llamadas recursivas corrompe la iteración externa y desordena la
// composición. Se crea uno NUEVO en cada invocación.
function resolveIncludes(src: string, seen: Set<string> = new Set()): string {
  // Anclado a inicio de línea (flag m): un `#include` real va a principio de
  // línea; así NO se captura si aparece dentro de un comentario `// ...`.
  const re = /^[ \t]*#include\s+"([a-zA-Z0-9_]+)"/gm;
  return src.replace(re, (_m, name: string) => {
    if (seen.has(name)) return ""; // dedup: un solo lugar por función
    seen.add(name);
    const chunk = CHUNKS[name];
    if (chunk === undefined) {
      throw new Error(`[ShaderSystem] chunk GLSL desconocido: "${name}"`);
    }
    return resolveIncludes(chunk, seen);
  });
}

/** Verifica que un fragment de simulación NO declara los samplers reservados
 *  (evita el error real "redefinition" que vimos en S0). Solo en dev. */
function assertNoReserved(src: string, label: string): void {
  if (!import.meta.env.DEV) return;
  for (const name of GPGPU_RESERVED) {
    const re = new RegExp(`uniform\\s+sampler2D\\s+${name}\\b`);
    if (re.test(src)) {
      throw new Error(
        `[ShaderSystem] ${label} declara "uniform sampler2D ${name}" — ` +
          `GPUComputationRenderer ya lo antepone (error de redefinición). Quítalo.`,
      );
    }
  }
}

export const ShaderSystem = {
  /** Fragment de simulación de velocidad (para la variable textureVelocity del GPGPU). */
  buildSimVelocity(): string {
    const src = resolveIncludes(simVelocitySrc);
    assertNoReserved(src, "simVelocity");
    return src;
  },

  /** Fragment de simulación de posición (para la variable texturePosition del GPGPU). */
  buildSimPosition(): string {
    const src = resolveIncludes(simPositionSrc);
    assertNoReserved(src, "simPosition");
    return src;
  },

  /** Vertex de render (ShaderMaterial normal; SÍ declara texturePosition). */
  buildRenderVertex(): string {
    return resolveIncludes(renderVertexSrc);
  },

  /** Fragment de render. */
  buildRenderFragment(): string {
    return resolveIncludes(renderFragmentSrc);
  },
};
