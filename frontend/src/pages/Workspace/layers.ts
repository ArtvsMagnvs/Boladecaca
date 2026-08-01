// pages/Workspace/layers.ts — LAS CAPAS DE APILADO del Workspace (2026-07-25)
//
// EL BUG QUE CERRÓ EN SU DÍA (reportado por el usuario): al pulsar "Editar" en
// un proyecto, el popup aparecía DETRÁS de la tarjeta y era inalcanzable.
//
// CAUSA REAL: el `Modal` usaba `z-50` fijo, pero las tarjetas-ventana usan un
// z-index CRECIENTE (`useWindowCard` incrementa un contador en cada clic para
// traer al frente, y persiste el valor en localStorage). Tras unos cuantos
// clics, `zIndex` de una tarjeta pasa de 50 y la tarjeta tapa el popup. No era
// un fallo del popup: era que nadie había definido en qué RANGO vive cada cosa.
//
// LA REGLA, de una vez y en un solo sitio: quien necesite apilarse en el
// Workspace importa su capa de aquí. Nada de números mágicos repartidos.
//
//   [1 … 99.999]     TARJETAS-VENTANA (proyectos Y agentes, mismo rango)
//   1.000.000        POPUPS / MODALES         ← siempre encima de todo
//
// Además, los modales se pintan con `createPortal` en `document.body`: así son
// inmunes a cualquier `stacking context` intermedio (un `TaskPopup` vive DENTRO
// de la tarjeta que lo abrió, y sin portal quedaría atrapado en su contexto por
// mucho z-index que le pusiéramos).
//
// ───────────────────────────────────────────────────────────────────────────
// [hotfix 2026-08-02] APILADO ÚNICO PROYECTOS+AGENTES (petición del usuario:
// "como si tuvieras carpetas de Windows abiertas... hay que poder navegar
// donde quieras sin que una cosa limite a otra").
//
// ANTES: las ventanas de agente llevaban un offset FIJO de +100.000, así que
// vivían permanentemente por encima de cualquier tarjeta de proyecto. Eso hacía
// IMPOSIBLE por construcción la mitad de lo que el usuario pide: clicar el
// proyecto y que el agente pase detrás. Dos contadores independientes (uno por
// instancia de `useWorkspaceLayouts`) nunca pueden ordenarse entre sí.
//
// AHORA: un ÚNICO contador compartido por todas las tarjetas del Workspace, sea
// cual sea su tipo. Clicar CUALQUIER ventana le da el z más alto que existe en
// ese momento, así que siempre sube por encima de todas las demás — exactamente
// como las ventanas de un escritorio. El contador se persiste (sobrevive a
// recargas, igual que las disposiciones) y se COMPACTA globalmente al llegar al
// techo, renumerando todas las tarjetas de todos los stores a la vez y
// conservando su orden relativo.
// ───────────────────────────────────────────────────────────────────────────

/** Techo del contador de tarjetas. Al alcanzarlo se compacta (ver
 *  `allocateZ`) en vez de crecer sin límite: sin esto, una sesión larga podría
 *  llegar a la capa de modales y reproducir el bug original por otra vía. */
export const CARD_Z_MAX = 99_999;

/** Capa de popups/modales: por encima de CUALQUIER tarjeta-ventana. */
export const Z_MODAL = 1_000_000;

const Z_TOP_KEY = "aithera.workspace.zTop";

/** Un almacén de disposiciones que participa en el apilado global. Cada
 *  instancia de `useWorkspaceLayouts` (proyectos, agentes) registra el suyo. */
export interface ZStore {
  /** Pares [id, zIndex] de TODAS las tarjetas que gestiona este almacén. */
  entries: () => Array<[number, number]>;
  /** Aplica nuevos zIndex (solo a los ids que le pertenecen). */
  renumber: (next: Record<number, number>) => void;
}

const stores = new Set<ZStore>();

/** Registra un almacén en el apilado global. Devuelve la función para darlo de
 *  baja (pensada para usarse tal cual como cleanup de un `useEffect`). */
export function registerZStore(store: ZStore): () => void {
  stores.add(store);
  return () => {
    stores.delete(store);
  };
}

function readTop(): number {
  try {
    const raw = Number(localStorage.getItem(Z_TOP_KEY));
    // `Number(null)` es 0 y `Number("abc")` es NaN: ambos caen al 0 de arranque.
    return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0;
  } catch {
    return 0;
  }
}

function writeTop(value: number): void {
  try {
    localStorage.setItem(Z_TOP_KEY, String(value));
  } catch {
    // localStorage lleno/bloqueado: el apilado es preferencia visual, no datos
    // críticos — se degrada en silencio, nunca rompe el Workspace.
  }
}

/** Renumera TODAS las tarjetas de TODOS los almacenes conservando su orden
 *  relativo de apilado. Devuelve el siguiente z libre. */
function compactAll(): number {
  const all: Array<{ store: ZStore; id: number; z: number }> = [];
  stores.forEach((store) => {
    store.entries().forEach(([id, z]) => all.push({ store, id, z }));
  });
  all.sort((a, b) => a.z - b.z);

  const perStore = new Map<ZStore, Record<number, number>>();
  all.forEach((entry, i) => {
    const map = perStore.get(entry.store) ?? {};
    map[entry.id] = i + 1;
    perStore.set(entry.store, map);
  });
  perStore.forEach((map, store) => store.renumber(map));

  return all.length + 1;
}

/** El siguiente z-index "al frente de todo". Lo comparten proyectos y agentes:
 *  ese compartir ES lo que permite intercalarlos como ventanas de escritorio. */
export function allocateZ(): number {
  let next = readTop() + 1;
  if (next >= CARD_Z_MAX) next = compactAll();
  writeTop(next);
  return next;
}
