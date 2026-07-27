// pages/Workspace/Modal.tsx — shell de popup reutilizable (V0.87 WPMS W2a)
//
// Ratón primero: cierra con Esc, con clic fuera y con el botón X; el botón de
// guardar es siempre visible. El popup nunca saca al usuario de su contexto
// (patrón Linear, doc 18 §9.2).
import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useT } from "@/store/useI18n";
import { Z_MODAL } from "./layers";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  widthClass?: string;
}

export function Modal({ title, onClose, children, footer, widthClass = "max-w-lg" }: ModalProps) {
  const t = useT();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // [2026-07-25] PORTAL + capa Z_MODAL. Antes era `fixed inset-0 z-50` dentro del
  // árbol de la tarjeta: (a) las tarjetas suben de z-index al clicarlas y pasaban
  // de 50, tapando el popup; (b) los popups que viven DENTRO de una tarjeta
  // (TaskPopup, MilestonePopup) quedaban atrapados en su stacking context, donde
  // ningún z-index les habría servido. El portal los saca a `document.body` y
  // `Z_MODAL` los pone por encima de todo el rango de tarjetas (ver layers.ts).
  const overlay = (
    <div
      className="fixed inset-0 flex items-start justify-center bg-black/50 backdrop-blur-sm p-6 overflow-y-auto"
      style={{ zIndex: Z_MODAL }}
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
            aria-label={t("common.close")}
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

  // `document.body` puede no existir en un render de servidor; en Electron
  // siempre está, pero la guarda evita cualquier sorpresa en tests/SSR.
  return typeof document !== "undefined" ? createPortal(overlay, document.body) : overlay;
}

// Banner de error compartido: sin esto, un fallo al guardar (nombre
// duplicado, backend caido, migracion sin aplicar...) se veia como "no pasa
// nada al pulsar el boton" — el popup se quedaba abierto sin ninguna pista.
export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
      {message}
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
