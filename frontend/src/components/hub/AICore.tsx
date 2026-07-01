import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useAppStore, type AICoreState } from "@/store/useAppStore";

/**
 * Nucleo de IA - corazon visual de Aithera (ver PLAN_HUB_VISUAL_Y_VOZ.md).
 * Una esfera distorsionada por ruido, con color/intensidad/velocidad propios
 * de cada estado, transicionando siempre con un lerp suave (nunca un salto
 * brusco entre estados).
 */
const STATE_CONFIG: Record<AICoreState, { color: string; intensity: number; speed: number; rotationBoost: number }> = {
  idle: { color: "#5EA8FF", intensity: 0.12, speed: 0.18, rotationBoost: 1 },
  listening: { color: "#8FD9FF", intensity: 0.32, speed: 0.45, rotationBoost: 1.3 },
  thinking: { color: "#7C9CFF", intensity: 0.62, speed: 1.0, rotationBoost: 4 },
  speaking: { color: "#5EA8FF", intensity: 0.5, speed: 1.5, rotationBoost: 1.6 },
  processing: { color: "#7C9CFF", intensity: 0.7, speed: 1.15, rotationBoost: 3 },
  error: { color: "#D9756F", intensity: 0.4, speed: 0.5, rotationBoost: 1 },
};

const vertexShader = `
  uniform float uTime;
  uniform float uIntensity;
  varying vec3 vNormal;
  varying float vNoise;

  float noise(vec3 p) {
    return sin(p.x * 2.2 + uTime) * sin(p.y * 2.2 + uTime * 0.8) * sin(p.z * 2.2 + uTime * 1.3);
  }

  void main() {
    vNormal = normal;
    float n = noise(position * 1.6);
    vNoise = n;
    vec3 displaced = position + normal * n * uIntensity * 0.16;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
  }
`;

const fragmentShader = `
  uniform vec3 uColor;
  uniform float uIntensity;
  varying vec3 vNormal;
  varying float vNoise;

  void main() {
    float fresnel = pow(1.0 - clamp(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)), 0.0, 1.0), 2.0);
    vec3 glow = uColor * (0.55 + fresnel * 0.75 + vNoise * 0.18 * uIntensity);
    gl_FragColor = vec4(glow, 0.82 + fresnel * 0.18);
  }
`;

function CoreMesh({ audioLevel }: { audioLevel: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const coreState = useAppStore((s) => s.coreState);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uIntensity: { value: STATE_CONFIG.idle.intensity },
      uColor: { value: new THREE.Color(STATE_CONFIG.idle.color) },
    }),
    []
  );

  useFrame((_, delta) => {
    const config = STATE_CONFIG[coreState];
    const targetIntensity = config.intensity + (coreState === "speaking" ? audioLevel * 0.5 : 0);

    uniforms.uTime.value += delta * config.speed;
    uniforms.uIntensity.value = THREE.MathUtils.lerp(uniforms.uIntensity.value, targetIntensity, delta * 3);
    (uniforms.uColor.value as THREE.Color).lerp(new THREE.Color(config.color), delta * 2.5);

    if (meshRef.current) {
      // Respiracion en reposo: escala oscilante suave (1.0 <-> ~1.03 cada ~4s).
      const breathe = coreState === "idle" ? 1 + Math.sin(uniforms.uTime.value * 0.5) * 0.03 : 1 + audioLevel * 0.04;
      meshRef.current.scale.setScalar(breathe);
      meshRef.current.rotation.y += delta * 0.06 * config.rotationBoost;
      meshRef.current.rotation.x += delta * 0.015 * config.rotationBoost;
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1, 6]} />
      <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={uniforms} transparent />
    </mesh>
  );
}

/** Particulas orbitando, solo visibles en "thinking"/"processing" (spec: "Pensando: partículas"). */
function ThinkingParticles() {
  const groupRef = useRef<THREE.Group>(null);
  const coreState = useAppStore((s) => s.coreState);
  const visible = coreState === "thinking" || coreState === "processing";

  const positions = useMemo(() => {
    const arr = new Float32Array(60 * 3);
    for (let i = 0; i < 60; i++) {
      const radius = 1.6 + Math.random() * 0.5;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = radius * Math.cos(phi);
    }
    return arr;
  }, []);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.4;
      groupRef.current.rotation.x += delta * 0.15;
    }
  });

  if (!visible) return null;

  return (
    <group ref={groupRef}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial color="#8FD9FF" size={0.035} transparent opacity={0.75} />
      </points>
    </group>
  );
}

interface AICoreProps {
  size?: number;
  /** Nivel de audio 0-1 para sincronizar pulsos con la voz mientras habla. */
  audioLevel?: number;
}

export function AICore({ size = 280, audioLevel = 0 }: AICoreProps) {
  return (
    <div style={{ width: size, height: size }} className="relative mx-auto">
      <Canvas camera={{ position: [0, 0, 3] }} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.4} />
        <pointLight position={[2, 2, 2]} intensity={1.2} />
        <CoreMesh audioLevel={audioLevel} />
        <ThinkingParticles />
      </Canvas>
    </div>
  );
}
