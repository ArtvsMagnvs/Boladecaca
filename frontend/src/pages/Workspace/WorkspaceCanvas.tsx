// pages/Workspace/WorkspaceCanvas.tsx — el lienzo espacial (V0.87 W2b)
//
// [PU6b-vent t4] El fondo ambiental (AICore, el "orbe azul" heredado del Hub
// viejo) se ELIMINÓ a petición del usuario: desde que el AVCS real es el
// fondo permanente de la app (PU6b-vent t2), aquí se veían DOS núcleos
// superpuestos — el de verdad detrás y este viejo atenuado delante. Queda el
// marco del lienzo con su leve tinte (eso se pidió conservar) y el AVCS real
// visible a través.
import { useEffect, useRef, useState } from "react";
import type { Project } from "@/lib/api";
import { Shelf } from "./Shelf";
import { ProjectCard } from "./ProjectCard";
import { AgentWindowCard } from "./AgentWindowCard";
import { useWorkspaceLayouts } from "./useWindowCard";
import { useT } from "@/store/useI18n";

const AGENT_LAYOUTS_KEY = "aithera.workspace.agentCardLayouts";
// [hotfix 2026-08-02] APILADO ÚNICO. Antes, las ventanas de agente llevaban un
// offset fijo de z-index (+100.000) que las ponía SIEMPRE por encima de las
// tarjetas de proyecto. Eso tapaba un problema (dos contadores de zIndex
// independientes, uno por instancia de useWorkspaceLayouts, no son comparables
// entre sí) a costa de hacer imposible lo que el usuario pide: que al clicar la
// tarjeta del proyecto el agente pase DETRÁS, como ventanas de escritorio.
// Ahora ambas instancias comparten un único contador global (`layers.allocateZ`),
// así que el z-index ya se puede comparar directamente y no hace falta offset.

interface Props {
  projects: Project[];
  onCreateProject: () => void;
  onEditProject: (p: Project) => void;
  onProjectsRefresh: () => void;
}

export function WorkspaceCanvas({ projects, onCreateProject, onEditProject, onProjectsRefresh }: Props) {
  const t = useT();
  const { getLayout, setLayout, bringToFront, openFromShelf, sendToShelf, toggleExpanded } = useWorkspaceLayouts();
  // V0.87 (W4): las tarjetas de agente reusan EXACTAMENTE la misma mecanica
  // (arrastre/resize/expandir/"estanteria") sobre su PROPIA instancia del
  // hook — pedido explicito del usuario. "shelved" para un agente = su
  // ventana esta cerrada; el chip en AgentsSection sigue siendo como se
  // vuelve a abrir (equivalente a sacar un proyecto de la estanteria).
  const {
    getLayout: getAgentLayout, setLayout: setAgentLayout, bringToFront: bringAgentToFront,
    openFromShelf: openAgentWindow, sendToShelf: closeAgentWindow, toggleExpanded: toggleAgentExpanded,
    openIds: openAgentIds, forget: forgetAgentLayout,
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
  // [2026-07-25] Cuál está al frente (mayor zIndex entre las abiertas): se usa
  // solo para pintar el borde de foco, no altera el apilado.
  // [hotfix 2026-08-02] Ahora el foco se calcula contra TODAS las ventanas
  // (proyectos Y agentes), que ya comparten escala de z-index: si la ventana al
  // frente es la de un agente, ningún proyecto lleva el borde de acento —
  // marcar uno sería mentir sobre quién tiene el foco.
  const topZ = Math.max(
    0,
    ...openCards.map((p) => getLayout(p.id).zIndex),
    ...openAgentIds.map((id) => getAgentLayout(id).zIndex),
  );
  const frontProjectId = openCards.find((p) => getLayout(p.id).zIndex === topZ)?.id ?? null;

  return (
    <div className="h-full flex gap-4">
      <div ref={shelfWrapRef}>
        <Shelf projects={projects} getLayout={getLayout} onOpen={openFromShelf} onDragOut={handleDragOut} onCreate={onCreateProject} />
      </div>

      {/* [PU7, 2026-08-02] `holo-frame-canvas` — marca este lienzo como el
          ÚNICO que conserva el cometa DORADO en tema claro (petición
          explícita del usuario tras ver el dorado fundirse en las tarjetas
          blancas: el resto de `.holo-frame` — ProjectCard/AgentWindowCard/
          Shelf/Modal/UserQuestionCard — pasa a violeta en claro; ver
          styles/index.css). */}
      <div ref={canvasRef} className="flex-1 min-w-0 relative rounded-2xl overflow-hidden holo-frame holo-frame-canvas bg-base-900/20 border border-base-700/30">
        {/* [PU6b-vent t4] Los textos centrados ("no hay proyectos" / "todo en
            la estantería") se retiraron junto con el orbe — el usuario pidió
            ver SOLO el AVCS real a través del marco. La estantería con su "+"
            ya explica qué hacer cuando el lienzo está vacío. */}
        {projects.map((p) => {
          const layout = getLayout(p.id);
          if (layout.shelved) return null;
          return (
            <ProjectCard
              key={p.id}
              project={p}
              allProjects={projects}
              layout={layout}
              // [2026-07-25] Foco visible: la tarjeta al frente se marca con el
              // borde de acento. Clicar una tarjeta de detrás YA la traía al
              // frente (`onPointerDownCapture`, fase de captura, que ningún
              // `stopPropagation` de los hijos puede bloquear), pero sin señal
              // visual el usuario no podía saber que había pasado.
              isFront={p.id === frontProjectId}
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
            arriba). [hotfix 2026-08-02] Comparten el contador de z-index con
            las tarjetas de proyecto, así que se intercalan por orden de uso
            como las ventanas de un escritorio: la última que tocas, delante. */}
        {openAgentIds.map((agentId) => {
          const layout = getAgentLayout(agentId);
          return (
            <AgentWindowCard
              key={agentId}
              agentId={agentId}
              layout={layout}
              bounds={bounds}
              onInteractStart={() => bringAgentToFront(agentId)}
              onCommit={(patch) => setAgentLayout(agentId, patch)}
              onMinimize={() => closeAgent(agentId)}
              onToggleExpanded={() => toggleAgentExpanded(agentId)}
              onAgentChanged={bumpAgentsRefresh}
              onGone={() => { forgetAgentLayout(agentId); bumpAgentsRefresh(); }}
            />
          );
        })}
      </div>
    </div>
  );
}
