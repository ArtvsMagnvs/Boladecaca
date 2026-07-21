// components/Modal.tsx — shell de modal reutilizable (Opt v0.9.5, O2)
//
// El primitivo de ventana modal de Aithera: backdrop atenuado con blur, panel
// centrado con tamaño máximo (no ocupa toda la pantalla), cierre por Esc y por
// clic fuera, y bloqueo del scroll del fondo mientras está abierto. Estética de
// app desktop de alta gama (misma línea que Claude/ChatGPT desktop): superficie
// de cristal, bordes sutiles, esquinas redondeadas grandes.
//
// Lo usa Settings (como panel de ajustes), y queda disponible para cualquier
// diálogo futuro que deba dejar de ser una página a pantalla completa.
import { useEffect, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Ancho máximo del panel. Default: 5xl (≈1024px), cómodo para ajustes. */
  maxWidth?: string;
  /** aria-label del diálogo (accesibilidad). */
  label?: string;
  /** [2026-07-21] Altura FIJA (88vh) en vez de máxima: el panel no cambia de
   *  tamaño según el contenido — lo pide Ajustes para que las pestañas no
   *  hagan "saltar" la ventana al cambiar entre una corta y una larga. */
  fixedHeight?: boolean;
}

export default function Modal({ open, onClose, children, maxWidth = "max-w-5xl", label, fixedHeight = false }: ModalProps) {
  // Esc cierra; el scroll del fondo se bloquea mientras el modal vive.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      {/* Backdrop: clic fuera cierra. */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        style={{ animation: "modal-fade var(--duration-base) var(--ease-smooth)" }}
        onClick={onClose}
      />
      {/* Panel — borde/sombra por tema vía .modal-panel (index.css), no azul
          hardcodeado (en claro quedaba chillón). */}
      <div
        className={`relative w-full ${maxWidth} ${fixedHeight ? "h-[88vh]" : "max-h-[88vh]"} flex flex-col overflow-hidden rounded-2xl modal-panel bg-base-900/95`}
        style={{ animation: "modal-pop var(--duration-base) var(--ease-smooth)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
