// AVCS — visibilidad por ruta + tier desde ajustes. Sin re-crear el Canvas:
// solo decide si la presencia está visible y con qué tier arranca.
import type { QualityTier } from "../types";
import { useAppStore } from "@/store/useAppStore";

/** Rutas donde la presencia es plenamente visible (doc 13 §13.5). El resto la
 *  atenúa/pausa sin desmontar el Canvas. */
const VISIBLE_ROUTES = new Set(["/", "/chat"]);

export function isPresenceVisible(pathname: string): boolean {
  return VISIBLE_ROUTES.has(pathname);
}

/** Tier de calidad, editable en vivo desde Settings (S3, §16) — persistido en
 *  localStorage por el store (avcsTier), leído aquí de forma reactiva para que
 *  un cambio en Ajustes reconfigure el motor sin recargar la app. */
export function useAvcsTier(): QualityTier {
  return useAppStore((s) => s.avcsTier);
}
