import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { PresenceToggle } from "./PresenceToggle";
import { AitheraPresence } from "@/avcs";
import { useAppStore } from "@/store/useAppStore";

// Navegación simple sin animaciones de transición que pueden causar pantallas en negro.
// FIX V0.3 (Fase 1 Estabilizacion Hub V03): el Hub quiere llenar toda la
// pantalla con su CSS Grid de 280px/1fr/280px + barra inferior. Por eso el
// contenedor es h-screen flex-col y el main usa h-full con padding mas
// compacto; las paginas que no necesitan el layout a pantalla completa
// (Chat, Settings, etc.) siguen funcionando porque solo dependen de
// overflow-y-auto.
export function AppLayout() {
  const location = useLocation();
  const presenceMode = useAppStore((s) => s.presenceMode);
  const setPresenceMode = useAppStore((s) => s.setPresenceMode);
  const togglePresenceMode = useAppStore((s) => s.togglePresenceMode);

  // AVCS S3 (doc 13 §13.4 Modo Presencia): F9 pliega/despliega toda la UI de
  // chrome; Esc SIEMPRE restaura (nunca activa). Ninguna de las dos teclas
  // inserta texto, así que no hace falta comprobar qué elemento tiene foco.
  // Vive aquí (AppLayout es la única instancia persistente del árbol) para
  // que el atajo funcione en cualquier página, sin listeners duplicados.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "F9") {
        e.preventDefault();
        togglePresenceMode();
      } else if (e.key === "Escape" && presenceMode) {
        setPresenceMode(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [presenceMode, setPresenceMode, togglePresenceMode]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-base-950 text-ink">
      <div
        className={`shrink-0 overflow-hidden transition-all duration-[400ms] ease-out ${
          presenceMode ? "w-0 opacity-0 -translate-x-4" : "w-60 opacity-100 translate-x-0"
        }`}
      >
        <Sidebar />
      </div>
      <main className="flex-1 overflow-hidden relative">
        {/* AVCS S1 (doc 13 §13.1): el Canvas de la presencia vive AQUI, hermano
            del div con key=pathname y FUERA de el, para que NO se remonte al
            navegar (una sola instancia, el contexto WebGL y las FBO persisten).
            pointer-events-none: los clics atraviesan a la UI. */}
        <AitheraPresence className="absolute inset-0 z-0 pointer-events-none" />
        <div
          className={`h-full p-6 relative z-10 transition-all duration-[400ms] ease-out ${
            presenceMode ? "opacity-0 translate-y-2 pointer-events-none" : "opacity-100 translate-y-0"
          }`}
          key={location.pathname}
        >
          <Outlet />
        </div>
        <PresenceToggle />
      </main>
    </div>
  );
}
