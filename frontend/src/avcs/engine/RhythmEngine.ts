// AVCS — RhythmEngine: state machine de ritmos. Traduce coreState → ritmo,
// interpola vectores de pesos (crossfade), calcula la respiración (§8, nunca
// sin(t)) y gestiona el nacimiento/disolución de ondas (Poisson). SOLO escribe
// el bus de uniforms; NUNCA toca three.js (salvo mutar .value de los uniforms).
import {
  FIELD_COUNT,
  MAX_WAVES,
  RHYTHM_BREATH_PERIOD,
  RHYTHM_SYNC,
  RHYTHM_WEIGHTS,
  STATE_TO_RHYTHM,
  WAVE_MAX_RADIUS,
  weightsToArray,
} from "../constants";
import { mulberry32, noise1D, poissonInterval } from "../math/prng";
import type { CoreStateId, RhythmName, UniformBus } from "../types";

interface Wave {
  r: number;
  vel: number;
  age: number;
  ampBase: number;
  seed: number;
}

export interface RhythmEngineOptions {
  bus: UniformBus;
  sessionSeed: number;
}

const TWO_PI = Math.PI * 2;

export class RhythmEngine {
  private bus: UniformBus;
  private rand: () => number;

  private rhythm: RhythmName = "repose";
  private targetWeights = new Float32Array(FIELD_COUNT);
  private curWeights = new Float32Array(FIELD_COUNT);
  private crossfadeSpeed = 1 / 3; // 3s por defecto (2-4s doc 13)
  private targetSync = 0.9;

  // Respiración
  private breathPhase = 0; // acumulador (rad) — velocidad angular variable
  private breathTime = 0;
  private cyclesSinceDeep = 0;
  private nextDeepCycles: number;
  private deepEnv = 0; // 0-1 envolvente de respiración profunda

  // Ondas
  private waves: Wave[] = [];
  private nextWaveIn: number;
  private maxWaves = MAX_WAVES;

  // seeds derivadas (anti-mecanicidad §10.1)
  private seedA: number;
  private seedB: number;

  constructor(opts: RhythmEngineOptions) {
    this.bus = opts.bus;
    this.rand = mulberry32((opts.sessionSeed | 0) ^ 0x9e37);
    this.seedA = (opts.sessionSeed % 1000) * 0.001 * 7.0;
    this.seedB = ((opts.sessionSeed * 31) % 1000) * 0.001 * 11.0;
    this.nextDeepCycles = 6 + Math.floor(this.rand() * 6); // 6-12
    this.nextWaveIn = poissonInterval(RHYTHM_BREATH_PERIOD.repose, this.rand);
    weightsToArray(RHYTHM_WEIGHTS.repose, this.targetWeights);
    weightsToArray(RHYTHM_WEIGHTS.repose, this.curWeights);
    this.bus.uWeights.value.set(this.curWeights);
  }

  setCoreState(state: CoreStateId): void {
    this.setRhythm(STATE_TO_RHYTHM[state]);
  }

  setRhythm(name: RhythmName, transitionS = 3): void {
    if (name === this.rhythm) return;
    this.rhythm = name;
    weightsToArray(RHYTHM_WEIGHTS[name], this.targetWeights);
    this.targetSync = RHYTHM_SYNC[name];
    this.crossfadeSpeed = 1 / Math.max(0.5, transitionS);
  }

  setSync(s: number, _transitionS = 2): void {
    this.targetSync = Math.max(0, Math.min(1, s));
  }

  setMaxWaves(n: number): void {
    this.maxWaves = n;
  }

  get currentRhythm(): RhythmName {
    return this.rhythm;
  }

  /** Escribe todo el bus para este frame. Llamado por HubEngine.frame. */
  update(dt: number, _time: number, lifePhase: number): void {
    this.updateWeights(dt);
    this.updateBreath(dt, lifePhase);
    this.updateWaves(dt);
  }

  private updateWeights(dt: number): void {
    // crossfade lineal-por-frame hacia el target (curva orgánica suficiente para S1).
    const k = Math.min(1, this.crossfadeSpeed * dt * 3);
    const w = this.bus.uWeights.value;
    for (let i = 0; i < FIELD_COUNT; i++) {
      this.curWeights[i] += (this.targetWeights[i] - this.curWeights[i]) * k;
      w[i] = this.curWeights[i];
    }
    this.bus.uSync.value += (this.targetSync - this.bus.uSync.value) * k;
  }

  private updateBreath(dt: number, lifePhase: number): void {
    this.breathTime += dt;
    const P = RHYTHM_BREATH_PERIOD[this.rhythm];
    // (1) periodo modulado por noise 1D lento (±15%) — desplazado por sessionSeed+lifePhase
    const period = P * (1 + 0.15 * noise1D(lifePhase * 0.05 + this.seedA));
    const omega = TWO_PI / period;
    const prevCycle = Math.floor(this.breathPhase / TWO_PI);
    this.breathPhase += omega * dt; // velocidad angular NO constante → ceros irregulares
    const cycle = Math.floor(this.breathPhase / TWO_PI);

    // (2) conteo de ciclos + respiración profunda Poisson cada 6-12
    if (cycle !== prevCycle) {
      this.cyclesSinceDeep++;
      if (this.cyclesSinceDeep >= this.nextDeepCycles) {
        this.deepEnv = 1;
        this.cyclesSinceDeep = 0;
        this.nextDeepCycles = 6 + Math.floor(this.rand() * 6);
      }
    }
    this.deepEnv = Math.max(0, this.deepEnv - dt / 4.5); // decae ~4.5s

    // (3) amplitud: jitter 8% + boost profundo hasta 1.4x
    const jitter = 1 + 0.08 * noise1D(this.breathTime * 0.3 + this.seedB);
    const deep = 1 + 0.4 * smooth01(this.deepEnv);
    const amp = 0.065 * jitter * deep;

    // (4) señal: sin() de una FASE YA DEFORMADA (no de t) + micro-fluctuación
    const raw = Math.sin(this.breathPhase);
    const ripple = 0.06 * noise1D(this.breathPhase * 1.7 + 3.1 + this.seedA);
    const signal = raw + ripple;

    this.bus.uBreath.value = amp * signal; // drive radial (fuerza)
    this.bus.uBreathScale.value = 1 + amp * signal * 0.5; // escala/glow del núcleo
  }

  private updateWaves(dt: number): void {
    // avanzar + disolver
    for (let i = this.waves.length - 1; i >= 0; i--) {
      const wv = this.waves[i];
      wv.age += dt;
      wv.r += wv.vel * dt;
      wv.vel *= Math.pow(0.985, dt * 60); // desacelera (frame-rate independiente)
      const amp = wv.ampBase * Math.exp(-wv.age / 1.6);
      if (wv.r > WAVE_MAX_RADIUS || amp < 0.004) {
        this.waves.splice(i, 1); // disolución (nunca "pop": amp ya decayó a ~0)
      }
    }
    // nacimiento Poisson en torno al periodo respiratorio
    this.nextWaveIn -= dt;
    if (this.nextWaveIn <= 0) {
      this.nextWaveIn = poissonInterval(RHYTHM_BREATH_PERIOD[this.rhythm], this.rand);
      if (this.waves.length < this.maxWaves) {
        this.waves.push({ r: 0.05, vel: 0.85, age: 0, ampBase: 0.12, seed: this.rand() * 1000 });
      }
    }
    // volcar al bus
    const R = this.bus.uWaveR.value;
    const A = this.bus.uWaveAmp.value;
    const S = this.bus.uWaveSeed.value;
    const n = Math.min(this.waves.length, MAX_WAVES);
    for (let i = 0; i < n; i++) {
      const wv = this.waves[i];
      R[i] = wv.r;
      A[i] = wv.ampBase * Math.exp(-wv.age / 1.6);
      S[i] = wv.seed;
    }
    for (let i = n; i < MAX_WAVES; i++) {
      A[i] = 0;
    }
    this.bus.uWaveCount.value = n;
  }

  dispose(): void {
    this.waves.length = 0;
  }
}

function smooth01(x: number): number {
  const t = Math.max(0, Math.min(1, x));
  return t * t * (3 - 2 * t);
}
