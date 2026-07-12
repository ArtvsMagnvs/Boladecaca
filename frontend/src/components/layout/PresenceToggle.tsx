// AVCS S3 — Modo Presencia (doc 13 §13.4): botón mínimo de esquina que pliega
// TODA la UI de chrome (sidebar + contenido de página), dejando solo la
// presencia a pantalla completa. Vive FUERA de los contenedores que se
// pliegan (ver AppLayout.tsx) para poder pulsarse también estando activo.
import { useAppStore } from "@/store/useAppStore";

export function PresenceToggle() {
  const presenceMode = useAppStore((s) => s.presenceMode);
  const togglePresenceMode = useAppStore((s) => s.togglePresenceMode);

  return (
    <button
      type="button"
      onClick={togglePresenceMode}
      title={presenceMode ? "Restaurar interfaz (Esc)" : "Modo Presencia (F9)"}
      aria-label="Modo Presencia"
      aria-pressed={presenceMode}
      className={`fixed bottom-5 right-5 z-30 w-9 h-9 rounded-full flex items-center justify-center border backdrop-blur-sm transition-all duration-300 ${
        presenceMode
          ? "bg-base-900/40 text-ink-faint/70 border-base-700/40 hover:text-ink hover:opacity-100 opacity-40 hover:bg-base-900/70"
          : "bg-base-800/70 text-ink-dim border-base-700 hover:text-ink hover:border-accent/40"
      }`}
    >
      {presenceMode ? (
        // "restaurar": flechas hacia dentro (compress)
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 3v4a2 2 0 0 1-2 2H3M15 3v4a2 2 0 0 0 2 2h4M3 15h4a2 2 0 0 1 2 2v4M21 15h-4a2 2 0 0 0-2 2v4" />
        </svg>
      ) : (
        // "presencia": flechas hacia fuera (expand)
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9V5a2 2 0 0 1 2-2h4M21 9V5a2 2 0 0 0-2-2h-4M3 15v4a2 2 0 0 0 2 2h4M21 15v4a2 2 0 0 1-2 2h-4" />
        </svg>
      )}
    </button>
  );
}
