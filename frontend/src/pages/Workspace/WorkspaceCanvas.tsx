// pages/Workspace/WorkspaceCanvas.tsx — el lienzo espacial (V0.87 W2b)
//
// Fondo ambiental: reusa AICore.tsx TAL CUAL (regla ya vigente en Hub.tsx: "no
// se modifica"), atenuado y sin interaccion. NO es el AVCS completo de doc 13
// (ParticleEngine full-bleed, V0.82/V0.83, sin construir todavia) — es el
// mismo lenguaje visual del Hub reusando el componente que ya existe.
import { useEffect, useRef, useState } from "react";
import type { Project } from "@/lib/api";
import { AICore } from "@/components/hub/AICore";
import { Shelf } from "./Shelf";
import { ProjectCard } from "./ProjectCard";
import { AgentWindowCard } from "./AgentWindowCard";
import { useWorkspaceLayouts } from "./useWindowCard";

const AGENT_LAYOUTS_KEY = "aithera.workspace.agentCardLayouts";
// V0.87 (W4): las ventanas de agente flotan SIEMPRE por encima de las
// tarjetas de proyecto (offset plano de z-index) — son dos instancias
// independientes de useWorkspaceLayouts (contadores de zIndex separados, ver
// useWindowCard.ts), así que sus valores numéricos podrían solaparse; este
// offset evita que una tarjeta de proyecto "tape" una ventana de agente
// mientras cada tipo sigue respetando su propio orden de traer-al-frente.
const AGENT_Z_OFFSET = 100000;

interface Props {
  projects: Project[];
  onCreateProject: () => void;
  onEditProject: (p: Project) => void;
  onProjectsRefresh: () => void;
}

export function WorkspaceCanvas({ projects, onCreateProject, onEditProject, onProjectsRefresh }: Props) {
  const { getLayout, setLayout, bringToFront, openFromShelf, sendToShelf, toggleExpanded } = useWorkspaceLayouts();
  // V0.87 (W4): las tarjetas de agente reusan EXACTAMENTE la misma mecanica
  // (arrastre/resize/expandir/"estanteria") sobre su PROPIA instancia del
  // hook — pedido explicito del usuario. "shelved" para un agente = su
  // ventana esta cerrada; el chip en AgentsSection sigue siendo como se
  // vuelve a abrir (equivalente a sacar un proyecto de la estanteria).
  const {
    getLayout: getAgentLayout, setLayout: setAgentLayout, bringToFront: bringAgentToFront,
    openFromShelf: openAgentWindow, sendToShelf: closeAgentWindow, toggleExpanded: toggleAgentExpanded,
    openIds: openAgentIds,
  } = useWorkspaceLayouts(AGENT_LAYOUTS_KEY);
  // El chip pequeño en AgentsSection es OTRA instancia con sus propios datos
  // ya cargados — no se entera sola de que is_active/icon/edicion cambiaron
  // en la ventana. Subir este contador fuerza a TODAS las AgentsSection a
  // refetch (barato: pocos agentes por proyecto) sin necesitar un bus de
  // eventos para un caso tan puntual.
  const [agentsRefreshTick, setAgentsRefreshTick] = useState(0);
  const bumpAgentsRefresh = () => setAgentsRefreshTick((t) => t + 1);
  const closeAgent = (agentId: number) => {
    closeAgentWindow(agentId);
    bumpAgentsRefresh();
  };

  const canvasRef = useRef<HTMLDivElement>(null);
  const shelfWrapRef = useRef<HTMLDivElement>(null);
  const [bounds, setBounds] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const measure = () => setBounds({ width: el.clientWidth, height: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const isOverShelf = (clientX: number, clientY: number) => {
    const el = shelfWrapRef.current;
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom;
  };

  // Simetrico a isOverShelf: al soltar un arrastre iniciado EN la estanteria,
  // si cae dentro de la propia estanteria no hace nada (sigue guardado); si
  // cae fuera, se saca y se posiciona centrada bajo el cursor.
  const handleDragOut = (projectId: number, clientX: number, clientY: number) => {
    if (isOverShelf(clientX, clientY)) return;
    const canvasRect = canvasRef.current?.getBoundingClientRect();
    const x = canvasRect ? clientX - canvasRect.left - 180 : 40;
    const y = canvasRect ? clientY - canvasRect.top - 20 : 40;
    setLayout(projectId, { x: Math.max(0, x), y: Math.max(0, y), shelved: false });
    bringToFront(projectId);
  };

  const openCards = projects.filter((p) => !getLayout(p.id).shelved);

  return (
    <div className="h-full flex gap-4">
      <div ref={shelfWrapRef}>
        <Shelf projects={projects} getLayout={getLayout} onOpen={openFromShelf} onDragOut={handleDragOut} onCreate={onCreateProject} />
      </div>

      <div ref={canvasRef} className="flex-1 min-w-0 relative rounded-2xl overflow-hidden bg-base-900/30 border border-base-700/40">
        {/* Fondo ambiental — no interactivo, siempre detrás de las tarjetas */}
        <div className="absolute inset-0 flex items-center justify-center opacity-[0.12] pointer-events-none select-none">
          <AICore size={520} />
        </div>

        {projects.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-ink-faint">
            Sin proyectos. Crea uno desde la estantería.
          </div>
        )}

        {openCards.length === 0 && projects.length > 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-ink-faint pointer-events-none">
            Todos los proyectos están en la estantería. Haz clic en uno para sacarlo.
          </div>
        )}

        {projects.map((p) => {
          const layout = getLayout(p.id);
          if (layout.shelved) return null;
          return (
            <ProjectCard
              key={p.id}
              project={p}
              allProjects={projects}
              layout={layout}
              bounds={bounds}
              onInteractStart={() => bringToFront(p.id)}
              onCommit={(patch) => setLayout(p.id, patch)}
              onMinimize={() => sendToShelf(p.id)}
              onToggleExpanded={() => toggleExpanded(p.id)}
              isOverShelf={isOverShelf}
              onEditProject={() => onEditProject(p)}
              onProjectsRefresh={onProjectsRefresh}
              onOpenAgentWindow={openAgentWindow}
              agentsRefreshTick={agentsRefreshTick}
            />
          );
        })}

        {/* V0.87 (W4): ventanas de agente — mismo mecanismo que las tarjetas
            de proyecto, en su propia instancia de useWorkspaceLayouts (ver
            arriba). Flotan por encima de las tarjetas de proyecto a
            proposito (AGENT_Z_OFFSET): se abren para trabajar con ellas. */}
        {openAgentIds.map((agentId) => {
          const layout = getAgentLayout(agentId);
          return (
            <AgentWindowCard
              key={agentId}
              agentId={agentId}
              layout={{ ...layout, zIndex: layout.zIndex + AGENT_Z_OFFSET }}
              bounds={bounds}
              onInteractStart={() => bringAgentToFront(agentId)}
              onCommit={(patch) => setAgentLayout(agentId, patch)}
              onMinimize={() => closeAgent(agentId)}
              onToggleExpanded={() => toggleAgentExpanded(agentId)}
              onAgentChanged={bumpAgentsRefresh}
            />
          );
        })}
      </div>
    </div>
  );
}
