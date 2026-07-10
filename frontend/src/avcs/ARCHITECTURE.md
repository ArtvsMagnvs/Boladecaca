# AVCS — Arquitectura del motor (Fase 0 / S1)

> **Fuente de verdad del código** del Aithera Visual Consciousness System.
> El diseño de producto/identidad vive en `PLAN_MAESTRO_2026/13_AVCS_DISENO_MAESTRO.md`
> (doc 13). Este archivo es el **contrato congelado de la arquitectura**: síntesis
> de un panel de 4 arquitectos (lentes: permanencia de API · viabilidad GPU ·
> fidelidad conductual · pragmatismo Fase 0) + crítica adversarial (2026-07-10).
>
> **Regla de oro**: MVP1 y MVP2 **añaden datos** (entradas de tabla, funciones de
> campo, variantes de union) — **nunca cambian firmas** de §"API pública". Si un
> cambio futuro obliga a tocar un consumidor (RhythmEngine, HubEngine,
> `<AitheraPresence/>`, Hub, Chat), la arquitectura falló.

## Principio maestro (constraint del usuario)
La **arquitectura** (módulos + API pública) es definitiva desde S1. La
**implementación** de Fase 0 puede ser más simple de lo ideal: donde GPGPU o bloom
compromentan estabilidad, se sustituyen por CPU/hibrido **sin cambiar la API**.
Simplicidad y estabilidad sobre sofisticación, sin comprometer el contrato.

---

## 1. Módulos (bajo `frontend/src/avcs/`)

```
index.ts            Barrel público. UNICO import que ve el resto de la app: <AitheraPresence/> + tipos.
types.ts            Tipos congelados: RhythmName, FieldName, FieldWeights, Palette, QualityTier, AudioFrame,
                    StructureSpec/Handle, UniformBus, CoreStateId.
constants.ts        FIELD_ORDER (append-only), TIERS, RHYTHM_WEIGHTS, RHYTHM_SYNC, PALETTES, STATE_TO_RHYTHM.
math/prng.ts        mulberry32 (PRNG por sessionSeed), noise1D (CPU, para respiración), poissonInterval.
math/lotus.ts       FUENTE DE VERDAD de la FORMA de la semilla: genera genome+anchor (silueta de pétalo de loto).
shaders/ShaderSystem.ts   Registro/composición de chunks GLSL. Sortea los gotchas de GPUComputationRenderer (S0).
shaders/glsl/*.glsl noise, curl, fields, palette + simVelocity/simPosition (GPGPU) + render vert/frag.
engine/UniformBus.ts      Crea el bus (objetos {value} de three, mutados en sitio, compartidos por referencia).
engine/ParticleEngine.ts  Sim GPGPU (GPUComputationRenderer ping-pong) + render THREE.Points. API CONGELADA.
engine/RhythmEngine.ts    State machine de ritmos -> pesos + respiración + ondas (poisson) -> escribe el bus. NO toca three.
engine/AudioReactor.ts    Stub S1 ({envelope:0,bands:[0,0,0],silence:true}). API real en S2.
engine/PerformanceManager.ts  Tier Q1-Q3 (S1) + escalera dinámica pasos 1-3. UNICO que muta presupuestos.
engine/HubEngine.ts       Orquestador. Reloj único, lifePhase, sessionSeed. UN solo tick maestro. Compone escena.
react/AitheraPresence.tsx UN <Canvas> R3F persistente + el UNICO useFrame maestro + bloom. El engine NO conoce React.
react/useAvcsRoute.ts     Visibilidad por ruta + tier desde ajustes (localStorage). Sin re-crear el Canvas.
```

**Cambios a archivos existentes (mínimos):**
- `store/useAppStore.ts`: `AICoreState` += `"action" | "recovering"`.
- `components/layout/AppLayout.tsx`: montar `<AitheraPresence/>` FUERA del `<div key={location.pathname}>`.
- `pages/Hub.tsx`: quitar `<CoreModelView>`/`CoreSelector` del centro (celda transparente). Barra de estado intacta.
- Los 6 juguetes viejos (`CoreSelector`, `AICore`, `AitheraSeed`, `PoopSphere`, `RasenganSphere`, `CoreDesignPanel`)
  se **desconectan** de Hub (dejan de importarse). No se borran (recuperables por git; tree-shaking los excluye).

Dependencias **solo hacia abajo**: `react → HubEngine → {Rhythm, Particle, Perf, Audio} → Shader`. Ningún import lateral.

---

## 2. API pública (CONGELADA)

- **`FieldWeights = Record<FieldName, number>`** — diccionario. Añadir un campo = clave nueva (aditivo). NUNCA array posicional en la API.
- **`FIELD_ORDER`** (10, append-only): `breath, wave, curl, gravity, root, branch, mandala, channel, return, self`. El índice ES la posición en `uWeights[10]`. Nuevos campos se añaden AL FINAL (nunca reordenar) → shaders compilados nunca se corrompen.
- **`ParticleEngine`** (5 métodos obligatorios doc 13 §12): `setFieldWeights(FieldWeights)`, `spawnStructure(StructureSpec): Handle`, `dissolve(Handle, s?)`, `setSync(number)`, `setPalette(Palette, s?)`. + plumbing: `update(dt)`, `setTier`, `object3D`, `dispose`. S1 realiza `'seed'`; `root/branch/mandala/channel` devuelven handle no-op.
- **`RhythmEngine`**: `setCoreState(CoreStateId)`, `setRhythm(name, s?)`, `setSync(s)`, `setAudio(frame)`, `update(dt, time, lifePhase)`. Un ritmo es DATOS (`RHYTHM_WEIGHTS[name]`), no código; el crossfade es genérico sobre el vector de pesos (sin `switch` por ritmo).
- **`HubEngine`**: `mount()`, `frame(dt)` (EL único tick), `setCoreState`, `setVisible(bool)`, `setTier`, `dispose`.
- **`<AitheraPresence/>`**: `{ className? }`. No recibe estado por props: lee el store y la ruta internamente.

**Por qué no cambia**: enums completas desde hoy (7 ritmos, 10 campos, 4 tiers, todas las StructureKind). Los métodos reciben *intención* (nombre de ritmo, vector de pesos), nunca *animación* (curvas/keyframes → prohibido P2). Backend de partículas intercambiable (WebGL2 hoy, WebGPU MVP2) detrás de `ParticleEngine` sin que HubEngine/Rhythm se enteren.

---

## 3. El bus de uniforms (contrato RhythmEngine → sim shader)

Objetos `{value}` de three, **mutados en sitio** (cero alocación/frame), compartidos por referencia entre el material de velocidad (GPGPU), el material de render y RhythmEngine. **Propiedad de escritura disjunta** (sin carreras conceptuales): HubEngine escribe tiempo/sessionSeed/lifePhase/audio; RhythmEngine escribe pesos/sync/respiración/ondas/gravedad/paleta; PerformanceManager escribe tamaño de punto/dpr/tier. Uniforms clave: `uTime, uDelta, uSessionSeed, uLifePhase, uWeights[10], uSync, uSeedCenter, uBreath, uBreathScale, uWaveCount, uWaveR[6], uWaveAmp[6], uWaveSeed[6], uWaveThickness, uGravityDir, uHeart, uAura, uField, uDamping, uCurlFreq, uCurlFlow` + samplers propios `uGenome, uAnchor`. Añadir un uniform (MVP1) = campo nuevo con default; los shaders viejos lo ignoran.

## 4. Modelo de campos (sim shader)

`uWeights[10]` (orden `FIELD_ORDER`). `fields.glsl` define una función pura por campo; `computeForce()` suma ponderado y mezcla con el factor de sincronía `S`:
`force = mix(fSelf, common, uSync) + uWeights[self]*fSelf*(1 - uSync*0.5)`. `fReturn` SIEMPRE activo (evita dispersión). En S1, `fRoot/fBranch/fMandala/fChannel` son `return vec3(0.0)` (firma real, cuerpo en MVP1). **Reposo** = vector de pesos concreto en `RHYTHM_WEIGHTS.repose`. Añadir campo = escribir `fX()` + una línea en `computeForce` + append a `FIELD_ORDER`; consumidores: cero cambios.

## 5. Montaje persistente (fix crítico)

`AppLayout` envuelve `<Outlet/>` en `<div key={location.pathname}>` → remonta el subárbol en cada ruta. El `<Canvas>` NO vive ahí: vive en `AppLayout` como **hermano** del div keyeado (`absolute inset-0 z-0 pointer-events-none`), montado una vez, sobrevive a las navegaciones. Un **único `useFrame`** dentro del Canvas llama `HubEngine.frame(dt)`. Orden estricto por frame: reloj+lifePhase → `rhythm.update` (escribe bus) → `particle.update` (compute GPGPU) → R3F/EffectComposer renderiza (el compute corre en `useFrame` priority 0, ANTES del render de bloom). Hub/Chat "usan" la presencia dejando su zona transparente; otras rutas → `setVisible(false)` (pausa, no desmonta). `dispose()` solo al cerrar la app (libera FBOs + contexto).

## 6. GLSL — gotchas de GPUComputationRenderer (verificados en S0)

1. `init()` **antepone** `uniform sampler2D texturePosition;` y `textureVelocity;` (uno por variable/dependencia). ⇒ NUNCA declararlos en el shader propio (error "redefinition"). `ShaderSystem` valida que ningún chunk los declare.
2. `resolution` es un **`#define`** automático (no uniform). Usar `gl_FragCoord.xy / resolution.xy`.
3. Uniforms/samplers propios (`uGenome`, `uAnchor`, `uWeights`...) SÍ se declaran; sus nombres no colisionan con variables GPGPU.
4. En el material de **render** (ShaderMaterial normal, NO envuelto por GPGPU) SÍ se declara `uniform sampler2D texturePosition;`.
5. GLSL ES 1.00 (three no fija glslVersion en GPGPU): `texture2D`, `gl_FragColor`, loops de bound CONSTANTE (loop a 6 + guarda `if(i<uWaveCount)`, sin break/continue de condición dinámica).
6. Verificar SIEMPRE por screenshot; nunca `canvas.toDataURL()` async sin `preserveDrawingBuffer`.

## 7. Semilla + Ondas (Reposo)

Un pool de N partículas, rol en `uGenome.g` (0=campo, 0.5=cáscara-pétalo, 1=núcleo). La forma **emerge** del campo: `fReturn` tira cada partícula a su `uAnchor` (muestreado de `math/lotus.ts`, la silueta de pétalo de la imagen de referencia) — la forma nunca se "dibuja" (P2/P6). Doble capa de color: `uHeart` (Ámbar #FFD9A0 CONSTANTE, invariante nº1) para el núcleo; `mix(uHeart, uAura, k)` para la cáscara (aura del ritmo). **Ondas**: frentes de presión en `uWaveR/Amp/Seed[6]`, nacimiento **Poisson** en torno al periodo respiratorio, frente FBM **no-circular** (`r(θ) = R·(1+Σaᵢ·fbm)`, 2-3 octavas 6-12%), viajan desacelerando y se disuelven por transparencia (nunca "pop"). La onda es presión que empuja el campo, no un dibujo.

## 8. Respiración + anti-mecanicidad

Respiración en **CPU** (RhythmEngine), publicada como escalar (`uBreath`, `uBreathScale`). **Prohibido `sin(t)` puro**: el argumento de `sin` es una **fase acumulada** cuya velocidad angular varía cada frame por `noise1D(lifePhase + sessionSeed)`, + micro-fluctuación (`ripple`) + amplitud con jitter 8% + respiración profunda 1.4× cada 6-12 ciclos (Poisson). 5 fuentes: (1) `sessionSeed` desplaza todo noise; (2) `lifePhase` desfasa fases lentas; (3) noise 4D en curl/self; (4) Poisson/jitter en ondas y profundas; (5) test: 5 min sin bucle detectable.

## 9. Rendimiento

Presupuesto: GPU ≤8ms, CPU main ≤2ms (sim en GPU; JS solo escribe uniforms), draw calls ≤6 (2 compute + 1 Points = 3; bloom = overhead de post, no draw de geometría), VRAM ≤160MB. Tiers: Q1 64²/4096 (sin bloom), Q2 128²/16384 (bloom ligero), Q3 256²/65536 (bloom selectivo, default), Q4 512²/262144. Escalera dinámica S1 (pasos 1-3): bloom off → DPR 1.0 → bajar textura sim. **Invariantes que NUNCA se degradan**: semilla presente y cálida, ondas deformadas (jamás círculos), respiración variable, transiciones suaves, factor de sincronía.

## 10. Decisiones abiertas (dirección, no arquitectura)

- **Paleta Reposo por defecto**: núcleo Ámbar constante (invariante) + aura. Se ofrecen `PALETTES.doc13` (aura Aliento azul), `PALETTES.warm` (aura oro cálido, honra las imágenes de referencia y el mockup de sistema) y se elige por `setPalette` sin refactor. Default S1: `warm` (coherente con el concept art del usuario); cambiar = una constante.
- **Visibilidad**: presente en Hub y Chat (misma instancia), atenuada/oculta en el resto. Cumple el criterio de aceptación (navegar Hub↔Chat sin re-crear).

---
*S1 — 2026-07-10. Reposo completo; Escucha/Comunicación en S2; los otros 4 ritmos + sync visual + estructuras maduras en MVP1. La API de §2 y el bus de §3 son el contrato congelado.*
