// DockIcons.tsx — Iconografía del sistema (PU6a-bis v2, doc 35 §PU6).
//
// FIELES a la lámina de referencia del usuario ("ICONOGRAFÍA DEL SISTEMA"):
// línea fina geométrica, composiciones orbitales, NODOS como puntos llenos
// (algunos con halo), en oro cálido. Asignación pedida, literal:
//   · "Inicio"    → Inicio (réplica tal cual: la semilla)
//   · "Proyectos" → Espacio de trabajo
//   · "Agentes"   → Mission Control
//   · "Calendario"→ Calendario (tal cual)
//   · "Email"     → Correo
//   · "Configuración" → Ajustes
//   · "Conexión"  → Modo Presencia
//
// Todos comparten viewBox 24×24 y stroke="currentColor": el COLOR lo pone el
// botón (oro `signal-warn`, más brillante al hover). Los puntos llenos usan
// fill sin stroke para conservar la finura de la lámina.
import type { ReactNode } from "react";

const S = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.05,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" {...S} aria-hidden="true">
      {children}
    </svg>
  );
}

/** Nodo lleno (los puntos de los vértices de la lámina). */
function Dot({ cx, cy, r = 1.1 }: { cx: number; cy: number; r?: number }) {
  return <circle cx={cx} cy={cy} r={r} fill="currentColor" stroke="none" />;
}

/** Nodo con HALO (punto lleno + anillo fino alrededor — muy de la lámina). */
function Node({ cx, cy, r = 1.05, halo = 2 }: { cx: number; cy: number; r?: number; halo?: number }) {
  return (
    <>
      <circle cx={cx} cy={cy} r={halo} strokeWidth={0.8} />
      <circle cx={cx} cy={cy} r={r} fill="currentColor" stroke="none" />
    </>
  );
}

/** INICIO — la semilla de Aithera, réplica del icono "Inicio" de la lámina:
 *  lágrima ojival con contorno interior, almendra central, núcleo con punto,
 *  y la aguja del eje asomando por la punta superior. */
export function IconHome() {
  return (
    <Svg>
      {/* eje: aguja arriba + cola abajo */}
      <path d="M12 0.9v2.1M12 21.2v1.9" strokeWidth={0.85} />
      {/* contorno exterior (lágrima: fina arriba, panza abajo del centro) */}
      <path d="M12 2.4c3.3 3.1 5.1 6.3 5.1 9.6 0 4.1-2 7.4-5.1 9.9-3.1-2.5-5.1-5.8-5.1-9.9 0-3.3 1.8-6.5 5.1-9.6Z" />
      {/* contorno interior */}
      <path d="M12 4.3c2.5 2.6 3.75 5.2 3.75 7.75 0 3.2-1.5 5.9-3.75 7.9-2.25-2-3.75-4.7-3.75-7.9 0-2.55 1.25-5.15 3.75-7.75Z" strokeWidth={0.9} />
      {/* almendra (vesica) alrededor del núcleo */}
      <path d="M12 8.1c1.45 1.5 2.15 3 2.15 4.4 0 1.5-.7 2.9-2.15 4.2-1.45-1.3-2.15-2.7-2.15-4.2 0-1.4.7-2.9 2.15-4.4Z" strokeWidth={0.85} />
      {/* núcleo: anillo + sol */}
      <circle cx="12" cy="12.4" r="1.6" strokeWidth={0.85} />
      <Dot cx={12} cy={12.4} r={0.75} />
      {/* chispa sobre el núcleo (la lámina lleva un punto en el canal) */}
      <Dot cx={12} cy={9.3} r={0.5} />
    </Svg>
  );
}

/** ESPACIO DE TRABAJO — icono "Proyectos" de la lámina: sistema orbital, dos
 *  anillos concéntricos con nodos ensartados en el exterior y núcleo con halo. */
export function IconWorkspace() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="9" strokeWidth={0.95} />
      <circle cx="12" cy="12" r="5.1" strokeWidth={0.9} />
      {/* radios cortos entre los dos anillos, en las diagonales */}
      <path d="M15.6 8.4 17 7M8.4 8.4 7 7M8.4 15.6 7 17M15.6 15.6 17 17" strokeWidth={0.8} />
      {/* nodos ensartados EN el anillo exterior (cardinales, con halo) */}
      <Node cx={12} cy={3} halo={1.9} />
      <Node cx={21} cy={12} halo={1.9} />
      <Node cx={12} cy={21} halo={1.9} />
      <Node cx={3} cy={12} halo={1.9} />
      {/* satélites pequeños en el anillo interior */}
      <Dot cx={12} cy={6.9} r={0.8} />
      <Dot cx={12} cy={17.1} r={0.8} />
      {/* núcleo con halo */}
      <circle cx="12" cy="12" r="2.5" strokeWidth={0.85} />
      <Dot cx={12} cy={12} r={1.15} />
    </Svg>
  );
}

/** MISSION CONTROL — icono "Agentes" de la lámina: red poliédrica (geodésica)
 *  con nodos en los vértices, aristas cruzadas y núcleo conectado a todo. */
export function IconMissionControl() {
  // Hexágono de radio 8.4 (vértices arriba/abajo) + centro.
  // cos/sin precalculados para ángulos 90°,30°,-30°,-90°,-150°,150°.
  const v: [number, number][] = [
    [12, 3.6],       // N
    [19.27, 7.8],    // NE
    [19.27, 16.2],   // SE
    [12, 20.4],      // S
    [4.73, 16.2],    // SO
    [4.73, 7.8],     // NO
  ];
  const edge = (a: number, b: number) => `M${v[a][0]} ${v[a][1]} L${v[b][0]} ${v[b][1]}`;
  return (
    <Svg>
      {/* contorno del poliedro */}
      <path d={[edge(0, 1), edge(1, 2), edge(2, 3), edge(3, 4), edge(4, 5), edge(5, 0)].join(" ")} strokeWidth={0.9} />
      {/* diagonales largas (la malla interior de la lámina) */}
      <path d={[edge(0, 2), edge(2, 4), edge(4, 0), edge(1, 3), edge(3, 5), edge(5, 1)].join(" ")} strokeWidth={0.55} opacity={0.65} />
      {/* radios al núcleo */}
      <path d={v.map(([x, y]) => `M12 12 L${x} ${y}`).join(" ")} strokeWidth={0.55} opacity={0.8} />
      {/* nodos en los vértices (los superiores con halo, como la lámina) */}
      <Node cx={12} cy={3.6} halo={1.8} r={0.95} />
      <Dot cx={19.27} cy={7.8} />
      <Node cx={19.27} cy={16.2} halo={1.8} r={0.95} />
      <Dot cx={12} cy={20.4} />
      <Node cx={4.73} cy={16.2} halo={1.8} r={0.95} />
      <Dot cx={4.73} cy={7.8} />
      {/* núcleo: el orquestador */}
      <circle cx="12" cy="12" r="2.2" strokeWidth={0.85} />
      <Dot cx={12} cy={12} r={1.05} />
    </Svg>
  );
}

/** CALENDARIO — tal cual la lámina: tablilla con dos argollas de espiral
 *  arriba, banda de cabecera y rejilla de días como PUNTOS redondos. */
export function IconCalendar() {
  return (
    <Svg>
      <rect x="3.2" y="5.2" width="17.6" height="16" rx="2.4" strokeWidth={0.95} />
      <path d="M3.2 9.9h17.6" strokeWidth={0.8} />
      {/* argollas de espiral: anillo + vástago que entra en la tablilla */}
      <circle cx="7.9" cy="3.5" r="1.25" strokeWidth={0.85} />
      <path d="M7.9 4.75v1.5" strokeWidth={0.85} />
      <circle cx="16.1" cy="3.5" r="1.25" strokeWidth={0.85} />
      <path d="M16.1 4.75v1.5" strokeWidth={0.85} />
      {/* días: rejilla 3×3 de puntos (la lámina los lleva redondos y llenos) */}
      <Dot cx={7.9} cy={12.7} r={0.95} />
      <Dot cx={12} cy={12.7} r={0.95} />
      <Dot cx={16.1} cy={12.7} r={0.95} />
      <Dot cx={7.9} cy={15.7} r={0.95} />
      <Dot cx={12} cy={15.7} r={0.95} />
      <Dot cx={16.1} cy={15.7} r={0.95} />
      <Dot cx={7.9} cy={18.7} r={0.95} />
      <Dot cx={12} cy={18.7} r={0.95} />
    </Svg>
  );
}

/** CORREO — icono "Email" de la lámina: sobre con solapa en V profunda y las
 *  líneas de velocidad entrando por la izquierda. */
export function IconEmail() {
  return (
    <Svg>
      <rect x="6.6" y="6" width="15" height="12" rx="1.9" strokeWidth={0.95} />
      {/* solapa */}
      <path d="m7.1 7.2 7 5.5 6.9-5.5" strokeWidth={0.9} />
      {/* pliegues inferiores (las diagonales del sobre) */}
      <path d="m7.3 16.9 4.6-4M20.8 16.9l-4.6-4" strokeWidth={0.6} opacity={0.7} />
      {/* punto en el vértice de la solapa */}
      <Dot cx={14.1} cy={12.9} r={0.7} />
      {/* líneas de velocidad (entrega) */}
      <path d="M1.6 9.2h3.2M2.4 12h2.4M1.6 14.8h3.2" strokeWidth={0.95} />
    </Svg>
  );
}

/** CONFIGURACIÓN — el engranaje de la lámina: corona dentada + anillo
 *  interior + núcleo, con nodos en diagonales. */
export function IconSettings() {
  // 8 dientes: segmentos radiales cortos y gruesos sobre la corona r=6.6→8.6.
  const teeth: string[] = [];
  for (let k = 0; k < 8; k++) {
    const a = (k * Math.PI) / 4;
    const c = Math.cos(a);
    const s = Math.sin(a);
    teeth.push(`M${(12 + c * 6.9).toFixed(2)} ${(12 + s * 6.9).toFixed(2)} L${(12 + c * 8.7).toFixed(2)} ${(12 + s * 8.7).toFixed(2)}`);
  }
  return (
    <Svg>
      <path d={teeth.join(" ")} strokeWidth={2.1} strokeLinecap="butt" />
      <circle cx="12" cy="12" r="6.7" strokeWidth={0.95} />
      <circle cx="12" cy="12" r="3.7" strokeWidth={0.9} />
      {/* nodos entre corona y núcleo, en las diagonales (detalle de la lámina) */}
      <Dot cx={15.7} cy={8.3} r={0.65} />
      <Dot cx={8.3} cy={15.7} r={0.65} />
      {/* núcleo */}
      <Dot cx={12} cy={12} r={1.25} />
    </Svg>
  );
}

/** MODO PRESENCIA — icono "Conexión" de la lámina: órbita con nodos
 *  ensartados, núcleo con halo y marcas de eje en los cardinales. */
export function IconPresence() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="7.6" strokeWidth={0.95} />
      {/* marcas de eje fuera de la órbita */}
      <path d="M12 1.7v1.6M12 20.7v1.6M1.7 12h1.6M20.7 12h1.6" strokeWidth={0.85} />
      {/* nodos ensartados en la órbita, a tercios (con halo, como la lámina) */}
      <Node cx={18.58} cy={8.2} halo={1.9} r={1} />
      <Node cx={5.42} cy={8.2} halo={1.9} r={1} />
      <Node cx={12} cy={19.6} halo={1.9} r={1} />
      {/* núcleo: doble anillo + sol */}
      <circle cx="12" cy="12" r="2.9" strokeWidth={0.85} />
      <Dot cx={12} cy={12} r={1.2} />
    </Svg>
  );
}

/** BRIEFING — [PU4, doc 35] el amanecer: horizonte + sol naciente en arco,
 *  núcleo con halo asomando y rayos ascendentes con nodos en la punta (mismo
 *  vocabulario que el resto: línea fina, puntos llenos, halos). No existía en
 *  la lámina original — compuesto siguiendo el mismo lenguaje geométrico. */
export function IconBriefing() {
  return (
    <Svg>
      {/* horizonte */}
      <path d="M2.2 16.4h19.6" strokeWidth={0.95} />
      {/* arco del sol asomando justo sobre el horizonte */}
      <path d="M5.6 16.4a6.4 6.4 0 0 1 12.8 0" strokeWidth={0.95} />
      {/* núcleo del sol: halo + punto */}
      <circle cx="12" cy="16.4" r="2.1" strokeWidth={0.85} />
      <Dot cx={12} cy={16.4} r={0.95} />
      {/* rayos ascendentes, con nodo en la punta (el central con halo) */}
      <path d="M12 7.4v2.1" strokeWidth={0.85} />
      <Node cx={12} cy={6.2} halo={1.6} r={0.85} />
      <path d="M6.7 9.3l1.3 1.6M17.3 9.3l-1.3 1.6" strokeWidth={0.8} />
      <Dot cx={5.9} cy={8.3} r={0.75} />
      <Dot cx={18.1} cy={8.3} r={0.75} />
    </Svg>
  );
}

/** Conversación — compuesto con el mismo vocabulario de la lámina (núcleo +
 *  arcos concéntricos): la semilla emitiendo/escuchando. Lo usa la pill del
 *  Hub, no el dock. */
export function IconConversation() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="2.4" />
      <Dot cx={12} cy={12} r={0.9} />
      <path d="M7.6 8.4a6.2 6.2 0 0 0 0 7.2M16.4 8.4a6.2 6.2 0 0 1 0 7.2" />
      <path d="M4.6 5.6a10.4 10.4 0 0 0 0 12.8M19.4 5.6a10.4 10.4 0 0 1 0 12.8" />
    </Svg>
  );
}
