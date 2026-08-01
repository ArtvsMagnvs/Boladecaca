import { lazy, Suspense, useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { Dock } from "./Dock";

// [PU6a-bis v2] El chat ya no es una ruta: es una VENTANA montada aquí, en la
// única instancia persistente del árbol. Dos consecuencias buscadas:
//   · el Modo Conversación corre con el chat OCULTO (SPACE desde el Hub): el
//     componente sigue montado, su bucle de voz sigue vivo, y la conversación
//     se graba en el chat aunque no se vea;
//   · el AVCS queda SIEMPRE de fondo — el chat es una tarjeta encima, no una
//     página que lo tapa.
// Lazy + gate `chatBooted`: el chunk del chat (grande) no se carga hasta la
// primera vez que hace falta, igual que cuando era ruta.
const ChatWindow = lazy(() => import("@/pages/Chat"));
import { PresenceToggle } from "./PresenceToggle";
import { BriefingButton } from "./BriefingButton";
// [PU4b, doc 35] El "show" del briefing: tarjetas/calendario/pantalla de
// noticias sincronizados con la locución. Vive aquí (única instancia
// persistente) porque debe verse sobre CUALQUIER página; no renderiza nada
// mientras no hay briefing en curso.
import BriefingShow from "@/components/briefing/BriefingShow";
import WelcomeOverlay from "@/components/onboarding/WelcomeOverlay";
import { AitheraPresence } from "@/avcs";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

// Navegación simple sin animaciones de transición que pueden causar pantallas en negro.
// FIX V0.3 (Fase 1 Estabilizacion Hub V03): el Hub quiere llenar toda la
// pantalla con su CSS Grid de 280px/1fr/280px + barra inferior. Por eso el
// contenedor es h-screen flex-col y el main usa h-full con padding mas
// compacto; las paginas que no necesitan el layout a pantalla completa
// (Chat, Settings, etc.) siguen funcionando porque solo dependen de
// overflow-y-auto.
export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const presenceMode = useAppStore((s) => s.presenceMode);
  const setPresenceMode = useAppStore((s) => s.setPresenceMode);
  const togglePresenceMode = useAppStore((s) => s.togglePresenceMode);

  // [2026-07-21] Aviso "trabajando SOLO en local": permanente MIENTRAS dure la
  // situación (la nube configurada caída y todo cayendo a modelos locales) y
  // desaparece solo en cuanto la nube vuelve. Sondeo ligero visibility-aware.
  const [localOnly, setLocalOnly] = useState(false);
  const [showLocalInfo, setShowLocalInfo] = useState(false);
  usePolling(async () => {
    try {
      const s = await api.getMelHealthSummary();
      setLocalOnly(s.local_only);
      if (!s.local_only) setShowLocalInfo(false);
    } catch {
      /* backend caído: sin dato, sin banner (ya se ve "Conectando…") */
    }
  }, 45000);

  // AVCS S3 (doc 13 §13.4 Modo Presencia): F9 pliega/despliega toda la UI de
  // chrome; Esc restaura si está en modo presencia. Ninguna de las dos teclas
  // inserta texto, así que no hace falta comprobar qué elemento tiene foco.
  // Vive aquí (AppLayout es la única instancia persistente del árbol) para
  // que el atajo funcione en cualquier página, sin listeners duplicados.
  //
  // [PU6a, doc 35] Fuera de modo presencia, Esc vuelve al Hub inmersivo —
  // mismo destino que el logo del dock. Es el atajo de "salir de lo que sea
  // que esté haciendo y volver a casa", coherente con que el Hub ya no es un
  // dashboard sino el punto de entrada limpio.
  //
  // [PU6a-bis v2] Ventana de chat + Modo Conversación oculto. `chatBooted`
  // retrasa la carga del chunk hasta la primera necesidad real (abrir el chat
  // o pedir conversación por SPACE); una vez cargado, queda montado para
  // siempre — ocultarlo es `display:none`, nunca desmontar (su bucle de voz y
  // sus envíos en curso deben sobrevivir).
  const chatOpen = useAppStore((s) => s.chatOpen);
  const setChatOpen = useAppStore((s) => s.setChatOpen);
  const conversationRequested = useAppStore((s) => s.conversationRequested);
  // [PU4, doc 35] El botón de Briefing (y el disparo automático de las 8:15,
  // que también pasa por requestBriefing) necesitan el chat MONTADO para que
  // su efecto de escucha pueda reaccionar — mismo motivo que chatOpen/
  // conversationRequested arriba.
  const briefingRequestId = useAppStore((s) => s.briefingRequestId);
  const [chatBooted, setChatBooted] = useState(false);
  useEffect(() => {
    if (chatOpen || conversationRequested || briefingRequestId > 0) setChatBooted(true);
  }, [chatOpen, conversationRequested, briefingRequestId]);

  // [PU6a-bis v2] Orden de prioridad de Esc, de más local a más global:
  //   1. un diálogo abierto lo consume (Modal.tsx ya tiene su propio Esc)
  //   2. el chat abierto: se cierra (vuelve a verse el Hub/la página de abajo)
  //   3. Modo Presencia: restaura la UI
  //   4. cualquier página ≠ Hub: cierra y vuelve al Hub
  //   5. nada que cerrar: pedir a Electron salir de pantalla completa (IPC;
  //      fuera de Electron no hace nada)
  // El paso 5 es la mitad del fix del fallo reportado ("Esc con el chat
  // abierto salía de fullscreen"): Electron ya NO decide nada sobre Esc — la
  // otra mitad vive en main.cjs, que retiró su preventDefault.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "F9") {
        e.preventDefault();
        togglePresenceMode();
        return;
      }
      if (e.key !== "Escape") return;
      if (document.querySelector('[role="dialog"]')) return; // (1)
      if (useAppStore.getState().chatOpen) {
        setChatOpen(false); // (2)
      } else if (presenceMode) {
        setPresenceMode(false); // (3)
      } else if (location.pathname !== "/") {
        navigate("/"); // (4)
      } else {
        window.aithera?.exitFullscreen?.(); // (5)
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [presenceMode, setPresenceMode, togglePresenceMode, location.pathname, navigate, setChatOpen]);

  // [PU6a-bis v2] SPACE activa/desactiva el Modo Conversación desde cualquier
  // sitio — SIN abrir el chat (petición literal: "debería entrar en modo
  // conversación manteniendo el chat oculto, aunque la conversación se grabe
  // en el chat"). El componente del chat se monta oculto (chatBooted) y su
  // bucle de voz corre igual; abrirlo después muestra la transcripción.
  //
  // Guardas: no robarle la barra espaciadora a quien escribe (input/textarea/
  // contentEditable), ni a un diálogo, ni a un botón enfocado (preventDefault:
  // SPACE sobre un <button> enfocado lo "pulsa").
  const toggleConversationRequested = useAppStore((s) => s.toggleConversationRequested);
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.ctrlKey || e.metaKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el?.isContentEditable) return;
      if (document.querySelector('[role="dialog"]')) return;
      e.preventDefault();
      toggleConversationRequested();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggleConversationRequested]);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-base-950 text-ink">
      <main className="absolute inset-0 overflow-hidden">
        {/* AVCS S1 (doc 13 §13.1): el Canvas de la presencia vive AQUI, hermano
            del div con key=pathname y FUERA de el, para que NO se remonte al
            navegar (una sola instancia, el contexto WebGL y las FBO persisten).
            pointer-events-none: los clics atraviesan a la UI. */}
        <AitheraPresence className="absolute inset-0 z-0 pointer-events-none" />

        {/* [2026-07-21] Banner naranja: Aithera trabajando SOLO en local.
            Visible incluso en modo presencia (es un aviso de avería, no chrome). */}
        {localOnly && (
          <div className="absolute top-0 left-0 right-0 z-40 bg-signal-warn/15 border-b border-signal-warn/40 backdrop-blur-sm px-4 py-2 flex items-center justify-center gap-2 text-xs">
            <span className="font-medium text-signal-warn">
              AVISO: Aithera está trabajando exclusivamente con modelos de IA en local.
            </span>
            <button
              type="button"
              onClick={() => setShowLocalInfo((v) => !v)}
              className="w-5 h-5 rounded-full border border-signal-warn/50 text-signal-warn hover:bg-signal-warn/20 flex items-center justify-center text-[11px] font-bold shrink-0"
              aria-label="Más información sobre el modo local"
            >
              ?
            </button>
            {showLocalInfo && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1.5 glass-surface rounded-xl px-4 py-3 text-[11px] text-ink max-w-sm text-center shadow-xl">
                Revisa tu conexión a internet, o cambia los modelos en la sección{" "}
                <button
                  type="button"
                  className="text-accent underline font-medium"
                  onClick={() => {
                    setShowLocalInfo(false);
                    navigate("/settings", { state: { tab: "ia" } });
                  }}
                >
                  Inteligencia
                </button>{" "}
                de configuración. El aviso desaparecerá solo en cuanto la nube vuelva a responder.
              </div>
            )}
          </div>
        )}
        {/* `pb-28`: los botones sueltos flotan encima del contenido (son
            `fixed`, ya no ocupan sitio en el flujo como la barra vieja), así
            que el hueco se lo reserva la página para no quedar tapada. */}
        <div
          className={`h-full p-6 pb-28 relative z-10 transition-all duration-[400ms] ease-out ${
            presenceMode ? "opacity-0 translate-y-2 pointer-events-none" : "opacity-100 translate-y-0"
          }`}
          key={location.pathname}
        >
          <Outlet />
        </div>

        {/* [PU6a-bis v2] VENTANA de chat — montada una vez, oculta con
            display:none (los bucles de voz y los envíos siguen vivos).
            `pointer-events-none` en el contenedor: solo el panel del chat
            captura clics; el resto de la pantalla sigue siendo del Hub/página
            de debajo. */}
        {chatBooted && (
          <div className={`absolute inset-0 z-30 pointer-events-none ${chatOpen ? "" : "hidden"}`}>
            <Suspense fallback={null}>
              <ChatWindow />
            </Suspense>
          </div>
        )}
        <PresenceToggle />
        <BriefingButton />
        <BriefingShow />
      </main>

      {/* [PU6a-bis, doc 35] Botones SUELTOS (sin barra). Se posicionan solos
          (`fixed`) y gestionan su propio plegado en Modo Presencia. */}
      <Dock />

      {/* OB-1 (doc 30 §1): asistente de bienvenida. Se auto-decide si mostrarse
          (primera vez, flag en BD); no renderiza nada si el onboarding ya se
          completó. Fuera del <main> para cubrir toda la ventana. */}
      <WelcomeOverlay />
    </div>
  );
}
