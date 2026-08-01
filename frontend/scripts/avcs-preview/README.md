# AVCS · previsualizador de tiers (CPU)

Renderiza el AVCS **sin GPU ni navegador**, usando la geometría REAL
(`src/avcs/math/lotus.ts`) y la configuración REAL (`src/avcs/constants.ts`).
Replica proyección, `gl_PointSize`, el perfil de glow del fragment, el blending
aditivo y el efecto del DPR por tier.

## Para qué sirve

Nació porque PU5 (doc 35) se entregó dos veces mal por diseñar el AVCS **a
ciegas**, sin ver el resultado: la primera versión escaló el tamaño de punto y
lo volvió borroso. Esta herramienta permite iterar viendo, en segundos, sin
depender de tener el frontend arrancado ni una GPU.

**Si vas a tocar densidad, tamaño de punto, reparto de partículas o el perfil
del glow: pasa por aquí antes.** No es un sustituto de mirar la app real
(no simula bloom ni la animación), pero sí es fiel en lo que decide si una
línea "se lee": cuántos puntos hay, dónde caen y cómo se dibuja cada uno.

## Uso

```bash
cd frontend
# los 4 tiers con la config real del código
node_modules/.bin/esbuild scripts/avcs-preview/preview-tiers.ts \
  --bundle --platform=node --format=cjs --outfile=/tmp/p.cjs && node /tmp/p.cjs

# un caso suelto (para probar valores antes de tocar constants.ts)
node_modules/.bin/esbuild scripts/avcs-preview/render.ts \
  --bundle --platform=node --format=cjs --outfile=/tmp/r.cjs && \
node /tmp/r.cjs --n=4096 --dpr=1 --ps=52 --boost=1.45 --hard=0.3 --seed=0.86 --name=prueba

# franja comparativa de 3 PNG
node scripts/avcs-preview/compose.cjs
```

## `glslcheck.cjs` — validar los shaders sin GPU

`node scripts/avcs-preview/glslcheck.cjs` parsea `simVelocity` + `fields` +
`render.frag` con los includes resueltos (requiere `@shaderfrog/glsl-parser`,
instalable con `npm i -D @shaderfrog/glsl-parser`). Un error de sintaxis en un
shader deja el AVCS en negro, así que conviene pasarlo antes de dar por buena
cualquier edición de `.glsl`. Los avisos "undefined variable" sobre `gl_*` y
`resolution` son normales: son builtins que el parser no conoce.

## Limitaciones honestas

- **No hay bloom** — los tiers con bloom se ven algo menos "glow" que en la app.
- **Estático** (uTime=0, partículas en reposo sobre su ancla): no muestra
  respiración, ondas, deriva NI el giro de los anillos. Todo lo que dependa de
  la simulación (rigidez efectiva, rotación) hay que verlo en la app real; aquí
  se ve la GEOMETRÍA y la LUMINOSIDAD, que es para lo que sirve.
- Es una réplica del pipeline, no el pipeline. Para el visto bueno final,
  mirar la app de verdad.
