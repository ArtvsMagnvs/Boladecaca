# Auditoría Técnica del Hub — Aithera V0.7.3

**Equipo**: Senior React Architect · Senior R3F Engineer · Three.js Graphics Engineer · UX/UI Systems Designer · Software Architect  
**Fecha**: 2026-07-04  
**Scope**: Análisis de solo lectura. Cero cambios de código.  
**Archivos inspeccionados**: `AICore.tsx` · `CoreSelector.tsx` · `PoopSphere.tsx` · `RasenganSphere.tsx` · `HubPanel.tsx` · `Hub.tsx` · `useAppStore.ts` · `drei-shim.tsx`

---

## Índice

1. Arquitectura general del sistema Hub
2. Flujo de estado: coreState y coreModel
3. CoreSelector — diseño, sub-componentes y patrones
4. AICore — análisis completo
5. Shaders GLSL — análisis técnico
6. Pipeline de renderizado: Canvases, cámara e iluminación
7. Uso de React Three Fiber (R3F)
8. Uso de Three.js
9. Drei / shim — situación actual y consecuencias
10. Escalabilidad a 20 núcleos
11. Modularidad
12. Rendimiento — análisis frame a frame
13. Mantenibilidad
14. Identidad visual y coherencia de estados
15. Hub futuro procedural
16. Qué NO tocar bajo ningún concepto
17. Qué cambiar y cómo
18. Resumen ejecutivo y prioridades

---

## 1. Arquitectura general del sistema Hub

### Capa de datos (`useAppStore.ts`)

El store Zustand gestiona **tres responsabilidades**:

- `backendConnected: boolean` — salud del backend (refresh vía `api.health()`).
- `aiStatus: AIStatus | null` — proveedor activo, modelo, fallback.
- `coreState: AICoreState` — estado del núcleo 3D (`idle | listening | thinking | speaking | processing | error`).

`pulseError()` es la única acción con lógica temporal: cambia a `error` y auto-revierte a `idle` tras 1500 ms. El resto son setters directos. La disciplina es correcta: el store no sabe nada de 3D.

### Capa de orquestación (`Hub.tsx`)

`Hub.tsx` es el único componente stateful del conjunto. Gestiona **diez estados locales** (proyectos, tareas, eventos, agentes, chat reciente, voz, email, digest, propuestas y modelo de núcleo) más un polling de 30 segundos. El modelo 3D seleccionado (`coreModel`) también vive aquí y se persiste en `localStorage` directamente — duplicando parcialmente la lógica que ya hace `CoreSelector`.

Hub inyecta `coreModel` al árbol mediante props directas a `CoreSelectorButton` y `CoreModelView`. No hay Context; no hay prop drilling profundo.

### Capa de envoltura (`CoreSelector.tsx`)

`CoreSelector` expone cuatro piezas:

| Pieza | Responsabilidad |
|---|---|
| `CoreFrame` | Anillos decorativos + ondas + glow según coreState |
| `CoreModelView` | Renderiza el modelo 3D activo + CoreFrame |
| `CoreSelectorButton` | Dropdown de selección de núcleo |
| `CoreSelector` | Wrapper de compatibilidad (button + view + localStorage) |

Hub usa `CoreSelectorButton` + `CoreModelView` **por separado**, con el estado en Hub. `CoreSelector` queda como wrapper legacy de compatibilidad (no lo usa el Hub actual).

### Capa de renderizado 3D

Tres componentes independientes, cada uno con su propio `<Canvas>`:

- `AICore` — orbe azul con shaders procedurales personalizados.
- `PoopSphere` — emoji de caca (GLB externo + moscas animadas).
- `RasenganSphere` — GLB del Rasengan con halo wireframe.

Solo uno está montado en el DOM en cada momento (el selector de `CoreModelView` es un ternario). Los otros dos no existen como nodos React.

### Árbol resumido

```
Hub
 ├── CoreSelectorButton          (dropdown en cabecera, posición absoluta)
 ├── [izquierda] HubPanel x3    (proyectos, tareas, agentes)
 ├── [centro] CoreModelView
 │    └── CoreFrame
 │         └── AICore | PoopSphere | RasenganSphere
 ├── [derecha] HubPanel x3      (eventos, chat, email)
 └── [footer] barra de estado
```

**Valoración**: la separación de capas es clara y razonable para un proyecto personal/producto en crecimiento. No hay acoplamiento circular. La única grieta es la duplicación del estado `coreModel` entre Hub y el `CoreSelector` wrapper.

---

## 2. Flujo de estado: coreState y coreModel

### coreState (global, reactivo, drive the 3D)

`coreState: AICoreState` es el único estado que fluye hacia los componentes 3D. El flujo completo es:

```
Cualquier módulo que detecte una acción
  → useAppStore.getState().setCoreState("thinking")
  → Zustand notifica suscriptores
  → Los componentes 3D leen el estado dentro del contexto R3F
  → useFrame aplica lerp hacia los parámetros del nuevo estado
```

Los tres componentes 3D suscriben a `coreState` con el mismo selector mínimo: `useAppStore((s) => s.coreState)`. Zustand solo re-renderiza cuando cambia `coreState`, no ante cambios de `aiStatus` u otras props.

**Importante**: `coreState` jamás se modifica desde dentro de los componentes 3D. Los shaders y animaciones son puramente reactivos al estado externo. Esta es una decisión arquitectónica correcta y debe preservarse.

### coreModel (local, persistido en localStorage, switch de visibilidad)

`coreModel: CoreModelId` determina qué Canvas se monta. No está en Zustand porque no necesita reactividad cross-componente: solo Hub y CoreSelectorButton lo leen.

La persistencia en `localStorage` usa la misma clave (`"aithera.coreModel"`) tanto en Hub como en `CoreSelector`, lo que crea una dependencia implícita. Si un futuro refactor mueve el estado a Zustand, la clave debe migrarse también.

**Valoración**: la decisión de separar `coreState` (Zustand) de `coreModel` (localStorage) es la correcta. El estado visual 3D es global; el modelo elegido por el usuario es preferencia local persistida.

---

## 3. CoreSelector — diseño, sub-componentes y patrones

### Análisis de `CoreFrame`

`CoreFrame` es el componente más denso de `CoreSelector.tsx`: gestiona **cuatro capas visuales** mediante `AnimatePresence`:

1. **Anillo exterior**: siempre presente, color y animación CSS según estado (`ring-idle`, `ring-listening`, etc. — estas clases deben existir en el CSS global).
2. **Anillo interior dashed**: aparece solo en `thinking` y `processing`.
3. **Ondas de escucha**: dos divs con `wave-ring` CSS, desfasados 0.7 s.
4. **Pulsos de voz**: dos divs con `wave-ring`, duración 1.2 s.

Las transiciones de entrada/salida (`opacity: 0→1→0`) están bien configuradas con `AnimatePresence`. Sin embargo, las ondas y pulsos usan clases CSS globales (`wave-ring`) que no están definidas en este archivo — son dependencias implícitas del sistema de diseño.

### Análisis de `CoreSelectorButton`

Dropdown accesible: `role="listbox"`, `role="option"`, `aria-selected`, `aria-expanded`, `aria-haspopup`. Cierre por clic fuera (usando `mousedown` en `window`, patrón correcto) y por tecla `Escape`. El `useEffect` añade/elimina listeners solo cuando `open` es `true` — eficiente.

El componente es **controlado**: el padre le pasa `value` y recibe cambios por `onChange`. Esto es correcto.

### Patrones de diseño identificados

- **Separación button / view**: permite al Hub posicionar el botón de selección en la cabecera y el modelo en el centro, sin acoplar layout y lógica.
- **Centralización del registry**: `CORE_MODELS` es el único lugar donde se define qué núcleos existen. Añadir uno nuevo requiere solo una entrada en ese array + el componente.
- **`loadStoredModel()`**: exportado como función pura, con type guard explícito sobre los tres valores válidos. Si `localStorage` devuelve un valor desconocido (ej. un modelo eliminado en el futuro), cae a `"blue_orb"` por defecto. Patrón defensivo correcto.

### Limitación detectada

`STATE_RING_COLOR` y `STATE_GLOW` mapean los 6 estados a clases Tailwind con valores de opacidad en formato `border-accent/20`, `shadow-[...]`. Estos valores están hardcodeados en el componente y no están coordinados con `STATE_CONFIG` de AICore ni con `AGITATION` de PoopSphere. Si se añade un séptimo estado en el futuro, habría que actualizar tres tablas en tres archivos distintos.

---

## 4. AICore — análisis completo

### CoreMesh

`CoreMesh` tiene cuatro responsabilidades en 89 líneas:

1. Lee `coreState` del store.
2. Crea los uniformes con `useMemo` (ejecutado una vez en el mount).
3. Anima color, intensidad, tiempo y rotación en `useFrame`.
4. Renderiza `<mesh>` con `icosahedronGeometry` y `shaderMaterial`.

La geometría usa `icosahedronGeometry args={[1, 6]}` — un icosaedro de radio 1 subdividido 6 veces, lo que genera aproximadamente 5120 triángulos. Es apropiado para un shader de desplazamiento suave; más subdivisiones darían transiciones más suaves pero elevarían el coste de vértice sin beneficio visible dado el nivel de desplazamiento actual (`n * 0.16`).

**Bug de rendimiento en `useFrame`**: en la línea que anima el color:

```typescript
(uniforms.uColor.value as THREE.Color).lerp(new THREE.Color(config.color), delta * 2.5);
```

Se instancia `new THREE.Color(config.color)` en **cada frame** (60 veces/segundo). `THREE.Color` es un objeto que el GC debe recolectar. El patrón correcto es pre-alocar un `THREE.Color` fuera del loop y reutilizarlo. Este es el único error de rendimiento en AICore.

### ThinkingParticles

`ThinkingParticles` usa un patrón correcto: si `!visible` retorna `null` antes del JSX. Sin embargo, **el hook `useFrame` se llama incondicionalmente** antes del `return null` — esto es obligatorio en React (los hooks no pueden estar después de retornos condicionales). El resultado es que el grupo de partículas siempre rota, pero no se renderiza cuando no es visible. Coste: una operación de rotación por frame aunque las partículas sean invisibles. No es crítico, pero es innecesario.

Las posiciones de partículas se generan con `useMemo` sin semilla fija — se usan `Math.random()` directamente, lo que significa que las posiciones cambian en cada hot-reload durante el desarrollo. En producción no importa.

### AICore (Canvas wrapper)

`Canvas camera={{ position: [0, 0, 3] }}` — fov por defecto (75°). Para un objeto de radio ~1, a distancia 3, el objeto ocupa aproximadamente el 60% del viewport vertical. La configuración produce el encuadre deseado.

Sin `dpr` explícito: R3F usa `window.devicePixelRatio` por defecto, lo que en pantallas Retina/HiDPI puede suponer 2× o 3× los fragmentos a shaders. En la práctica, con el shader simple de AICore esto no es un problema; con el shader más complejo de PoopSphere podría serlo.

---

## 5. Shaders GLSL — análisis técnico

### Vertex shader de AICore

```glsl
float noise(vec3 p) {
  return sin(p.x * 2.2 + uTime) * sin(p.y * 2.2 + uTime * 0.8) * sin(p.z * 2.2 + uTime * 1.3);
}
```

Este "ruido" es el producto de tres funciones seno con frecuencias iguales (2.2) y distintas velocidades temporales. No es ruido estocástico en sentido estricto (como Perlin o Simplex), sino una función periódica que produce un patrón ondulante con 3 frecuencias temporales distintas. El resultado visual es un desplazamiento orgánico pero con simetría implícita — suficientemente aleatorio a primera vista.

El desplazamiento máximo es `n * uIntensity * 0.16`. Con `uIntensity = 0.7` (estado `processing`), el desplazamiento máximo es `±0.112` unidades sobre un radio de 1 — visible pero no distorsionante. Bien calibrado.

### Fragment shader de AICore

```glsl
float fresnel = pow(1.0 - clamp(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)), 0.0, 1.0), 2.0);
vec3 glow = uColor * (0.55 + fresnel * 0.75 + vNoise * 0.18 * uIntensity);
gl_FragColor = vec4(glow, 0.82 + fresnel * 0.18);
```

El fresnel es una aproximación simple (comparando normal con la dirección de la cámara en espacio de vista, asumiendo cámara en Z+). No usa la normal de vista real (`vViewDir`), sino el vector fijo `[0,0,1]`. Esto es una simplificación válida porque la cámara está fija en `[0,0,3]` — el "frente" en espacio de modelo coincide exactamente con `[0,0,1]` en espacio de cámara. Si la cámara se moviera orbiting, el fresnel se vería incorrecto.

La transparencia (`alpha = 0.82 + fresnel * 0.18`) hace que el borde brille más (mayor fresnel → más transparente hacia el borde, más opaco en el centro). Efecto de glow de borde realista.

### Shaders de PoopSphere

PoopSphere tiene el shader más elaborado del proyecto:

**Vertex**: FBM (Fractal Brownian Motion) de 4 octavas sobre un hash de valor (no perlin, pero funcional). Dos capas de FBM con velocidades opuestas (`+uTime * 0.12` y `-uTime * 0.08`). Perturbación sumada con pesos 0.14 y 0.04.

**Fragment**: Toon shading de 3 bandas (`if ndl > 0.55 → 1.0`, `> 0.20 → 0.82`, etc.), venas horizontales con `sin(vObjPos.y * 14.0)`, oscurecimiento de valles entre rolls, motas como semillas (`step(0.86, seedHash)`), highlight especular Blinn-Phong, rim light y oscurecimiento de borde.

Este es un shader de producción completo. Está bien escrito, bien comentado y cubre todos los casos de iluminación que necesita un modelo cartoon. El coste de fragmento es mayor que el de AICore (7 operaciones vs ~3), pero completamente aceptable en GPU moderna.

### RasenganSphere

No tiene shaders GLSL personalizados. Usa `THREE.MeshStandardMaterial` clonado desde el GLB con emisión manual (`emissiveIntensity = 0.35`). El efecto visual depende completamente del modelo GLB. El halo exterior es `MeshBasicMaterial wireframe` — extremadamente barato.

### Conclusión comparativa

| Componente | Vertex complexity | Fragment complexity | Enfoque |
|---|---|---|---|
| AICore | Bajo (3 sin) | Medio (fresnel + blend) | Procedural puro |
| PoopSphere | Alto (FBM 4 oct) | Alto (toon + 6 efectos) | Procedural + GLB |
| RasenganSphere | N/A | N/A (MeshStandard) | GLB + emissive override |

---

## 6. Pipeline de renderizado: Canvases, cámara e iluminación

Cada núcleo 3D tiene su propio `<Canvas>`, lo que implica un contexto WebGL independiente. Los navegadores modernos limitan a 8-16 contextos WebGL activos por pestaña. Con un solo Canvas activo a la vez (el ternario de `CoreModelView`), esto no es un problema en absoluto.

### Configuraciones comparadas

| Canvas | position | fov | dpr | antialias | alpha | notes |
|---|---|---|---|---|---|---|
| AICore | [0,0,3] | 75° (default) | window.dpr | true | true | Mínimo necesario |
| PoopSphere | [0,0.15,3.6] | 75° (default) | window.dpr | true | true | Ligero desplazamiento Y |
| RasenganSphere | [0,0.4,4.6] | 38° | [1,2] | true | high-performance | Mejor configuración |

**RasenganSphere tiene la mejor configuración de Canvas**: `fov=38` (teleobjetivo, da sensación de profundidad al Rasengan), `dpr=[1,2]` (cap a 2× en Retina, evita 3× en pantallas de alta densidad), `powerPreference: "high-performance"`.

**AICore y PoopSphere no tienen `dpr` explícito**: en pantallas Retina esto puede resultar en pixel ratio 3 (especialmente en macOS o iPhone), triplicando el coste de fragmento. Con el Canvas del Hub en `size={900}`, esto es potencialmente `900 × 900 × 3 = 2.43M píxeles` por frame en shaders.

### Iluminación

- **AICore**: `ambientLight 0.4` + `pointLight [2,2,2] 1.2`. Mínimo efectivo para el shader (que no usa normales de forma realista en fragment — solo el fresnel).
- **PoopSphere**: `ambientLight 0.55` + `directionalLight [2.2,3,1.8] 1.8 #ffe6c8` (cálida) + `directionalLight [-2,-0.5,-1] 0.4 #7c9cff` (fill fría). Iluminación de tres puntos simplificada — correcta para cartoon.
- **RasenganSphere**: `ambientLight 0.55` + `directionalLight [3,4,5] 0.6 #cfeaff` + `directionalLight [-3,-2,3] 0.25 RASENGAN_BLUE` + `pointLight` interno al grupo (se mueve con la rotación). El punto de luz rotante es el detalle que da la impresión de "energía desde dentro".

---

## 7. Uso de React Three Fiber (R3F)

### Patrones correctos identificados

**`useFrame` para animación**: todos los componentes usan `useFrame` correctamente para actualizaciones por frame. Ninguno usa `setState` dentro de `useFrame` (lo que causaría re-renders innecesarios).

**`useMemo` para geometrías y materiales**: `AICore`, `PoopSphere` y `RasenganSphere` crean geometrías y materiales dentro de `useMemo`, evitando reinstanciación en cada render de React.

**`useRef` para meshes**: todos los meshes animados usan `useRef<THREE.Mesh>` para acceder al objeto Three.js sin forzar re-renders.

**`useLoader` para GLBs**: `PoopSphere` usa `useLoader(GLTFLoader, src)` en `FlyModel`, que integra con el sistema de Suspense de R3F correctamente. `RasenganSphere` usa `useGLTF` del shim.

### Problemas detectados

**Problema 1 — `ThinkingParticles` ejecuta `useFrame` innecesariamente**

```typescript
// Siempre se ejecuta:
useFrame((_, delta) => {
  if (groupRef.current) {
    groupRef.current.rotation.y += delta * 0.4;
    groupRef.current.rotation.x += delta * 0.15;
  }
});

// Solo después viene el early return:
if (!visible) return null;
```

`useFrame` no puede estar después de `return null` (viola las reglas de hooks). El resultado es que el grupo rota aunque no sea visible. El coste es mínimo (una operación de rotación sobre un group vacío), pero es lógicamente incorrecto. La solución correcta es usar `<group ref={groupRef} visible={visible}>` con el group siempre montado, o mover las partículas a un componente hijo que solo se monta cuando es visible.

**Problema 2 — Múltiples suscripciones al store en PoopSphere**

`PoopSphere` tiene **9 componentes** suscritos a `useAppStore((s) => s.coreState)`:
- `PoopMesh` / `PoopMeshGLTF`
- `HairTufts`
- 7 instancias de `Fly` (una por mosca)

Cada suscripción es una llamada independiente a `useAppStore`. Zustand es eficiente y notifica solo cuando el selector cambia, pero 9 suscripciones al mismo slice es innecesario. El patrón correcto es pasar `coreState` como prop desde `PoopSphere` (que ya lo lee) hacia `HairTufts` y `Flies`.

**Problema 3 — `useMemo` con efectos secundarios en RasenganSphere**

```typescript
useMemo(() => {
  scene.traverse((obj) => {
    // ... muta los materiales del scene
  });
}, [scene]);
```

`useMemo` no está diseñado para efectos secundarios — está diseñado para cómputo de valores. La mutación de materiales es un efecto secundario. En `StrictMode`, React puede ejecutar `useMemo` múltiples veces en desarrollo (aunque no en producción). El código funciona porque la mutación es idempotente, pero debería estar en `useEffect`. Como Electron no usa StrictMode habitualmente, esto no causa problemas prácticos.

---

## 8. Uso de Three.js

### Patrón de geometrías

| Componente | Geometría | Vértices aprox | Notas |
|---|---|---|---|
| AICore | IcosahedronGeometry(1, 6) | ~5120 triángulos | Correcta para shader de desplazamiento |
| PoopSphere (proc.) | LatheGeometry(profile, 96) | ~19200 triángulos | 200 puntos × 96 segmentos × 2 triángulos |
| PoopSphere (pelo) | CylinderGeometry(0.008, 0.005, 1, 5) | ~60 vértices × 36 instancias | InstancedMesh correcto |
| RasenganSphere (halo) | IcosahedronGeometry(1.55, 1) | ~80 triángulos | Muy barato (wireframe) |
| RasenganSphere (aura) | SphereGeometry(1.65, 32, 32) | ~2048 triángulos | BackSide, semi-transparente |

**LatheGeometry de PoopSphere**: 200 puntos de perfil × 96 segmentos radiales = ~19200 triángulos para el cuerpo. Cuando `USE_GLB = true` (valor actual), esta geometría no se usa. Queda como fallback procedural para cuando no haya GLB disponible.

**InstancedMesh para pelos**: uso correcto de instancing para 36 objetos idénticos (con distintas transformaciones). `dummy.updateMatrix()` + `setMatrixAt` por frame es el patrón estándar.

### Gestión de objetos Three.js por frame

**Problema crítico en AICore**:
```typescript
(uniforms.uColor.value as THREE.Color).lerp(new THREE.Color(config.color), delta * 2.5);
```
`new THREE.Color(config.color)` instancia un objeto nuevo en el heap de JavaScript **60 veces/segundo**. El Garbage Collector de V8 debe recolectar estos objetos. Con una vida útil muy corta, caen en la generación joven (scavenge GC), que es rápido, pero es presión innecesaria sobre el GC. Solución: pre-alocar un `THREE.Color` temporal fuera de `useFrame`.

**`sampleSurface()` en PoopSphere**:
Esta función interpola un punto sobre el perfil del poop y retorna un `THREE.Vector3`. Se llama **múltiples veces por frame por mosca** (en `walk`, `clean`, `takeoff`, `land`) sin pre-alocación. Cada llamada instancia un `new THREE.Vector3(...)`. Con 7 moscas en estados activos, esto puede suponer 7-21 new Vector3 por frame. Tolerable pero mejorable.

**`performance.now()` en PoopSphere**:
`HairTufts` y los cuerpos de moscas usan `performance.now() * 0.001` para animar. R3F ya proporciona el clock en `useFrame((state, delta) => ...)` vía `state.clock.elapsedTime`. El uso de `performance.now()` es redundante y más propenso a deriva entre frames.

### Gestión de instancias GLB

**RasenganSphere** clona los materiales del GLB en `useMemo` con `m.clone()` para no mutar el caché compartido de `useGLTF`. Patrón correcto.

**PoopSphere `FlyModel`** usa `useMemo(() => gltf.scene.clone(true), [gltf])` — clona la escena completa (deep clone, `true`) para que cada mosca tenga su propia jerarquía de objetos. Patrón correcto para múltiples instancias del mismo GLB.

---

## 9. Drei / shim — situación actual y consecuencias

### Historia del problema

`@react-three/drei@9.122.0` se instaló pero carece de los archivos de entrada `index.js` e `index.cjs.js`. El módulo existe en `node_modules` pero no puede importarse. Para resolverlo se creó `frontend/src/lib/drei-shim.tsx`.

### Análisis de `drei-shim.tsx`

El shim implementa:

```typescript
export function Gltf({ src, ...props }) {
  const gltf = useLoader(GLTFLoader, src);
  return <primitive object={gltf.scene} {...props} />;
}

export function useGLTF(path: string) {
  return useLoader(GLTFLoader, path);
}

useGLTF.preload = (path: string) => {
  const _gltfLoader = new GLTFLoader();
  _gltfLoader.load(path, () => {}, undefined, () => {});
};
```

**Lo que funciona**: `Gltf` y `useGLTF` para carga básica de GLBs con Suspense. Suficiente para las necesidades actuales.

**Lo que no funciona igual que drei**:
1. `useGLTF.preload` no registra el resultado en el caché de R3F. Drei usa `useLoader.preload(GLTFLoader, path)` que sí integra con el sistema de Suspense. La implementación del shim es `fire-and-forget` — puede precargar el recurso en la red, pero no garantiza que el Suspense evite el flicker la primera vez.
2. El shim no implementa `Draco` decoder, `KTX2` textures ni ningún otro loader de Drei.
3. `useGLTF` del shim retorna el objeto `GLTF` completo; drei retorna un objeto con propiedades adicionales (nodes, materials, etc.).

**Consecuencia práctica**: el shim es suficiente para los tres modelos actuales (GLBs simples sin Draco ni texturas KTX2). Si se añaden modelos comprimidos con Draco, el shim necesitará extensión.

### Opción de resolución a futuro

La ruta correcta es reinstalar drei en una versión compatible: `npm install @react-three/drei@9.x` donde x sea una versión que tenga los entry points correctos, o actualizar a `@react-three/drei@10.x`. El shim puede eliminarse en ese momento.

---

## 10. Escalabilidad a 20 núcleos

La arquitectura actual soporta la adición de nuevos núcleos con cambios mínimos y bien localizados.

### Pasos para añadir un nuevo núcleo (ej. "Cristal")

1. **Crear `CrystalSphere.tsx`** siguiendo el patrón: props `{ size, audioLevel }`, propio `<Canvas>`, mapeado de `coreState` a parámetros.

2. **Registrar en `CoreSelector.tsx`**:
```typescript
const CORE_MODELS: CoreModel[] = [
  // existentes...
  {
    id: "crystal",
    label: "Cristal",
    shortLabel: "Cristal",
    hint: "Núcleo cristalino con refracciones",
    dotClass: "bg-cyan-300",
  },
];
```

3. **Añadir al tipo `CoreModelId`**:
```typescript
export type CoreModelId = "blue_orb" | "poop_sphere" | "rasengan" | "crystal";
```

4. **Añadir a `CoreModelView`**:
```typescript
: model === "crystal" ? (
  <CrystalSphere size={size} audioLevel={0} />
) : (
  // fallback
)
```

5. **Añadir a `loadStoredModel()`** el nuevo id en el type guard.

Con 20 núcleos, la cadena `model === "blue_orb" ? ... : model === "poop_sphere" ? ...` se vuelve ilegible. La mejora natural es un mapa de componentes:

```typescript
const CORE_COMPONENTS: Record<CoreModelId, React.ComponentType<{size: number, audioLevel: number}>> = {
  blue_orb: AICore,
  poop_sphere: PoopSphere,
  rasengan: RasenganSphere,
};
```

Y en `CoreModelView`:
```typescript
const Component = CORE_COMPONENTS[model];
return <Component size={size} audioLevel={0} />;
```

### Límites reales

- **Bundle**: cada núcleo añade peso al bundle de JavaScript. Con 20 núcleos y algunos con shaders complejos, el bundle puede crecer significativamente. Considerar lazy loading por modelo.
- **GLBs**: los modelos GLB suman en disco (poop.glb=18MB, rasengan.glb=16MB). Con 20 núcleos GLB, el directorio `public/models/` podría superar 300MB. Considerar CDN o carga bajo demanda.
- **Múltiples `useFrame`**: cada núcleo activo tiene su loop de animación. Solo uno está activo a la vez, por lo que esto no es un problema real.

---

## 11. Modularidad

### Tamaño de archivos

| Archivo | Líneas | Responsabilidades | Valoración |
|---|---|---|---|
| `AICore.tsx` | 149 | Shaders + mesh + partículas + Canvas | ✅ Tamaño adecuado |
| `CoreSelector.tsx` | 440 | 4 sub-componentes + tipos + constantes | ⚠️ Podría dividirse |
| `PoopSphere.tsx` | 837 | Cuerpo + pelo + moscas (FSM) + Canvas | ❌ Demasiado grande |
| `RasenganSphere.tsx` | 197 | GLB + halo + aura + Canvas | ✅ Tamaño adecuado |
| `HubPanel.tsx` | 32 | Panel de cristal reutilizable | ✅ Mínimo |
| `Hub.tsx` | 718 | Orquestación + 6 paneles + polling | ⚠️ Denso pero justificado |
| `useAppStore.ts` | 47 | Estado global | ✅ Mínimo |

### PoopSphere como caso de estudio

`PoopSphere.tsx` con 837 líneas es el único módulo que rompe el principio de responsabilidad única. Contiene:
- Perfil procedural del cuerpo (`generatePoopProfile`)
- Shaders GLSL del cuerpo (vertex + fragment)
- Mesh del cuerpo (`PoopMesh`, `PoopMeshGLTF`, `PoopMeshWrapper`)
- Pelusas (`HairTufts`)
- Sistema de moscas con máquina de estados completa (`FlySpec`, `FlyRuntime`, `FlyState`, `makeRuntime`, `FlyModel`, `Fly`, `Flies`)
- Utilidades (`mulberry32`, `sampleSurface`)
- Canvas wrapper (`PoopSphere`)

La máquina de estados de las moscas (walk → clean → takeoff → fly → land) es un sistema complejo que merece su propio archivo. En el estado actual, encontrar el código de la mosca requiere desplazarse 400 líneas hacia abajo.

### `CoreSelector.tsx` como caso de estudio positivo

Aunque tiene 440 líneas, la separación de sus 4 sub-componentes es clara y cada uno tiene una responsabilidad bien definida. Es denso, no complejo.

---

## 12. Rendimiento — análisis frame a frame

### Coste estimado por frame (60 fps)

**AICore activo** (frame budget más barato):
- 1 llamada `useFrame` para CoreMesh
- 1 llamada `useFrame` para ThinkingParticles (siempre, aunque no visible)
- ~5120 vértices procesados por vertex shader
- ~width×height píxeles procesados por fragment shader
- 1 `new THREE.Color()` instanciado y descartado (presión GC)

**PoopSphere activo con USE_GLB=true** (frame budget más caro):
- 1 llamada `useFrame` para PoopMeshGLTF
- 1 llamada `useFrame` para HairTufts
- 7 llamadas `useFrame` para moscas
- 9 lecturas al store de Zustand por frame (1 por PoopMeshGLTF + 1 por HairTufts + 7 por moscas)
- N llamadas a `sampleSurface()` según estados de moscas activas
- N instancias de `new THREE.Vector3()` por frame

**RasenganSphere activo** (frame budget moderado):
- 1 llamada `useFrame` para RasenganMesh
- Rotación y lerp de parámetros
- Sin `new THREE.XXX()` en useFrame ✅

### El elefante en la habitación: `size={900}` en Hub.tsx

```typescript
<CoreModelView model={coreModel} size={900} .../>
```

El Canvas se renderiza a 900×900 píxeles. Con `window.devicePixelRatio = 2` (pantalla Retina), son **1800×1800 = 3.24 millones de píxeles** procesados por el fragment shader en cada frame. Para el shader de AICore, esto es aceptable (shader simple). Para el shader de PoopSphere (FBM de 4 octavas), podría ser un problema en hardware integrado.

RasenganSphere tiene `dpr={[1,2]}` — por lo que se limita a 1800×1800 máximo. AICore y PoopSphere no tienen este cap: en un dispositivo con dpr=3 (algunos móviles, aunque Aithera es desktop-only hoy), serían 2700×2700 = 7.29 millones de píxeles.

**Recomendación**: añadir `dpr={[1, 2]}` a los Canvas de AICore y PoopSphere.

### Presión de memoria

Los GLBs cargados permanecen en el caché de `useLoader` durante toda la sesión. Si el usuario cambia de núcleo varias veces, el GLB del modelo anterior permanece en memoria (texture data, geometry buffers en GPU). Con tres modelos y GLBs de ~16-18 MB cada uno, la VRAM consumida puede ser de ~50-60 MB solo en modelos del Hub.

---

## 13. Mantenibilidad

### Lo que es fácil de cambiar

- **Parámetros de estado**: editar `STATE_CONFIG` (AICore), `AGITATION` (PoopSphere) o `STATE_SPIN` (RasenganSphere) es trivial. Cada tabla tiene una fila por estado y las claves son auto-documentadas.
- **Colores del sistema**: `STATE_RING_COLOR` y `STATE_GLOW` en CoreSelector centralizan los colores del marco decorativo.
- **Añadir estados 3D**: si se añade un séptimo estado de IA, solo hace falta añadir una fila a tres tablas.
- **Umbrales de comportamiento de moscas**: `flyProb`, `walkSpeed`, `orbitRadius`, etc. están como constantes claras en `AGITATION` y en los specs de `FLY_SPECS`.

### Lo que es difícil de cambiar

- **El vertex shader de AICore**: cualquier cambio en la función de ruido cambia la identidad visual del producto. No tiene tests visuales automatizados — los cambios deben evaluarse visualmente.
- **La máquina de estados de las moscas**: el FSM de 5 estados entrelazado dentro de un único `useFrame` con un `switch` de 120 líneas es difícil de extender sin riesgo de romper transiciones.
- **La geometría del poop**: `generatePoopProfile()` con sus 3 rolls gaussianos está bien documentada, pero cambiar la silueta requiere entender la matemática de las curvas LatheGeometry.

### Documentación

El código del Hub es el mejor documentado del proyecto. Todos los archivos tienen:
- Comentario de cabecera con propósito y decisiones de diseño.
- Secciones separadas por comentarios delimitadores (especialmente PoopSphere).
- Explicaciones inline en los puntos no obvios.

Las decisiones de diseño más importantes están explícitas: "Estado persistido en localStorage (sobrevive a recargas, sin acoplar a Zustand)" en `CoreSelector.tsx`, "AICore.tsx NO se modifica" en `Hub.tsx`.

### Onboarding

Un nuevo ingeniero puede entender el sistema en aproximadamente 2 horas de lectura. El punto de entrada es `Hub.tsx`, que describe el layout en el comentario de cabecera con diagrama ASCII. La progresión `Hub → CoreSelector → AICore/PoopSphere/RasenganSphere → useAppStore` es natural.

---

## 14. Identidad visual y coherencia de estados

### Paleta del sistema de estados

| Estado | AICore (color shader) | CoreFrame (ring/glow) | Semántica |
|---|---|---|---|
| idle | `#5EA8FF` (azul medio) | `border-accent/20` (sutil) | Reposo, disponible |
| listening | `#8FD9FF` (azul claro) | `border-accent-glow/60` + waves | Atención activa |
| thinking | `#7C9CFF` (azul-violeta) | `border-accent-soft/50` + inner ring | Procesamiento interno |
| speaking | `#5EA8FF` (azul medio) | `border-accent/55` + pulsos | Salida de voz |
| processing | `#7C9CFF` (azul-violeta) | `border-accent-soft/45` + inner ring | Ejecución de tarea |
| error | `#D9756F` (rojo-naranja) | `border-signal-error/50` | Alerta |

La paleta es coherente: azules fríos para estados de información (idle, listening), azules-violeta para estados de cómputo (thinking, processing), azul puro para output de voz, rojo para error. El sistema de CSS variables (`--accent`, `--accent-glow`, `--accent-soft`, `--signal-error`) permite cambiar toda la paleta desde un solo fichero de estilos.

### Coherencia entre núcleos

`AICore` y `PoopSphere` tienen tablas de parámetros propias (`STATE_CONFIG`, `AGITATION`) que son **temáticamente coherentes** pero **estructuralmente independientes**. Las curvas de intensidad van en la misma dirección (más animación en thinking/processing, menos en idle), pero los valores son diferentes — apropiado dado que cada modelo tiene sensibilidades distintas.

`RasenganSphere` tiene `STATE_SPIN` con velocidades de rotación: idle=5.5 rad/s (ya rápido), thinking=14 rad/s, error=4 rad/s. La semántica es la misma pero el registro visual es completamente diferente al orbe azul — un Rasengan "idle" gira a velocidad constante alta porque eso define al jutsu.

### Lo que podría mejorar

Los tres modelos reaccionan a `coreState` pero ninguno reacciona a `audioLevel` excepto AICore (con modulación parcial en el fragmento). PoopSphere recibe `audioLevel` como prop pero el valor pasado desde `CoreModelView` es siempre `0`:

```typescript
<PoopSphere size={size} audioLevel={0} />
<RasenganSphere size={size} audioLevel={0} />
```

Esto es un placeholder explícito (futuro). Cuando se integre el pipeline de voz, los tres modelos podrán modular su animación con el nivel de audio real.

---

## 15. Hub futuro procedural

La solicitud de un Hub "procedural completo" sugiere una futura versión donde el núcleo central sea más contextual, dinámico o personalizable. La arquitectura actual ya lo permite con los siguientes ganchos:

### Lo que el Hub ya tiene

- Un sistema de registro de núcleos (`CORE_MODELS`) que es el único punto de adición.
- Un `CoreFrame` que aplica decoración visual uniforme independientemente del modelo interior.
- Un `coreState` con 6 estados semánticos que los modelos pueden interpretar a su manera.
- Un `audioLevel` prop que llega a los tres modelos (aunque solo AICore lo usa hoy).

### Extensiones naturales

**Núcleo generativo contextual**: un núcleo que cambie de geometría o shader según el contexto de la conversación (ej. activa una constelación de estrellas cuando se habla de astronomía) sería simplemente un nuevo `CoreModelId` con un componente que lee más slices del store.

**Núcleo personalizable por el usuario**: el sistema `CORE_MODELS` + `loadStoredModel` es la infraestructura para permitir que el usuario descargue y cargue sus propios modelos GLB. Requeriría añadir soporte de modelos dinámicos al registro.

**Ambiente procedural**: `CoreFrame` hoy solo tiene anillos CSS. Una versión futura podría añadir partículas R3F en el `CoreFrame` mismo — un Canvas de fondo que persiste mientras el modelo interior se intercambia. Esto requeriría mover el Canvas de ambiente fuera de cada core individual.

**Hub fullscreen con paneles plegables**: la especificación del roadmap (V0.82 — Hub Visual) menciona modo pantalla completa con paneles desplegables. El layout CSS Grid actual (`280px / 1fr / 280px`) soporta esto con media queries o toggles de clases.

---

## 16. Qué NO tocar bajo ningún concepto

### 1. El vertex y fragment shader de AICore

```typescript
const vertexShader = `...`
const fragmentShader = `...`
```

Estos 30 líneas de GLSL son el corazón visual del producto. El patrón de ruido (tres senos desfasados), el fresnel, la transparencia de borde — definen la identidad visual de Aithera. Cualquier cambio altera la personalidad del agente. Si se quiere experimentar, crear un nuevo `CoreModelId`, nunca editar el shader existente.

### 2. `STATE_CONFIG` en AICore

Las 6 filas de `STATE_CONFIG` son el resultado de ajuste visual iterativo. Representan la "personalidad" de cada estado. No deben cambiarse sin revisión visual explícita.

### 3. El contrato de `AICoreState` en `useAppStore.ts`

El tipo `AICoreState` y los 6 estados son el contrato entre la lógica de negocio y el sistema visual. Múltiples módulos del backend y frontend dependen de este enum. Añadir un estado requiere actualizar 6+ ficheros (store, AICore, PoopSphere, RasenganSphere, CoreSelector, y cualquier componente que mapee estados a labels).

### 4. La API de `CoreModelView`

```typescript
<CoreModelView model={coreModel} size={size} linkToChat={bool} onNavigateToChat={fn} />
```

Esta interfaz es el contrato entre el layout del Hub y el sistema de núcleos 3D. Cambiarla rompe el Hub.

### 5. El patrón `useRef` para uniforms en AICore

```typescript
const uniforms = useMemo(() => ({ uTime: { value: 0 }, ... }), []);
// Dentro de useFrame: uniforms.uTime.value += delta; // NO setState
```

Este es el patrón correcto de R3F para actualizar uniforms sin re-renders. Sustituirlo por `useState` causaría re-renders de React por cada frame y destruiría el rendimiento.

### 6. La máquina de estados de las moscas

La FSM de las moscas (`walk→clean→takeoff→fly→land`) está bien calibrada visualmente. Editar los tiempos de duración de estado, velocidades o probabilidades de transición requiere revisión visual. El comportamiento actual es parte de la personalidad del componente.

---

## 17. Qué cambiar y cómo

Las siguientes mejoras están ordenadas de mayor a menor impacto y son todas de alcance limitado.

### Cambio 1 — Pre-alocar `THREE.Color` temporal en AICore (URGENTE)

**Problema**: `new THREE.Color(config.color)` se instancia 60 veces/segundo en `useFrame`.

**Solución**: pre-alocar fuera del loop.

```typescript
// Fuera del componente, a nivel de módulo:
const _tmpColor = new THREE.Color();

// Dentro de useFrame:
(uniforms.uColor.value as THREE.Color).lerp(_tmpColor.set(config.color), delta * 2.5);
```

**Impacto**: elimina presión sobre el GC. **Riesgo**: cero.

### Cambio 2 — Añadir `dpr={[1, 2]}` a Canvas de AICore y PoopSphere

**Problema**: sin `dpr` explícito, en Retina el canvas puede crecer a 3600×3600 en dpr=4.

**Solución**: añadir `dpr={[1, 2]}` al Canvas de ambos componentes, igual que RasenganSphere.

**Impacto**: rendimiento más predecible en cualquier pantalla. **Riesgo**: mínimo — la imagen puede parecer ligeramente menos nítida en dpr=3+, pero Aithera es app de escritorio Windows donde dpr raramente supera 2.

### Cambio 3 — Reducir suscripciones al store en PoopSphere

**Problema**: 9 componentes suscriben a `coreState` individualmente.

**Solución**: leer `coreState` una sola vez en `PoopSphere` y pasarlo como prop a `HairTufts` y `Flies`.

```typescript
export function PoopSphere({ size = 280, audioLevel = 0 }: PoopSphereProps) {
  const coreState = useAppStore((s) => s.coreState);  // ← única suscripción
  return (
    <Canvas ...>
      <PoopMeshWrapper audioLevel={audioLevel} coreState={coreState} />
      {!USE_GLB && <HairTufts coreState={coreState} />}
      <Flies coreState={coreState} />
    </Canvas>
  );
}
```

**Impacto**: reduce de 9 a 1 las suscripciones al store. **Riesgo**: requiere actualizar interfaces de props de 3 sub-componentes.

### Cambio 4 — Corregir `ThinkingParticles` para evitar rotación invisible

**Problema**: el grupo de partículas rota aunque no sea visible.

**Solución**: usar `visible` prop en lugar de `return null`:

```typescript
return (
  <group ref={groupRef} visible={visible}>
    <points>...</points>
  </group>
);
```

Con `visible={false}`, R3F no procesa los hijos en el render pass de WebGL, pero la rotación del `useFrame` sigue siendo innecesaria. Para parar completamente el loop cuando no es visible, usar `<group ref={groupRef}>` y en `useFrame` hacer early return si `!visible`.

**Impacto**: limpieza lógica. **Riesgo**: cero.

### Cambio 5 — Revisar `size={900}` en Hub.tsx

**Problema**: el Canvas se renderiza a 900×900px, lo cual puede ser excesivo dependiendo del viewport real.

**Solución**: determinar empíricamente si la columna central del grid puede ser más pequeña. En un monitor de 1920×1080 con la barra lateral, la columna central (`1fr`) tiene aproximadamente 1920 - 280 - 280 - 32 = 1328px de ancho. Un Canvas de 900×900 encaja. Pero en un laptop de 1366×768, el canvas de 900px puede superar el espacio disponible.

**Opción alternativa**: usar `size` dinámico basado en viewport con un `useResizeObserver` o simplemente usar `min(900, 60vh)` vía CSS.

**Impacto**: mejora en portátiles. **Riesgo**: bajo.

### Cambio 6 — Dividir PoopSphere.tsx

**Problema**: 837 líneas con 4 sistemas distintos.

**Solución**: extraer el sistema de moscas a `frontend/src/components/hub/Flies.tsx`.

```
PoopSphere.tsx (~400 líneas) — body, shaders, hairs, canvas
Flies.tsx (~450 líneas) — FSM, FlyModel, Fly, Flies, FlySpec, FlyRuntime
```

**Impacto**: mantenibilidad. **Riesgo**: refactor de importaciones, bajo.

### Cambio 7 — Elevar `coreModel` a Zustand (opcional, largo plazo)

**Problema**: `coreModel` está en `useState` del Hub y se duplica con la lógica de `CoreSelector` wrapper.

**Solución**: añadir `coreModel` al store de Zustand con persistencia en `localStorage` mediante el middleware `zustand/middleware/persist`. El `CoreSelector` wrapper quedaría como wrapper de compatibilidad o se eliminaría.

**Impacto**: simplifica el Hub, elimina la duplicación de `CORE_MODEL_STORAGE_KEY`. **Riesgo**: medio — requiere testing de la persistencia y del comportamiento en SSR (aunque Electron no tiene SSR).

---

## 18. Resumen ejecutivo y prioridades

### Estado general: SÓLIDO

El sistema Hub de Aithera V0.7.3 es un trabajo de ingeniería de calidad para un producto personal. La separación de capas es correcta, el contrato Zustand ↔ 3D es limpio, y el sistema de intercambio de núcleos (`CoreSelector`) es una arquitectura que escala bien hasta 20+ modelos con cambios mínimos.

Los tres núcleos tienen personalidades visuales distintas y coherentes. `AICore` es la identidad del producto; `PoopSphere` y `RasenganSphere` son extensiones que demuestran la flexibilidad del sistema.

No hay bugs bloqueantes. Los problemas detectados son de rendimiento (pre-alocación de objetos Three.js), configuración (dpr), estructura (suscripciones al store) y tamaño de archivo (PoopSphere monolítico).

### Matriz de prioridades

| Prioridad | Cambio | Impacto | Riesgo | Esfuerzo |
|---|---|---|---|---|
| 🔴 P0 | Pre-alocar `THREE.Color` en AICore | Elimina presión GC | Cero | 5 min |
| 🔴 P0 | Añadir `dpr={[1,2]}` a AICore y PoopSphere | Rendimiento en HiDPI | Mínimo | 5 min |
| 🟡 P1 | Reducir suscripciones al store en PoopSphere | Eficiencia Zustand | Bajo | 30 min |
| 🟡 P1 | Corregir rotación invisible en ThinkingParticles | Limpiar lógica | Cero | 10 min |
| 🟢 P2 | Revisar/dinamizar `size={900}` en Hub | Adaptabilidad viewport | Bajo | 30 min |
| 🟢 P2 | Dividir PoopSphere.tsx (extraer Flies.tsx) | Mantenibilidad | Bajo | 1h |
| 🔵 P3 | Elevar `coreModel` a Zustand + persist | Simplificación arquitectura | Medio | 2h |
| 🔵 P3 | Actualizar `@react-three/drei` o mantener shim | Eliminar deuda técnica | Bajo | 30 min test |

### Lo que está bien y debe quedar así

- La arquitectura de 4 capas (store → Hub → CoreSelector → Core3D).
- El contrato `coreState` como único canal de comunicación hacia el 3D.
- Los vertex/fragment shaders de AICore — identidad visual intocable.
- Las tablas de configuración por estado (`STATE_CONFIG`, `AGITATION`, `STATE_SPIN`) — patrón correcto y extensible.
- `CoreFrame` como decorador agnóstico del modelo interior.
- La máquina de estados de las moscas — compleja pero bien construida y documentada.
- El uso de `useMemo` para geometrías y materiales.
- El patrón `useRef` para uniforms dentro de `useFrame`.

### Próximo hito: V0.82 — Hub Visual

Las mejoras de V0.82 (animación de conversación en el Hub, modo fullscreen con paneles plegables) se apoyan sobre esta base. El sistema de paneles (`HubPanel`) ya es CSS Grid puro — los paneles plegables se implementan añadiendo clases `hidden` o transiciones de anchura. La animación de conversación puede implementarse como un nuevo panel central o como un overlay animado con Framer Motion sobre `CoreFrame`.

Nada en la arquitectura actual bloquea V0.82.

---

*Auditoría completada — 2026-07-04*  
*Archivos analizados: 8 | Líneas de código revisadas: ~2000 | Cambios de código realizados: 0*
