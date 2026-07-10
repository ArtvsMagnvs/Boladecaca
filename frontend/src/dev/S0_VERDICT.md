# S0 — Veredicto del spike de riesgo (AVCS Fase 0)

Fecha: 2026-07-10. Código: `S0Spike.tsx` (mismo directorio), ruta `/dev/s0-spike`.
Verificado en el navegador real (Vite dev server), no solo por lectura de código.

## 1. GPUComputationRenderer + ping-pong FBO + curl noise

**Veredicto: GO.**

- `three/examples/jsm/misc/GPUComputationRenderer.js` (three@0.160, ya instalado,
  cero dependencias nuevas) funciona limpio con React 18 + R3F v8 + Vite.
- 4096 partículas (textura sim 64×64, tamaño del tier Q1) simuladas en GPU con
  curl noise real (simplex 3D de Ashima Arts + diferencias finitas) + retorno
  suave al origen (F_return). Confirmado visualmente: las partículas fluyen en
  streamers/tendrils orgánicos entre frames, no jitter aleatorio — el
  comportamiento que pide 13 §5 (F_curl).
- Sin pantalla negra, sin pérdida de contexto WebGL en una carga limpia.

**Dos correcciones a la asunción inicial, importantes para S1:**

1. `GPUComputationRenderer.init()` **antepone automáticamente**
   `uniform sampler2D <nombreVariable>;` al fragment shader de cada variable
   registrada vía `setVariableDependencies()` (confirmado en
   `GPUComputationRenderer.js:232`, y con un error real de compilación
   "redefinition" al declararlo también a mano). **No declarar en el shader
   propio ningún uniform cuyo nombre coincida con una variable GPGPU.**
2. `resolution` sí es un `#define` automático (no uniform) — la asunción
   original sobre esto era correcta.

## 2. @react-three/postprocessing + EffectComposer + Bloom

**Veredicto: GO, con una nota de instalación.**

- Instalado `@react-three/postprocessing@^2.19.1` (línea 2.x, compatible con
  R3F v8/three r160 — la 3.x pide R3F v9/React 19, que no tenemos).
- La instalación con `npm install` normal falla por ERESOLVE: `@react-three/fiber`
  declara un peer **opcional** hacia `expo` (soporte React Native, que no usamos)
  y el resolver de npm tropieza con esa cadena. Hace falta `--legacy-peer-deps`.
  No es un conflicto real — el `react-dom` instalado ya cumple todo lo que pide
  la librería.
- Al cargar, esbuild/Vite reventó con ~220 errores "Could not resolve" dentro
  de `three-stdlib` (el mismo paquete detrás del bug ya conocido de
  `@react-three/drei`, documentado en `drei-shim.tsx`). Investigado a fondo:
  **esta vez NO era un problema del paquete publicado** — la carpeta
  `node_modules/three-stdlib/_polyfill/` faltaba por una instalación local
  corrupta (efecto colateral de la resolución con conflictos del paso
  anterior). `rm -rf node_modules/three-stdlib && npm install three-stdlib@2.36.1`
  lo arregló limpio. Si esto reaparece, primero descartar corrupción local
  antes de asumir que hay que evitar el paquete.
- `EffectComposer` + `Bloom` renderizan correctamente una vez resuelto lo
  anterior. Ajuste de calibración (no bug): los valores de ejemplo
  (`intensity=0.9, luminanceThreshold=0.15`) saturaban a blanco el racimo
  denso de partículas del centro — bajados a `0.35/0.4` para un glow moderado,
  en línea con 13 §11 ("bloom moderado, nunca neón total").

## 3. Falso positivo durante la verificación (nota metodológica)

Verificar el contenido de un canvas WebGL con `canvas.toDataURL()` de forma
asíncrona (tras un `setTimeout`) puede devolver un buffer ya limpiado por el
navegador si el contexto no tiene `preserveDrawingBuffer: true` — durante la
depuración esto hizo parecer que el canvas estaba vacío cuando en realidad
renderizaba bien. Se activó `preserveDrawingBuffer` solo para verificar y se
retiró después (no es apto para producción: impide optimizaciones del
compositor). Para S1+: verificar visualmente con capturas de pantalla, no con
`toDataURL()` async sin ese flag.

## Conclusión para S1

Ambas técnicas núcleo aprobadas en 13 §11 (GPGPU con FBO ping-pong,
`@react-three/postprocessing` para bloom) son viables tal cual en este stack.
S1 puede construir `ParticleEngine`/`ShaderSystem` sobre GPGPU real desde el
principio — no hace falta activar la cláusula de fallback CPU/híbrido para
Fase 0. Único cambio de dependencias a conservar:
`@react-three/postprocessing@^2.19.1` en `frontend/package.json`.

Este spike (`S0Spike.tsx`, la ruta `/dev/s0-spike` en `App.tsx`) se borra antes
de empezar S1.
