// CoreSelector.tsx — Selector del nucleo 3D del Hub (V0.7 extra).
//
// Wrapper discreto arriba del Hub con un boton que muestra el modelo
// actualmente seleccionado. Al hacer click se despliega un dropdown
// con todas las opciones. Al elegir una, el componente renderiza ese
// modelo 3D en el mismo sitio centrico donde estaba el AI Core.
//
// Decisiones:
// - Estado persistido en localStorage (sobrevive a recargas, sin
//   acoplar a Zustand para no tocar el store global).
// - La decoracion (anillo exterior, anillo interior dashed, ondas de
//   escucha, pulsos de voz, glow segun coreState) es la MISMA que
//   llevaba AICoreWithRings — solo cambia el modelo 3D de dentro.
// - Las moscas orbitando del PoopSphere se renderizan solo cuando
//   este modelo esta activo (sin doble render).

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AitheraSeed } from "@/components/hub/AitheraSeed";
import { AICore } from "@/components/hub/AICore";
import { PoopSphere } from "@/components/hub/PoopSphere";
import { RasenganSphere } from "@/components/hub/RasenganSphere";
import { DEFAULT_CORE_DESIGN, type CoreDesignSettings, type CoreModelId } from "@/components/hub/coreDesign";
import { useAppStore, type AICoreState } from "@/store/useAppStore";

export type { CoreModelId } from "@/components/hub/coreDesign";

interface CoreModel {
  id: CoreModelId;
  label: string;
  /** Texto corto que aparece en el boton cuando esta seleccionado. */
  shortLabel: string;
  /** Descripcion de una linea para el item del dropdown. */
  hint: string;
  /** Color del dot indicador en el boton (cuando esta activo). */
  dotClass: string;
}

const CORE_MODELS: CoreModel[] = [
  {
    id: "aithera_seed",
    label: "Semilla de Aithera",
    shortLabel: "Semilla",
    hint: "Logo vivo inicial, dorado y centrado",
    dotClass: "bg-amber-300",
  },
  {
    id: "blue_orb",
    label: "Orbe azul",
    shortLabel: "Orbe azul",
    hint: "Nucleo clasico con shaders procedurales",
    dotClass: "bg-accent",
  },
  {
    id: "poop_sphere",
    label: "Bola de caca",
    shortLabel: "Bola de caca",
    hint: "Emoji cartoon con moscas orbitando",
    dotClass: "bg-amber-400",
  },
  {
    id: "rasengan",
    label: "Rasengan",
    shortLabel: "Rasengan",
    hint: "Jutsu de Naruto: esfera azul giratoria",
    dotClass: "bg-sky-300",
  },
];

const STORAGE_KEY = "aithera.coreModel";

export function loadStoredModel(): CoreModelId {
  if (typeof window === "undefined") return "aithera_seed";
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v === "aithera_seed" || v === "blue_orb" || v === "poop_sphere" || v === "rasengan") return v;
  } catch {
    // localStorage no disponible (modo incognito, etc.) — fallback silencioso.
  }
  return "aithera_seed";
}

const STATE_RING_COLOR: Record<AICoreState, string> = {
  idle: "border-accent/20",
  listening: "border-accent-glow/60",
  thinking: "border-accent-soft/50",
  speaking: "border-accent/55",
  processing: "border-accent-soft/45",
  error: "border-signal-error/50",
  // AVCS S1: estados nuevos (componente congelado).
  action: "border-accent-soft/50",
  recovering: "border-accent/25",
};

const STATE_GLOW: Record<AICoreState, string> = {
  idle: "",
  listening: "shadow-[0_0_40px_rgba(143,217,255,0.18)]",
  thinking: "shadow-[0_0_50px_rgba(124,156,255,0.22)]",
  speaking: "shadow-[0_0_45px_rgba(94,168,255,0.25)]",
  processing: "shadow-[0_0_50px_rgba(124,156,255,0.2)]",
  error: "shadow-[0_0_40px_rgba(224,113,110,0.2)]",
  // AVCS S1: estados nuevos (componente congelado).
  action: "shadow-[0_0_50px_rgba(127,224,195,0.2)]",
  recovering: "shadow-[0_0_35px_rgba(94,168,255,0.12)]",
};

interface CoreFrameProps {
  coreState: AICoreState;
  size: number;
  design: CoreDesignSettings;
  children: React.ReactNode;
}

/**
 * Marco decorativo comun (anillos + ondas + glow) que envuelve al
 * modelo 3D. Antes vivia dentro de AICoreWithRings en Hub.tsx;
 * ahora es reutilizable para cualquier modelo.
 */
function CoreFrame({ coreState, size, design, children }: CoreFrameProps) {
  const ringColor = STATE_RING_COLOR[coreState];
  const glow = STATE_GLOW[coreState];
  const designGlow = Math.round(22 * design.glow);
  const glowAlpha = Math.min(0.28, 0.06 + design.glow * 0.08);

  return (
    <div
      className={`relative transition-shadow duration-700 ${glow}`}
      style={{
        width: size,
        height: size,
        transform: `scale(${design.scale})`,
        filter: `brightness(${design.brightness}) drop-shadow(0 0 ${designGlow}px rgba(125, 211, 252, ${glowAlpha}))`,
      }}
    >
      {/* Anillo exterior */}
      <div
        className={`absolute inset-0 rounded-full border ${ringColor} ${
          coreState === "idle"
            ? "ring-idle"
            : coreState === "listening"
            ? "ring-listening"
            : coreState === "thinking"
            ? "ring-thinking"
            : coreState === "speaking"
            ? "ring-speaking"
            : coreState === "processing"
            ? "ring-processing"
            : ""
        }`}
      />

      {/* Anillo interior giratorio — solo thinking/processing */}
      <AnimatePresence>
        {(coreState === "thinking" || coreState === "processing") && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute inset-[16px] rounded-full border border-dashed border-accent-soft/30 ring-thinking-rev pointer-events-none"
          />
        )}
      </AnimatePresence>

      {/* Ondas de escucha */}
      <AnimatePresence>
        {coreState === "listening" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-[-8px] rounded-full border border-accent-glow/20 wave-ring pointer-events-none"
              style={{ animationDelay: "0s" }}
            />
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-[-8px] rounded-full border border-accent-glow/15 wave-ring pointer-events-none"
              style={{ animationDelay: "0.7s" }}
            />
          </>
        )}
      </AnimatePresence>

      {/* Pulsos de voz */}
      <AnimatePresence>
        {coreState === "speaking" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-[-6px] rounded-full border border-accent/25 wave-ring pointer-events-none"
              style={{ animationDelay: "0s", animationDuration: "1.2s" }}
            />
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-[-6px] rounded-full border border-accent/18 wave-ring pointer-events-none"
              style={{ animationDelay: "0.4s", animationDuration: "1.2s" }}
            />
          </>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="absolute inset-0"
      >
        {children}
      </motion.div>
    </div>
  );
}

interface CoreModelViewProps {
  /** Identificador del modelo a renderizar (controlado). */
  model: CoreModelId;
  /** Tamano del area del modelo 3D en pixeles. */
  size: number;
  /** Ajustes internos de diseno para el modelo activo. */
  design?: CoreDesignSettings;
  /**
   * Si true, el area del modelo actua como link al chat (clic = navega
   * a /chat, igual que hacia AICoreWithRings antes).
   */
  linkToChat?: boolean;
  onNavigateToChat?: () => void;
}

/**
 * Renderiza SOLO el modelo 3D seleccionado, envuelto en el CoreFrame
 * comun (anillos + ondas + glow segun coreState). Sin boton — pensado
 * para layouts donde el selector vive en otra zona (cabecera, sidebar).
 */
export function CoreModelView({
  model,
  size,
  design = DEFAULT_CORE_DESIGN,
  linkToChat = false,
  onNavigateToChat,
}: CoreModelViewProps) {
  const coreState = useAppStore((s) => s.coreState);

  const inner = (
    <CoreFrame coreState={coreState} size={size} design={design}>
      {model === "aithera_seed" ? (
        <AitheraSeed size={size} design={design} />
      ) : model === "blue_orb" ? (
        <AICore size={size} design={design} />
      ) : model === "poop_sphere" ? (
        <PoopSphere size={size} audioLevel={0} design={design} />
      ) : (
        <RasenganSphere size={size} audioLevel={0} design={design} />
      )}
    </CoreFrame>
  );

  if (linkToChat && onNavigateToChat) {
    return (
      <div
        onClick={onNavigateToChat}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onNavigateToChat();
        }}
        className="cursor-pointer outline-none rounded-full"
        aria-label="Abrir chat"
        title="Abrir chat"
      >
        {inner}
      </div>
    );
  }
  return inner;
}

interface CoreSelectorButtonProps {
  /** Modelo actualmente seleccionado (controlado). */
  value: CoreModelId;
  /** Notifica al padre cuando el usuario elige otra opcion. */
  onChange: (id: CoreModelId) => void;
}

/**
 * Boton-dropdown standalone para cambiar el nucleo 3D. Solo el boton
 * (sin el modelo). Pensado para colocarlo en la cabecera del Hub (u
 * otro lugar) mientras el modelo vive en el centro. Controlado: el
 * padre guarda el estado y se lo pasa en `value` + `onChange`.
 */
export function CoreSelectorButton({ value, onChange }: CoreSelectorButtonProps) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Cerrar el dropdown al clicar fuera o pulsar Escape.
  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onClickOutside);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onClickOutside);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = CORE_MODELS.find((m) => m.id === value) ?? CORE_MODELS[0];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={[
          "group flex items-center gap-1.5 px-2.5 py-1 rounded-full",
          "text-[11px] uppercase tracking-wider text-ink-dim",
          "bg-base-900/60 border border-base-700/60",
          "hover:border-accent/40 hover:text-ink hover:bg-base-800/80",
          "transition-colors backdrop-blur-sm",
          open ? "border-accent/50 text-ink bg-base-800/80" : "",
        ].join(" ")}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Cambiar nucleo 3D"
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${current.dotClass}`}
        />
        <span>{current.shortLabel}</span>
        <svg
          width="9"
          height="9"
          viewBox="0 0 10 10"
          className={`transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path
            d="M2 4 L5 7 L8 4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.96 }}
            transition={{ duration: 0.12, ease: "easeOut" }}
            role="listbox"
            className={[
              "absolute z-30 left-1/2 -translate-x-1/2 mt-2",
              "min-w-[220px] py-1 rounded-lg",
              "bg-base-900/95 border border-base-700/80",
              "backdrop-blur-md shadow-2xl",
            ].join(" ")}
          >
            {CORE_MODELS.map((m) => {
              const active = m.id === value;
              return (
                <button
                  type="button"
                  key={m.id}
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    onChange(m.id);
                    setOpen(false);
                  }}
                  className={[
                    "w-full text-left px-3 py-2 flex items-start gap-2.5",
                    "transition-colors",
                    active
                      ? "bg-accent/10 text-ink"
                      : "text-ink-dim hover:bg-base-800/70 hover:text-ink",
                  ].join(" ")}
                >
                  <span
                    className={`mt-1 h-1.5 w-1.5 rounded-full shrink-0 ${
                      active ? m.dotClass : "bg-ink-faint"
                    }`}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm leading-tight">{m.label}</span>
                    <span className="block text-[10px] text-ink-faint mt-0.5 leading-snug">
                      {m.hint}
                    </span>
                  </span>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface CoreSelectorProps {
  /** Tamano del area del modelo 3D en pixeles. */
  size?: number;
  /**
   * Si true, el area del modelo actua como link al chat (clic = navega
   * a /chat, igual que hacia AICoreWithRings antes).
   */
  linkToChat?: boolean;
  onNavigateToChat?: () => void;
}

/**
 * Renderiza el modelo 3D actualmente seleccionado, envuelto en el
 * CoreFrame comun, con un boton-dropdown discreto arriba del Hub para
 * cambiar de modelo. La eleccion persiste en localStorage.
 *
 * Wrapper de compat: mantiene su propio state interno (id + persistencia
 * en localStorage) y delega en `CoreSelectorButton` + `CoreModelView`.
 * Para layouts donde el boton debe vivir separado del modelo (ej. el
 * Hub con el boton en la cabecera), usar directamente esos dos
 * sub-componentes y gestionar el estado desde fuera.
 */
export function CoreSelector({
  size = 320,
  linkToChat = true,
  onNavigateToChat,
}: CoreSelectorProps) {
  const [selected, setSelected] = useState<CoreModelId>(loadStoredModel);

  // Persistir eleccion.
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, selected);
    } catch {
      // localStorage no disponible — ignorar.
    }
  }, [selected]);

  return (
    <div className="flex flex-col items-center gap-3">
      <CoreSelectorButton value={selected} onChange={setSelected} />
      <CoreModelView
        model={selected}
        size={size}
        linkToChat={linkToChat}
        onNavigateToChat={onNavigateToChat}
      />
    </div>
  );
}

export default CoreSelector;