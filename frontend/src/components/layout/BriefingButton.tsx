// [PU4, doc 35] Botón extra de Briefing — pedido explícito del usuario:
// "que lo pueda activar yo con un botón en un botón extra que estará al lado
// del botón del modo presencia, diseñalo con la iconografia del proyecto".
//
// Mismo DockButton/iconografía que PresenceToggle.tsx (cuerpo, rim, cometa
// orbitando, polvo al pulsar), colocado inmediatamente a su IZQUIERDA en la
// misma fila (bottom-[41px], 46px de círculo, gap de 12px — el mismo que ya
// usa la fila de Configuración de la esquina izquierda).
//
// A diferencia de PresenceToggle (que debe seguir visible en Modo Presencia
// porque es la única vía de ratón para salir), este botón se OCULTA por
// completo en Modo Presencia: no hace falta un briefing mientras el AVCS
// ocupa toda la pantalla, y un botón extra ahí solo añadiría ruido visual.
//
// El clic no calcula nada aquí: solo anuncia la INTENCIÓN incrementando
// `briefingRequestId` en el store (mismo patrón que conversationRequested) —
// Chat.tsx (montado de forma persistente, PU6a-bis v2) es quien de verdad
// pide GET /api/memory/briefing y locuta la respuesta, sobreviva o no este
// botón al ciclo de vida de la página actual.
import { useAppStore } from "@/store/useAppStore";
import { useT } from "@/store/useI18n";
import { DockButton } from "./DockButton";
import { IconBriefing } from "./DockIcons";

export function BriefingButton() {
  const presenceMode = useAppStore((s) => s.presenceMode);
  const briefingBusy = useAppStore((s) => s.briefingBusy);
  const requestBriefing = useAppStore((s) => s.requestBriefing);
  const t = useT();

  if (presenceMode) return null;

  return (
    <div className="fixed right-[78px] bottom-[41px] z-30">
      <DockButton
        icon={<IconBriefing />}
        label={t("nav.briefing")}
        onClick={requestBriefing}
        active={briefingBusy}
        size={46}
        labelAlign="right"
      />
    </div>
  );
}
