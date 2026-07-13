// pages/Workspace/Modal.tsx — shell de popup reutilizable (V0.87 WPMS W2a)
//
// Ratón primero: cierra con Esc, con clic fuera y con el botón X; el botón de
// guardar es siempre visible. El popup nunca saca al usuario de su contexto
// (patrón Linear, doc 18 §9.2).
import { useEffect, type ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  widthClass?: string;
}

export function Modal({ title, onClose, children, footer, widthClass = "max-w-lg" }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm p-6 overflow-y-auto"
      onMouseDown={onClose}
    >
      <div
        className={`w-full ${widthClass} mt-[6vh] glass-surface rounded-2xl border border-base-700 shadow-glass`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-base-700/60">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <button
            onClick={onClose}
            className="text-ink-faint hover:text-ink text-lg leading-none px-1"
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>
        <div className="px-5 py-4 flex flex-col gap-4 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-base-700/60">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

// Estilos compartidos de campos (para consistencia entre popups).
export const fieldLabel = "text-[11px] uppercase tracking-wide text-ink-faint mb-1.5 block";
export const fieldInput =
  "w-full bg-base-800 border border-base-700 rounded-xl px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent/50 focus:outline-none";
export const btnPrimary =
  "px-4 py-2 bg-accent/15 text-accent rounded-xl text-sm font-medium border border-accent/30 hover:bg-accent/25 disabled:opacity-40 disabled:cursor-not-allowed";
export const btnGhost = "px-4 py-2 bg-base-700/50 text-ink-dim rounded-xl text-sm hover:text-ink";
