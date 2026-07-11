// AVCS — tipos públicos CONGELADOS (ver ARCHITECTURE.md §2).
// MVP1/MVP2 añaden entradas de tabla / funciones de campo / variantes de union,
// NUNCA cambian estas firmas.
import type * as THREE from "three";

/** Estado del núcleo tal como lo expone el store (useAppStore.AICoreState).
 *  Se duplica aquí como tipo del AVCS para trazabilidad; deben coincidir. */
export type CoreStateId =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "processing"
  | "error"
  | "action"
  | "recovering";

/** Los 7 ritmos (doc 13 §4). S1 implementa 'repose' completo; el resto son
 *  entradas de tabla (placeholder = pesos de reposo) hasta S2/MVP1. */
export type RhythmName =
  | "repose"        // Reposo         (S1)
  | "listening"     // Escucha        (S2)
  | "communication" // Comunicación   (S2)
  | "comprehension" // Comprensión    (MVP1)
  | "action"        // Acción         (MVP1)
  | "recovery"      // Recuperación   (MVP1)
  | "error";        // Error          (MVP1)

/** Biblioteca FIJA de campos de fuerza (doc 13 §5). El ORDEN (FIELD_ORDER en
 *  constants.ts) es la posición en uWeights[10]. APPEND-ONLY: nuevos campos al
 *  final, jamás reordenar. */
export type FieldName =
  | "breath"
  | "wave"
  | "curl"
  | "gravity"
  | "root"
  | "branch"
  | "mandala"
  | "channel"
  | "return"
  | "self";

/** Vector de pesos: diccionario completo (Reposo rellena los 10). Añadir un
 *  campo nuevo = una clave nueva; ningún consumidor existente se rompe. */
export type FieldWeights = Record<FieldName, number>;

/** Paleta de un ritmo. El corazón (heart) es Ámbar CONSTANTE — nunca cambia
 *  entre ritmos (invariante nº1). aura = color del ritmo; field = partículas de campo. */
export interface Palette {
  /** RGB 0-1 lineal. */
  heart: readonly [number, number, number];
  aura: readonly [number, number, number];
  field: readonly [number, number, number];
}

export type QualityTier = "Q1" | "Q2" | "Q3" | "Q4";

/** Salida del AudioReactor (stub en S1, real en S2). Contrato doc 13 §8. */
export interface AudioFrame {
  envelope: number; // 0-1 energía global (RMS suavizado)
  bands: readonly [number, number, number]; // graves/medios/agudos 0-1
  silence: boolean;
}

/** Estructuras procedurales materializables. Unión cerrada = congelada.
 *  S1 realiza 'seed'; el resto tiene firma viva e implementación no-op. */
export type StructureSpec =
  | { kind: "seed"; scale: number; seed: number }
  | { kind: "root"; depth: number; strands: number; seed: number }
  | { kind: "branch"; depth: number; strands: number; seed: number }
  | { kind: "mandala"; fold: number; radius: number }
  | { kind: "channel"; dir: readonly [number, number, number] }
  | { kind: "wave"; amplitude: number; seed: number };

export type StructureKind = StructureSpec["kind"];

export interface StructureHandle {
  readonly id: number;
  readonly kind: StructureKind;
}

/** El bus de uniforms — contrato RhythmEngine → sim shader (ARCHITECTURE.md §3).
 *  Objetos {value} de three, mutados en sitio, compartidos por referencia. */
export interface UniformBus {
  // Tiempo / anti-mecanicidad
  uTime: THREE.IUniform<number>;
  uDelta: THREE.IUniform<number>;
  uSessionSeed: THREE.IUniform<number>;
  uLifePhase: THREE.IUniform<number>;
  // Campos
  uWeights: THREE.IUniform<Float32Array>; // length 10, orden FIELD_ORDER
  uSync: THREE.IUniform<number>; // 0-1
  // Geometría base
  uSeedCenter: THREE.IUniform<THREE.Vector3>;
  uBounds: THREE.IUniform<number>;
  uDamping: THREE.IUniform<number>;
  // Respiración (§8) — forma preservada: escala global + giro del núcleo + latido
  uBreathScale: THREE.IUniform<number>; // escala global del logo (no deforma)
  uCoreSpin: THREE.IUniform<number>; // ángulo de giro acumulado del núcleo
  uPulse: THREE.IUniform<number>; // vibración/latido 0-1 (decae tras cada pulso)
  // Ondas (§7)
  uWaveCount: THREE.IUniform<number>;
  uWaveR: THREE.IUniform<Float32Array>; // length 6
  uWaveAmp: THREE.IUniform<Float32Array>; // length 6
  uWaveSeed: THREE.IUniform<Float32Array>; // length 6
  uWaveThickness: THREE.IUniform<number>;
  // Direccionales (S1: gravedad 0; base para Escucha/Comunicación en S2)
  uGravityDir: THREE.IUniform<THREE.Vector3>;
  uCurlFreq: THREE.IUniform<number>;
  uCurlFlow: THREE.IUniform<number>;
  // Paleta (resuelta a RGB lineal)
  uHeart: THREE.IUniform<THREE.Color>; // Ámbar constante
  uAura: THREE.IUniform<THREE.Color>;
  uField: THREE.IUniform<THREE.Color>;
  // Audio (stub S1)
  uAudioEnv: THREE.IUniform<number>;
  uAudioBands: THREE.IUniform<THREE.Vector3>;
  // Render / tier (los escribe PerformanceManager)
  uPointSize: THREE.IUniform<number>;
}
