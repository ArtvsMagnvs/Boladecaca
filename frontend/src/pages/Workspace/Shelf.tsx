// pages/Workspace/Shelf.tsx — la "estanteria" del lienzo espacial (V0.87 W2b)
//
// Lista TODOS los proyectos (no solo los minimizados): un proyecto que ya
// esta fuera (flotando en el lienzo) sigue apareciendo aqui, marcado con un
// punto, para que nunca se "pierda" detras de otras tarjetas — clic siempre
// lo trae al frente. Arrastrar el header de una tarjeta hasta aqui la
// minimiza (logica en ProjectCard via useDragResize.isOverShelf); arrastrar
// una fila de aqui HACIA FUERA la saca (simetria pedida: "guardar" y "sacar"
// son el mismo gesto en direcciones opuestas).
//
// La tarjeta real (ProjectCard) todavia no existe mientras el proyecto sigue
// en la estanteria, asi que no hay a que "engancharle" un arrastre en vivo.
// En su lugar, este gesto usa un FANTASMA ligero (una etiqueta que sigue al
// cursor) durante el arrastre; la tarjeta real se crea y se posiciona UNA
// vez, al soltar — patron estandar de drag-and-drop cuando el objetivo del
// arrastre no esta montado todavia.
import { useRef, useState } from "react";
import type { Project } from "@/lib/api";
import type { CardLayout } from "./useWindowCard";
import { pct } from "./shared";

const CLICK_THRESHOLD_PX = 4;

interface Props {
  projects: Project[];
  getLayout: (projectId: number) => CardLayout;
  onOpen: (projectId: number) => void;
  onDragOut: (projectId: number, clientX: number, clientY: number) => void;
  onCreate: () => void;
}

export function Shelf({ projects, getLayout, onOpen, onDragOut, onCreate }: Props) {
  const [ghost, setGhost] = useState<{ name: string; x: number; y: number } | null>(null);
  const gesture = useRef<{ id: number; name: string; startX: number; startY: number; moved: boolean } | null>(null);

  const onPointerMove = (e: PointerEvent) => {
    const g = gesture.current;
    if (!g) return;
    const dx = e.clientX - g.startX;
    const dy = e.clientY - g.startY;
    if (!g.moved && Math.hypot(dx, dy) > CLICK_THRESHOLD_PX) g.moved = true;
    if (g.moved) setGhost({ name: g.name, x: e.clientX, y: e.clientY });
  };

  const endGesture = (e: PointerEvent) => {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", endGesture);
    const g = gesture.current;
    gesture.current = null;
    setGhost(null);
    if (!g) return;
    if (g.moved) onDragOut(g.id, e.clientX, e.clientY);
    else onOpen(g.id); // sin movimiento real = clic normal (abre/trae al frente)
  };

  const onRowPointerDown = (p: Project) => (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    gesture.current = { id: p.id, name: p.name, startX: e.clientX, startY: e.clientY, moved: false };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endGesture);
  };

  return (
    <aside className="w-56 shrink-0 flex flex-col gap-2 relative z-10">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-xs uppercase tracking-wide text-ink-faint">Proyectos</h2>
        <button onClick={onCreate} className="text-accent hover:text-accent-soft text-lg leading-none px-1" title="Nuevo proyecto">+</button>
      </div>
      <div className="flex-1 overflow-y-auto flex flex-col gap-1">
        {projects.map((p) => {
          const layout = getLayout(p.id);
          return (
            <div
              key={p.id}
              onPointerDown={onRowPointerDown(p)}
              className={`text-left px-3 py-2 rounded-xl text-sm border transition-all cursor-grab active:cursor-grabbing select-none ${
                !layout.shelved
                  ? "bg-accent/12 text-ink border-accent/25"
                  : "text-ink-dim hover:bg-base-700/40 border-transparent"
              }`}
              title={layout.shelved ? "Arrastra para sacar, clic para abrir" : "Traer al frente"}
            >
              <div className="flex items-center gap-2">
                {!layout.shelved && <span className="h-1.5 w-1.5 rounded-full bg-accent shrink-0" />}
                <span className="truncate flex-1">{p.name}</span>
                {p.archived_at && (
                  <span className="text-[9px] px-1 py-0.5 rounded bg-base-700/60 text-ink-faint shrink-0" title="Archivado">Archivado</span>
                )}
                {p.current_version && <span className="text-[10px] text-ink-faint shrink-0">{p.current_version}</span>}
              </div>
              <div className="mt-1.5 h-1 bg-base-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent/50 rounded-full" style={{ width: `${pct(p.progress)}%` }} />
              </div>
            </div>
          );
        })}
        {projects.length === 0 && (
          <p className="text-xs text-ink-faint px-3 py-4">Sin proyectos. Crea uno con +.</p>
        )}
      </div>

      {ghost && (
        <div
          className="fixed pointer-events-none z-50 px-3 py-2 rounded-xl bg-accent/20 border border-accent/40 text-xs text-ink backdrop-blur-sm shadow-glass"
          style={{ left: ghost.x + 14, top: ghost.y + 14 }}
        >
          {ghost.name}
        </div>
      )}
    </aside>
  );
}
