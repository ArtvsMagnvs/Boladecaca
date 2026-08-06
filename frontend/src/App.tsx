import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useAppStore } from "@/store/useAppStore";
// El Hub es la ruta raíz (lo primero que se ve): se carga de forma eager para
// que el arranque no muestre un spinner. El resto van lazy (code-splitting) —
// [Opt v0.9.5, P2] EmailAssistant (1600+ líneas), Settings (2000+) y las demás
// no hacen falta hasta que el usuario navega a ellas, así que no deben pesar en
// el JS del arranque. Con `base: "./"` en vite.config, los chunks dinámicos
// cargan bien bajo el file:// de Electron.
import Hub from "@/pages/Hub";

// [PU6a-bis v2] El chat dejó de ser una ruta: es una VENTANA flotante montada
// en AppLayout (para que el Modo Conversación corra con el chat oculto y el
// AVCS quede siempre de fondo). El enlace viejo /chat sigue funcionando: abre
// la ventana y aterriza en el Hub — mismo patrón que /projects → /workspace.
function ChatRedirect() {
  const setChatOpen = useAppStore((s) => s.setChatOpen);
  useEffect(() => { setChatOpen(true); }, [setChatOpen]);
  return <Navigate to="/" replace />;
}
// V0.87 (WPMS W2a): Workspace unifica Proyectos + Tareas. Las paginas viejas
// (Projects.tsx/Tasks.tsx) se retiran; /projects y /tasks redirigen aqui.
const Workspace = lazy(() => import("@/pages/Workspace"));
const CalendarPage = lazy(() => import("@/pages/Calendar"));
const Settings = lazy(() => import("@/pages/Settings"));
const Agents = lazy(() => import("@/pages/Agents"));
const EmailAssistant = lazy(() => import("@/pages/EmailAssistant"));
// V0.9 (Automation Engine A3): reglas + historial + aprobaciones.
const Automation = lazy(() => import("@/pages/Automation"));
// V1.0 (TIE v1, T4b): misiones — plan, pasos, aprobación y kill-switch.
const Missions = lazy(() => import("@/pages/Missions"));
const Learning = lazy(() => import("@/pages/Learning"));

// Placeholder mientras carga un chunk de página (imperceptible en local, pero
// evita un parpadeo en blanco). Discreto, en el lenguaje visual de la app.
function RouteFallback() {
  return (
    <div className="h-full flex items-center justify-center text-ink-dim text-sm">
      Cargando…
    </div>
  );
}

// HashRouter (no BrowserRouter): cuando Electron carga el build empaquetado
// via file://, no hay servidor que resuelva rutas tipo /chat - el hash
// (#/chat) funciona sin servidor, evitando pantallas en blanco al refrescar
// o al cargar una ruta que no sea la raiz.
export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Hub />} />
          <Route path="/chat" element={<ChatRedirect />} />
          <Route path="/email" element={<Suspense fallback={<RouteFallback />}><EmailAssistant /></Suspense>} />
          <Route path="/workspace" element={<Suspense fallback={<RouteFallback />}><Workspace /></Suspense>} />
          {/* V0.87: rutas viejas -> Workspace (sin romper enlaces existentes) */}
          <Route path="/projects" element={<Navigate to="/workspace" replace />} />
          <Route path="/tasks" element={<Navigate to="/workspace" replace />} />
          <Route path="/calendar" element={<Suspense fallback={<RouteFallback />}><CalendarPage /></Suspense>} />
          <Route path="/agents" element={<Suspense fallback={<RouteFallback />}><Agents /></Suspense>} />
          <Route path="/automation" element={<Suspense fallback={<RouteFallback />}><Automation /></Suspense>} />
          <Route path="/missions" element={<Suspense fallback={<RouteFallback />}><Missions /></Suspense>} />
          {/* [V1.1 L4] Lo que Aithera ha aprendido: página propia, no una pestaña de Ajustes. */}
          <Route path="/learning" element={<Suspense fallback={<RouteFallback />}><Learning /></Suspense>} />
          {/* [2026-07-21] El Centro de Voz se fusionó en Configuración → Voz
              (petición del usuario: nada de config dispersa). El enlace viejo
              redirige, mismo patrón que /projects y /tasks. */}
          <Route path="/voice" element={<Navigate to="/settings" replace />} />
          <Route path="/settings" element={<Suspense fallback={<RouteFallback />}><Settings /></Suspense>} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
