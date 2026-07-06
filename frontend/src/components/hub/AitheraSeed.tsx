import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

const GOLD_CORE = new THREE.Color("#FFF6D8");
const GOLD_LIGHT = new THREE.Color("#FFD77A");
const GOLD_MID = new THREE.Color("#F2B94B");
const GOLD_DEEP = new THREE.Color("#A56212");
const GOLD_PARTICLE = new THREE.Color("#FFCB66");

const OUTER_LEFT = [
  [0.0, -1.55, 0.0],
  [-0.58, -1.1, 0.0],
  [-0.96, -0.2, 0.0],
  [-0.98, 0.86, 0.0],
  [-0.46, 1.48, 0.0],
  [0.0, 1.72, 0.0],
] as const;

const INNER_LEFT = [
  [0.0, -1.38, 0.0],
  [-0.34, -0.92, 0.0],
  [-0.58, -0.08, 0.0],
  [-0.54, 0.88, 0.0],
  [-0.2, 1.38, 0.0],
  [0.0, 1.58, 0.0],
] as const;

const OUTER_RIGHT = OUTER_LEFT.map(([x, y, z]) => [-x, y, z] as const);
const INNER_RIGHT = INNER_LEFT.map(([x, y, z]) => [-x, y, z] as const);

const CENTRAL_SPINE = [
  [0.0, -1.48, 0.0],
  [0.0, -0.7, 0.0],
  [0.0, 0.22, 0.0],
  [0.0, 1.66, 0.0],
] as const;

const ROOT_LEFT = [
  [0.0, -1.5, 0.0],
  [-0.1, -1.68, 0.0],
  [-0.35, -1.98, 0.0],
  [-0.62, -2.08, 0.0],
] as const;

const ROOT_RIGHT = ROOT_LEFT.map(([x, y, z]) => [-x, y, z] as const);
const ROOT_CENTER = [
  [0.0, -1.52, 0.0],
  [0.0, -1.8, 0.0],
  [0.0, -2.12, 0.0],
] as const;

function toCurve(points: ReadonlyArray<readonly [number, number, number]>) {
  return new THREE.CatmullRomCurve3(
    points.map(([x, y, z]) => new THREE.Vector3(x, y, z)),
    false,
    "centripetal",
    0.55,
  );
}

function SeedTube({
  points,
  radius,
  tubularSegments = 128,
  radialSegments = 10,
  color = GOLD_LIGHT,
  emissive = GOLD_MID,
  opacity = 1,
  glow = false,
}: {
  points: ReadonlyArray<readonly [number, number, number]>;
  radius: number;
  tubularSegments?: number;
  radialSegments?: number;
  color?: THREE.Color;
  emissive?: THREE.Color;
  opacity?: number;
  glow?: boolean;
}) {
  const curve = useMemo(() => toCurve(points), [points]);

  return (
    <mesh>
      <tubeGeometry args={[curve, tubularSegments, radius, radialSegments, false]} />
      {glow ? (
        <meshBasicMaterial
          color={color}
          transparent
          opacity={opacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      ) : (
        <meshStandardMaterial
          color={color}
          emissive={emissive}
          emissiveIntensity={1.2}
          roughness={0.22}
          metalness={0.28}
          transparent
          opacity={opacity}
        />
      )}
    </mesh>
  );
}

function SeedParticles() {
  const groupRef = useRef<THREE.Group>(null);

  const positions = useMemo(() => {
    const points = new Float32Array(96 * 3);
    for (let i = 0; i < 96; i++) {
      const t = i / 95;
      const angle = t * Math.PI * 8 + Math.sin(i * 1.7) * 0.35;
      const band = Math.sin(t * Math.PI);
      const radius = 1.15 + band * 0.55 + (i % 5) * 0.03;
      const y = (t - 0.5) * 2.8 + Math.sin(i * 0.9) * 0.12;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius * 0.35 + Math.cos(i * 0.45) * 0.05;
      points[i * 3] = x;
      points[i * 3 + 1] = y;
      points[i * 3 + 2] = z;
    }
    return points;
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.08;
    groupRef.current.rotation.z = Math.sin(performance.now() * 0.00018) * 0.02;
  });

  return (
    <group ref={groupRef}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color={GOLD_PARTICLE}
          size={0.035}
          transparent
          opacity={0.76}
          depthWrite={false}
          sizeAttenuation
        />
      </points>
    </group>
  );
}

function SeedCore() {
  const groupRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const flareRef = useRef<THREE.Mesh>(null);
  const auraRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.09;
      groupRef.current.rotation.x = Math.sin(performance.now() * 0.00022) * 0.015;
      groupRef.current.position.y = Math.sin(performance.now() * 0.00045) * 0.03;
    }

    const pulse = 1 + Math.sin(performance.now() * 0.0014) * 0.035;
    if (glowRef.current) glowRef.current.scale.setScalar(pulse);
    if (flareRef.current) flareRef.current.scale.setScalar(1 + Math.sin(performance.now() * 0.001) * 0.025);
    if (auraRef.current) auraRef.current.scale.setScalar(1 + Math.sin(performance.now() * 0.0011) * 0.02);
  });

  return (
    <group ref={groupRef}>
      {/* Halo suave para el brillo central */}
      <mesh ref={auraRef}>
        <sphereGeometry args={[0.28, 32, 32]} />
        <meshBasicMaterial
          color={GOLD_MID}
          transparent
          opacity={0.14}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh ref={glowRef}>
        <sphereGeometry args={[0.16, 32, 32]} />
        <meshBasicMaterial
          color={GOLD_CORE}
          transparent
          opacity={0.95}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {/* Flare sutil en cruz, como el destello del centro de la imagen */}
      <mesh ref={flareRef} rotation={[Math.PI / 2, 0, Math.PI / 4]}>
        <planeGeometry args={[0.84, 0.02]} />
        <meshBasicMaterial
          color={GOLD_LIGHT}
          transparent
          opacity={0.5}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, -Math.PI / 4]}>
        <planeGeometry args={[0.84, 0.02]} />
        <meshBasicMaterial
          color={GOLD_LIGHT}
          transparent
          opacity={0.4}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {/* Eje central */}
      <SeedTube points={CENTRAL_SPINE} radius={0.032} color={GOLD_CORE} emissive={GOLD_LIGHT} opacity={1} />

      {/* Silueta principal en capas */}
      <SeedTube points={OUTER_LEFT} radius={0.048} color={GOLD_LIGHT} emissive={GOLD_MID} opacity={0.98} />
      <SeedTube points={INNER_LEFT} radius={0.042} color={GOLD_CORE} emissive={GOLD_LIGHT} opacity={0.98} />
      <SeedTube points={INNER_RIGHT} radius={0.042} color={GOLD_CORE} emissive={GOLD_LIGHT} opacity={0.98} />
      <SeedTube points={OUTER_RIGHT} radius={0.048} color={GOLD_LIGHT} emissive={GOLD_MID} opacity={0.98} />

      {/* Líneas de raíz inferiores */}
      <SeedTube points={ROOT_LEFT} radius={0.026} color={GOLD_MID} emissive={GOLD_DEEP} opacity={0.9} glow />
      <SeedTube points={ROOT_CENTER} radius={0.018} color={GOLD_CORE} emissive={GOLD_LIGHT} opacity={0.9} glow />
      <SeedTube points={ROOT_RIGHT} radius={0.026} color={GOLD_MID} emissive={GOLD_DEEP} opacity={0.9} glow />

      {/* Pequeña base luminosa */}
      <mesh position={[0, -2.14, 0]}>
        <sphereGeometry args={[0.025, 24, 24]} />
        <meshBasicMaterial
          color={GOLD_LIGHT}
          transparent
          opacity={0.95}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <pointLight color={GOLD_LIGHT} intensity={1.35} distance={7} decay={1.8} />
    </group>
  );
}

export interface AitheraSeedProps {
  size?: number;
}

export function AitheraSeed({ size = 280 }: AitheraSeedProps) {
  return (
    <div style={{ width: size, height: size }} className="relative mx-auto" aria-label="Semilla de Aithera">
      <Canvas
        camera={{ position: [0, 0.15, 4.35], fov: 38 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.45} />
        <directionalLight position={[3.2, 4.2, 4.5]} intensity={0.95} color={"#fff1c9"} />
        <directionalLight position={[-2.8, -1.8, 3.2]} intensity={0.45} color={"#c97b16"} />
        <SeedCore />
        <SeedParticles />
      </Canvas>
    </div>
  );
}

export default AitheraSeed;
