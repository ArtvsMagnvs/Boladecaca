// pages/Workspace/layers.ts — LAS CAPAS DE APILADO del Workspace (2026-07-25)
//
// EL BUG QUE CIERRA (reportado por el usuario): al pulsar "Editar" en un
// proyecto, el popup aparecía DETRÁS de la tarjeta y era inalcanzable.
//
// CAUSA REAL: el `Modal` usaba `z-50` fijo, pero las tarjetas-ventana usan un
// z-index CRECIENTE (`useWindowCard` incrementa un contador en cada clic para
// traer al frente, y persiste el valor en localStorage). Tras unos cuantos
// clics, `zIndex` de una tarjeta pasa de 50 y la tarjeta tapa el popup — y las
// de agente peor todavía: llevan +100.000 por diseño. No era un fallo del
// popup: era que nadie había definido en qué RANGO vive cada cosa.
//
// LA REGLA, de una vez y en un solo sitio: quien necesite apilarse en el
// Workspace importa su capa de aquí. Nada de números mágicos repartidos.
//
//   [1 … 99.999]            tarjetas de PROYECTO   (contador de useWindowCard)
//   [100.001 … 199.999]     tarjetas de AGENTE     (+ AGENT_Z_OFFSET)
//   1.000.000               POPUPS / MODALES       ← siempre encima de todo
//
// Además, los modales se pintan con `createPortal` en `document.body`: así son
// inmunes a cualquier `stacking context` intermedio (un `TaskPopup` vive DENTRO
// de la tarjeta que lo abrió, y sin portal quedaría atrapado en su contexto por
// mucho z-index que le pusiéramos).

/** Desplazamiento de las tarjetas de agente: siempre por encima de las de
 *  proyecto. Vive aquí (no en WorkspaceCanvas) para que el techo del rango de
 *  proyectos y este offset se lean juntos y no se solapen nunca. */
export const AGENT_Z_OFFSET = 100_000;

/** Techo del contador de tarjetas. `useWindowCard` lo usa para reciclar en vez
 *  de crecer sin límite: sin esto, una sesión larga podría llegar a la capa de
 *  modales y reproducir el bug por otra vía. */
export const CARD_Z_MAX = 99_999;

/** Capa de popups/modales: por encima de proyectos Y de agentes. */
export const Z_MODAL = 1_000_000;
