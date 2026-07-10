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
    this.rhythm.update(d, this.time, this.lifePhase);
    this.particles.update(d);

    // presupuesto (escalera dinámica)
    if (this.perf.observe(dt * 1000)) {
      this.applyPerf();
    }
  }

  private applyPerf(): void {
    // S1 (perf v0): la escalera dinámica re-aplica bloom/DPR/maxWaves. La
    // reducción real del tamaño de textura sim (escalón 3) se afina en MVP1;
    // aquí no se re-inicializa el FBO en caliente para no arriesgar estabilidad.
    const cfg = this.perf.renderConfig;
    this.renderConfig = cfg;
    this.rhythm.setMaxWaves(cfg.maxWaves);
    this.onRenderConfigChange?.(cfg);
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

  setTier(tier: QualityTier): void {
    this.perf.setTier(tier);
    const obj = this.particles.object3D;
    if (obj) this.scene.remove(obj);
    this.particles.setTier(tier);
    const nobj = this.particles.object3D;
    if (nobj) this.scene.add(nobj);
    this.particles.setPalette(DEFAULT_PALETTE);
    this.rhythm.setMaxWaves(TIERS[tier].maxWaves);
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
