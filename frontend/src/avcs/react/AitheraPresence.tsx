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
import { TIERS } from "../constants";
import type { CoreStateId, QualityTier } from "../types";

interface RunnerProps {
  visible: boolean;
  tier: QualityTier;
}

function PresenceRunner({ visible, tier }: RunnerProps) {
  const { gl, scene, camera } = useThree();
  const engineRef = useRef<HubEngine | null>(null);
  const [bloom, setBloom] = useState<boolean>(() => TIERS[tier].bloom);
  const [bloomIntensity, setBloomIntensity] = useState<number>(() => TIERS[tier].bloomIntensity);

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
    if (import.meta.env.DEV) {
      // Marca de instancia única: debe verse UNA sola vez por vida de la app.
      // eslint-disable-next-line no-console
      console.info("[AVCS] HubEngine montado", engine.healthy ? "(OK)" : `(FALLO: ${engine.lastError})`);
    }
    return () => {
      engine.setRenderConfigListener(null);
      engine.dispose();
      engineRef.current = null;
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
  useFrame((_, dt) => {
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

  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 0, 8.5], fov: 45 }}
        dpr={[1, TIERS[tier].dpr]}
        gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      >
        <PresenceRunner visible={visible} tier={tier} />
      </Canvas>
    </div>
  );
}

export default AitheraPresence;
