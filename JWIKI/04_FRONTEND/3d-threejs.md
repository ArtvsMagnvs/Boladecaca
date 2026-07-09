# Three.js — 3D engine para AICore

## Resumen

**Three.js 0.160** es el motor 3D usado en Aithera V0.7.3 para el AICore (esfera 3D en el Hub). Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Three.js 0.160.0 (CLAUDE.md §2). Stable release.

## Por qué Three.js

- ✅ **WebGL standard** (WebGL2).
- ✅ **Ecosistema masivo**.
- ✅ **React Three Fiber** wrapper (CLAUDE.md §2).
- ✅ **drei** helpers (Environment, OrbitControls, etc.).

## AICore en Aithera

AICore es una **esfera 3D** en el Hub con **shaders custom** (CLAUDE.md §2: "AICore.tsx con shaders custom").

```tsx
// frontend/src/components/hub/AICore.tsx (sketch)
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { Sphere, Environment, OrbitControls } from "@react-three/drei";

function AICore() {
    return (
        <Canvas>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} />
            
            <Sphere args={[1, 64, 64]}>
                <meshStandardMaterial
                    color="#4a90e2"
                    roughness={0.3}
                    metalness={0.8}
                />
            </Sphere>
            
            <Environment preset="city" />
            <OrbitControls />
        </Canvas>
    );
}
```

## Performance

- ✅ **InstancedMesh** para objects repetidos.
- ✅ **Frustum culling** (built-in).
- ✅ **LOD** (level of detail) para escenas complejas.
- ❌ **No usar geometries > 100K tris** sin optimizar.
- ❌ **No poner 100+ lights**.

## Aithera V0.85+ ideas

- **Shaders custom para el AICore**: glow, pulse, particles.
- **Hub con más 3D**: proyectos como nodos, conexiones como aristas.
- **V0.85 audit** (CLAUDE.md §1): "perf hub" — optimizations de render.

## Referencias cruzadas

- [JWIKI-089 3d-react-three-fiber.md](./3d-react-three-fiber.md)
- [JWIKI-090 animations-framer.md](./animations-framer.md)
- [JWIKI-204 electron-tauri.md](../13_DEPLOYMENT/electron-tauri.md)

## Fuentes

1. https://threejs.org/
2. CLAUDE.md §2
3. AUDITORIA_HUB_V073.md (audit document)

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified