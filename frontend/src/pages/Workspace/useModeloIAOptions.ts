// pages/Workspace/useModeloIAOptions.ts — lista de "Modelo IA" para agentes
// (V0.87 WPMS W2e). Antes era un array fijo con "custom" (inservible — no hay
// proveedor "custom" real) y proveedores hardcodeados que podian no estar
// conectados. Ahora: "Flexible según necesidad" (generic, sin atar el agente
// a un proveedor) + solo los proveedores IA que el usuario ya tiene
// configurados (AIProviderEntry.is_configured) — si el usuario añade o quita
// un proveedor en Ajustes, esta lista se actualiza sola, sin tocar código.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface ModeloIAOption {
  value: string;
  label: string;
}

const GENERIC: ModeloIAOption = { value: "generic", label: "Flexible según necesidad" };

export function useModeloIAOptions() {
  const [options, setOptions] = useState<ModeloIAOption[]>([GENERIC]);

  useEffect(() => {
    let cancelled = false;
    api
      .getConfiguredProviders()
      .then((providers) => {
        if (cancelled) return;
        const configured = providers
          .filter((p) => p.is_configured)
          .map((p) => ({ value: p.provider, label: p.label || p.provider }));
        setOptions([GENERIC, ...configured]);
      })
      .catch(() => {
        if (!cancelled) setOptions([GENERIC]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return options;
}
