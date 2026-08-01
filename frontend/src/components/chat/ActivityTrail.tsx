// components/chat/ActivityTrail.tsx — el rastro de lo que Aithera va haciendo
//
// [2026-08-02, petición del usuario] Antes, una misión decía "Entendido, me
// pongo con ello" y el chat se quedaba mudo hasta la respuesta final. El
// detalle solo existía en Mission Control: otra pantalla, y después. Esto trae
// al chat lo mismo que el usuario ve trabajando en Claude — una línea corta por
// cada cosa que se está haciendo, según pasa.
//
// DOS ESTADOS, decididos con el usuario:
//   · EN VIVO (`live`): abierto, con la última línea destacada y un punto que
//     late. Se ve lo que está pasando AHORA.
//   · TERMINADO: se pliega a un resumen de una línea ("7 pasos · 4 herramientas")
//     que se puede desplegar. El chat no crece, pero nada se pierde.
//
// NO duplica Mission Control: aquí van frases cortas ("Leyendo GDD.docx"), allí
// el grafo entero con estados, duraciones, errores y salidas.
import { useEffect, useMemo, useRef, useState } from "react";
import { useT } from "@/store/useI18n";

interface Props {
  lines: string[];
  /** true mientras el turno sigue en marcha (rastro abierto y con latido). */
  live?: boolean;
}

export default function ActivityTrail({ lines, live = false }: Props) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // En vivo el rastro se sigue solo: la línea nueva siempre a la vista.
  useEffect(() => {
    if (live) endRef.current?.scrollIntoView({ block: "nearest" });
  }, [lines.length, live]);

  // Cuántas herramientas DISTINTAS se han usado: el resumen plegado dice
  // "7 pasos · 4 herramientas", y para eso hace falta contar líneas únicas, no
  // repeticiones (leer 3 archivos son 3 pasos pero una sola herramienta).
  const tools = useMemo(() => new Set(lines.map((l) => l.split(/[:·]/)[0].trim())).size, [lines]);

  if (!lines.length) return null;

  const expanded = live || open;

  return (
    <div className="mt-1.5 text-[11px]">
      {!live && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1.5 text-ink-faint hover:text-ink-dim transition-colors"
          aria-expanded={open}
        >
          <svg
            viewBox="0 0 12 12"
            className={`w-2.5 h-2.5 transition-transform ${open ? "rotate-90" : ""}`}
            aria-hidden
          >
            <path d="M4 2 L8 6 L4 10" fill="none" stroke="currentColor" strokeWidth="1.4"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>{t("chat.activity.summary", { steps: lines.length, tools })}</span>
        </button>
      )}

      {expanded && (
        <ul
          className={`flex flex-col gap-0.5 ${
            live ? "" : "mt-1.5 pl-1 border-l border-base-700"
          } ${live ? "max-h-40 overflow-y-auto pr-1" : ""}`}
        >
          {lines.map((l, i) => {
            const last = live && i === lines.length - 1;
            return (
              <li
                key={`${i}-${l}`}
                className={`flex items-start gap-1.5 ${
                  last ? "text-ink-dim" : "text-ink-faint"
                }`}
              >
                <span
                  className={`mt-[5px] h-1 w-1 rounded-full shrink-0 ${
                    last ? "bg-accent animate-pulse" : "bg-ink-faint/50"
                  }`}
                  aria-hidden
                />
                <span className="break-words">{l}</span>
              </li>
            );
          })}
          <div ref={endRef} />
        </ul>
      )}
    </div>
  );
}
