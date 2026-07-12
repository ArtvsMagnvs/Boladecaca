// AVCS — RhythmEngine: state machine de ritmos. Traduce coreState → ritmo,
// interpola vectores de pesos (crossfade), calcula la respiración (§8, nunca
// sin(t)) y gestiona el nacimiento/disolución de ondas (Poisson). SOLO escribe
// el bus de uniforms; NUNCA toca three.js (salvo mutar .value de los uniforms).
import {
  FIELD_COUNT,
  GRAVITY_MAGNITUDE,
  MAX_WAVES,
  RHYTHM_BREATH_PERIOD,
  RHYTHM_GRAVITY_Y,
  RHYTHM_SETTLE_Y,
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

  // Escucha/Comunicación (S2): F_gravity con signo por ritmo + offset de
  // "asentado" del grupo entero. Ambos crossfadean con la misma k que los pesos.
  private targetGravityY = 0;
  private curGravityY = 0;
  private targetSettleY = 0;
  private curSettleY = 0;

  // Respiración (forma preservada): escala global + giro del núcleo + latido
  private breathPhase = 0; // acumulador (rad) — velocidad angular variable
  private breathTime = 0;
  private coreSpinAngle = 0;
  private pulseEnv = 0; // 0-1 envolvente del latido (decae)
  private nextPulseIn: number;

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
    this.nextPulseIn = poissonInterval(6.5, this.rand);
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
    this.targetGravityY = RHYTHM_GRAVITY_Y[name];
    this.targetSettleY = RHYTHM_SETTLE_Y[name];
    this.crossfadeSpeed = 1 / Math.max(0.5, transitionS);
  }

  /** Offset Y a aplicar sobre object3D.position (HubEngine.frame lo lee cada frame). */
  get settleOffset(): number {
    return this.curSettleY;
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
    this.updateBreathAndPulse(dt, lifePhase);
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

    this.curGravityY += (this.targetGravityY - this.curGravityY) * k;
    this.bus.uGravityDir.value.set(0, this.curGravityY * GRAVITY_MAGNITUDE, 0);
    this.curSettleY += (this.targetSettleY - this.curSettleY) * k;
  }

  private updateBreathAndPulse(dt: number, lifePhase: number): void {
    this.breathTime += dt;
    const P = RHYTHM_BREATH_PERIOD[this.rhythm];

    // (1) ESCALA GLOBAL del logo (respira sin deformarse). Periodo variable +
    // micro-fluctuación → nunca sin(t) puro. Amplitud pequeña (±~5%).
    const period = P * (1 + 0.15 * noise1D(lifePhase * 0.05 + this.seedA));
    this.breathPhase += (TWO_PI / period) * dt;
    const raw = Math.sin(this.breathPhase);
    const ripple = 0.06 * noise1D(this.breathPhase * 1.7 + 3.1 + this.seedB);
    const jitter = 1 + 0.1 * noise1D(this.breathTime * 0.3 + this.seedB);
    // Comunicación (doc 13 §13.5, "la voz mueve la presencia"): la envolvente
    // de voz real (ya escrita en el bus por HubEngine antes de este update) se
    // suma a la escala global — el logo entero se hincha visiblemente al
    // hablar, sin deformarse (mismo mecanismo que la respiración ambiental).
    const audioSwell = 0.16 * this.bus.uAudioEnv.value;
    this.bus.uBreathScale.value = 1 + 0.05 * (raw + ripple) * jitter + audioSwell;

    // (2) GIRO del núcleo como un sol: velocidad variable (a veces lenta, a
    // veces invierte el patrón) modulada por noise → nunca mecánico.
    const spinMod = noise1D(this.breathTime * 0.07 + this.seedA * 2.0); // -1..1
    const spinRate = 0.16 + 0.22 * spinMod; // rad/s (puede ir muy lento)
    this.coreSpinAngle += spinRate * dt;
    this.bus.uCoreSpin.value = this.coreSpinAngle;

    // (3) LATIDO (Poisson): un pulso que decae y se propaga (fPulse).
    this.nextPulseIn -= dt;
    if (this.nextPulseIn <= 0) {
      this.pulseEnv = 1;
      this.nextPulseIn = poissonInterval(6.5, this.rand);
    }
    this.pulseEnv = Math.max(0, this.pulseEnv - dt / 1.6); // decae en ~1.6s
    this.bus.uPulse.value = this.pulseEnv;
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
