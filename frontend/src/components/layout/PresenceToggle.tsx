// AVCS S3 — Modo Presencia (doc 13 §13.4): pliega TODA la UI de chrome
// dejando solo la presencia a pantalla completa. Vive FUERA de los
// contenedores que se pliegan (AppLayout lo monta suelto) para poder pulsarse
// también estando activo.
//
// [PU6a-bis v2, doc 35 §PU6] Rediseñado como un botón del dock (mismo
// DockButton: cuerpo, rim, cometa orbitando, polvo al pulsar) con el icono
// "Conexión" de la lámina de referencia, y ALINEADO con el resto: su centro
// va a los mismos 64px del borde inferior que la fila central y que el botón
// de Configuración de la esquina izquierda (46px de círculo → bottom 41px).
// Antes era un botón pequeño propio, más abajo que los demás — se veía
// descolgado (fallo (3) reportado).
//
// En Modo Presencia se queda VISIBLE (atenuado): es la única vía de ratón
// para salir. La etiqueta se alinea a la derecha para no salirse del borde.
import { useAppStore } from "@/store/useAppStore";
import { useT } from "@/store/useI18n";
import { DockButton } from "./DockButton";
import { IconPresence } from "./DockIcons";

export function PresenceToggle() {
  const presenceMode = useAppStore((s) => s.presenceMode);
  const togglePresenceMode = useAppStore((s) => s.togglePresenceMode);
  const t = useT();

  return (
    <div
      className={`fixed right-5 bottom-[41px] z-30 transition-opacity duration-300 ${
        presenceMode ? "opacity-35 hover:opacity-100" : "opacity-100"
      }`}
    >
      <DockButton
        icon={<IconPresence />}
        label={presenceMode ? `${t("nav.presence")} · Esc` : `${t("nav.presence")} · F9`}
        onClick={togglePresenceMode}
        active={presenceMode}
        size={46}
        labelAlign="right"
      />
    </div>
  );
}
