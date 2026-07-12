// AVCS — HubEngine: orquestador. Reloj ÚNICO, lifePhase, sessionSeed. UN solo
// tick maestro (frame). Compone la escena (añade los Points del ParticleEngine),
// traduce coreState → ritmo, y deja que PerformanceManager gobierne el presupuesto.
// El engine NO conoce React (ARCHITECTURE.md §5).
import * as THREE from "three";
import { ParticleEngine } from "./ParticleEngine";
import { RhythmEngine } from "./RhythmEngine";
import { AudioReactor } from "./AudioReactor";
import { PerformanceManager, type RenderConfig } from "./PerformanceManager";
import { DEFAULT_PALETTE, TIERS } from "../constants";
import type { CoreStateId, Palette, QualityTier } from "../types";

export interface HubEngineOptions {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.Camera;
  getCoreState: () => CoreStateId;
  initialTier: QualityTier;
  sessionSeed: number;
}

export class HubEngine {
  readonly particles: ParticleEngine;
  readonly rhythm: RhythmEngine;
  readonly audio: AudioReactor;
  readonly perf: PerformanceManager;

  private scene: THREE.Scene;
  private getCoreState: () => CoreStateId;
  private time = 0;
  private lifePhase = 0;
  private lastCoreState: CoreStateId | null = null;
  private visible = true;
  private mounted = false;
  private onRenderConfigChange: ((c: RenderConfig) => void) | null = null;
  private renderConfig: RenderConfig;
  private lastEffectiveTier: QualityTier;

  constructor(opts: HubEngineOptions) {
    this.scene = opts.scene;
    this.getCoreState = opts.getCoreState;
    this.particles = new ParticleEngine({
      renderer: opts.renderer,
      tier: opts.initialTier,
      sessionSeed: opts.sessionSeed,
    });
    this.rhythm = new RhythmEngine({ bus: this.particles.bus, sessionSeed: opts.sessionSeed });
    this.audio = new AudioReactor();
    this.perf = new PerformanceManager(opts.initialTier);
    this.renderConfig = this.perf.renderConfig;
    this.lastEffectiveTier = opts.initialTier;
    this.rhythm.setMaxWaves(TIERS[opts.initialTier].maxWaves);
  }

  mount(): void {
    if (this.mounted) return;
    this.particles.init();
    const obj = this.particles.object3D;
    if (obj) this.scene.add(obj);
    this.particles.setPalette(DEFAULT_PALETTE);
    // arrancar en el ritmo del estado actual
    const cs = this.getCoreState();
    this.rhythm.setCoreState(cs);
    this.lastCoreState = cs;
    this.mounted = true;
  }

  /** EL único tick maestro. Orden estricto: reloj → ritmo (bus) → sim (GPU). */
  frame(dt: number): void {
    if (!this.mounted) return;
    const d = Math.min(dt, 0.05);
    this.time += d;
    this.lifePhase += d;
    this.particles.bus.uTime.value = this.time;
    this.particles.bus.uDelta.value = this.visible ? d : d * 0.35; // oculto: sigue vivo, más lento
    this.particles.bus.uLifePhase.value = this.lifePhase;

    // store → ritmo (solo si cambió)
    const cs = this.getCoreState();
    if (cs !== this.lastCoreState) {
      this.rhythm.setCoreState(cs);
      this.lastCoreState = cs;
    }

    this.audio.update(d);
    const af = this.audio.frame;
    this.particles.bus.uAudioEnv.value = af.envelope;
    this.particles.bus.uAudioBands.value.set(af.bands[0], af.bands[1], af.bands[2]);

    this.rhythm.update(d, this.time, this.lifePhase);
    this.particles.update(d);

    // "se asienta" (Escucha) / "se eleva" (Comunicación) — offset del grupo entero.
    const obj = this.particles.object3D;
    if (obj) obj.position.y = this.rhythm.settleOffset;

    // presupuesto (escalera dinámica)
    if (this.perf.observe(dt * 1000)) {
      this.applyPerf();
    }
  }

  private applyPerf(): void {
    // PerformanceManager v0 (doc 13 §16): escalera completa, pasos 1-3 —
    // 1) bloom off, 2) DPR 1.0 (ambos vía renderConfig), 3) bajar UN tier
    // completo de partículas (effectiveTier) cuando el frametime no se
    // recupera con los pasos 1-2. Sube de nuevo sola cuando el frametime lo
    // permite (histéresis en PerformanceManager.observe). Nunca baja de Q1.
    const cfg = this.perf.renderConfig;
    this.renderConfig = cfg;
    this.rhythm.setMaxWaves(cfg.maxWaves);

    const eff = this.perf.effectiveTier;
    if (eff !== this.lastEffectiveTier) {
      this.lastEffectiveTier = eff;
      this.reinitParticlesTier(eff);
    }

    this.onRenderConfigChange?.(cfg);
  }

  /** Quita/reconstruye/vuelve a añadir los Points del ParticleEngine para un
   *  tier dado (manual desde Settings, o automático desde la escalera). */
  private reinitParticlesTier(tier: QualityTier): void {
    const obj = this.particles.object3D;
    if (obj) this.scene.remove(obj);
    this.particles.setTier(tier);
    const nobj = this.particles.object3D;
    if (nobj) this.scene.add(nobj);
    this.particles.setPalette(DEFAULT_PALETTE);
    this.rhythm.setMaxWaves(TIERS[tier].maxWaves);
  }

  setCoreState(state: CoreStateId): void {
    this.rhythm.setCoreState(state);
    this.lastCoreState = state;
  }

  setVisible(v: boolean): void {
    this.visible = v;
    const obj = this.particles.object3D;
    if (obj) obj.visible = v;
  }

  /** Cambio MANUAL de tier (Settings, S3 — doc 13 §16.1). Resetea la escalera
   *  dinámica: el nuevo tier pasa a ser la base desde la que se degrada/sube. */
  setTier(tier: QualityTier): void {
    this.perf.setTier(tier);
    this.lastEffectiveTier = tier;
    this.reinitParticlesTier(tier);
    this.renderConfig = this.perf.renderConfig;
    this.onRenderConfigChange?.(this.renderConfig);
  }

  setPalette(p: Palette): void {
    this.particles.setPalette(p);
  }

  getRenderConfig(): RenderConfig {
    return this.renderConfig;
  }

  setRenderConfigListener(cb: ((c: RenderConfig) => void) | null): void {
    this.onRenderConfigChange = cb;
  }

  get healthy(): boolean {
    return this.particles.healthy;
  }

  get lastError(): string | null {
    return this.particles.lastError;
  }

  dispose(): void {
    const obj = this.particles.object3D;
    if (obj) this.scene.remove(obj);
    this.particles.dispose();
    this.rhythm.dispose();
    this.audio.dispose();
    this.mounted = false;
  }
}
