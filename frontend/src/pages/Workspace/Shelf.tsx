// pages/Workspace/Shelf.tsx — la "estanteria" del lienzo espacial (V0.87 W2b)
//
// Lista TODOS los proyectos (no solo los minimizados): un proyecto que ya
// esta fuera (flotando en el lienzo) sigue apareciendo aqui, marcado con un
// punto, para que nunca se "pierda" detras de otras tarjetas — clic siempre
// lo trae al frente. Arrastrar el header de una tarjeta hasta aqui la
// minimiza (logica en ProjectCard via useDragResize.isOverShelf).
import type { Project } from "@/lib/api";
import type { CardLayout } from "./useWindowCard";
import { pct } from "./shared";

interface Props {
  projects: Project[];
  getLayout: (projectId: number) => CardLayout;
  onOpen: (projectId: number) => void;
  onCreate: () => void;
}

export function Shelf({ projects, getLayout, onOpen, onCreate }: Props) {
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
            <button
              key={p.id}
              onClick={() => onOpen(p.id)}
              className={`text-left px-3 py-2 rounded-xl text-sm border transition-all ${
                !layout.shelved
                  ? "bg-accent/12 text-ink border-accent/25"
                  : "text-ink-dim hover:bg-base-700/40 border-transparent"
              }`}
              title={layout.shelved ? "Sacar de la estantería" : "Traer al frente"}
            >
              <div className="flex items-center gap-2">
                {!layout.shelved && <span className="h-1.5 w-1.5 rounded-full bg-accent shrink-0" />}
                <span className="truncate flex-1">{p.name}</span>
                {p.current_version && <span className="text-[10px] text-ink-faint shrink-0">{p.current_version}</span>}
              </div>
              <div className="mt-1.5 h-1 bg-base-700 rounded-full overflow-hidden">
                <div className="h-full bg-accent/50 rounded-full" style={{ width: `${pct(p.progress)}%` }} />
              </div>
            </button>
          );
        })}
        {projects.length === 0 && (
          <p className="text-xs text-ink-faint px-3 py-4">Sin proyectos. Crea uno con +.</p>
        )}
      </div>
    </aside>
  );
}
