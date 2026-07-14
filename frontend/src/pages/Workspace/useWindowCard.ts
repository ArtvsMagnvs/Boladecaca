// pages/Workspace/useWindowCard.ts — mecanica del lienzo espacial (V0.87 W2b)
//
// Pointer Events nativos, sin libreria nueva (doc 16 principio 5): el encaje
// con la "estanteria" es logica propia de Aithera que ninguna libreria
// generica de drag/resize conoce. Durante el gesto se muta el DOM directamente
// (via ref, sin pasar por React) para que arrastrar/redimensionar sea fluido a
// 60fps; el estado de React (y localStorage) solo se confirma en pointerup.
//
// Alcance de resize deliberadamente acotado a 3 asas (borde derecho = ancho,
// borde inferior = alto, esquina inferior-derecha = ambos) — borde
// izquierdo/superior exigirian mover x/y A LA VEZ que w/h, acoplando posicion
// y tamano en el mismo gesto (mas superficie de bugs). Si hace falta mas
// adelante, se anade; no es un recorte de producto, es un recorte de riesgo.
import { useCallback, useEffect, useRef, useState } from "react";

export interface CardLayout {
  x: number;
  y: number;
  w: number;
  h: number;
  shelved: boolean; // true = vive en la estanteria, no se renderiza como ventana
  expanded: boolean; // true = ocupa el area del lienzo (doble clic en el header)
  zIndex: number;
}

const STORAGE_KEY = "aithera.workspace.cardLayouts";
export const MIN_CARD_W = 260;
export const MIN_CARD_H = 180;
const DEFAULT_W = 360;
const DEFAULT_H = 280;
const CLICK_THRESHOLD_PX = 4;

function readStore(): Record<number, CardLayout> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeStore(map: Record<number, CardLayout>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // localStorage lleno/bloqueado: la disposicion es preferencia visual, no
    // datos criticos — se pierde en silencio, nunca rompe el Workspace.
  }
}

// Se indexa por project_id (estable), NO por la posicion en el array de
// proyectos: un indice de array puede pasarse distinto (o no pasarse) segun
// desde donde se llame, lo que causaba que dos proyectos abiertos por primera
// vez desde sitios distintos cayeran ambos en (40,40), exactamente superpuestos
// (bug encontrado en verificacion en vivo de W2b). El project_id siempre esta
// disponible en cualquier call site, así que el stagger es correcto sin
// coordinar quien pasa que indice.
function defaultLayout(projectId: number): CardLayout {
  // Un proyecto nuevo nace en la estanteria (metafora: libros que aun no has
  // sacado). x/y/w/h por defecto solo importan si el usuario lo saca sin
  // haberlo movido nunca — stagger para que no nazcan todos superpuestos.
  const stagger = (projectId % 5) * 28;
  return {
    x: 40 + stagger,
    y: 40 + stagger,
    w: DEFAULT_W,
    h: DEFAULT_H,
    shelved: true,
    expanded: false,
    zIndex: 1,
  };
}

/** Disposicion de TODAS las tarjetas — una sola instancia en WorkspaceCanvas. */
export function useWorkspaceLayouts() {
  const [layouts, setLayouts] = useState<Record<number, CardLayout>>(() => readStore());
  const zCounter = useRef(1 + Math.max(0, ...Object.values(readStore()).map((l) => l.zIndex)));

  useEffect(() => {
    writeStore(layouts);
  }, [layouts]);

  const getLayout = useCallback(
    (projectId: number): CardLayout => layouts[projectId] ?? defaultLayout(projectId),
    [layouts],
  );

  const setLayout = useCallback((projectId: number, patch: Partial<CardLayout>) => {
    setLayouts((prev) => {
      const current = prev[projectId] ?? defaultLayout(projectId);
      return { ...prev, [projectId]: { ...current, ...patch } };
    });
  }, []);

  const bringToFront = useCallback(
    (projectId: number) => {
      zCounter.current += 1;
      setLayout(projectId, { zIndex: zCounter.current });
    },
    [setLayout],
  );

  const openFromShelf = useCallback(
    (projectId: number) => {
      setLayout(projectId, { shelved: false });
      bringToFront(projectId);
    },
    [setLayout, bringToFront],
  );

  const sendToShelf = useCallback(
    (projectId: number) => {
      setLayout(projectId, { shelved: true, expanded: false });
    },
    [setLayout],
  );

  const toggleExpanded = useCallback(
    (projectId: number) => {
      const current = layouts[projectId] ?? defaultLayout(projectId);
      setLayout(projectId, { expanded: !current.expanded, shelved: false });
      bringToFront(projectId);
    },
    [layouts, setLayout, bringToFront],
  );

  return { getLayout, setLayout, bringToFront, openFromShelf, sendToShelf, toggleExpanded };
}

type GestureKind = "drag" | "resize-w" | "resize-h" | "resize-wh";
interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DragResizeOptions {
  layout: CardLayout;
  bounds: { width: number; height: number };
  onCommit: (patch: Partial<CardLayout>) => void;
  onInteractStart: () => void;
  /** true si (clientX,clientY) cae dentro de la estanteria — solo se consulta al soltar un arrastre. */
  isOverShelf?: (clientX: number, clientY: number) => boolean;
  onDropOnShelf?: () => void;
}

/** Arrastrar (header) y redimensionar (asas) de UNA tarjeta que NO esta expandida. */
export function useDragResize({
  layout, bounds, onCommit, onInteractStart, isOverShelf, onDropOnShelf,
}: DragResizeOptions) {
  const nodeRef = useRef<HTMLDivElement>(null);
  const gesture = useRef<{
    kind: GestureKind;
    startX: number;
    startY: number;
    startRect: Rect;
    lastRect: Rect;
    moved: boolean;
  } | null>(null);

  const clamp = useCallback(
    (r: Rect): Rect => {
      const w = Math.min(Math.max(r.w, MIN_CARD_W), Math.max(MIN_CARD_W, bounds.width));
      const h = Math.min(Math.max(r.h, MIN_CARD_H), Math.max(MIN_CARD_H, bounds.height));
      // Deja siempre al menos 60px del header visible dentro del lienzo, para
      // que una tarjeta nunca se pueda "perder" fuera de alcance del raton.
      const x = Math.min(Math.max(r.x, -w + 60), Math.max(0, bounds.width - 60));
      const y = Math.min(Math.max(r.y, 0), Math.max(0, bounds.height - 32));
      return { x, y, w, h };
    },
    [bounds.width, bounds.height],
  );

  const applyRect = (r: Rect) => {
    const el = nodeRef.current;
    if (!el) return;
    el.style.transform = `translate(${r.x}px, ${r.y}px)`;
    el.style.width = `${r.w}px`;
    el.style.height = `${r.h}px`;
  };

  const onPointerMove = useCallback(
    (e: PointerEvent) => {
      const g = gesture.current;
      if (!g) return;
      const dx = e.clientX - g.startX;
      const dy = e.clientY - g.startY;
      if (!g.moved && Math.hypot(dx, dy) > CLICK_THRESHOLD_PX) g.moved = true;
      if (!g.moved) return;

      const next: Rect = { ...g.startRect };
      if (g.kind === "drag") {
        next.x = g.startRect.x + dx;
        next.y = g.startRect.y + dy;
      }
      if (g.kind === "resize-w" || g.kind === "resize-wh") next.w = g.startRect.w + dx;
      if (g.kind === "resize-h" || g.kind === "resize-wh") next.h = g.startRect.h + dy;

      const clamped = clamp(next);
      applyRect(clamped);
      g.lastRect = clamped;
    },
    [clamp],
  );

  const endGesture = useCallback(
    (e: PointerEvent) => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", endGesture);
      const g = gesture.current;
      gesture.current = null;
      if (!g || !g.moved) return;

      if (g.kind === "drag" && isOverShelf?.(e.clientX, e.clientY)) {
        onDropOnShelf?.();
        return;
      }
      onCommit(g.lastRect);
    },
    [onPointerMove, isOverShelf, onDropOnShelf, onCommit],
  );

  const startGesture = useCallback(
    (kind: GestureKind) => (e: React.PointerEvent) => {
      if (e.button !== 0) return; // solo boton izquierdo
      e.stopPropagation();
      onInteractStart();
      gesture.current = {
        kind,
        startX: e.clientX,
        startY: e.clientY,
        startRect: { x: layout.x, y: layout.y, w: layout.w, h: layout.h },
        lastRect: { x: layout.x, y: layout.y, w: layout.w, h: layout.h },
        moved: false,
      };
      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", endGesture);
    },
    [layout.x, layout.y, layout.w, layout.h, onInteractStart, onPointerMove, endGesture],
  );

  return {
    nodeRef,
    headerHandlers: { onPointerDown: startGesture("drag") },
    resizeHandlers: {
      right: { onPointerDown: startGesture("resize-w") },
      bottom: { onPointerDown: startGesture("resize-h") },
      corner: { onPointerDown: startGesture("resize-wh") },
    },
  };
}
