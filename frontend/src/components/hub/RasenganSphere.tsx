// RasenganSphere.tsx — Rasengan (Naruto) como tercer nucleo 3D del Hub (V0.7 extra).
//
// Idea:
// - Carga el GLB del Rasengan (esfera azul con tres anillos concentricos tipicos
//   del jutsu de Naruto) y lo hace girar rapido sobre su eje.
// - Anade un halo azul procedural alrededor (esfera wireframe emisiva) para
//   reforzar el "glow" caracteristico del Rasengan aunque el GLB no tenga
//   emision.
// - Reactividad al coreState de Aithera: cuando el nucleo esta activo
//   (thinking/speaking/processing/listening) el Rasengan gira mas rapido y
//   el halo pulsa mas fuerte. En idle, gira suave y constante (como un
//   Rasengan "en reposo").
// - Como el modelo pesa 16 MB, se usa useGLTF.preload opcional en el padre.
//
// NO se superpone con la bola de caca ni con el orbe azul: vive en su
// propia entrada del CoreSelector y solo se monta cuando el usuario lo
// elige desde el dropdown.

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF } from "@/lib/drei-shim";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import { useAppStore, type AICoreState } from "@/store/useAppStore";

// Velocidad de rotacion (rad/s) segun estado del core. El Rasengan debe
// girar rapido SIEMPRE (es su rasgo visual), pero escala segun actividad.
const STATE_SPIN: Record<AICoreState, { spinY: number; spinX: number; haloPulse: number }> = {
  idle:       { spinY: 5.5,  spinX: 0.8,  haloPulse: 0.25 },
  listening:  { spinY: 9.0,  spinX: 1.4,  haloPulse: 0.55 },
  thinking:   { spinY: 14.0, spinX: 2.2,  haloPulse: 0.85 },
  speaking:   { spinY: 11.0, spinX: 1.6,  haloPulse: 0.65 },
  processing: { spinY: 13.0, spinX: 2.0,  haloPulse: 0.80 },
  error:      { spinY: 4.0,  spinX: 0.4,  haloPulse: 0.30 },
};

// Color base del Rasengan (azul cian brillante, tipo "chakra de Naruto").
const RASENGAN_BLUE = new THREE.Color("#7DD3FC");
const RASENGAN_DEEP = new THREE.Color("#1E3A8A");

interface RasenganMeshProps {
  /** Audio level 0..1 (placeholder para futura modulacion). */
  audioLevel?: number;
}

function RasenganMesh({ audioLevel = 0 }: RasenganMeshProps) {
  const groupRef = useRef<THREE.Group>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const haloMatRef = useRef<THREE.MeshBasicMaterial>(null);
  const coreState = useAppStore((s) => s.coreState);

  // Carga del GLB. Suspense lo gestiona arriba en el padre.
  const { scene } = useGLTF("/models/rasengan.glb");

  // Estado objetivo (cambio suave con lerp manual).
  const target = useRef(STATE_SPIN.idle);
  target.current = STATE_SPIN[coreState];

  // Valores actuales (interpolados).
  const current = useRef({ spinY: target.current.spinY, spinX: target.current.spinX, haloPulse: target.current.haloPulse });

  // Tinte material del GLB: aplicamos un color emisivo azul para que el
  // Rasengan "brille" sin necesidad de un HDR environment map.
  useMemo(() => {
    scene.traverse((obj) => {
      if ((obj as THREE.Mesh).isMesh) {
        const mesh = obj as THREE.Mesh;
        mesh.castShadow = false;
        mesh.receiveShadow = false;
        const mat = mesh.material as THREE.Material | THREE.Material[];
        const apply = (m: THREE.Material) => {
          // Hacemos una copia para no mutar el material cacheado por drei.
          const cloned = m.clone() as THREE.MeshStandardMaterial;
          cloned.emissive = RASENGAN_BLUE.clone();
          cloned.emissiveIntensity = 0.35;
          if (cloned.color) {
            // Mezcla 35% del azul Rasengan sobre el color original.
            cloned.color = cloned.color.clone().lerp(RASENGAN_BLUE, 0.35);
          }
          cloned.toneMapped = true;
          mesh.material = cloned;
        };
        if (Array.isArray(mat)) {
          mesh.material = mat.map(apply) as unknown as THREE.Material[];
        } else {
          apply(mat);
        }
      }
    });
  }, [scene]);

  useFrame((_state, dt) => {
    // Lerp suave hacia el target del estado actual (evita saltos bruscos).
    const k = 1 - Math.pow(0.001, dt); // ~constante de tiempo 0.1s
    current.current.spinY += (target.current.spinY - current.current.spinY) * k;
    current.current.spinX += (target.current.spinX - current.current.spinX) * k;
    current.current.haloPulse += (target.current.haloPulse - current.current.haloPulse) * k;

    if (groupRef.current) {
      groupRef.current.rotation.y += current.current.spinY * dt;
      groupRef.current.rotation.x += current.current.spinX * dt;
      // Subtle bob vertical cuando esta activo (sensacion de "energia viva").
      const bob = coreState === "idle" ? 0 : Math.sin(performance.now() * 0.003) * 0.02;
      groupRef.current.position.y = bob;
    }

    if (haloRef.current) {
      // Pulso del halo: escala oscilante + opacidad variable.
      const t = performance.now() * 0.002;
      const pulse = 1.0 + Math.sin(t) * current.current.haloPulse * 0.08;
      haloRef.current.scale.setScalar(pulse);
    }

    if (haloMatRef.current) {
      haloMatRef.current.opacity =
        0.10 + current.current.haloPulse * 0.12 + audioLevel * 0.15;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Modelo GLB */}
      <primitive object={scene} />

      {/* Halo azul exterior — esfera wireframe emisiva */}
      <mesh ref={haloRef}>
        <icosahedronGeometry args={[1.55, 1]} />
        <meshBasicMaterial
          ref={haloMatRef}
          color={RASENGAN_BLUE}
          wireframe
          transparent
          opacity={0.18}
          toneMapped={false}
          depthWrite={false}
        />
      </mesh>

      {/* Aura azul interior difusa */}
      <mesh>
        <sphereGeometry args={[1.65, 32, 32]} />
        <meshBasicMaterial
          color={RASENGAN_BLUE}
          transparent
          opacity={0.07}
          toneMapped={false}
          depthWrite={false}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Sphere invisible para debug si hicera falta, no se renderiza. */}
      {/* Luz puntual azul que anade "luz desde dentro" al Rasengan. */}
      <pointLight color={RASENGAN_BLUE} intensity={0.9} distance={6} decay={1.6} />
    </group>
  );
}

export interface RasenganSphereProps {
  /** Tamano del area del modelo en pixeles. */
  size?: number;
  /** Audio level 0..1. */
  audioLevel?: number;
}

export function RasenganSphere({ size = 280, audioLevel = 0 }: RasenganSphereProps) {
  return (
    <div
      style={{ width: size, height: size }}
      className="relative"
      aria-label="Rasengan (Naruto) - nucleo 3D"
    >
      <Canvas
        camera={{ position: [0, 0.4, 4.6], fov: 38 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        {/* Iluminacion ambiental para que el modelo no quede totalmente oscuro. */}
        <ambientLight intensity={0.55} />
        <directionalLight position={[3, 4, 5]} intensity={0.6} color="#cfeaff" />
        <directionalLight position={[-3, -2, 3]} intensity={0.25} color={RASENGAN_BLUE} />

        <RasenganMesh audioLevel={audioLevel} />
      </Canvas>
    </div>
  );
}

// Preload del GLB para que cuando el usuario elija el Rasengan desde el
// dropdown, aparezca casi instantaneamente (sin el "loading" inicial del
// useGLTF). Es un side-effect a nivel de modulo; barato porque solo se
// ejecuta una vez al importar este archivo. Usa un loader dedicado (no
// cacheamos en el loader interno de R3F, que se reinicia entre Suspenses).
new GLTFLoader().load("/models/rasengan.glb", () => {}, undefined, () => {});

export default RasenganSphere;