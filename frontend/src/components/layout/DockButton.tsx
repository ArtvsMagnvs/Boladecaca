// DockButton.tsx — El "botón suelto" del dock (PU6a-bis, doc 35 §PU6).
//
// Tres cosas que pidió el usuario y que condicionan el marcado:
//
// 1. **Solo icono; el texto aparece al pasar el ratón, "como integrado"** —
//    y el icono NO se puede mover al aparecer. Por eso la etiqueta es un
//    elemento ABSOLUTO (`top-full`) dentro del botón: al estar fuera del
//    flujo, no aporta altura, así que el centro del círculo se queda
//    exactamente donde estaba. Si fuera un hijo normal en columna, el
//    conjunto crecería hacia abajo y el icono subiría — el fallo concreto
//    que se pidió evitar.
// 2. **Anillo azul con un punto de luz girando** (`.dock-ring`, CSS) —
//    permanente, lento en reposo y acelerado al pasar el ratón.
// 3. **Polvo de estrellas al pulsar**: partículas que salen en todas
//    direcciones y se difuminan. Se generan en `pointerdown` (no en
//    `click`) para que la respuesta sea inmediata al gesto, cada una con su
//    propio vector en --dx/--dy, y se retiran solas al terminar.
import { useCallback, useRef, useState, type CSSProperties, type ReactNode } from "react";

const DUST_COUNT = 14;
const DUST_MS = 760;

interface Burst {
  id: number;
  dots: { dx: string; dy: string; delay: string; size: number }[];
}

function makeBurst(id: number): Burst {
  const dots = Array.from({ length: DUST_COUNT }, (_, i) => {
    // Reparto angular regular + jitter: sin el jitter se ve una estrella
    // mecánica de N puntas; solo con azar quedan huecos feos.
    const angle = (i / DUST_COUNT) * Math.PI * 2 + (Math.random() - 0.5) * 0.45;
    const dist = 26 + Math.random() * 20;
    return {
      dx: `${Math.cos(angle) * dist}px`,
      dy: `${Math.sin(angle) * dist}px`,
      delay: `${Math.random() * 70}ms`,
      size: Math.random() < 0.3 ? 4 : 2.5,
    };
  });
  return { id, dots };
}

export interface DockButtonProps {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
  badge?: number;
  badgeTone?: "error" | "warn";
  /** Tamaño del círculo en px. 62 por defecto (fila central del dock,
   *  [PU6a-bis v2]: +20% sobre los 52 originales, petición del usuario). */
  size?: number;
  /** Alineación de la etiqueta: los botones de esquina la necesitan hacia
   *  dentro de la pantalla para que no se salga por el borde. */
  labelAlign?: "center" | "left" | "right";
}

export function DockButton({
  icon,
  label,
  onClick,
  active = false,
  badge = 0,
  badgeTone = "error",
  size = 62,
  labelAlign = "center",
}: DockButtonProps) {
  const [bursts, setBursts] = useState<Burst[]>([]);
  const seq = useRef(0);

  const fire = useCallback(() => {
    const id = ++seq.current;
    setBursts((b) => [...b, makeBurst(id)]);
    window.setTimeout(() => setBursts((b) => b.filter((x) => x.id !== id)), DUST_MS);
  }, []);

  return (
    <button
      type="button"
      onClick={onClick}
      onPointerDown={fire}
      title={label}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      style={{ width: size, height: size }}
      className="dock-btn group flex items-center justify-center shrink-0 backdrop-blur-md transition-transform duration-200 active:scale-[0.94] focus:outline-none"
    >
      {/* Peana de luz bajo el botón de la sección ACTIVA (lámina de botones). */}
      {active && <span className="dock-platform" />}
      <span className="dock-rim" />
      <span className="dock-ring" />

      {/* Onda + polvo del clic. Fuera del contenedor que escala con
          active:scale para que la explosión no se encoja con el botón. */}
      {bursts.map((b) => (
        <span key={b.id} className="absolute inset-0 pointer-events-none">
          <span className="dock-shock" />
          {b.dots.map((d, i) => (
            <span
              key={i}
              className="dock-dust"
              style={
                {
                  "--dx": d.dx,
                  "--dy": d.dy,
                  animationDelay: d.delay,
                  width: d.size,
                  height: d.size,
                  marginTop: -d.size / 2,
                  marginLeft: -d.size / 2,
                } as CSSProperties
              }
            />
          ))}
        </span>
      ))}

      {/* El glifo: oro cálido de la lámina de referencia. Solo el ICONO
          escala al pasar el ratón — el botón no, para no desplazar nada. */}
      <span
        className={`relative transition-[transform,color,filter] duration-200 group-hover:scale-110 ${
          active
            ? "text-signal-warn brightness-125"
            : "text-signal-warn/75 group-hover:text-signal-warn group-hover:brightness-125"
        }`}
      >
        {icon}
      </span>

      {badge > 0 && (
        <span
          className={`absolute top-0 right-0 min-w-[16px] h-[16px] px-[3px] rounded-full text-[9px] font-bold leading-none flex items-center justify-center text-base-950 ${
            badgeTone === "warn" ? "bg-signal-warn" : "bg-signal-error"
          }`}
        >
          {badge > 9 ? "9+" : badge}
        </span>
      )}

      {/* Etiqueta: absoluta => altura 0 en el flujo => el icono NO se mueve. */}
      <span
        className={`absolute top-full mt-2 whitespace-nowrap text-[10.5px] tracking-wide text-ink-dim opacity-0 -translate-y-[3px] transition-[opacity,transform] duration-200 group-hover:opacity-100 group-hover:translate-y-0 pointer-events-none ${
          labelAlign === "left" ? "left-0" : labelAlign === "right" ? "right-0" : "left-1/2 -translate-x-1/2"
        }`}
      >
        {label}
      </span>
    </button>
  );
}
