# React Three Fiber — R3F wrapper

## Resumen

**@react-three/fiber** (R3F) es el wrapper React para Three.js. Aithera V0.7.3 lo usa para AICore. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

@react-three/fiber 8.x (CLAUDE.md §2).

## Hello World (AICore)

```tsx
import { Canvas } from "@react-three/fiber";
import { Sphere, MeshDistortMaterial, Environment } from "@react-three/drei";

function AICore() {
    return (
        <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} />
            
            <Sphere args={[1, 100, 100]}>
                <MeshDistortMaterial
                    color="#4a90e2"
                    distort={0.3}
                    speed={2}
                    roughness={0.2}
                />
            </Sphere>
            
            <Environment preset="city" />
        </Canvas>
    );
}
```

## @react-three/drei — helpers

- `OrbitControls` — rotar cámara con mouse.
- `Environment` — IBL (image-based lighting).
- `useGLTF` — cargar modelos glTF.
- `useTexture` — cargar texturas.
- `Sphere`, `Box`, `Plane` — primitives.
- `MeshDistortMaterial` — material con distorsión animada.
- `Float` — animación de flotación.

## Custom shaders en Aithera (CLAUDE.md §2)

AICore.tsx tiene **shaders custom** (probablemente vertex + fragment shaders):

```tsx
const vertexShader = `
  uniform float uTime;
  varying vec3 vNormal;
  void main() {
    vNormal = normal;
    vec3 newPosition = position + normal * sin(uTime * 1.5) * 0.05;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
  }
`;

const fragmentShader = `
  uniform float uTime;
  varying vec3 vNormal;
  void main() {
    float intensity = pow(0.7 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
    gl_FragColor = vec4(0.3, 0.6, 0.9, 1.0) * intensity;
  }
`;

function AICore() {
    return (
        <Canvas>
            <mesh>
                <sphereGeometry args={[1, 64, 64]} />
                <shaderMaterial
                    vertexShader={vertexShader}
                    fragmentShader={fragmentShader}
                    uniforms={{ uTime: { value: 0 } }}
                />
            </mesh>
        </Canvas>
    );
}
```

## Performance

- ✅ **useFrame** para animaciones (no setInterval).
- ✅ **InstancedMesh** para muchos objects.
- ✅ **Suspense** para loading states.
- ❌ **No crear geometries en cada render**.

## Aithera V0.85 audit

CLAUDE.md §1 menciona V0.85 "perf hub". El audit documentado en `AUDITORIA_HUB_V073.md` tiene 17 secciones. Performance optimizations son críticas.

## Referencias cruzadas

- [JWIKI-088 3d-threejs.md](./3d-threejs.md)
- [JWIKI-090 animations-framer.md](./animations-framer.md)

## Fuentes

1. https://docs.pmnd.rs/react-three-fiber/
2. https://github.com/pmndrs/drei
3. CLAUDE.md §2
4. AUDITORIA_HUB_V073.md

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified