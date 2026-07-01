import type { ReactNode } from "react";

interface HubPanelProps {
  title: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
  // FIX V0.3 (Fase 1 Estabilizacion Hub V03): contador discreto junto al
  // titulo, para que el usuario sepa cuantos elementos hay en el panel
  // sin tener que contarlos a ojo.
  count?: number;
}

/** Panel de cristal reutilizable para las zonas del Hub (izquierda/derecha/inferior). */
export function HubPanel({ title, children, className = "", action, count }: HubPanelProps) {
  return (
    <div className={`glass-surface rounded-2xl p-5 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium uppercase tracking-wider text-ink-faint">
          {title}
          {typeof count === "number" && (
            <span className="ml-2 text-[10px] text-ink-faint/70 normal-case tracking-normal">
              ({count})
            </span>
          )}
        </h3>
        {action}
      </div>
      {children}
    </div>
  );
}
