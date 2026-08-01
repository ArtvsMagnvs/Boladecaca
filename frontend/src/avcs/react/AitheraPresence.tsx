// AVCS — <AitheraPresence/>: el UNICO símbolo React que ve el resto de la app.
// Monta UN <Canvas> persistente (una sola vez, en AppLayout, fuera del div
// key=pathname) y ejecuta el UNICO useFrame maestro. El engine NO conoce React.
//
// Route/tier se leen FUERA del <Canvas> (useLocation depende del contexto de
// Router, que R3F no puentea) y se pasan como props. El coreState se lee del
// store zustand DENTRO del frame (zustand es context-free → cruza el Canvas).
import { useEffect, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { useLocation } from "react-router-dom";
import * as THREE from "three";
import { HubEngine } from "../engine/HubEngine";
import { useAppStore } from "@/store/useAppStore";
import { isPresenceVisible, useAvcsTier } from "./useAvcsRoute";
import { CONTENT_HALF_HEIGHT, CONTENT_HALF_WIDTH, FIT_MARGIN, TIERS } from "../constants";
import type { CoreStateId, QualityTier } from "../types";

// [2026-07-21] El AVCS NO reacciona al tema claro/oscuro de la UI: es la
// identidad visual de Aithera y se mantiene 100% igual en cualquier tema
// (decisión explícita del usuario).

// [PU5c] Zoom y órbita manuales. `zoomRef` lo comparten el runner (que lo
// aplica a la cámara cada frame) y el contenedor (que escucha la rueda), y
// `engineRef` sale del runner para que los eventos de puntero del div puedan
// empujar la órbita al engine. Un ref simple basta: no hace falta re-render.
const DIST_BASE = 8.5;
const ZOOM_MIN = 0.5;   // alejado
const ZOOM_MAX = 3.0;   // acercado

interface RunnerProps {
  visible: boolean;
  tier: QualityTier;
  zoomRef: React.MutableRefObject<number>;
  onEngine: (e: HubEngine | null) => void;
}

function PresenceRunner({ visible, tier, zoomRef, onEngine }: RunnerProps) {
  const { gl, scene, camera } = useThree();
  const engineRef = useRef<HubEngine | null>(null);
  const [bloom, setBloom] = useState<boolean>(() => TIERS[tier].bloom);
  const [bloomIntensity, setBloomIntensity] = useState<number>(() => TIERS[tier].bloomIntensity);
  const lastAspectRef = useRef(-1);

  // Crear el engine UNA vez (sobrevive a cambios de ruta porque el Canvas persiste).
  useEffect(() => {
    const engine = new HubEngine({
      renderer: gl,
      scene: scene as THREE.Scene,
      camera,
      getCoreState: () => useAppStore.getState().coreState as CoreStateId,
      initialTier: tier,
      sessionSeed: Math.floor(Math.random() * 1_000_000),
    });
    engine.mount();
    engine.setRenderConfigListener((cfg) => {
      setBloom(cfg.bloom);
      setBloomIntensity(cfg.bloomIntensity);
    });
    engineRef.current = engine;
    onEngine(engine);
    if (import.meta.env.DEV) {
      // Marca de instancia única: debe verse UNA sola vez por vida de la app.
      // eslint-disable-next-line no-console
      console.info("[AVCS] HubEngine montado", engine.healthy ? "(OK)" : `(FALLO: ${engine.lastError})`);
    }
    return () => {
      engine.setRenderConfigListener(null);
      engine.dispose();
      engineRef.current = null;
      onEngine(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Ruta → visibilidad (sin desmontar).
  useEffect(() => {
    engineRef.current?.setVisible(visible);
  }, [visible]);

  // Tier → re-aplica (realoca FBOs sin re-crear el contexto).
  useEffect(() => {
    engineRef.current?.setTier(tier);
    setBloom(TIERS[tier].bloom);
    setBloomIntensity(TIERS[tier].bloomIntensity);
  }, [tier]);

  // EL UNICO useFrame maestro. Priority 0: hace compute + escribe uniforms, NO
  // renderiza. R3F auto-renderiza (sin bloom) o <EffectComposer> renderiza
  // (con bloom, a mayor priority) DESPUES — el compute siempre precede al render.
  //
  // Cámara fit-contain (doc 13 §13.3, "sin clipping"): la semilla + 2ª capa
  // (doc: CONTENT_HALF_WIDTH/HEIGHT) deben caber SIEMPRE, cualquiera sea el
  // aspect ratio de la ventana. FOV vertical = max(el que necesita la altura,
  // el que necesita la anchura convertido a vertical vía el aspect actual).
  useFrame((state, dt) => {
    const cam0 = state.camera as THREE.PerspectiveCamera;
    // [PU5c] ZOOM: acerca/aleja la cámara. El zoom PERSISTE (no vuelve solo);
    // lo que vuelve al soltar es la órbita. Se suaviza para que la rueda no dé
    // tirones.
    const targetZ = DIST_BASE / zoomRef.current;
    cam0.position.z += (targetZ - cam0.position.z) * Math.min(1, dt * 9);

    const aspect = state.size.width / Math.max(1, state.size.height);
    if (Math.abs(aspect - lastAspectRef.current) > 0.001) {
      lastAspectRef.current = aspect;
      const cam = state.camera as THREE.PerspectiveCamera;
      // Distancia BASE a propósito: el encuadre fit-contain se calcula sobre la
      // escena sin zoom, así que hacer zoom no reajusta el FOV (y al
      // redimensionar la ventana el zoom del usuario se respeta).
      const dist = DIST_BASE;
      const halfW = CONTENT_HALF_WIDTH * FIT_MARGIN;
      const halfH = CONTENT_HALF_HEIGHT * FIT_MARGIN;
      const halfAngleForHeight = Math.atan(halfH / dist);
      const halfAngleNeededH = Math.atan(halfW / dist); // ángulo horizontal necesario
      const halfAngleForWidth = Math.atan(Math.tan(halfAngleNeededH) / aspect); // → vertical equivalente
      const vFovRad = 2 * Math.max(halfAngleForHeight, halfAngleForWidth);
      cam.fov = THREE.MathUtils.radToDeg(vFovRad);
      cam.updateProjectionMatrix();
    }
    engineRef.current?.frame(dt);
  });

  if (!bloom) return null;
  return (
    <EffectComposer>
      <Bloom intensity={bloomIntensity} luminanceThreshold={0.62} luminanceSmoothing={0.3} mipmapBlur />
    </EffectComposer>
  );
}

export interface AitheraPresenceProps {
  className?: string;
}

export function AitheraPresence({ className }: AitheraPresenceProps) {
  const location = useLocation();
  const tier = useAvcsTier();
  const visible = isPresenceVisible(location.pathname);

  // [PU5c] Interacción: arrastrar = girar (vuelve al soltar), rueda = zoom.
  const zoomRef = useRef(1);
  const engineRef = useRef<HubEngine | null>(null);
  const dragRef = useRef<{ id: number; x: number; y: number } | null>(null);
  const [grabbing, setGrabbing] = useState(false);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    dragRef.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
    setGrabbing(true);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (!d || d.id !== e.pointerId) return;
    // px → radianes. Una pasada de ~400 px llega al tope de giro.
    const yaw = (e.clientX - d.x) * 0.005;
    const pitch = (e.clientY - d.y) * 0.005;
    engineRef.current?.setOrbit(yaw, pitch, true);
  };
  const endDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current || dragRef.current.id !== e.pointerId) return;
    dragRef.current = null;
    // dragging=false → el engine devuelve el objetivo a 0 y el AVCS vuelve
    // suavemente a mirar de frente.
    engineRef.current?.setOrbit(0, 0, false);
    setGrabbing(false);
  };
  const onWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const f = Math.exp(-e.deltaY * 0.0016);
    zoomRef.current = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoomRef.current * f));
  };
  // EL ESCENARIO DEL NÚCLEO (2026-07-21): el AVCS se ve EXACTAMENTE igual en
  // cualquier tema — sus partículas pintan con luz ADITIVA, así que exigen el
  // MISMO fondo oscuro debajo. Sin esto, en tema claro el fondo gris claro se
  // transparenta tras el canvas y el núcleo aparece "con un velo blanco".
  // [PU6a-bis v2] El escenario va SIEMPRE, en todas las rutas: el AVCS es
  // ahora el fondo permanente de la app (las páginas flotan encima como
  // tarjetas), así que su telón oscuro también lo es. CERO cambios en
  // engine/shaders — sigue siendo solo el color del telón de fondo.
  const stage = true;

  return (
    <div
      className={className}
      // `pointerEvents: auto` SOLO donde el AVCS está visible: el contenedor
      // vive al fondo (z-0), así que los paneles y controles de la UI —que van
      // encima— siguen recibiendo sus eventos primero; aquí solo llegan los
      // clics sobre zonas vacías, que es justo lo que queremos capturar.
      onPointerDown={visible ? onPointerDown : undefined}
      onPointerMove={visible ? onPointerMove : undefined}
      onPointerUp={visible ? endDrag : undefined}
      onPointerCancel={visible ? endDrag : undefined}
      onWheel={visible ? onWheel : undefined}
      style={{
        transition: "background-color 400ms ease",
        pointerEvents: visible ? "auto" : "none",
        cursor: visible ? (grabbing ? "grabbing" : "grab") : undefined,
        touchAction: "none",
        ...(stage ? { backgroundColor: "#0a0a0f" } : null),
      }}
    >
      <Canvas
        camera={{ position: [0, 0, DIST_BASE], fov: 45 }}
        dpr={[1, TIERS[tier].dpr]}
        gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      >
        <PresenceRunner
          visible={visible}
          tier={tier}
          zoomRef={zoomRef}
          onEngine={(e) => { engineRef.current = e; }}
        />
      </Canvas>
    </div>
  );
}

export default AitheraPresence;
