// pages/Workspace/AgentsSection.tsx — sección "Agentes" del cuerpo de la
// tarjeta de proyecto (V0.87 W2c). Fetch de los agentes del proyecto,
// reorden 1D por arrastre (persistido en localStorage — preferencia visual,
// nunca SQL/mem_project), y wiring de los popups crear/detalle.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Agent, type AgentExecution } from "@/lib/api";
import { AgentChip, type ChipSize } from "./AgentChip";
import { AgentCreatePopup } from "./AgentCreatePopup";
import { AgentDetailPopup } from "./AgentDetailPopup";

const CLICK_THRESHOLD_PX = 5;

function orderKey(projectId: number) {
  return `aithera.workspace.agentOrder.${projectId}`;
}
function loadOrder(projectId: number): number[] {
  try {
    const raw = localStorage.getItem(orderKey(projectId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
function saveOrder(projectId: number, order: number[]) {
  try {
    localStorage.setItem(orderKey(projectId), JSON.stringify(order));
  } catch {
    /* preferencia visual, no critico si no se guarda */
  }
}

interface Props {
  projectId: number;
  size: ChipSize; // calculado por ProjectCard segun el alto/ancho disponible
  // W2d abrira aqui la pantalla completa del agente; hasta entonces el doble
  // clic degrada con gracia al mismo popup de detalle que el clic simple
  // (ver onDoubleClickAgent mas abajo) — no hace falta que ProjectCard sepa
  // nada de esto todavia.
  onOpenFullscreen?: (agentId: number) => void;
}

export function AgentsSection({ projectId, size, onOpenFullscreen }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [order, setOrder] = useState<number[]>(() => loadOrder(projectId));
  const [execByAgent, setExecByAgent] = useState<Record<number, AgentExecution[]>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [detailAgent, setDetailAgent] = useState<Agent | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const orderRef = useRef<number[]>([]);
  const dragState = useRef<{ id: number; startX: number; startY: number; moved: boolean } | null>(null);

  const load = useCallback(async () => {
    const list = await api.getAgents(projectId);
    setAgents(list);
    // Ejecuciones recientes: de los inactivos (para el marco gris/rojo) y de
    // todos si hay sitio para el contador de tareas ("full").
    const need = size === "full" ? list : list.filter((a) => !a.is_active);
    const pairs = await Promise.all(
      need.map(async (a) => [a.id, await api.getAgentExecutions(a.id, 20).catch(() => [])] as const),
    );
    setExecByAgent(Object.fromEntries(pairs));
  }, [projectId, size]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const ordered = useMemo(() => {
    const byId = new Map(agents.map((a) => [a.id, a]));
    const known = order.filter((id) => byId.has(id)).map((id) => byId.get(id)!);
    const rest = agents.filter((a) => !order.includes(a.id));
    return [...known, ...rest];
  }, [agents, order]);

  useEffect(() => {
    orderRef.current = ordered.map((a) => a.id);
  }, [ordered]);

  // --- reorden 1D por arrastre: busca el chip mas cercano al puntero (por
  // distancia al centro) — funciona igual en fila (iconos) que en columna
  // (compact/full), sin duplicar logica por layout. Se muta un ref durante
  // el gesto (nunca lee estado de React directamente, evita closures
  // obsoletas) y solo se confirma en localStorage al soltar. ---
  const onPointerMove = useCallback((e: PointerEvent) => {
    const d = dragState.current;
    if (!d || !containerRef.current) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.moved && Math.hypot(dx, dy) > CLICK_THRESHOLD_PX) {
      d.moved = true;
      setDragId(d.id);
    }
    if (!d.moved) return;

    const chips = [...containerRef.current.querySelectorAll<HTMLElement>("[data-agent-id]")];
    let closestId: number | null = null;
    let closestDist = Infinity;
    for (const el of chips) {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
      if (dist < closestDist) {
        closestDist = dist;
        closestId = Number(el.dataset.agentId);
      }
    }
    if (closestId != null && closestId !== d.id) {
      const cur = [...orderRef.current];
      const from = cur.indexOf(d.id);
      const to = cur.indexOf(closestId);
      if (from !== -1 && to !== -1 && from !== to) {
        cur.splice(from, 1);
        cur.splice(to, 0, d.id);
        orderRef.current = cur;
        setOrder(cur);
      }
    }
  }, []);

  const endDrag = useCallback(
    (_e: PointerEvent) => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", endDrag);
      const d = dragState.current;
      dragState.current = null;
      setDragId(null);
      if (d?.moved) saveOrder(projectId, orderRef.current);
    },
    [onPointerMove, projectId],
  );

  const startDrag = (agentId: number) => (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    dragState.current = { id: agentId, startX: e.clientX, startY: e.clientY, moved: false };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endDrag);
  };

  const lastFailed = (agentId: number) => {
    const execs = execByAgent[agentId];
    return !!execs && execs.length > 0 && execs[0].status === "failed";
  };

  const wrapClass = size === "icon" ? "flex flex-wrap gap-2" : "flex flex-col gap-1.5";

  return (
    <section>
      <div className="flex items-center justify-between mb-1.5">
        <h3 className="text-xs font-medium text-ink-dim">Agentes</h3>
        <button onClick={() => setCreateOpen(true)} className="text-[11px] text-accent hover:text-accent-soft">+ Agente</button>
      </div>

      {ordered.length === 0 ? (
        <p className="text-[11px] text-ink-faint px-1">Sin agentes. Añade uno con "+ Agente".</p>
      ) : (
        <div ref={containerRef} className={wrapClass}>
          {ordered.map((a) => (
            <div key={a.id} data-agent-id={a.id} onPointerDown={startDrag(a.id)}>
              <AgentChip
                agent={a}
                size={size}
                lastExecutionFailed={lastFailed(a.id)}
                executions={execByAgent[a.id] ?? []}
                isDragging={dragId === a.id}
                onOpen={() => setDetailAgent(a)}
                onOpenFullscreen={() => (onOpenFullscreen ? onOpenFullscreen(a.id) : setDetailAgent(a))}
              />
            </div>
          ))}
        </div>
      )}

      {createOpen && (
        <AgentCreatePopup
          projectId={projectId}
          onSave={async (data) => {
            await api.createAgent(data);
            setCreateOpen(false);
            await load();
          }}
          onClose={() => setCreateOpen(false)}
        />
      )}

      {detailAgent && (
        <AgentDetailPopup
          agent={detailAgent}
          executions={execByAgent[detailAgent.id] ?? []}
          onClose={() => setDetailAgent(null)}
        />
      )}
    </section>
  );
}
