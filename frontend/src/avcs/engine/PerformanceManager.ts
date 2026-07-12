// AVCS — PerformanceManager: ÚNICO módulo autorizado a mutar presupuestos
// (doc 13 §16). Tier manual Q1-Q3 (Settings) + escalera dinámica pasos 1-3:
//   nivel 1: bloom off · nivel 2: + DPR 1.0 · nivel 3: + bajar textura sim un paso.
// Invariantes que NUNCA se degradan (§16.4): la escalera jamás baja de 64² ni
// toca semilla/respiración/sincronía — solo bloom, DPR y nº de partículas.
import { TIERS } from "../constants";
import type { QualityTier } from "../types";

export interface RenderConfig {
  bloom: boolean;
  bloomIntensity: number;
  dpr: number;
  maxWaves: number;
}

const SIM_LADDER: Record<number, number> = { 64: 64, 128: 64, 256: 128, 512: 256 };

export class PerformanceManager {
  private baseTier: QualityTier;
  private level = 0; // 0..3 (escalón de degradación)
  private frames: number[] = [];
  private windowMs = 3000;
  private acc = 0;

  constructor(initialTier: QualityTier) {
    this.baseTier = initialTier;
  }

  setTier(tier: QualityTier): void {
    this.baseTier = tier;
    this.level = 0;
    this.frames.length = 0;
  }

  get tier(): QualityTier {
    return this.baseTier;
  }

  /** Tamaño de textura de simulación efectivo (tras la escalera). */
  get simSize(): number {
    const base = TIERS[this.baseTier].sim;
    return this.level >= 3 ? Math.max(64, SIM_LADDER[base]) : base;
  }

  /** Tier efectivo (escalón 3: baja un nivel de calidad completo — menos
   *  partículas, no solo menos resolución de textura — nunca por debajo de Q1,
   *  §16.4). HubEngine lo usa para re-inicializar el ParticleEngine SIN pasar
   *  por setTier() (que resetearía la propia escalera). */
  get effectiveTier(): QualityTier {
    if (this.level < 3) return this.baseTier;
    const LADDER: QualityTier[] = ["Q1", "Q2", "Q3", "Q4"];
    const idx = LADDER.indexOf(this.baseTier);
    return LADDER[Math.max(0, idx - 1)];
  }

  get renderConfig(): RenderConfig {
    const spec = TIERS[this.baseTier];
    return {
      bloom: spec.bloom && this.level < 1,
      bloomIntensity: spec.bloomIntensity,
      dpr: this.level >= 2 ? 1.0 : spec.dpr,
      maxWaves: spec.maxWaves,
    };
  }

  /** Observa el frametime; puede subir/bajar un escalón. Devuelve true si cambió
   *  algo que el consumidor deba re-aplicar (sim size / bloom / dpr). */
  observe(frameMs: number): boolean {
    this.frames.push(frameMs);
    this.acc += frameMs;
    if (this.acc < this.windowMs) return false;

    const avg = this.frames.reduce((a, b) => a + b, 0) / this.frames.length;
    this.frames.length = 0;
    this.acc = 0;

    const before = this.level;
    if (avg > 26 && this.level < 3) {
      this.level++; // >26ms (~38 FPS) sostenido → degradar
    } else if (avg < 13 && this.level > 0) {
      this.level--; // <13ms (~77 FPS) → restaurar (histéresis amplia, no oscila)
    }
    return this.level !== before;
  }

  reset(): void {
    this.level = 0;
    this.frames.length = 0;
    this.acc = 0;
  }
}
