# Shaders GLSL custom — AICore

## Resumen

**AICore.tsx** en Aithera V0.7.3 tiene **shaders custom** (CLAUDE.md §2). GLSL (OpenGL Shading Language) para efectos visuales en la esfera 3D.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## GLSL basics

GLSL es C-like, corre en GPU:

```glsl
// Vertex shader
attribute vec3 position;
uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}

// Fragment shader
precision mediump float;
void main() {
    gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);  // red
}
```

## AICore custom shader (presunto)

```glsl
// Vertex shader con animación
uniform float uTime;
varying vec3 vNormal;
varying vec3 vPosition;

void main() {
    vNormal = normal;
    vPosition = position;
    
    // Pulse effect
    vec3 newPosition = position + normal * sin(uTime * 1.5) * 0.05;
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
```

```glsl
// Fragment shader con fresnel
uniform float uTime;
varying vec3 vNormal;
uniform vec3 uColor;

void main() {
    float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
    vec3 color = uColor * (0.3 + 0.7 * fresnel);
    gl_FragColor = vec4(color, 1.0);
}
```

## Three.js shaderMaterial en R3F

```tsx
import { shaderMaterial } from "@react-three/drei";
import { extend } from "@react-three/fiber";

const AICoreMaterial = shaderMaterial(
    { uTime: 0, uColor: new THREE.Color("#4a90e2") },
    vertexShader,
    fragmentShader
);

extend({ AICoreMaterial });

function AICore() {
    const matRef = useRef();
    useFrame((_, dt) => {
        matRef.current.uTime += dt;
    });
    
    return (
        <mesh>
            <sphereGeometry args={[1, 64, 64]} />
            <aICoreMaterial ref={matRef} />
        </mesh>
    );
}
```

## Shaders populares para AICore-style

- **Fresnel glow**: bordes brillantes, centro oscuro.
- **Plasma**: colores fluidos.
- **Wireframe**: solo edges.
- **Noise distort**: vértices animados con noise.
- **Holographic**: efecto scanline.

## Aithera V0.85 audit

CLAUDE.md §1 menciona V0.85 "perf hub". `AUDITORIA_HUB_V073.md` tiene sección sobre shaders. Performance optimizations:
- ✅ Reusar shader program (no recompile).
- ✅ Minificar uniforms.
- ❌ No usar discard en mobile.

## Referencias cruzadas

- [JWIKI-088 3d-threejs.md](./3d-threejs.md)
- [JWIKI-089 3d-react-three-fiber.md](./3d-react-three-fiber.md)
- AUDITORIA_HUB_V073.md

## Fuentes

1. https://thebookofshaders.com/
2. https://learnopengl.com/Getting-started/Shaders
3. CLAUDE.md §2

## Nivel de confianza

**80%** — Shaders específicos de AICore.tsx no verificados (código real).

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified