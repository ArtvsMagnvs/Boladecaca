// hooks/usePolling.ts — sondeo periódico consciente de visibilidad (Opt v0.9.5, P1)
//
// Reemplaza el patrón repetido `setInterval(fn, ms)` que había en Hub, Chat,
// Missions, Automation y Settings. Aporta lo que a esos setInterval sueltos les
// faltaba: NO sondear cuando la ventana está oculta/minimizada (sondear el
// backend cada 1-2s sin que nadie mire es carga inútil), y refrescar al instante
// al volver a primer plano para que el usuario nunca vea datos rancios.
import { useEffect, useRef } from "react";

/**
 * Ejecuta `fn` cada `intervalMs` mientras la pestaña esté visible.
 * @param fn         trabajo a repetir (idealmente idempotente / cancelable).
 * @param intervalMs periodo en ms; <= 0 desactiva el polling.
 * @param enabled    condición para sondear (p. ej. "hay algo vivo que seguir").
 */
export function usePolling(fn: () => void, intervalMs: number, enabled = true) {
  // `fn` en un ref para no re-crear el intervalo en cada render (la mayoría de
  // callers pasan una closure nueva cada vez).
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;

    const run = () => {
      if (document.hidden) return;
      fnRef.current();
    };

    run(); // primera pasada inmediata
    const id = window.setInterval(run, intervalMs);
    const onVisible = () => { if (!document.hidden) run(); };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [intervalMs, enabled]);
}
