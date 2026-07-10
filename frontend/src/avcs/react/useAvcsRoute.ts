// AVCS — visibilidad por ruta + tier desde ajustes (localStorage). Sin re-crear
// el Canvas: solo decide si la presencia está visible y con qué tier arranca.
import { useState } from "react";
import type { QualityTier } from "../types";
import { DEFAULT_TIER } from "../constants";

const TIER_KEY = "avcs.tier";

/** Rutas donde la presencia es plenamente visible (doc 13 §13.5). El resto la
 *  atenúa/pausa sin desmontar el Canvas. */
const VISIBLE_ROUTES = new Set(["/", "/chat"]);

export function isPresenceVisible(pathname: string): boolean {
  return VISIBLE_ROUTES.has(pathname);
}

/** Lee el tier de calidad persistido (Settings, S3). Default Q3 escritorio. */
export function useAvcsTier(): QualityTier {
  const [tier] = useState<QualityTier>(() => {
    try {
      const v = window.localStorage.getItem(TIER_KEY);
      if (v === "Q1" || v === "Q2" || v === "Q3" || v === "Q4") return v;
    } catch {
      /* localStorage no disponible */
    }
    return DEFAULT_TIER;
  });
  return tier;
}
