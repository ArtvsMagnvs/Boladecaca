// pages/Workspace/HelpPanel.tsx — botón "(?)" de atajos/gestos, compartido
// entre ProjectCard y AgentWindowCard (V0.87 W4, pedido explicito del
// usuario: "el (?) no lo veo en ninguna parte, añadelo en el header de cada
// tarjeta de proyecto/agente"). Antes vivía escondido dentro del Kanban
// (solo visible con la tarjeta expandida) — ahora es SIEMPRE visible en la
// cabecera de cualquier tarjeta-ventana, controlado por el padre (mismo
// estado que la tecla "?" del board, para que ambos abran/cierren lo mismo).
import type { ReactNode } from "react";

export type ShortcutEntry = [string, string];

// Gestos de la mecánica de ventana (useWindowCard.ts) — comunes a
// ProjectCard y AgentWindowCard, que comparten exactamente la misma
// mecánica de arrastre/resize/expandir.
export function windowShortcuts(expanded: boolean): ShortcutEntry[] {
  if (expanded) {
    return [["Doble clic en la cabecera", "Restaurar tamaño"]];
  }
  return [
    ["Arrastrar la cabecera", "Mover la tarjeta"],
    ["Doble clic en la cabecera", "Expandir a pantalla completa"],
    ["Arrastrar bordes/esquinas", "Redimensionar"],
  ];
}

interface Props {
  open: boolean;
  onToggle: () => void;
  extra?: ShortcutEntry[];
  align?: "left" | "right";
  title?: ReactNode;
}

export function HelpButton({ open, onToggle, extra = [], align = "right", title = "Atajos y gestos" }: Props) {
  return (
    <div className="relative shrink-0">
      <button
        onClick={onToggle}
        className="h-5 w-5 rounded-full border border-signal-warn/60 bg-signal-warn/15 text-signal-warn text-[11px] font-bold flex items-center justify-center hover:bg-signal-warn/25 hover:border-signal-warn transition-colors"
        title="Atajos de teclado y gestos"
        aria-label="Ayuda: atajos y gestos"
      >
        ?
      </button>
      {open && (
        <div className={`absolute top-7 ${align === "right" ? "right-0" : "left-0"} z-30 glass-surface rounded-xl border border-base-700 p-3 w-64 shadow-glass`}>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint mb-2">{title}</p>
          <div className="flex flex-col gap-1.5">
            {extra.map(([key, desc]) => (
              <div key={key} className="flex items-start gap-2 text-[11px]">
                <span className="shrink-0 px-1.5 py-0.5 rounded bg-base-700/60 text-ink-dim font-mono">{key}</span>
                <span className="text-ink-faint">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
