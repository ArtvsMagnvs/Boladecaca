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

/** [PU5e] Por encima de esto un frame no se considera una medida de
 *  rendimiento sino un artefacto. 200 ms = 5 FPS: ningún equipo que de verdad
 *  vaya a 5 FPS sostenidos llega aquí sin haber degradado antes con muestras
 *  normales, así que filtrar no enmascara un problema real — solo evita que un
 *  parón puntual (pestaña en segundo plano, GC, cambio de ventana) dispare una
 *  degradación que el usuario percibe como "se ha apagado". */
const MAX_SANE_FRAME_MS = 200;
/** Frames que se ignoran tras uno anómalo: al volver de segundo plano suelen
 *  venir 2-3 aún irregulares mientras el navegador recompone. */
const GRACE_FRAMES = 6;

export class PerformanceManager {
  private baseTier: QualityTier;
  private level = 0; // 0..3 (escalón de degradación)
  private frames: number[] = [];
  private windowMs = 3000;
  private acc = 0;
  private graceFrames = 0;

  constructor(initialTier: QualityTier) {
    this.baseTier = initialTier;
  }

  setTier(tier: QualityTier): void {
    this.baseTier = tier;
    this.level = 0;
    this.frames.length = 0;
    this.acc = 0;
    this.graceFrames = 0;
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
   *  partículas, no solo menos resolución de textura — nunca por debajo de Q2,
   *  §16.4). HubEngine lo usa para re-inicializar el ParticleEngine SIN pasar
   *  por setTier() (que resetearía la propia escalera). */
  get effectiveTier(): QualityTier {
    if (this.level < 3) return this.baseTier;
    const LADDER: QualityTier[] = ["Q2", "Q3", "Q4"];
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
    // ------------------------------------------------------------------
    // [PU5e] EL BUG DEL "SE APAGA AL VOLVER DE OTRA PESTAÑA".
    // ------------------------------------------------------------------
    // Síntoma: con Aithera en segundo plano la luminosidad caía de golpe, y al
    // volver tardaba unos segundos en recuperarse.
    // Causa: el navegador PAUSA requestAnimationFrame en una pestaña oculta, así
    // que el primer frame al volver trae un `dt` enorme — todo el tiempo que
    // estuviste fuera. Esa única muestra bastaba para superar la ventana de
    // 3000 ms de golpe, dar una media altísima y degradar un escalón. Y el
    // escalón 1 es precisamente `bloom: false` → el glow desaparece = "baja la
    // luminosidad". Unos segundos después, con frames normales, la media volvía
    // a bajar de 13 ms, se restauraba el escalón y con él el bloom = "se
    // ilumina de nuevo". El ciclo completo que se veía.
    //
    // Arreglo: un frame anormalmente largo NO mide rendimiento — es un
    // artefacto (pestaña oculta, GC, el SO ocupado, la ventana redimensionada).
    // Se descarta, se limpia la ventana de muestreo para que no arrastre nada
    // raro, y se abre un breve periodo de gracia porque tras volver de segundo
    // plano suelen venir 2-3 frames aún irregulares mientras el navegador
    // recompone.
    if (frameMs > MAX_SANE_FRAME_MS) {
      this.frames.length = 0;
      this.acc = 0;
      this.graceFrames = GRACE_FRAMES;
      return false;
    }
    if (this.graceFrames > 0) {
      this.graceFrames--;
      return false;
    }

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
    this.graceFrames = 0;
  }
}
