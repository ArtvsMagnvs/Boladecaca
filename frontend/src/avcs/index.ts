// AVCS — barrel público. El resto de la app SOLO importa desde aquí.
export { AitheraPresence } from "./react/AitheraPresence";
export type { AitheraPresenceProps } from "./react/AitheraPresence";
export type {
  RhythmName,
  FieldName,
  FieldWeights,
  Palette,
  QualityTier,
  AudioFrame,
  StructureSpec,
  StructureHandle,
  CoreStateId,
} from "./types";
export { PALETTES, DEFAULT_PALETTE, DEFAULT_TIER } from "./constants";
export { attachVoiceAudio } from "./audio/AudioBridge";
