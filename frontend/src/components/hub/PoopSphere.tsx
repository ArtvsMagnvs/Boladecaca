// PoopSphere.tsx — Bola de caca cartoon estilo emoji 💩 para el Hub de Aithera (V0.7 extra).
//
// Geometria procedural MEJORADA (despues de ver referencia visual):
//   - LatheGeometry con perfil que tiene 3 BULTOS pronunciados (los rolls) y 2
//     valles entre ellos. Esto genera la silueta real del poop emoji con sus
//     enrollamientos laterales visibles (no un cono liso como el intento v2).
//   - Mismo shader toon-shaded calido del intento v2 (ya estaba bien).
//   - Pelo: lineas finas dispersas.
//   - Moscas: 4 unidades cartoon, 2 posadas + 2 volando.
//   - Sin gusano (no aparece en la referencia).

import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { Gltf } from "@/lib/drei-shim";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import { useAppStore, type AICoreState } from "@/store/useAppStore";

// -----------------------------------------------------------------------------
// ¿Usar modelo GLB externo? Si es true, el componente intenta cargar
// `/models/poop.glb`. Si el archivo no existe, se muestra el procedural.
//
// -----------------------------------------------------------------------------
// ACTIVO: GLB generado localmente con TripoSR + RTX 3070.
// El modelo real esta en frontend/public/models/poop.glb (18 MB).
// Si en algun momento quieres regenerarlo, el script vive en:
//   C:\Users\Alejandro\Desktop\CLAUDE\Aithera\TripoSR\run_poop.bat
//   Usa la imagen `frontend/public/models/poop-reference.png` como input.
// -----------------------------------------------------------------------------
const USE_GLB = true;
const GLB_PATH = "/models/poop.glb";

// -----------------------------------------------------------------------------
// Constantes
// -----------------------------------------------------------------------------

const NUM_FLIES = 4;
const NUM_HAIRS = 36;
const POOP_SCALE = 1.4; // escala global del poop en escena

// -----------------------------------------------------------------------------
// AGITATION — mapeo coreState -> parametros (consistente con AICore.tsx).
// -----------------------------------------------------------------------------

interface Agitation {
  intensity: number;
  speed: number;
  flyRadius: number;
  flySpeed: number;
  wingHz: number;
  hairErect: number;
}

const AGITATION: Record<AICoreState, Agitation> = {
  idle:       { intensity: 0.10, speed: 0.18, flyRadius: 1.0, flySpeed: 0.30, wingHz: 22, hairErect: 0.0 },
  listening:  { intensity: 0.18, speed: 0.45, flyRadius: 1.05, flySpeed: 0.55, wingHz: 28, hairErect: 0.10 },
  thinking:   { intensity: 0.30, speed: 1.0,  flyRadius: 1.10, flySpeed: 0.85, wingHz: 32, hairErect: 0.35 },
  speaking:   { intensity: 0.35, speed: 1.5,  flyRadius: 1.45, flySpeed: 1.40, wingHz: 44, hairErect: 0.25 },
  processing: { intensity: 0.40, speed: 1.15, flyRadius: 1.20, flySpeed: 1.10, wingHz: 36, hairErect: 0.45 },
  error:      { intensity: 0.25, speed: 0.50, flyRadius: 1.0, flySpeed: 0.20, wingHz: 14, hairErect: 0.0 },
};

// -----------------------------------------------------------------------------
// Perfil del poop emoji — 3 rolls como bultos gaussianos sobre una silueta creciente.
// -----------------------------------------------------------------------------

/**
 * Genera el perfil del poop emoji con 3 rolls visibles como bultos laterales.
 * El perfil se rota alrededor del eje Y para crear la malla 3D (LatheGeometry).
 *
 *  perfil:
 *    - t=0:    cerrado (puntito abajo)
 *    - t=0.20: bulto roll 1 (centro en 0.20)
 *    - t=0.40: valle entre roll 1 y 2
 *    - t=0.55: bulto roll 2 (centro en 0.55)
 *    - t=0.70: valle entre roll 2 y 3
 *    - t=0.85: bulto roll 3 (centro en 0.85)
 *    - t=1.00: cerrado arriba
 */
function generatePoopProfile(): THREE.Vector2[] {
  const N = 200;
  const pts: THREE.Vector2[] = [];

  // Parametros de los rolls: [centro en t, ancho gaussiano, altura del bulto]
  const ROLLS: Array<[number, number, number]> = [
    [0.20, 0.040, 0.22],  // roll 1 (el mas pequeno, abajo)
    [0.55, 0.045, 0.28],  // roll 2 (mediano)
    [0.85, 0.050, 0.34],  // roll 3 (mas ancho, arriba)
  ];

  // Valles (zonas mas estrechas entre rolls)
  const VALLEYS: Array<[number, number, number]> = [
    [0.40, 0.020, 0.08],
    [0.70, 0.022, 0.09],
  ];

  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const y = t * 1.0; // altura normalizada

    // Radio base: crece de 0.20 (abajo) a 0.70 (arriba)
    let r = 0.20 + t * 0.50;

    // Sumar bultos de los rolls
    for (const [center, width, height] of ROLLS) {
      const dist = t - center;
      r += height * Math.exp(-(dist * dist) / width);
    }

    // Restar valles
    for (const [center, width, depth] of VALLEYS) {
      const dist = t - center;
      r -= depth * Math.exp(-(dist * dist) / width);
    }

    // Cerrar abajo (puntito)
    if (t < 0.04) {
      r *= t / 0.04;
    }
    // Cerrar arriba
    if (t > 0.96) {
      r *= (1 - t) / 0.04;
    }

    pts.push(new THREE.Vector2(Math.max(0.001, r), y));
  }
  return pts;
}

const PROFILE = generatePoopProfile();

/** Muestrea un punto sobre la superficie del poop dados theta y t a lo largo del perfil. */
function sampleSurface(theta: number, tAlong: number): THREE.Vector3 {
  const idx = tAlong * (PROFILE.length - 1);
  const i0 = Math.floor(idx);
  const i1 = Math.min(i0 + 1, PROFILE.length - 1);
  const f = idx - i0;
  const p0 = PROFILE[i0];
  const p1 = PROFILE[i1];
  const r = (p0.x * (1 - f) + p1.x * f) * POOP_SCALE;
  const y = (p0.y * (1 - f) + p1.y * f - 0.5) * POOP_SCALE; // centrar
  return new THREE.Vector3(
    Math.cos(theta) * r,
    y,
    Math.sin(theta) * r,
  );
}

// -----------------------------------------------------------------------------
// Shader del cuerpo principal — toon shading calido
// -----------------------------------------------------------------------------

const poopVertexShader = `
  uniform float uTime;
  uniform float uIntensity;
  uniform float uAudioLevel;
  varying vec3 vNormal;
  varying vec3 vWorldPos;
  varying vec3 vObjPos;
  varying float vNoise;

  float hash(vec3 p) {
    return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
  }
  float noise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec3(1.0, 0.0, 0.0));
    float c = hash(i + vec3(0.0, 1.0, 0.0));
    float d = hash(i + vec3(1.0, 1.0, 0.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }
  float fbm(vec3 p) {
    float v = 0.0;
    float amp = 0.5;
    for (int i = 0; i < 4; i++) {
      v += amp * noise(p);
      p *= 2.0;
      amp *= 0.5;
    }
    return v;
  }

  void main() {
    vNormal = normal;
    vObjPos = position;
    float n1 = fbm(position * 3.5 + uTime * 0.12);
    float n2 = fbm(position * 9.0 - uTime * 0.08);
    float perturb = (n1 - 0.5) * 0.14 + (n2 - 0.5) * 0.04;
    float totalIntensity = uIntensity + uAudioLevel * 0.30;
    vec3 displaced = position + normal * perturb * totalIntensity;
    vNoise = n1;
    vec4 worldPos = modelMatrix * vec4(displaced, 1.0);
    vWorldPos = worldPos.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

const poopFragmentShader = `
  uniform float uTime;
  uniform float uIntensity;
  uniform vec3  uLightDir;
  uniform vec3  uColorWarm;
  uniform vec3  uColorShadow;
  uniform vec3  uColorHighlight;
  varying vec3 vNormal;
  varying vec3 vWorldPos;
  varying vec3 vObjPos;
  varying float vNoise;

  float hash21(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }

  void main() {
    vec3 N = normalize(vNormal);
    vec3 L = normalize(uLightDir);
    vec3 V = normalize(cameraPosition - vWorldPos);

    float t1 = smoothstep(0.30, 0.70, vNoise);
    vec3 base = mix(uColorShadow, uColorWarm, t1);
    float t2 = smoothstep(0.70, 0.92, vNoise);
    base = mix(base, uColorHighlight, t2 * 0.5);

    // Toon shading: 3 bandas planas
    float ndl = dot(N, L);
    float toon;
    if (ndl > 0.55)      toon = 1.0;
    else if (ndl > 0.20) toon = 0.82;
    else if (ndl > -0.1) toon = 0.62;
    else                 toon = 0.48;
    vec3 col = base * toon;

    // Vetas horizontales sutiles (pliegues del poop)
    float vein = sin(vObjPos.y * 14.0 + vNoise * 4.0);
    vein = smoothstep(0.85, 1.0, vein);
    col = mix(col, col * 0.72, vein * 0.45);

    // Sombras mas oscuras en los valles (entre rolls)
    float valley = smoothstep(0.02, 0.10, abs(fract(vObjPos.y * 3.5) - 0.5));
    col *= mix(0.78, 1.0, valley);

    // Motas / semillas brillantes dispersas
    vec2 seedUV = vObjPos.xz * 5.0 + vObjPos.y * 2.5;
    float seedHash = hash21(floor(seedUV * 2.0));
    float seed = step(0.86, seedHash);
    col = mix(col, uColorHighlight, seed * 0.55);

    // Highlight especular cartoon
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(N, H), 0.0), 24.0);
    spec = smoothstep(0.4, 0.55, spec);
    col = mix(col, uColorHighlight * 1.1, spec * 0.4);

    // Rim light suave
    float rim = pow(1.0 - max(dot(N, V), 0.0), 2.5);
    col += uColorHighlight * rim * 0.18;

    // Oscurecimiento sutil en el borde extremo
    float edge = smoothstep(0.88, 1.0, 1.0 - max(dot(N, V), 0.0));
    col = mix(col, uColorShadow * 0.7, edge * 0.35);

    gl_FragColor = vec4(col, 1.0);
  }
`;

function PoopMesh({ audioLevel }: { audioLevel: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const coreState = useAppStore((s) => s.coreState);

  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: poopVertexShader,
      fragmentShader: poopFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uIntensity: { value: AGITATION.idle.intensity },
        uAudioLevel: { value: 0 },
        uLightDir: { value: new THREE.Vector3(0.5, 0.85, 0.6).normalize() },
        uColorWarm:      { value: new THREE.Color(0x8b5a2b) },
        uColorShadow:    { value: new THREE.Color(0x4a2d18) },
        uColorHighlight: { value: new THREE.Color(0xc89368) },
      },
    });
  }, []);

  // Geometria con perfil de 3 rolls (bultos gaussianos).
  // 96 segmentos radiales para que los enrollamientos se vean suaves.
  const geometry = useMemo(() => {
    const centered = PROFILE.map((p) => new THREE.Vector2(p.x * POOP_SCALE, (p.y - 0.5) * POOP_SCALE));
    return new THREE.LatheGeometry(centered, 96);
  }, []);

  useFrame((_, delta) => {
    const a = AGITATION[coreState];
    material.uniforms.uTime.value += delta * a.speed;
    material.uniforms.uIntensity.value = THREE.MathUtils.lerp(
      material.uniforms.uIntensity.value,
      a.intensity,
      delta * 2.5,
    );
    material.uniforms.uAudioLevel.value = THREE.MathUtils.lerp(
      material.uniforms.uAudioLevel.value,
      audioLevel,
      delta * 8.0,
    );
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.08;
    }
  });

  return (
    <mesh ref={meshRef} material={material} geometry={geometry} />
  );
}

// -----------------------------------------------------------------------------
// Pelusas — lineas finas dispersas sobre la superficie
// -----------------------------------------------------------------------------

function HairTufts() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const coreState = useAppStore((s) => s.coreState);

  const { baseDirs, baseLengths, baseAngles, baseTAlong } = useMemo(() => {
    const dirs: THREE.Vector3[] = [];
    const lengths: number[] = [];
    const angles: number[] = [];
    const tAlongs: number[] = [];
    const rng = mulberry32(7919);
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < NUM_HAIRS; i++) {
      const theta = i * goldenAngle + rng() * 0.4;
      const t = 0.10 + rng() * 0.80;
      const pos = sampleSurface(theta, t);
      const radial = new THREE.Vector3(pos.x, 0, pos.z).normalize();
      const dir = radial.clone().add(new THREE.Vector3(0, 0.15, 0)).normalize();
      dirs.push(dir);
      lengths.push(0.06 + rng() * 0.10);
      angles.push(theta);
      tAlongs.push(t);
    }
    return { baseDirs: dirs, baseLengths: lengths, baseAngles: angles, baseTAlong: tAlongs };
  }, []);

  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame((_, delta) => {
    if (!meshRef.current) return;
    const a = AGITATION[coreState];
    meshRef.current.userData.erect = THREE.MathUtils.lerp(
      meshRef.current.userData.erect ?? 0,
      a.hairErect,
      delta * 2.5,
    );
    const erect = meshRef.current.userData.erect ?? 0;
    const t = performance.now() * 0.001;

    for (let i = 0; i < NUM_HAIRS; i++) {
      const theta = baseAngles[i];
      const tProf = baseTAlong[i];
      const pos = sampleSurface(theta, tProf);
      const dir = baseDirs[i];
      const len = baseLengths[i] * (1 + erect * 0.8);

      const surfacePos = pos.clone().add(dir.clone().multiplyScalar(0.02));
      dummy.position.copy(surfacePos);
      dummy.lookAt(surfacePos.clone().add(dir));
      dummy.rotateX(Math.PI / 2);
      const wobble = Math.sin(t * 1.3 + i * 0.7) * 0.02;
      dummy.scale.set(1, len + wobble, 1);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, NUM_HAIRS]}>
      <cylinderGeometry args={[0.008, 0.005, 1, 5, 1, false]} />
      <meshStandardMaterial color="#2a1607" roughness={1.0} />
    </instancedMesh>
  );
}

// -----------------------------------------------------------------------------
// Moscas — 7 unidades con comportamiento real (caminar, limpiarse, volar)
// -----------------------------------------------------------------------------
//
// Cada mosca es una maquina de estados:
//   walk  -> se mueve por la superficie en una direccion tangente aleatoria
//   clean -> para y se "frota las patas" (cuerpo vibra rapido)
//   takeoff -> despega verticalmente
//   fly   -> orbita alrededor de la bola a radio y altura variables
//   land  -> baja hacia un punto aleatorio de la superficie y vuelve a walk
//
// Cuando coreState esta agitado (speaking/processing/thinking) las moscas
// estan mas activas: cambian de estado mas a menudo, vuelan mas rapido.
//
// 4 negras (funny fly anime) + 2 verdes normales + 1 verde mas grande
// (la tipica mosca de la caca, verde con brillos iridiscentes).
// -----------------------------------------------------------------------------

const GLB_FLY_BLACK = "/models/fly-black.glb";
const GLB_FLY_GREEN = "/models/fly-green.glb";

interface FlySpec {
  kind: "black" | "green";
  /** Escala base del GLB en escena. */
  bodyScale: number;
  /** Posicion inicial sobre la superficie. */
  theta: number;
  tProfile: number;
  /** Semilla para el RNG (movimientos reproducibles por mosca). */
  seed: number;
  /** Indica si esta mosca es la grande verde (la "jefa"). */
  bigGreen?: boolean;
}

const FLY_SPECS: FlySpec[] = [
  // 4 negras — funny fly estilo anime
  { kind: "black", bodyScale: 0.38, theta: 0.40,             tProfile: 0.65, seed: 1011 },
  { kind: "black", bodyScale: 0.34, theta: Math.PI * 1.10,   tProfile: 0.50, seed: 2022 },
  { kind: "black", bodyScale: 0.42, theta: Math.PI * 1.80,   tProfile: 0.78, seed: 3033 },
  { kind: "black", bodyScale: 0.36, theta: Math.PI * 0.40 + 2.4, tProfile: 0.40, seed: 4044 },
  // 3 verdes — 2 normales + 1 mas grande (la iridiscente)
  { kind: "green", bodyScale: 0.42, theta: Math.PI * 0.90,   tProfile: 0.55, seed: 5055 },
  { kind: "green", bodyScale: 0.38, theta: Math.PI * 1.55,   tProfile: 0.70, seed: 6066 },
  { kind: "green", bodyScale: 0.58, theta: Math.PI * 0.30,   tProfile: 0.45, seed: 7077, bigGreen: true },
];

// -----------------------------------------------------------------------------
// Estado mutable por mosca (no React state: evita renders por frame).
// -----------------------------------------------------------------------------

type FlyState = "walk" | "clean" | "takeoff" | "fly" | "land";

interface FlyRuntime {
  state: FlyState;
  stateTime: number;
  stateDuration: number;

  // walk
  theta: number;
  tProfile: number;
  walkDir: 1 | -1;
  walkSpeed: number;

  // fly
  orbitTheta: number;
  orbitRadius: number;
  orbitSpeed: number;
  orbitYBase: number;
  orbitYAmp: number;
  orbitYSpeed: number;

  // land target
  targetTheta: number;
  targetT: number;
  takeoffPos: THREE.Vector3;

  // visual
  flapPhase: number;
  /** Fase para el wandering del tProfile mientras camina. */
  tWanderPhase: number;
}

function makeRuntime(spec: FlySpec): FlyRuntime {
  const rng = mulberry32(spec.seed);
  const pickDir = (): 1 | -1 => (rng() < 0.5 ? -1 : 1);
  return {
    state: "walk",
    stateTime: 0,
    stateDuration: 1.5 + rng() * 3.0,
    theta: spec.theta,
    tProfile: spec.tProfile,
    walkDir: pickDir(),
    walkSpeed: 0.20 + rng() * 0.25,
    orbitTheta: rng() * Math.PI * 2,
    orbitRadius: 0.45 + rng() * 0.30,
    orbitSpeed: (0.35 + rng() * 0.40) * pickDir(),
    orbitYBase: 0.10 + rng() * 0.15,
    orbitYAmp: 0.08 + rng() * 0.12,
    orbitYSpeed: 0.5 + rng() * 0.8,
    targetTheta: 0,
    targetT: 0.4,
    takeoffPos: new THREE.Vector3(),
    flapPhase: rng() * Math.PI * 2,
    tWanderPhase: rng() * Math.PI * 2,
  };
}

// -----------------------------------------------------------------------------
// FlyModel — carga un GLB y devuelve una escena clonada (cada mosca = clone).
// useLoader suspende, asi que va envuelto en <Suspense> en Flies().
// -----------------------------------------------------------------------------

function FlyModel({ src }: { src: string }) {
  const gltf = useLoader(GLTFLoader, src);
  const cloned = useMemo(() => gltf.scene.clone(true), [gltf]);
  return <primitive object={cloned} />;
}

function Fly({ spec, index }: { spec: FlySpec; index: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const bodyRef = useRef<THREE.Group>(null);
  const coreState = useAppStore((s) => s.coreState);

  // Runtime mutable, inicializado UNA vez por mosca.
  const runtime = useRef<FlyRuntime>(makeRuntime(spec)).current;

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const a = AGITATION[coreState];
    runtime.stateTime += delta;

    // Factor de agitacion: cuanto mas alterado el core, mas nerviosa la mosca.
    const agFactor = 0.6 + a.intensity * 1.8;

    // Variables visuales que se aplican al final del frame.
    let bodyShakeX = 0;
    let bodyShakeZ = 0;
    let squashY = 0;
    let squashX = 0;

    switch (runtime.state) {
      case "walk": {
        if (runtime.stateTime >= runtime.stateDuration) {
          // Probabilidad de transicion: mas agitacion = mas probable volar.
          const flyProb = 0.25 + a.intensity * 0.30;
          if (Math.random() < flyProb) {
            runtime.state = "takeoff";
            runtime.stateDuration = 0.35;
            runtime.takeoffPos.copy(groupRef.current.position);
          } else {
            runtime.state = "clean";
            runtime.stateDuration = 1.2 + Math.random() * 2.0;
          }
          runtime.stateTime = 0;
          break;
        }

        // Avanzar theta en la direccion de marcha + wander del tProfile.
        runtime.theta +=
          runtime.walkDir * runtime.walkSpeed * delta * agFactor;
        runtime.tWanderPhase += delta * 0.6;
        const tWander = Math.sin(runtime.tWanderPhase) * 0.04;
        runtime.tProfile = THREE.MathUtils.clamp(
          runtime.tProfile + tWander * delta,
          0.20,
          0.85,
        );
        // Wrap theta en [0, 2pi).
        if (runtime.theta > Math.PI * 2) runtime.theta -= Math.PI * 2;
        if (runtime.theta < 0) runtime.theta += Math.PI * 2;

        const pos = sampleSurface(runtime.theta, runtime.tProfile);
        const radial = new THREE.Vector3(pos.x, 0, pos.z).normalize();
        // Offset hacia afuera para que la mosca "se pose" sobre la superficie.
        const surfacePos = pos
          .clone()
          .add(radial.clone().multiplyScalar(0.025));
        groupRef.current.position.copy(surfacePos);

        // Orientacion: tangente en la direccion de marcha + up radial.
        const tangent = new THREE.Vector3(
          -Math.sin(runtime.theta) * runtime.walkDir,
          0,
          Math.cos(runtime.theta) * runtime.walkDir,
        );
        const lookAt = surfacePos.clone().add(tangent);
        groupRef.current.lookAt(lookAt);
        // Ligero cabeceo al andar.
        bodyShakeZ = Math.sin(performance.now() * 0.012 + index) * 0.06;
        break;
      }

      case "clean": {
        if (runtime.stateTime >= runtime.stateDuration) {
          runtime.state = "walk";
          runtime.stateDuration = 2.0 + Math.random() * 3.0;
          runtime.stateTime = 0;
          break;
        }
        // Quieto en el sitio, frotando las patas (cuerpo vibra rapido).
        const pos = sampleSurface(runtime.theta, runtime.tProfile);
        const radial = new THREE.Vector3(pos.x, 0, pos.z).normalize();
        const surfacePos = pos
          .clone()
          .add(radial.clone().multiplyScalar(0.025));
        groupRef.current.position.copy(surfacePos);
        groupRef.current.lookAt(surfacePos.clone().add(radial));

        // Frotamiento: vibracion lateral rapida + cabeceo vertical sutil.
        bodyShakeX = Math.sin(runtime.stateTime * 38 + index) * 0.10;
        bodyShakeZ = Math.sin(runtime.stateTime * 31 + index * 1.7) * 0.08;
        break;
      }

      case "takeoff": {
        const t = THREE.MathUtils.clamp(
          runtime.stateTime / runtime.stateDuration,
          0,
          1,
        );
        const start = runtime.takeoffPos;
        const target = sampleSurface(runtime.theta, runtime.tProfile);
        const radial = new THREE.Vector3(target.x, 0, target.z).normalize();
        const surfacePos = target
          .clone()
          .add(radial.clone().multiplyScalar(0.025));
        const lifted = surfacePos
          .clone()
          .add(new THREE.Vector3(0, 0.55, 0))
          .add(radial.clone().multiplyScalar(0.30));
        const newPos = start.clone().lerp(lifted, t);
        groupRef.current.position.copy(newPos);
        // Mirar hacia donde va.
        groupRef.current.lookAt(lifted);
        squashY = 0.05; // alas extendidas
        squashX = -0.05;

        if (t >= 1) {
          runtime.state = "fly";
          runtime.stateDuration = 4.0 + Math.random() * 5.0;
          runtime.stateTime = 0;
          runtime.orbitTheta = runtime.theta;
          runtime.targetTheta = Math.random() * Math.PI * 2;
          runtime.targetT = 0.30 + Math.random() * 0.50;
        }
        break;
      }

      case "fly": {
        if (runtime.stateTime >= runtime.stateDuration) {
          runtime.state = "land";
          runtime.stateDuration = 0.45;
          runtime.stateTime = 0;
          break;
        }
        runtime.orbitTheta += runtime.orbitSpeed * delta * agFactor;
        const yOsc =
          Math.sin(runtime.stateTime * runtime.orbitYSpeed) *
          runtime.orbitYAmp;
        const r = runtime.orbitRadius * a.flyRadius;
        const x = Math.cos(runtime.orbitTheta) * r;
        const z = Math.sin(runtime.orbitTheta) * r;
        const y = runtime.orbitYBase + yOsc;
        groupRef.current.position.set(x, y, z);
        // Mirar hacia adelante en la orbita.
        const nextT = runtime.orbitTheta + runtime.orbitSpeed * 0.2;
        const nextY =
          runtime.orbitYBase +
          Math.sin(
            (runtime.stateTime + 0.2) * runtime.orbitYSpeed,
          ) *
            runtime.orbitYAmp;
        groupRef.current.lookAt(
          Math.cos(nextT) * r,
          nextY,
          Math.sin(nextT) * r,
        );
        squashY = 0.06;
        squashX = -0.06;
        break;
      }

      case "land": {
        const t = THREE.MathUtils.clamp(
          runtime.stateTime / runtime.stateDuration,
          0,
          1,
        );
        const start = runtime.takeoffPos;
        const target = sampleSurface(runtime.targetTheta, runtime.targetT);
        const radial = new THREE.Vector3(target.x, 0, target.z).normalize();
        const surfacePos = target
          .clone()
          .add(radial.clone().multiplyScalar(0.025));
        const newPos = start.clone().lerp(surfacePos, t);
        groupRef.current.position.copy(newPos);
        // Orientacion final: tangente en la nueva theta.
        const tangent = new THREE.Vector3(
          -Math.sin(runtime.targetTheta),
          0,
          Math.cos(runtime.targetTheta),
        );
        groupRef.current.lookAt(newPos.clone().add(tangent));
        squashY = 0.06 * (1 - t);
        squashX = -0.06 * (1 - t);

        if (t >= 1) {
          runtime.state = "walk";
          runtime.stateDuration = 1.8 + Math.random() * 3.5;
          runtime.stateTime = 0;
          runtime.theta = runtime.targetTheta;
          runtime.tProfile = runtime.targetT;
          runtime.walkDir = Math.random() < 0.5 ? -1 : 1;
        }
        break;
      }
    }

    // Wing flap / body shake animation (se aplica al bodyRef, no al grupo
    // que controla la posicion — asi no interfiere con lookAt).
    if (bodyRef.current) {
      const t = performance.now() * 0.001;
      const flapFreq = a.wingHz * (Math.abs(squashY) > 0 ? 1 : 0.3);
      const flap = Math.sin(t * flapFreq * Math.PI * 2 + runtime.flapPhase);
      bodyRef.current.rotation.z =
        bodyShakeZ + flap * 0.08 * (Math.abs(squashY) > 0 ? 1 : 0);
      bodyRef.current.rotation.x = bodyShakeX + flap * 0.04;
      const sY = 1 + squashY + flap * 0.05 * (Math.abs(squashY) > 0 ? 1 : 0);
      const sX = 1 + squashX - flap * 0.05 * (Math.abs(squashY) > 0 ? 1 : 0);
      bodyRef.current.scale.set(sX, sY, 1);
    }
  });

  // bodyScale para tamano (la verde grande lleva un plus extra).
  const finalScale = spec.bodyScale;

  return (
    <group ref={groupRef}>
      {/* bodyRef recibe la animacion de shake/squash (multiplicativa sobre su escala base) */}
      <group ref={bodyRef}>
        {/* Grupo con la escala base absoluta — el squash del bodyRef se aplica ENCIMA */}
        <group scale={finalScale}>
          <FlyModel src={spec.kind === "black" ? GLB_FLY_BLACK : GLB_FLY_GREEN} />
        </group>
      </group>
    </group>
  );
}

function Flies() {
  return (
    <Suspense fallback={null}>
      {FLY_SPECS.map((spec, i) => (
        <Fly key={i} spec={spec} index={i} />
      ))}
    </Suspense>
  );
}

// -----------------------------------------------------------------------------
// Utilidades
// -----------------------------------------------------------------------------

function mulberry32(seed: number) {
  let a = seed | 0;
  return function () {
    a = (a + 0x6D2B79F5) | 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// -----------------------------------------------------------------------------
// PoopMeshGLTF — carga un modelo GLB externo (recomendado).
// Usa drei <Gltf> que internamente hace useGLTF (suspense + cache).
// Si el archivo no existe, simplemente no renderiza nada (silencioso).
// -----------------------------------------------------------------------------

function PoopMeshGLTF({ audioLevel }: { audioLevel: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const wrapRef = useRef<THREE.Group>(null);
  const coreState = useAppStore((s) => s.coreState);

  // Auto-fit: el GLB generado por TripoSR viene en coords locales pequenas
  // (~0.9 unidades). Lo centramos y escalamos a ~1.4 unidades para que
  // encaje en la camara (z=3.6, fov default).
  useFrame((_, delta) => {
    const a = AGITATION[coreState];
    if (wrapRef.current) {
      wrapRef.current.rotation.y += delta * 0.08;
      // Reactividad: cuando habla, el modelo "respira" mas fuerte
      const breathe = 1 + Math.sin(performance.now() * 0.001 * a.speed) * a.intensity * 0.4;
      wrapRef.current.scale.setScalar(breathe);
    }
  });

  return (
    <group ref={wrapRef}>
      <group ref={groupRef}>
        <Gltf
          src={GLB_PATH}
          scale={1.6}
          position={[0, 0, 0]}
        />
      </group>
    </group>
  );
}

// -----------------------------------------------------------------------------
// PoopMesh wrapper — elige procedural o GLTF segun USE_GLB
// -----------------------------------------------------------------------------

function PoopMeshWrapper({ audioLevel }: { audioLevel: number }) {
  return USE_GLB ? (
    <PoopMeshGLTF audioLevel={audioLevel} />
  ) : (
    <PoopMesh audioLevel={audioLevel} />
  );
}

// -----------------------------------------------------------------------------
// Canvas principal
// -----------------------------------------------------------------------------

export interface PoopSphereProps {
  size?: number;
  audioLevel?: number;
}

export function PoopSphere({ size = 280, audioLevel = 0 }: PoopSphereProps) {
  return (
    <div style={{ width: size, height: size }} className="relative mx-auto">
      <Canvas camera={{ position: [0, 0.15, 3.6] }} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[2.2, 3.0, 1.8]} intensity={1.8} color="#ffe6c8" />
        <directionalLight position={[-2.0, -0.5, -1.0]} intensity={0.4} color="#7c9cff" />
        <PoopMeshWrapper audioLevel={audioLevel} />
        {/* Pelo viene ya bakeado en el GLB, no hace falta dibujarlo procedural.
            Cuando USE_GLB=false (procedural), si queremos pelo tenemos que anadirlo. */}
        {!USE_GLB && <HairTufts />}
        <Flies />
      </Canvas>
    </div>
  );
}

export default PoopSphere;