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
  /** [2026-07-21] Altura FIJA en vez de máxima: el panel no cambia de
   *  tamaño según el contenido — lo pide Ajustes para que las pestañas no
   *  hagan "saltar" la ventana al cambiar entre una corta y una larga. */
  fixedHeight?: boolean;
  /** [PU6b-vent t4] Sin velo: el fondo NO se oscurece ni se desenfoca — el
   *  AVCS se sigue viendo intacto alrededor de la ventana (petición del
   *  usuario para Ajustes; el clic fuera sigue cerrando igual). Dentro de la
   *  ventana nada cambia. */
  clearBackdrop?: boolean;
}

export default function Modal({ open, onClose, children, maxWidth = "max-w-5xl", label, fixedHeight = false, clearBackdrop = false }: ModalProps) {
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
      // [PU6b-vent t4] `pb-28`: el hueco del dock (botones con centro a 64px)
      // se descuenta del área de centrado — el panel queda centrado en el
      // espacio LIBRE y su borde inferior nunca invade los botones.
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 pb-28 sm:pb-28"
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      {/* Backdrop: clic fuera cierra. Con `clearBackdrop`, transparente del
          todo (el AVCS se ve intacto alrededor); sin él, el velo de siempre. */}
      <div
        className={`absolute inset-0 ${clearBackdrop ? "" : "bg-black/60 backdrop-blur-sm"}`}
        style={clearBackdrop ? undefined : { animation: "modal-fade var(--duration-base) var(--ease-smooth)" }}
        onClick={onClose}
      />
      {/* Panel — borde/sombra por tema vía .modal-panel (index.css), no azul
          hardcodeado (en claro quedaba chillón).
          [PU6b-vent t4] Tope de altura acotado también por PÍXELES:
          calc(100vh−150px) deja sitio al dock (centro a 64px + etiqueta) — con
          el 88vh a secas, en pantallas bajas el panel llegaba hasta detrás de
          los botones. En pantallas altas manda el 88vh, como siempre. */}
      <div
        className={`relative w-full ${maxWidth} ${fixedHeight ? "h-[min(88vh,calc(100vh_-_150px))]" : "max-h-[min(88vh,calc(100vh_-_150px))]"} flex flex-col overflow-hidden rounded-2xl modal-panel holo-frame bg-base-900/95`}
        style={{ animation: "modal-pop var(--duration-base) var(--ease-smooth)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
