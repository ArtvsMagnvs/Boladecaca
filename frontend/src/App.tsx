import { HashRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Hub from "@/pages/Hub";
import Chat from "@/pages/Chat";
import Projects from "@/pages/Projects";
import Tasks from "@/pages/Tasks";
import CalendarPage from "@/pages/Calendar";
import Settings from "@/pages/Settings";
import VoiceCenter from "@/pages/VoiceCenter";
import Agents from "@/pages/Agents";
import EmailAssistant from "@/pages/EmailAssistant";

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
          <Route path="/chat" element={<Chat />} />
          <Route path="/email" element={<EmailAssistant />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/voice" element={<VoiceCenter />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
