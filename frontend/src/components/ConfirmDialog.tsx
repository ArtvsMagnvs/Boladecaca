// components/ConfirmDialog.tsx — confirmación elegante (Opt v0.9.5, U1)
//
// Reemplaza los `window.confirm()` nativos, que rompen la estética de app
// desktop de alta gama (salen con el chrome del sistema operativo, no con el
// lenguaje visual de Aithera). Mismo shell que Modal: backdrop con blur, panel
// centrado, Esc/clic-fuera cancelan.
//
// Uso con hook (`useConfirm`) para conservar el patrón imperativo `if (await
// confirm(...))` sin tener que cablear estado en cada página.
import { useCallback, useState } from "react";
import Modal from "./Modal";

interface ConfirmState {
  title: string;
  message?: string;
  confirmLabel: string;
  cancelLabel: string;
  danger: boolean;
  resolve: (ok: boolean) => void;
}

export interface ConfirmOptions {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Estilo destructivo (rojo) para borrados. Default true (el caso común). */
  danger?: boolean;
}

/**
 * Devuelve `[confirm, dialog]`. Renderiza `dialog` una vez en la página y llama
 * `await confirm({ title, ... })` donde antes usabas `window.confirm`.
 */
export function useConfirm(): [(o: ConfirmOptions) => Promise<boolean>, React.ReactNode] {
  const [state, setState] = useState<ConfirmState | null>(null);

  const confirm = useCallback((o: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setState({
        title: o.title,
        message: o.message,
        confirmLabel: o.confirmLabel ?? "Confirmar",
        cancelLabel: o.cancelLabel ?? "Cancelar",
        danger: o.danger ?? true,
        resolve,
      });
    });
  }, []);

  const close = (ok: boolean) => {
    state?.resolve(ok);
    setState(null);
  };

  const dialog = (
    <Modal open={state !== null} onClose={() => close(false)} maxWidth="max-w-sm" label={state?.title}>
      {state && (
        <div className="p-5 flex flex-col gap-4">
          <div>
            <h3 className="text-sm font-semibold text-ink">{state.title}</h3>
            {state.message && (
              <p className="text-xs text-ink-dim mt-1.5 leading-relaxed">{state.message}</p>
            )}
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => close(false)}
              className="text-xs px-3 py-2 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600"
            >
              {state.cancelLabel}
            </button>
            <button
              onClick={() => close(true)}
              className={`text-xs px-3 py-2 rounded-lg border ${
                state.danger
                  ? "bg-signal-error/15 text-signal-error border-signal-error/30 hover:bg-signal-error/25"
                  : "bg-accent/15 text-accent border-accent/30 hover:bg-accent/25"
              }`}
            >
              {state.confirmLabel}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );

  return [confirm, dialog];
}
