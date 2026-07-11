// AVCS — construcción del bus de uniforms (ARCHITECTURE.md §3).
// Objetos {value} de three, mutados en sitio, compartidos por referencia entre
// los materiales de simulación (GPGPU), el material de render y RhythmEngine.
import * as THREE from "three";
import { FIELD_COUNT, MAX_WAVES, REST_RADIUS, WAVE_THICKNESS, DEFAULT_PALETTE } from "../constants";
import { weightsToArray } from "../constants";
import { RHYTHM_WEIGHTS } from "../constants";
import type { UniformBus } from "../types";

export function createUniformBus(): UniformBus {
  const heart = new THREE.Color(...DEFAULT_PALETTE.heart);
  const aura = new THREE.Color(...DEFAULT_PALETTE.aura);
  const field = new THREE.Color(...DEFAULT_PALETTE.field);

  return {
    uTime: { value: 0 },
    uDelta: { value: 0 },
    uSessionSeed: { value: 0 },
    uLifePhase: { value: 0 },
    uWeights: { value: weightsToArray(RHYTHM_WEIGHTS.repose) },
    uSync: { value: 0.9 },
    uSeedCenter: { value: new THREE.Vector3(0, 0, 0) },
    uBounds: { value: REST_RADIUS * 2.6 },
    uDamping: { value: 0.9 },
    uBreathScale: { value: 1 },
    uCoreSpin: { value: 0 },
    uPulse: { value: 0 },
    uWaveCount: { value: 0 },
    uWaveR: { value: new Float32Array(MAX_WAVES) },
    uWaveAmp: { value: new Float32Array(MAX_WAVES) },
    uWaveSeed: { value: new Float32Array(MAX_WAVES) },
    uWaveThickness: { value: WAVE_THICKNESS },
    uGravityDir: { value: new THREE.Vector3(0, 0, 0) },
    uCurlFreq: { value: 0.6 },
    uCurlFlow: { value: 0.05 },
    uHeart: { value: heart },
    uAura: { value: aura },
    uField: { value: field },
    uAudioEnv: { value: 0 },
    uAudioBands: { value: new THREE.Vector3(0, 0, 0) },
    uPointSize: { value: 42 },
  };
}

/** Longitud esperada del array de pesos (sanity check en dev). */
export const EXPECTED_WEIGHTS_LEN = FIELD_COUNT;
