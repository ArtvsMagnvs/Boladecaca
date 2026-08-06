// Dock.tsx — Navegación en botones SUELTOS (PU6a-bis, doc 35 §PU6).
//
// Sustituye a `BottomBar.tsx`, que era una barra continua "tipo Windows".
// Ahora no hay barra: los botones flotan sobre el AVCS, centrados bajo la
// semilla. Geometría pedida por el usuario, literal: *"donde termina ahora
// la parte superior de la barra debería ser la altura del CENTRO de los
// botones sueltos"*. Esa barra medía 64px de alto, así que el CENTRO de los
// círculos va a 64px del borde inferior — con círculos de 52px, eso es
// `bottom: 38px` (≈1cm en pantalla estándar, dentro del "1 a 1,5 cm" que se
// pidió).
//
// Reparto de las tres zonas:
//   · centro  — los 4 destinos + Inicio (el logo/semilla abre el Hub)
//   · izquierda inferior — Configuración, "aparte" como pidió el usuario
//   · derecha inferior   — Modo Presencia (vive en PresenceToggle.tsx)
// Antes, Configuración estaba en el extremo derecho de la barra y el botón
// de Modo Presencia le caía justo encima, tapándolo: ese era el fallo (2)
// reportado. Separarlos a esquinas opuestas lo cierra por construcción, no
// con un ajuste de z-index.
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppStore } from "@/store/useAppStore";
import { usePolling } from "@/hooks/usePolling";
import { api, type Approval } from "@/lib/api";
import { shortRef } from "@/lib/modelNames";
import { useT } from "@/store/useI18n";
import { DockButton } from "./DockButton";
import {
  IconCalendar,
  IconEmail,
  IconHome,
  IconLearning,
  IconMissionControl,
  IconSettings,
  IconWorkspace,
} from "./DockIcons";

export function Dock() {
  const location = useLocation();
  const navigate = useNavigate();
  const t = useT();
  const presenceMode = useAppStore((s) => s.presenceMode);
  const backendConnected = useAppStore((s) => s.backendConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const chatPrimary = useAppStore((s) => s.chatPrimary);
  const chatPrimaryDown = useAppStore((s) => s.chatPrimaryDown);
  const refreshBackendStatus = useAppStore((s) => s.refreshBackendStatus);
  const refreshAIStatus = useAppStore((s) => s.refreshAIStatus);

  // Cuentas de lo que necesita atención, visibles desde CUALQUIER página —
  // antes vivían solo en las tarjetas del Hub. Un único sondeo de 30s
  // (visibility-aware) con `.catch()` independiente por llamada: que el
  // correo no esté conectado no debe dejar sin badge a las aprobaciones.
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [urgentEmails, setUrgentEmails] = useState(0);
  const [workspaceAlerts, setWorkspaceAlerts] = useState(0);
  // [V1.1 L4] Lo que el Learner tiene esperando una decisión.
  const [pendingLearning, setPendingLearning] = useState(0);

  usePolling(() => {
    refreshBackendStatus();
    refreshAIStatus();
    api
      .getApprovals()
      .then((list: Approval[]) => setPendingApprovals(list.filter((a) => a.status === "pending").length))
      .catch(() => setPendingApprovals(0));
    api
      .getDigest()
      .then((d) => setUrgentEmails(d.urgent_pending))
      .catch(() => setUrgentEmails(0));
    api
      .getMemoryBriefing()
      .then((b) =>
        setWorkspaceAlerts((b.workspace?.upcoming_deadlines.length ?? 0) + (b.workspace?.blocked.length ?? 0)),
      )
      .catch(() => setWorkspaceAlerts(0));
    api
      .getLearnerProposals()
      .then((r) => setPendingLearning(r.waiting_for_you))
      .catch(() => setPendingLearning(0));
  }, 30000);

  const go = (to: string) => () => navigate(to);
  const at = (to: string) => location.pathname === to;

  // Plegado en Modo Presencia: mismo gesto que tenía la barra, ahora hacia
  // abajo. `pointer-events-none` además de `opacity-0` para que un botón
  // invisible no siga capturando clics sobre el AVCS.
  const hidden = presenceMode
    ? "opacity-0 translate-y-6 pointer-events-none"
    : "opacity-100 translate-y-0";

  return (
    <>
      {/* ── Fila central de botones sueltos ──────────────────────────────
          [PU6a-bis v2] Círculos de 62px (+20%) y más aire entre ellos
          (gap-7). El CENTRO de los círculos sigue clavado a 64px del borde
          (la altura donde terminaba la barra vieja): 64 − 62/2 = 33px. */}
      <div
        className={`fixed left-1/2 -translate-x-1/2 bottom-[33px] z-30 flex items-center gap-7 transition-all duration-[400ms] ease-out ${hidden}`}
      >
        <DockButton icon={<IconHome />} label={t("nav.hub")} onClick={go("/")} active={at("/")} />
        <DockButton
          icon={<IconMissionControl />}
          label={t("nav.missionControl")}
          onClick={go("/missions")}
          active={at("/missions")}
          badge={pendingApprovals}
          badgeTone="error"
        />
        <DockButton
          icon={<IconLearning />}
          label={t("nav.learning")}
          onClick={go("/learning")}
          active={at("/learning")}
          badge={pendingLearning}
          badgeTone="warn"
        />
        <DockButton
          icon={<IconWorkspace />}
          label={t("nav.workspace")}
          onClick={go("/workspace")}
          active={at("/workspace")}
          badge={workspaceAlerts}
          badgeTone="warn"
        />
        <DockButton
          icon={<IconEmail />}
          label={t("nav.email")}
          onClick={go("/email")}
          active={at("/email")}
          badge={urgentEmails}
          badgeTone="error"
        />
        <DockButton
          icon={<IconCalendar />}
          label={t("nav.calendar")}
          onClick={go("/calendar")}
          active={at("/calendar")}
        />
      </div>

      {/* ── Esquina inferior izquierda: Configuración + estado del MEL ────
          Mismo centro (64px) que la fila: 64 − 46/2 = 41px. La esquina
          derecha es del botón de Modo Presencia (PresenceToggle, mismo
          diseño y misma altura). */}
      <div
        className={`fixed left-5 bottom-[41px] z-30 flex items-center gap-3 transition-all duration-[400ms] ease-out ${hidden}`}
      >
        <DockButton
          icon={<IconSettings />}
          label={t("nav.settings")}
          onClick={go("/settings")}
          active={at("/settings")}
          size={46}
          labelAlign="left"
        />
        {/* MEL-UI (§25): el modelo que de verdad lleva el chat + su breaker.
            Obligatorio conservarlo visible; solo cambia de sitio. */}
        {chatPrimary ? (
          <div
            className={`hidden md:flex items-center gap-1.5 text-[11px] ${chatPrimaryDown ? "text-signal-warn" : "text-ink-faint"}`}
            title={
              chatPrimaryDown
                ? t("hub.status.chatFailing", { model: shortRef(chatPrimary) })
                : t("hub.status.chatActive", { model: shortRef(chatPrimary) })
            }
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                backendConnected ? (chatPrimaryDown ? "bg-signal-warn" : "bg-signal-ok") : "bg-signal-error"
              }`}
            />
            {shortRef(chatPrimary)}
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-1.5 text-[11px] text-ink-faint">
            <span className={`h-1.5 w-1.5 rounded-full ${backendConnected ? "bg-signal-ok" : "bg-signal-error"}`} />
            {aiStatus?.provider ?? (backendConnected ? t("common.connected") : t("common.connecting"))}
          </div>
        )}
      </div>
    </>
  );
}
