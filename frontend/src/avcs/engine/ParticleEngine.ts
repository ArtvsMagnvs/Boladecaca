// AVCS — ParticleEngine: simulación GPGPU (GPUComputationRenderer ping-pong) +
// render THREE.Points. API pública CONGELADA (ARCHITECTURE.md §2, doc 13 §12).
//
// GOTCHAS S0 respetados: no declarar texturePosition/textureVelocity en los
// fragments de sim (los antepone init()); resolution es #define; verificar por
// screenshot. La respiración/pesos/ondas los escribe RhythmEngine en el bus, cuyas
// referencias de uniforms comparten los materiales de sim y render.

import * as THREE from "three";
import { GPUComputationRenderer } from "three/examples/jsm/misc/GPUComputationRenderer.js";
import { ShaderSystem } from "../shaders/ShaderSystem";
import { createUniformBus } from "./UniformBus";
import { buildSceneGeometry } from "../math/lotus";
import { TIERS, REST_RADIUS, weightsToArray } from "../constants";
import type { FieldWeights, Palette, QualityTier, StructureHandle, StructureSpec, UniformBus } from "../types";

export interface ParticleEngineOptions {
  renderer: THREE.WebGLRenderer;
  tier: QualityTier;
  sessionSeed: number;
}

export class ParticleEngine {
  readonly bus: UniformBus = createUniformBus();

  private renderer: THREE.WebGLRenderer;
  private tier: QualityTier;
  private sessionSeed: number;
  private sim = 256;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private gpu: any = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private posVar: any = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private velVar: any = null;

  private genomeTex: THREE.DataTexture | null = null;
  private anchorTex: THREE.DataTexture | null = null;
  private points: THREE.Points | null = null;
  private renderMat: THREE.ShaderMaterial | null = null;
  private geometry: THREE.BufferGeometry | null = null;

  private nextHandleId = 1;
  private initError: string | null = null;

  constructor(opts: ParticleEngineOptions) {
    this.renderer = opts.renderer;
    this.tier = opts.tier;
    this.sessionSeed = opts.sessionSeed;
    this.bus.uSessionSeed.value = (opts.sessionSeed % 1000) / 1000;
  }

  /** Crea el GPGPU, siembra la semilla y construye el render. Idempotente-ish
   *  (dispose antes de re-init en setTier). */
  init(): void {
    const spec = TIERS[this.tier];
    this.sim = spec.sim;
    const N = spec.particles;

    const gpu = new GPUComputationRenderer(this.sim, this.sim, this.renderer);

    // --- Geometría de la escena (semilla-logo + 2ª capa: anillos/bandas/starfield) ---
    const { genome, anchor } = buildSceneGeometry(N, REST_RADIUS, spec.seedFraction, this.sessionSeed);

    // Textura de posición inicial = anclas (+ jitter mínimo) → la forma nace visible.
    const posTex = gpu.createTexture();
    const velTex = gpu.createTexture();
    const posData = posTex.image.data as unknown as Float32Array;
    const velData = velTex.image.data as unknown as Float32Array;
    for (let i = 0; i < N; i++) {
      const i4 = i * 4;
      posData[i4] = anchor[i4] + (Math.random() - 0.5) * 0.03;
      posData[i4 + 1] = anchor[i4 + 1] + (Math.random() - 0.5) * 0.03;
      posData[i4 + 2] = anchor[i4 + 2] + (Math.random() - 0.5) * 0.03;
      posData[i4 + 3] = 0; // edad
      velData[i4] = 0;
      velData[i4 + 1] = 0;
      velData[i4 + 2] = 0;
      velData[i4 + 3] = 0;
    }

    // Texturas estáticas (uniforms propios, no variables GPGPU).
    this.genomeTex = new THREE.DataTexture(genome, this.sim, this.sim, THREE.RGBAFormat, THREE.FloatType);
    this.anchorTex = new THREE.DataTexture(anchor, this.sim, this.sim, THREE.RGBAFormat, THREE.FloatType);
    for (const t of [this.genomeTex, this.anchorTex]) {
      t.minFilter = THREE.NearestFilter;
      t.magFilter = THREE.NearestFilter;
      t.needsUpdate = true;
    }

    // --- Variables GPGPU ---
    const velVar = gpu.addVariable("textureVelocity", ShaderSystem.buildSimVelocity(), velTex);
    const posVar = gpu.addVariable("texturePosition", ShaderSystem.buildSimPosition(), posTex);
    gpu.setVariableDependencies(velVar, [velVar, posVar]);
    gpu.setVariableDependencies(posVar, [velVar, posVar]);

    // Uniforms propios en cada material de sim, COMPARTIENDO las referencias del bus.
    Object.assign(velVar.material.uniforms, {
      uTime: this.bus.uTime,
      uDelta: this.bus.uDelta,
      uSessionSeed: this.bus.uSessionSeed,
      uSync: this.bus.uSync,
      uDamping: this.bus.uDamping,
      uSeedCenter: this.bus.uSeedCenter,
      uGravityDir: this.bus.uGravityDir,
      uWeights: this.bus.uWeights,
      uBreathScale: this.bus.uBreathScale,
      uCoreSpin: this.bus.uCoreSpin,
      uPulse: this.bus.uPulse,
      uCurlFreq: this.bus.uCurlFreq,
      uCurlFlow: this.bus.uCurlFlow,
      uWaveCount: this.bus.uWaveCount,
      uWaveR: this.bus.uWaveR,
      uWaveAmp: this.bus.uWaveAmp,
      uWaveSeed: this.bus.uWaveSeed,
      uWaveThickness: this.bus.uWaveThickness,
      uAudioEnv: this.bus.uAudioEnv,
      uGenome: { value: this.genomeTex },
      uAnchor: { value: this.anchorTex },
    });
    Object.assign(posVar.material.uniforms, { uDelta: this.bus.uDelta });

    const error = gpu.init();
    if (error !== null) {
      this.initError = String(error);
      console.error("[AVCS ParticleEngine] GPUComputationRenderer.init() falló:", error);
      return;
    }
    this.initError = null;
    this.gpu = gpu;
    this.velVar = velVar;
    this.posVar = posVar;

    this.buildRenderObject(N);
    if (import.meta.env.DEV) {
      console.info(`[AVCS ParticleEngine] init OK — ${N} partículas, sim ${this.sim}² (tier ${this.tier}).`);
    }
  }

  private buildRenderObject(N: number): void {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(N * 3); // dummy (el vertex shader lee de textura)
    const refs = new Float32Array(N * 2);
    for (let i = 0; i < N; i++) {
      refs[i * 2] = (i % this.sim) / this.sim;
      refs[i * 2 + 1] = Math.floor(i / this.sim) / this.sim;
    }
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("aRef", new THREE.BufferAttribute(refs, 2));
    geo.setDrawRange(0, N);

    const mat = new THREE.ShaderMaterial({
      uniforms: {
        texturePosition: { value: null },
        uGenome: { value: this.genomeTex },
        uAnchor: { value: this.anchorTex },
        uPointSize: this.bus.uPointSize,
        uDpr: { value: Math.min(2, this.renderer.getPixelRatio()) },
        uTime: this.bus.uTime,
        uHeart: this.bus.uHeart,
        uAura: this.bus.uAura,
        uField: this.bus.uField,
      },
      vertexShader: ShaderSystem.buildRenderVertex(),
      fragmentShader: ShaderSystem.buildRenderFragment(),
      transparent: true,
      depthWrite: false,
      depthTest: false,
      blending: THREE.AdditiveBlending,
    });

    const points = new THREE.Points(geo, mat);
    points.frustumCulled = false; // las posiciones vienen de textura
    this.geometry = geo;
    this.renderMat = mat;
    this.points = points;
  }

  /** Avanza un paso de simulación GPGPU y actualiza la textura de posición del render. */
  update(_dt: number): void {
    if (!this.gpu || !this.renderMat) return;
    this.gpu.compute();
    this.renderMat.uniforms.texturePosition.value = this.gpu.getCurrentRenderTarget(this.posVar).texture;
  }

  // ---- API pública congelada (doc 13 §12) ----

  setFieldWeights(weights: FieldWeights): void {
    weightsToArray(weights, this.bus.uWeights.value);
  }

  setSync(s: number): void {
    this.bus.uSync.value = Math.max(0, Math.min(1, s));
  }

  setPalette(p: Palette): void {
    this.bus.uHeart.value.setRGB(p.heart[0], p.heart[1], p.heart[2]);
    this.bus.uAura.value.setRGB(p.aura[0], p.aura[1], p.aura[2]);
    this.bus.uField.value.setRGB(p.field[0], p.field[1], p.field[2]);
  }

  /** S1 realiza 'seed' en init(); el resto devuelve un handle no-op (firma viva). */
  spawnStructure(spec: StructureSpec): StructureHandle {
    return { id: this.nextHandleId++, kind: spec.kind };
  }

  /** Patrón universal de disolución (doc 13 §7.5). S1: no-op estructural (la
   *  semilla nunca se disuelve; las ondas se gestionan por uniforms). */
  dissolve(_handle: StructureHandle, _durationS = 1.0): void {
    /* MVP1: entrega las partículas de la estructura a F_curl + F_return. */
  }

  // ---- plumbing (solo PerformanceManager/HubEngine) ----

  setTier(tier: QualityTier): void {
    if (tier === this.tier && this.gpu) return;
    this.tier = tier;
    this.disposeGpu();
    this.init();
  }

  get object3D(): THREE.Points | null {
    return this.points;
  }

  get healthy(): boolean {
    return this.gpu !== null && this.initError === null;
  }

  get lastError(): string | null {
    return this.initError;
  }

  private disposeGpu(): void {
    try {
      this.gpu?.dispose?.();
    } catch {
      /* noop */
    }
    this.gpu = null;
    this.posVar = null;
    this.velVar = null;
    this.genomeTex?.dispose();
    this.anchorTex?.dispose();
    this.geometry?.dispose();
    this.renderMat?.dispose();
    this.points = null;
  }

  dispose(): void {
    this.disposeGpu();
  }
}
