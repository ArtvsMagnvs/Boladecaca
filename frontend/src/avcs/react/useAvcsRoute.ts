// AVCS — visibilidad por ruta + tier desde ajustes. Sin re-crear el Canvas:
// solo decide si la presencia está visible y con qué tier arranca.
import type { QualityTier } from "../types";
import { useAppStore } from "@/store/useAppStore";

/** [PU6a-bis v2, doc 35 §PU6] La presencia es visible en TODAS las rutas:
 *  petición directa del usuario — el AVCS queda SIEMPRE de fondo (semilla,
 *  anillos, animación) y las páginas flotan encima como tarjetas, nunca lo
 *  tapan con un fondo plano. Antes solo "/" y "/chat" lo mostraban y el resto
 *  pausaba el motor; ese ahorro ya no aplica (el fondo ES el producto).
 *  La firma se conserva por estabilidad del API. */
export function isPresenceVisible(_pathname: string): boolean {
  return true;
}

/** Tier de calidad, editable en vivo desde Settings (S3, §16) — persistido en
 *  localStorage por el store (avcsTier), leído aquí de forma reactiva para que
 *  un cambio en Ajustes reconfigure el motor sin recargar la app. */
export function useAvcsTier(): QualityTier {
  return useAppStore((s) => s.avcsTier);
}
