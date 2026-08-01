// Hub.tsx — Hub inmersivo (PU6a, doc 35 §PU6).
//
// "Inicio" deja de ser un dashboard de tarjetas y pasa a ser el punto de
// entrada limpio: solo la presencia (AVCS, montada full-bleed en AppLayout),
// la etiqueta de su estado, y un atajo a la conversación por voz. Los datos
// que antes vivían aquí en 6 paneles (proyectos, tareas, agentes, eventos,
// chat reciente, correo, memoria) no se pierden — se reparten entre badges en
// los botones sueltos (Dock, visibles desde cualquier página) y sus propias
// páginas, que son donde de verdad se trabaja con ellos.
//
// [PU6a-bis] Entrada al chat: SOLO la tecla Enter. El clic sobre el lienzo se
// retiró a petición del usuario — con el AVCS ocupando toda la pantalla,
// cualquier clic despistado (o el de volver de otra ventana) abría el chat sin
// querer, y ya hay dos vías explícitas: Enter y la pill de conversación.
import { useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import { useT } from "@/store/useI18n";
import { IconConversation } from "@/components/layout/DockIcons";

export default function Hub() {
  const conversationRequested = useAppStore((s) => s.conversationRequested);
  const toggleConversationRequested = useAppStore((s) => s.toggleConversationRequested);
  const setChatOpen = useAppStore((s) => s.setChatOpen);
  const t = useT();

  // Enter abre la VENTANA de chat (ya no es una ruta) con el input enfocado.
  // Sin modificadores, para no robarle Ctrl/Cmd/Shift+Enter a nada. Guard de
  // elemento con foco: Enter sobre un botón enfocado lo "pulsa", no debe
  // además abrir el chat.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Enter" || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "BUTTON" || el?.isContentEditable) return;
      setChatOpen(true);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setChatOpen]);

  return (
    <div className="h-full relative">
      {/* [PU6b-vent t4] La etiqueta central de estado ("En reposo · modelo")
          se ELIMINÓ a petición del usuario: la semilla habla por sí sola y el
          modelo activo ya se ve en la esquina del dock (MEL-UI, §25). */}

      {/* Pill de Conversación. Posición pedida por el usuario: "por debajo de
          la semilla, entre los botones sueltos y la semilla, un punto medio".
          Los botones tienen su centro a 64px del borde inferior y el centro
          de la semilla está a media pantalla; `bottom-[26%]` cae justo entre
          los dos y escala solo con el tamaño de la ventana (con un `bottom`
          en píxeles, en una pantalla alta acabaría pegada a los botones).
          `fixed` y no `absolute`: el contenedor de página lleva un `pb-28`
          para dejar sitio a los botones, y con `absolute` ese hueco falsearía
          el 26% subiendo la pill de más.

          Arranca/para el Modo Conversación a través del store — la MISMA
          bandera que mueve la tecla SPACE, así que el botón refleja siempre
          el estado real aunque la conversación se activara por teclado. Y NO
          abre el chat (petición literal): la conversación corre con el chat
          oculto y se graba ahí igualmente. */}
      <button
        type="button"
        onClick={toggleConversationRequested}
        title={t("chat.conversationStart")}
        aria-pressed={conversationRequested}
        className={`fixed bottom-[26%] left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-sm text-xs transition-all duration-300 ${
          conversationRequested
            ? "border-signal-ok/70 bg-signal-ok/15 text-ink shadow-[0_0_24px_-4px_rgb(var(--c-signal-ok)),inset_0_0_14px_-6px_rgb(var(--c-signal-ok))]"
            : "border-base-700 bg-base-900/60 text-ink-dim hover:text-ink hover:border-signal-ok/40 hover:bg-signal-ok/10"
        }`}
      >
        {/* Activo: el icono late en verde Y un halo pulsa alrededor de toda la
            pill — inconfundible a un vistazo, que era lo pedido. */}
        {conversationRequested && (
          <span className="absolute inset-0 rounded-full border border-signal-ok/50 animate-ping" />
        )}
        <span
          className={`[&>svg]:h-4 [&>svg]:w-4 ${conversationRequested ? "text-signal-ok animate-pulse" : "opacity-70"}`}
        >
          <IconConversation />
        </span>
        {conversationRequested ? t("chat.conversationActive") : t("hub.conversation")}
        <kbd className="ml-1 px-1.5 py-0.5 rounded border border-base-700/70 text-[9px] text-ink-faint">space</kbd>
      </button>
    </div>
  );
}
