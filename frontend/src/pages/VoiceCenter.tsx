// TOMBSTONE (2026-07-21) — el Centro de Voz se fusionó en Configuración → Voz.
// Todo el contenido vive ahora en components/voice/VoicePanel.tsx; la ruta
// /voice redirige a /settings (App.tsx). Este archivo queda solo para que un
// import rezagado no rompa; puede borrarse con `git rm` cuando se quiera.
export { default } from "@/components/voice/VoicePanel";
