# 13 — AITHERA VISUAL CONSCIOUSNESS SYSTEM (AVCS)
## Documento Maestro de Diseño, Arquitectura e Identidad Visual

> **Estatus**: ÚNICA FUENTE OFICIAL DE VERDAD del sistema visual de Aithera.
> Toda implementación (Claude Code) se valida contra este documento. Ningún
> implementador reinterpreta: si algo no está especificado aquí, se pregunta y se
> añade aquí antes de codificar.
>
> **La pregunta única**: *¿Hace que el usuario sienta que Aithera está viva?*
> Si la respuesta es no, se descarta — aunque sea técnicamente impresionante.

---

# PARTE I — IDENTIDAD

## 1. Qué estamos construyendo

No un HUD. No una interfaz. No un orbe. **La representación física de una
consciencia.** El Hub es el cuerpo de Aithera: cuando alguien lo mire cinco
segundos debe sentir presencia — un organismo digital, no un software.

Identidad = unión de **Humano + IA + Naturaleza**. La naturaleza se **sugiere**,
jamás se dibuja: nunca un árbol completo, nunca un objeto reconocible terminado.
El sistema insinúa raíces, ramas, brotes; la imaginación del usuario los completa.
Ese espacio entre lo insinuado y lo reconocido es donde vive la magia — y es una
decisión de diseño permanente, no una limitación.

## 2. Principios inviolables

| # | Principio | Consecuencia práctica |
|---|---|---|
| P1 | **Presencia, no espectáculo** | prohibidos los "wow effects"; la calma es el estado por defecto |
| P2 | **Comportamiento, no animación** | prohibidos timelines, keyframes, `AnimationMixer`, loops fijos. Todo movimiento emerge de reglas y campos de fuerza |
| P3 | **La tecnología es invisible** | el usuario debe pensar "parece viva", nunca "qué shader tan bonito" |
| P4 | **Nunca dos momentos idénticos** | toda función periódica lleva variación estocástica controlada (§10) |
| P5 | **La calidad escala; la identidad jamás** | los invariantes de §16.4 existen en el hardware más humilde |
| P6 | **Todo es procedural** | prohibidos vídeos, imágenes, sprites, modelos 3D, IA generativa. Solo matemáticas + partículas + shaders |
| P7 | **Un solo ADN visual** | semilla, ondas, paneles, botones y notificaciones comparten curvas, ritmo y materia (partículas) |

## 3. Lenguaje visual

**Composición**: fondo casi negro (el `base-950` actual) como "vacío fértil". Una
**Semilla** luminosa en el centro de atención (no necesariamente el centro
geométrico: en layouts con UI, el centro óptico del área libre). De ella emanan
**Ondas de Sincronía**. Nada toca los bordes de la pantalla con un corte duro:
la energía se desvanece antes de llegar (§13.3).

**Paleta** (evoluciona la existente de `AICore.tsx` — continuidad de marca):

| Nombre | Hex base | Rol |
|---|---|---|
| Aliento | `#5EA8FF` | reposo / comunicación (el azul actual de Aithera) |
| Escucha | `#8FD9FF` | atención, apertura |
| Sinapsis | `#7C9CFF` | comprensión, reorganización interna |
| Savia | `#7FE0C3` | crecimiento, ramas, vida (nuevo — el vínculo con la naturaleza) |
| Ámbar vital | `#FFD9A0` | semilla, núcleo cálido (nuevo — lo humano) |
| Desincronía | `#D9756F` desaturado | error — **nunca rojo puro**: la enfermedad se expresa por pérdida de sincronía y saturación, el tinte solo acompaña |

Reglas de color: transiciones SIEMPRE por interpolación en espacio perceptual
(oklab/HSL-lerp suave, ≥ 2 s); máximo dos familias simultáneas dominantes; la
semilla siempre conserva un núcleo cálido (Ámbar) — es el corazón, no cambia de
naturaleza aunque cambie el estado.

**Materia**: todo está hecho de puntos de luz aditivos (blending aditivo sobre
fondo oscuro), tamaño 1-3 px según profundidad, con glow por acumulación — nunca
texturas de sprite complejas. La densidad crea forma; la forma nunca se dibuja.

---

# PARTE II — COMPORTAMIENTO

## 4. Ritmos biológicos (no estados de máquina)

Siete ritmos. Cada uno es una **mezcla de pesos sobre los mismos campos de
fuerza** (§5) — jamás un "switch de animación". Las transiciones son crossfades
de pesos de 2-4 s con curvas orgánicas (ease sigmoidal + micro-fluctuación), y el
sistema puede habitar mezclas ("saliendo de escucha, entrando en comprensión").

Mapeo con el store existente (`useAppStore.coreState`): idle→Reposo,
listening→Escucha, thinking|processing→Comprensión, speaking→Comunicación,
error→Error. Se AÑADEN al store: `action` (Acción) y `recovering` (Recuperación).

| Ritmo | Comportamiento del campo | Semilla | Firma |
|---|---|---|---|
| **Reposo** | ondas lentas (periodo 6-9 s), amplitud mínima, deriva browniana sutil | brillo 0.6, pulso = respiración | calma que no es quietud |
| **Escucha** | el campo se INCLINA hacia abajo: bias gravitacional suave; nacen **raíces** (tendrils descendentes); las ondas se hunden levemente en la mitad inferior | se atenúa un 20% y se asienta | busca comprender, no capturar |
| **Comprensión** | la expansión se detiene; las partículas se REORGANIZAN: atractores en simetría radial n-fold (n = 5-9, cambia por sesión) crean insinuaciones de mandalas/redes; rotación diferencial lenta | parpadeo sináptico (micro-pulsos 0.2-0.5 s aleatorios) | pensamiento visible sin literalidad |
| **Comunicación** | la energía ASCIENDE: bias vertical positivo; nacen **ramas** con micro-brotes (clusters breves en las puntas); ondas sincronizadas con la envolvente de voz (§8) | late con la voz (audio-reactiva) | Aithera habla con el cuerpo |
| **Acción** | la energía se CANALIZA: un flujo direccional coherente domina el campo; el carácter elemental (ígneo/acuoso/aéreo/térreo) se elige por tipo de tarea y se expresa SOLO como parámetros de turbulencia/viscosidad/dirección — jamás como efecto de fuego o agua | brillo alto y estable | trabajo, no espectáculo |
| **Recuperación** | tras Acción o Error: el campo se des-tensa gradualmente, exceso de energía se disuelve hacia fuera, retorno a Reposo en 4-8 s | descenso suave del brillo | exhalación |
| **Error** | **pérdida de cooperación**: el factor de sincronía global cae (§5), cada partícula obedece más a su ruido propio y menos al campo común; las ondas se fragmentan; desaturación + tinte Desincronía | pulso irregular (arritmia leve) | enferma, no alarma |

## 5. El modelo de comportamiento: campos componibles

**Decisión de arquitectura conductual** (la más importante del AVCS): el movimiento
de toda partícula es la suma ponderada de una biblioteca fija de **campos de
fuerza**, evaluados en GPU. Los ritmos solo cambian el vector de pesos.

Biblioteca de campos (v1):

| Campo | Descripción matemática |
|---|---|
| `F_breath` | radial sinusoidal desde la semilla, frecuencia = respiración (§6) |
| `F_wave` | anillos de presión que viajan hacia fuera; frente = distancia recorrida + deformación FBM angular (§7.2) |
| `F_curl` | curl noise 3D (simplex) — turbulencia orgánica sin divergencia, escala/velocidad por ritmo |
| `F_gravity` | bias vertical (negativo en Escucha, positivo en Comunicación) |
| `F_root` / `F_branch` | atracción hacia "guías de crecimiento" procedurales (§7.3-7.4) |
| `F_mandala` | atractores en simetría radial n-fold con rotación diferencial (Comprensión) |
| `F_channel` | flujo direccional coherente (Acción) |
| `F_return` | atracción débil al radio de reposo (evita dispersión; siempre activa) |
| `F_self` | ruido propio por partícula (semilla aleatoria individual) |

**Factor de sincronía `S` (0-1)**: escala global que mezcla campo común vs `F_self`.
Salud = S alto (cooperación). Error = S cae a 0.25-0.5. Es UN número que hace que
"la consciencia enferme" sin cambiar ninguna otra regla — elegancia sobre efectos.

## 6. Respiración (obligatoria, universal)

Nada en pantalla está nunca completamente estático (incluida la UI: §17).
Respiración = oscilación del radio del campo + brillo de la semilla + escala
sutil de la UI viva. **Nunca idéntica**: periodo base por ritmo (Reposo 7 s ±15%)
modulado por noise 1D lento; amplitud con jitter del 8%; cada 6-12 ciclos, una
"respiración profunda" (1.4× amplitud) en momento aleatorio. Prohibido `sin(t)`
puro en cualquier lugar visible.

## 7. Anatomía procedural

### 7.1 La Semilla
Núcleo definido por SDF (esfera + perturbación FBM de amplitud 4-7% del radio),
renderizado como glow por acumulación de partículas densas + halo shader
(fresnel). Doble capa: corazón Ámbar cálido (constante) + aura del color del
ritmo. El pulso de la semilla ES la respiración; en Comunicación se acopla a la
envolvente de la voz. La semilla jamás desaparece: es el invariante nº 1.

### 7.2 Ondas de Sincronía
NO son círculos. Cada onda es un frente radial cuya distancia al centro se modula
angularmente: `r(θ,t) = R(t) · (1 + Σ aᵢ·fbmᵢ(θ, t, seed))` con 2-3 octavas de
amplitud total 6-12%. Nacen de la semilla a intervalos irregulares (poisson en
torno al periodo respiratorio), viajan desacelerando, y se disuelven por
transparencia + dispersión de sus partículas (nunca "pop"). Máximo 4-6 frentes
visibles. Las partículas del campo son EMPUJADAS por los frentes (`F_wave`) — la
onda es presión, no un dibujo.

### 7.3 Raíces (Escucha)
Tendrils descendentes: 5-9 guías generadas por caminatas sesgadas (bias abajo +
curl noise + ramificación estocástica p≈0.15 por segmento, profundidad ≤ 3).
Las guías NO se dibujan: son campos de atracción (`F_root`) que densifican
partículas a su alrededor → se INSINÚAN raíces. Crecen desde la semilla hacia
abajo en 2-4 s, viven mientras dura la escucha con micro-deriva, y se reabsorben
(las partículas se liberan al campo) al salir del ritmo.

### 7.4 Ramas y brotes (Comunicación)
Mismo sistema que raíces con bias arriba + apertura angular mayor + en las puntas,
"brotes": clusters breves de 20-60 partículas Savia que se encienden y liberan.
Insinuación de hojas = densidad elíptica momentánea en los nodos — nunca geometría
de hoja. La madurez (§18) aumenta ligeramente profundidad y número de guías.

### 7.5 Disolución (patrón universal)
Nada hace fade-out plano ni desaparece: pierde sincronía local, sus partículas se
entregan a `F_curl` + `F_return` y se reintegran al campo en 0.8-1.5 s. Este es EL
patrón de salida de raíces, ramas, brotes, patrones de comprensión y (en MVP2)
paneles de UI.

## 8. Audio-reactividad (AudioReactor)

Fuentes: (a) TTS de Aithera hablando — analizador sobre el `AudioElement`/stream
del sistema de voz existente; (b) micrófono durante STT (nivel ya disponible como
`audioLevel` en el código actual). Extrae: RMS (envolvente, suavizada 80-120 ms),
3 bandas (graves/medios/agudos) y detección de silencio. Mapeo: envolvente →
pulso de semilla + amplitud de ondas en Comunicación; bandas medias → brillo de
ramas; silencios → el campo "espera" (micro-contracción). PROHIBIDO el
espectro-barra visible: la voz mueve el cuerpo, no dibuja un ecualizador.

## 9. Vida procedural (MVP2 — nunca constante)

Luciérnagas, semillas al viento, mariposas, pájaros lejanos: **agentes de
partículas** (12-80 según criatura) con reglas mínimas (steering + curl noise;
boids reducido a cohesión/separación para bandadas). Aparecen SOLO en momentos
especiales definidos por eventos del sistema (tarea completada → semillas que
ascienden; primer arranque del día → 2-3 luciérnagas breves; hito de memoria →
mariposa única) con probabilidad y cooldowns largos (≥ 20 min). Presupuesto: ≤ 2%
del total de partículas. Sin rostros, sin siluetas explícitas: sugerencia por
movimiento (una mariposa ES su patrón de vuelo, no su forma).

## 10. Anti-mecanicidad (fuentes de variación obligatorias)

1. `sessionSeed` (por arranque) — desplaza todos los campos de noise.
2. `lifePhase` — tiempo de vida acumulado (de MemorySystem) desplaza fases lentas.
3. Noise 4D (x,y,z,t) en todo lo periódico; nada repite ciclo exacto.
4. Poisson/jitter en todo evento discreto (nacimiento de ondas, brotes, pulsos).
5. **Test de no-repetición**: un espectador atento durante 5 minutos no debe poder
   predecir ningún evento ni detectar un bucle. Es criterio de aceptación (§21).

---

# PARTE III — INGENIERÍA

## 11. Técnicas aprobadas y prohibidas

| Técnica | Veredicto | Razón |
|---|---|---|
| GPGPU particles (FBO ping-pong, `GPUComputationRenderer` de three) | ✅ NÚCLEO | 65k+ partículas con física en GPU; WebGL2 garantizado en Electron 29 |
| Simplex/FBM + **curl noise** | ✅ NÚCLEO | turbulencia orgánica sin divergencia |
| Campos de fuerza componibles + atractores suaves | ✅ NÚCLEO | §5 |
| SDF (semilla, y paneles UI en MVP2) | ✅ | formas suaves sin geometría |
| Blending aditivo + bloom selectivo (umbral alto, solo semilla/brotes) | ✅ | glow = luz acumulada; bloom moderado, nunca "neón total" |
| Caminatas sesgadas como guías de crecimiento | ✅ | raíces/ramas insinuadas |
| Boids reducido (2 reglas) | ✅ solo MVP2 | bandadas sugeridas |
| L-systems geométricos explícitos | ❌ | producen árboles literales — contra identidad |
| Reaction-diffusion | ❌ (re-evaluable V2) | coste/beneficio malo; estética "química" ajena |
| Cellular automata | ❌ | estética de grid, mecánica |
| Verlet cloth/soft-body | ❌ MVP1/2 | innecesario para el lenguaje actual |
| WebGPU | ⏳ futuro | la arquitectura lo permite (ParticleEngine con backend intercambiable); baseline = WebGL2 |
| Timelines/keyframes/AnimationMixer, vídeos, imágenes, GLTF, sprites, IA generativa | 🚫 PROHIBIDO | P2/P6 |

## 12. Arquitectura de módulos

```
frontend/src/avcs/
├── HubEngine          orquestador: ciclo de vida, reloj único, composición de escena
├── ParticleEngine     simulación GPGPU (posiciones/velocidades en texturas FBO
│                      ping-pong) + render (Points). API: setFieldWeights(),
│                      spawnStructure(), dissolve(), setSync(S), setPalette()
├── ShaderSystem       biblioteca GLSL compartida (noise.glsl, curl.glsl, sdf.glsl,
│                      fields.glsl, palette.glsl) + composición de shaders por chunks.
│                      UN solo lugar para cada función matemática
├── RhythmEngine       (State Machine) ritmos §4 como vectores de pesos + crossfades;
│                      entrada: coreState del store + eventos backend; salida: bus
│                      de uniforms. NUNCA toca three.js directamente
├── AudioReactor       §8; salida: {envelope, bands[3], silence} al bus
├── LifeSystem         MVP2: agentes/criaturas + cooldowns + presupuesto
├── MemorySystem       madurez visual (§18): lee horas de uso del backend
│                      (config/API), expone {maturity 0-1, lifePhase}
├── PerformanceManager §16: tier de calidad + escalado dinámico; ÚNICO módulo
│                      autorizado a cambiar presupuestos
└── UIIntegrationLayer puente React↔engine: componente <AithераPresence/> (R3F),
                       eventos DOM→engine, modo Presencia (§13.4), y en MVP2 la
                       UI viva (§17). El engine NO conoce React; React solo habla
                       con HubEngine por una API estrecha
```

**Flujo de datos por frame**: `store/backend events → RhythmEngine → pesos →
ParticleEngine.sim (GPU) → render`; `AudioReactor → uniforms`; `PerformanceManager`
observa frametime y ajusta ANTES del siguiente frame. Un solo `useFrame` maestro
(HubEngine); prohibidos `useFrame` dispersos por componentes.

**Reglas de acoplamiento**: dependencias solo hacia abajo (UI→Hub→Particle/Shader);
ningún módulo importa de otro lateral salvo vía el bus de uniforms/eventos;
`AICore.tsx` actual queda CONGELADO y se retira cuando `<AitheraPresence/>` lo
sustituya (Fase 0) — mismo contrato con el store, cero cambios fuera del Hub/Chat.

## 13. Integración en la aplicación (decisiones de producto)

### 13.1 Dónde vive
El AVCS es un componente único `<AitheraPresence/>` montado en Hub y Chat
(instancia única compartida — nunca dos simulaciones simultáneas; al navegar,
el canvas persiste vía layout, no se re-crea).

### 13.2 Estados ↔ producto
`coreState` ya existe (idle/listening/thinking/speaking/processing/error); se
añaden `action`/`recovering` al store. Eventos backend (tarea de agente corriendo,
automatización ejecutándose en V0.9+) alimentarán Acción vía el polling/SSE actual.

### 13.3 Sin clipping (requisito Fase 0)
El canvas es **full-bleed** (cubre todo el viewport del área de contenido, bajo la
UI). La cámara se ajusta por aspect-ratio con **fit contain + margen del 12%**: el
sistema completo (radio máximo de onda) siempre cabe. Además, **falloff de borde**:
la opacidad/energía de partículas decae suavemente (smoothstep) en el 8% exterior
del frustum — la energía nunca se corta contra un borde, se desvanece. Los paneles
de UI flotan POR ENCIMA con transparencia; jamás recortan el canvas con
`overflow:hidden` de contenedores intermedios.

### 13.4 Modo Presencia (requisito Fase 0)
Un botón (esquina, icono mínimo, y tecla rápida) pliega TODA la UI: paneles se
atenúan y retiran (Fase 0: fade+slide sobrio de 400 ms; MVP2: disolución en
partículas §17). Queda solo la presencia a pantalla completa. Segundo clic/Esc
restaura. El estado persiste por página.

### 13.5 Chat limpio (requisito Fase 0)
La página Chat se rediseña: presencia central dominante + **panel lateral
flotante** (derecha, ~360-400 px, glass sobrio) con: historial compacto, input,
botones de voz (STT push/continuo), TTS on/off y conversación continua —
reutilizando los controles de voz existentes. El panel respeta el ADN visual
(bordes suaves, respiración sutil de opacidad). Durante Comunicación, la voz
mueve la presencia (§8), no el panel.

---

# PARTE IV — RENDIMIENTO

## 14. Presupuestos

60 FPS objetivo (aceptable 30 en tier mínimo). Presupuesto frame GPU ≤ 8 ms para
el AVCS (deja margen a la UI). CPU main-thread del AVCS ≤ 2 ms/frame (la sim vive
en GPU; JS solo actualiza uniforms). Draw calls del AVCS ≤ 6. Memoria GPU ≤ 160 MB
en tier alto.

## 15. Tiers de calidad

| Tier | Textura sim | Partículas | Post | Extras |
|---|---|---|---|---|
| Q1 Brasa | 64² | 4.096 | sin bloom (glow por blending) | ondas 3, sin raíces densas |
| Q2 Llama | 128² | 16.384 | bloom ligero | completo básico |
| Q3 Aurora | 256² | 65.536 | bloom selectivo | default escritorio moderno |
| Q4 Bioluminiscencia | 512² | 262.144 | bloom + slight DOF | equipos gaming |

## 16. PerformanceManager

1. **Inicial**: tier por categoría declarada (Settings; default Q2) — Fase 0/MVP1
   sin detección automática.
2. **Dinámico**: frametime p95 en ventana de 3 s; si > presupuesto durante 2
   ventanas → degradar UN nivel de la escalera; si < 60% durante 60 s → subir.
   Histéresis obligatoria (nunca oscilar).
3. **Escalera de degradación** (orden): post-processing → resolución de render
   (DPR 1.0) → tamaño de textura sim (un nivel) → complejidad de shader (octavas
   de noise 3→2) → tasa de sim (60→30 Hz con interpolación de render).
4. **Invariantes de identidad (NUNCA se degradan)**: semilla presente y cálida;
   ondas deformadas (jamás círculos perfectos "baratos"); respiración variable;
   transiciones suaves; factor de sincronía. En Q1 hay menos materia, nunca menos
   alma.

## 17. UI viva (MVP2 — especificación)

Paneles/botones **se forman**: sus bordes son SDFs a los que converge un préstamo
de partículas del campo (300-800 por panel) en 500-800 ms; al cerrarse, se
disuelven (§7.5) devolviendo las partículas. El CONTENIDO (texto, controles) es
HTML/React superpuesto cuya opacidad está esclavizada al progreso de formación
(sincronía visual, accesibilidad intacta, sin texto-partícula ilegible).
Notificaciones = brotes que florecen desde el borde. Todos los radios, curvas y
tiempos provienen de tokens compartidos del ShaderSystem/tema — un solo ADN.

## 18. Memoria visual (MemorySystem)

Madurez `M ∈ [0,1]` = función logarítmica saturante de horas de uso acumuladas
(fuente: backend, tabla Config/endpoint de stats; MVP2 la persiste formalmente).
Efectos (imperceptibles a corto plazo, < 2% de cambio por semana de uso): +
profundidad/nº de guías de raíces y ramas, respiración levemente más lenta y
profunda ("madura"), paleta un 3-5% más rica en Savia, patrones de Comprensión
con n-fold más complejo. **Jamás** barras, niveles ni desbloqueos visibles:
crecimiento, no progreso.

## 19. Detección de hardware (DISEÑO — no implementar aún)

Para el instalador de V1.0+ (enlaza con doc 12 §3-B6 y el onboarding del MVP beta):

- **Señales**: GPU (`WEBGL_debug_renderer_info` / `navigator.gpu.requestAdapter`),
  RAM (`navigator.deviceMemory` + Electron `os.totalmem()`), CPU
  (`hardwareConcurrency` + `os.cpus()`), SO, y un **microbenchmark offscreen de
  2 s** (sim FBO 128² + render; se mide frametime real — la verdad por encima de
  las specs).
- **Decisión**: tabla `(benchmark, VRAM aprox, RAM, cores)` → tier Q1-Q4 + FPS
  objetivo + DPR + **modelo Ollama recomendado** (ej.: 8 GB RAM → 3B; 16 GB → 8B;
  32 GB+GPU → 14B+) + idioma inicial (locale del SO).
- **Persistencia**: `Config` del backend (`avcs_tier`, `avcs_fps_target`,
  `ollama_recommended`), editable en Settings ("Automático (recomendado)" +
  override manual).
- **Integración preparada**: el PerformanceManager ya lee su tier inicial de
  Settings — el detector futuro solo escribe esa misma clave. Cero refactor.

---

# PARTE V — ROADMAP DE IMPLEMENTACIÓN

## 20. Fases

### FASE 0 — "Génesis" (AHORA, dentro de V0.82/0.83) — 2-3 sesiones Opus
Alcance exacto (requisitos de producto ya decididos):
1. **Semilla + Ondas de Sincronía** con el motor real (ParticleEngine FBO mínimo,
   ShaderSystem con noise/curl, RhythmEngine con 3+1 ritmos) — diseño de
   partículas "bien hecho", no placeholder.
2. Ritmos: **Reposo** (respiración §6 completa), **Escucha** simple (hundimiento +
   primeras raíces insinuadas, versión reducida de §7.3), **Comunicación** simple
   (ascenso + acople a envolvente de voz vía audioLevel existente). Los demás
   ritmos mapean provisionalmente a Reposo/Comprensión-básica.
3. **Sin clipping** (§13.3) + **Modo Presencia** (§13.4) + **Chat limpio** (§13.5).
4. PerformanceManager v0: tiers manuales Q1-Q3 + escalado dinámico básico (solo
   escalera pasos 1-3). Retirada de `AICore.tsx`.
   
Orden: S1 motor+semilla+ondas+reposo → S2 escucha+habla+audio+sin-clipping →
S3 modo presencia+chat limpio+perf v0+pulido. **Criterio de cierre**: el test de
presencia (§21.1) superado en Q2.

### MVP 1 — "Lenguaje completo" (V1.5, tras el MVP beta V1.0) — 5-7 sesiones
Los 7 ritmos completos (§4) con campos componibles íntegros (§5); raíces/ramas
maduras (§7.3-7.4) + patrones de Comprensión; factor de sincronía y Error/
Recuperación; AudioReactor completo (bandas); arquitectura modular completa;
PerformanceManager íntegro (§16); rediseño general de la UI del Hub alrededor de
la presencia (aún UI convencional sobria — la UI viva es MVP2). Sin animales, sin
memoria visual. Orden: campos→ritmos→estructuras→audio→perf→UI.

### MVP 2 — "Organismo" (V1.6+/era V2.0) — 6-8 sesiones
UI viva (§17: paneles que se forman, botones que emergen, disolución universal);
vida procedural (§9); memoria visual (§18) con persistencia; optimización avanzada
(instancing de estructuras, sim a 30 Hz interpolada en tiers bajos); preparación
WebGPU (backend de ParticleEngine intercambiable). Orden: disolución universal→
paneles→vida→memoria→optimización.

## 21. Criterios de aceptación (por fase, obligatorios)

1. **Test de presencia**: 5 personas ven el Hub 5 s sin contexto; ≥ 4 usan
   palabras de ser vivo ("respira", "está viva", "me mira") y no de software.
2. **Test de no-repetición**: 5 min de observación sin poder predecir eventos ni
   detectar bucles (grabación revisada a 4×).
3. **Test de calma**: 30 min en Reposo en segunda pantalla sin robar atención.
4. **Perf**: 60 FPS sostenidos en el tier del equipo de referencia; degradación
   dinámica verificada limitando GPU; invariantes §16.4 presentes en Q1.
5. **Transiciones**: ningún cambio de ritmo produce salto perceptible (< 1 frame
   de discontinuidad); grabar y revisar cada transición.
6. **Sin clipping**: en 16:9, 16:10, 21:9 y ventana estrecha, ninguna energía se
   corta contra bordes.

## 22. Gobernanza

Este documento solo lo modifica una decisión explícita del usuario. Cada fase
implementada añade aquí su registro (fecha, tier de referencia, desviaciones
aprobadas). Los valores numéricos (periodos, amplitudes, conteos) son **puntos de
partida calibrables**: el implementador puede ajustarlos ±30% buscando la
sensación descrita, documentando el valor final aquí. Lo NO calibrable: los
principios (§2), los invariantes (§16.4) y las prohibiciones (§11).

---
*AVCS v1.0 — Comité de diseño (Fable 5), 2026-07-09. La pregunta única gobierna:
¿hace que el usuario sienta que Aithera está viva?*
