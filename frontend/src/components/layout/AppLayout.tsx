import { Outlet } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { AitheraPresence } from "@/avcs";

// Navegación simple sin animaciones de transición que pueden causar pantallas en negro.
// FIX V0.3 (Fase 1 Estabilizacion Hub V03): el Hub quiere llenar toda la
// pantalla con su CSS Grid de 280px/1fr/280px + barra inferior. Por eso el
// contenedor es h-screen flex-col y el main usa h-full con padding mas
// compacto; las paginas que no necesitan el layout a pantalla completa
// (Chat, Settings, etc.) siguen funcionando porque solo dependen de
// overflow-y-auto.
export function AppLayout() {
  const location = useLocation();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-base-950 text-ink">
      <Sidebar />
      <main className="flex-1 overflow-hidden relative">
        {/* AVCS S1 (doc 13 §13.1): el Canvas de la presencia vive AQUI, hermano
            del div con key=pathname y FUERA de el, para que NO se remonte al
            navegar (una sola instancia, el contexto WebGL y las FBO persisten).
            pointer-events-none: los clics atraviesan a la UI. */}
        <AitheraPresence className="absolute inset-0 z-0 pointer-events-none" />
        <div className="h-full p-6 relative z-10" key={location.pathname}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
