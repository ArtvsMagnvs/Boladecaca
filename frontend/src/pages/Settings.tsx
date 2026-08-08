// FIX V0.2: Página de Configuración completamente reescrita.
// Ahora incluye formulario para introducir API keys directamente desde la UI,
// sin necesidad de editar el .env ni llamar a la API manualmente.
// V0.6 (Fase 3 Memory System): nueva seccion "Memoria" con stats, gestion
// de preferencias del usuario y borrado del historial de ChromaDB.
import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, type AIProviderEntry, type ContextItem, type ProfileFact, type MemoryStats, type TelegramStatus, type SearchStatus, type SearchProviderStatus, type BrowserMode, type ElevenLabsCfgStatus, type PermissionCatalog, type MelPolicy, type MelModel, type MelOverride, type LocalModelCatalog } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { QualityTier } from "@/avcs";
import { Toggle } from "@/components/Toggle";
import Modal from "@/components/Modal";
import LanguageSelector from "@/components/LanguageSelector";
import { usePolling } from "@/hooks/usePolling";
import { useThemeStore } from "@/store/useThemeStore";
// [I18N-2] Alias `tr` (no `t`): el archivo ya usa `t` como variable de closure
// en varios `.map((t) => …)` — evita sombrear/confundir.
import { useT } from "@/store/useI18n";
// [2026-07-21] TODO el antiguo Centro de Voz vive ahora aquí (pestaña Voz).
import VoicePanel from "@/components/voice/VoicePanel";
import CodexSetup from "@/components/settings/CodexSetup";
// [PU4b] Pestaña Briefing (secciones/horarios/noticias del briefing 2.0).
import BriefingPanel from "@/components/settings/BriefingPanel";
import McpPanel from "@/components/settings/McpPanel";
import { shortRef } from "@/lib/modelNames";
import { PROVIDER_AUTH_HELP } from "@/data/providerAuthHelp";

// [O2] Pestañas del panel de Ajustes. Agrupan las secciones en dominios para
// que el usuario encuentre cada cosa de un vistazo, en vez de un scroll
// interminable a pantalla completa.
// [2026-07-21, reorganización pedida por el usuario]:
// - "Voz" absorbe TODO el antiguo Centro de Voz (voces, proveedor TTS,
//   personalidad, volumen) — nada de config dispersa fuera de Ajustes.
// - "HUB Visual" (nueva): Apariencia (tema claro/oscuro) + Presencia visual
//   (partículas del AVCS) — antes repartidas entre Sistema y Voz.
// - "Sistema" gana el panel informativo del escáner de hardware (CPU/GPU/RAM).
const SETTINGS_TABS = [
  { id: "ia", labelKey: "settings.tab.ia" },
  // [C1c, petición del usuario 2026-08-08] Los servicios externos (MCP) salen
  // de «Conexiones» a su propia pestaña, aquí: justo debajo de IA y Modelos y
  // encima de Permisos — es donde el usuario los busca, y ya no es un rincón.
  { id: "mcp", labelKey: "settings.tab.mcp" },
  { id: "permisos", labelKey: "settings.tab.permisos" },
  { id: "voz", labelKey: "settings.tab.voz" },
  // [PU4b, doc 35] Briefing: secciones, horarios (N al día) y noticias.
  { id: "briefing", labelKey: "settings.tab.briefing" },
  { id: "hub", labelKey: "settings.tab.hub" },
  { id: "conexiones", labelKey: "settings.tab.conexiones" },
  { id: "memoria", labelKey: "settings.tab.memoria" },
  { id: "sistema", labelKey: "settings.tab.sistema" },
] as const;
type SettingsTab = (typeof SETTINGS_TABS)[number]["id"];

/**
 * AVCS S3 (doc 13 §16 PerformanceManager v0): selector manual de tier de
 * calidad Q1-Q3 ("tiers manuales Q1-Q3" — Q4 queda fuera de Fase 0, es el
 * nivel "equipos gaming"). Escribe en el store (persistido en localStorage,
 * ver useAppStore.setAvcsTier) y AitheraPresence lo aplica EN VIVO sin
 * recargar — la escalera dinámica sigue pudiendo degradar/subir por encima
 * de este punto de partida.
 */
// [2026-07-21] Las 4 opciones de partículas del núcleo visual (AVCS), con su
// significado real. Q4 es el máximo (antes oculto).
// [I18N-7] Claves i18n en vez de literales — labelKey/particlesKey/hintKey.
const TIER_INFO: Record<QualityTier, { labelKey: string; particlesKey: string; hintKey: string }> = {
  Q2: { labelKey: "settings.hub.avcs.q2.label", particlesKey: "settings.hub.avcs.q2.particles", hintKey: "settings.hub.avcs.q2.hint" },
  Q3: { labelKey: "settings.hub.avcs.q3.label", particlesKey: "settings.hub.avcs.q3.particles", hintKey: "settings.hub.avcs.q3.hint" },
  Q4: { labelKey: "settings.hub.avcs.q4.label", particlesKey: "settings.hub.avcs.q4.particles", hintKey: "settings.hub.avcs.q4.hint" },
};

const TIER_ORDER: QualityTier[] = ["Q2", "Q3", "Q4"];

function AvcsPerformanceSettings() {
  const tr = useT();
  const avcsTier = useAppStore((s) => s.avcsTier);
  const setAvcsTier = useAppStore((s) => s.setAvcsTier);
  // [2026-07-21] Recomendación por hardware: marca el nivel óptimo para ESTE PC
  // y avisa en los que podrían ir justos. Fail-soft: sin dato, no avisa.
  const [recTier, setRecTier] = useState<QualityTier | null>(null);
  const [hwWhy, setHwWhy] = useState<string>("");

  useEffect(() => {
    api.getHardwareRecommendation()
      .then((r) => { setRecTier(r.avcs.recommended_tier as QualityTier); setHwWhy(r.avcs.why); })
      .catch(() => { /* sin scanner: sin recomendación, todo sigue funcionando */ });
  }, []);

  const recIdx = recTier ? TIER_ORDER.indexOf(recTier) : -1;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-ink-dim mb-1">
        {tr("settings.hub.avcs.intro")}
      </p>
      {TIER_ORDER.map((t) => {
        const active = avcsTier === t;
        const isRec = recTier === t;
        const tooHigh = recIdx >= 0 && TIER_ORDER.indexOf(t) > recIdx;
        return (
          <button
            key={t}
            type="button"
            onClick={() => setAvcsTier(t)}
            className={`text-left px-3 py-2 rounded-lg border text-xs transition-colors ${
              active ? "bg-accent/15 text-accent border-accent/30"
                     : "bg-base-700 text-ink-dim border-base-600 hover:bg-base-600"
            }`}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium">{tr(TIER_INFO[t].labelKey)}</span>
              <span className="opacity-70">· {tr(TIER_INFO[t].particlesKey)}</span>
              {isRec && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
                  {tr("settings.hub.avcs.recommended")}
                </span>
              )}
              {tooHigh && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-warn/15 text-signal-warn">
                  {tr("settings.hub.avcs.tooHigh")}
                </span>
              )}
            </div>
            <p className="opacity-60 mt-0.5">{tr(TIER_INFO[t].hintKey)}</p>
          </button>
        );
      })}
      {hwWhy && <p className="text-[10px] text-ink-faint mt-1">{tr("settings.hub.avcs.detected", { why: hwWhy })}</p>}
      <p className="text-[10px] text-ink-faint">
        {tr("settings.hub.avcs.autoAdjust")}
      </p>
    </div>
  );
}

/**
 * [2026-07-21] Panel INFORMATIVO del escáner de hardware (Ajustes → Sistema):
 * qué CPU/GPU/RAM ha detectado Aithera y qué recomienda con ello (modelo local
 * y nivel del núcleo visual). Solo lectura — los cambios se hacen en sus
 * secciones (IA y Modelos / HUB Visual).
 */
function SystemScanPanel() {
  const tr = useT();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.getHardwareRecommendation>> | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.getHardwareRecommendation().then(setData).catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="text-xs text-ink-faint">{tr("settings.sistema.scan.failed")}</p>;
  if (!data) return <p className="text-xs text-ink-faint">{tr("settings.sistema.scan.scanning")}</p>;

  const hw = data.hardware;
  const rows: { label: string; value: string }[] = [
    {
      label: "CPU",
      value: hw.cpu.name
        ? `${hw.cpu.name}${hw.cpu.cores ? ` · ${tr("settings.sistema.scan.cores", { n: hw.cpu.cores })}` : ""}`
        : hw.cpu.cores ? `${tr("settings.sistema.scan.cores", { n: hw.cpu.cores })} / ${tr("settings.sistema.scan.threads", { n: hw.cpu.threads ?? "?" })}` : "—",
    },
    {
      label: "GPU",
      value: hw.gpu.present
        ? `${hw.gpu.name ?? tr("settings.sistema.scan.dedicatedGpu")}${hw.gpu.vram_gb ? ` · ${hw.gpu.vram_gb} GB VRAM` : ""}`
        : tr("settings.sistema.scan.noGpu"),
    },
    { label: "RAM", value: hw.ram_gb ? `${hw.ram_gb} GB` : "—" },
    {
      label: tr("settings.sistema.scan.usableMemory"),
      value: hw.usable_model_gb
        ? `~${hw.usable_model_gb} GB (${hw.gpu.present ? tr("settings.sistema.scan.gpuVram") : tr("settings.sistema.scan.systemRam")})`
        : "—",
    },
  ];

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {rows.map((r) => (
          <div key={r.label} className="bg-base-900/40 rounded-lg p-2.5">
            <p className="text-[10px] text-ink-faint uppercase tracking-wider">{r.label}</p>
            <p className="text-xs text-ink mt-0.5">{r.value}</p>
          </div>
        ))}
      </div>
      <div className="text-[11px] text-ink-dim mt-1 space-y-1">
        {data.ollama.optimal && (
          <p>
            • {tr("settings.sistema.scan.recommendedModel")} <b className="text-ink">{data.ollama.optimal.label}</b>{" "}
            ({data.ollama.optimal.size_gb} GB) — {tr("settings.sistema.scan.installsAt")} <b>{tr("settings.tab.ia")}</b>.
          </p>
        )}
        <p>
          • {tr("settings.sistema.scan.recommendedTier")} <b className="text-ink">{data.avcs.recommended_tier}</b> — {tr("settings.sistema.scan.adjustsAt")}
          <b> {tr("settings.tab.hub")}</b>.
        </p>
      </div>
    </div>
  );
}


/**
 * V0.7 (Fase 4 Email + Calendar): sub-componente que permite configurar
 * client_id / client_secret de Google OAuth y conectar/desconectar la cuenta.
 *
 * V0.7 extra (refactor tras queja del usuario):
 * - Acepta credenciales de DOS fuentes: .env (GOOGLE_CLIENT_ID/SECRET) o BD.
 * - El formulario de "pegar claves" SOLO aparece si NO hay credenciales.
 * - Si las credenciales vienen del .env, se indica claramente para que el
 *   usuario sepa que NO hace falta pegarlas aqui.
 * - Las instrucciones paso a paso se muestran SIEMPRE que no este conectado.
 */
function EmailGoogleStatus() {
  const tr = useT();
  const [emailStatus, setEmailStatus] = useState<{
    connected: boolean;
    email: string | null;
    has_credentials: boolean;
    libs_available: boolean;
    credentials_source: "env" | "db" | "none";
    // AUTH-1: distingue caducado/revocado/offline de "nunca conectado".
    connection_state?: "connected" | "expired" | "revoked" | "no_token" | "no_credentials" | "libs_missing";
  } | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const refresh = async () => {
    try {
      const s = await api.getEmailStatus();
      // Backend puede no devolver credentials_source si es muy viejo.
      // Lo anadimos con default "none" para que TS este contento.
      setEmailStatus({
        credentials_source: "none",
        ...s,
      });
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const saveCredentials = async () => {
    if (!clientId.trim() || !clientSecret.trim()) {
      setMsg({ kind: "err", text: tr("connections.googleHelp.credsRequired") });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      await api.saveEmailCredentials({
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
      });
      setMsg({
        kind: "ok",
        text: tr("connections.googleHelp.credsSaved"),
      });
      setClientSecret("");
      setClientId("");
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("agents.error.save", { msg: (e as Error).message }) });
    } finally {
      setSaving(false);
    }
  };

  const connect = async () => {
    setConnecting(true);
    setMsg(null);
    try {
      const r = await api.startEmailOAuth();
      setMsg({ kind: "ok", text: tr("connections.googleHelp.connectedOk", { email: r.email || "Google account" }) });
      refresh();
    } catch (e) {
      const errMsg = (e as Error).message;
      if (errMsg.includes("Falta configurar")) {
        setMsg({
          kind: "err",
          text: tr("connections.googleHelp.noCredsYet"),
        });
      } else {
        setMsg({ kind: "err", text: tr("connections.googleHelp.errConnect", { msg: errMsg }) });
      }
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async () => {
    if (!confirm(tr("connections.googleHelp.disconnectConfirm"))) return;
    try {
      await api.disconnectEmail();
      setMsg({ kind: "ok", text: tr("connections.googleHelp.disconnected") });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("connections.googleHelp.errDisconnect", { msg: (e as Error).message }) });
    }
  };

  const clearDbCredentials = async () => {
    if (!confirm(tr("connections.googleHelp.clearDbConfirm"))) return;
    try {
      // Reutilizamos saveClientCredentials pasando strings vacios NO funciona,
      // asi que usamos un endpoint DELETE directo.
      const r = await fetch("/api/email/auth/credentials", { method: "DELETE" });
      if (r.ok) {
        setMsg({ kind: "ok", text: tr("connections.googleHelp.dbCleared") });
      }
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("agents.error.delete", { msg: (e as Error).message }) });
    }
  };

  const source = emailStatus?.credentials_source || "none";
  const sourceLabel = tr(`connections.googleHelp.source.${source}`);
  // AUTH-1: la sesión caducó (revocada o fallo transitorio) pero SÍ hay
  // credenciales -> ofrecemos "Volver a conectar" en vez del genérico.
  const cstate = emailStatus?.connection_state;
  const needsReconnect = cstate === "revoked" || cstate === "expired";

  return (
    <div className="space-y-3">
      {/* Estado + boton principal */}
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-ink-dim min-w-0 flex-1">
          {emailStatus?.connected ? (
            <>
              <span className="text-signal-ok">●</span> {tr("email.connectedAs")}{" "}
              <span className="text-ink font-medium">{emailStatus.email}</span>
            </>
          ) : cstate === "revoked" ? (
            // AUTH-1: el refresh_token ya no vale -> hay que reconectar (un clic).
            <>
              <span className="text-amber-400 light:text-amber-700">●</span>{" "}
              <span className="text-amber-300 light:text-amber-800">{tr("connections.googleHelp.sessionRevoked")}</span>
            </>
          ) : cstate === "expired" ? (
            // AUTH-1: fallo transitorio (sin internet) -> se reintenta solo.
            <>
              <span className="text-amber-400 light:text-amber-700">●</span>{" "}
              {tr("connections.googleHelp.offlineRetry")}
            </>
          ) : emailStatus?.has_credentials ? (
            <>
              <span className="text-amber-400 light:text-amber-700">●</span>{" "}
              {tr("connections.googleHelp.credsReady", { source: sourceLabel })}
            </>
          ) : (
            <>
              <span className="text-ink-faint">●</span>{" "}
              <span className="text-ink-faint">{tr("connections.googleHelp.noCreds")}</span>
            </>
          )}
          {emailStatus && !emailStatus.libs_available && (
            <div className="mt-1 text-signal-error">
              {tr("connections.googleHelp.libsMissing")}
            </div>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {!emailStatus?.connected && (
            <button
              onClick={connect}
              disabled={connecting || !emailStatus?.has_credentials}
              title={
                !emailStatus?.has_credentials
                  ? tr("connections.googleHelp.needCredsFirst")
                  : tr("connections.googleHelp.connectTitle")
              }
              className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {connecting
                ? tr("connections.googleHelp.openingBrowser")
                : needsReconnect
                  ? tr("connections.googleHelp.reconnect")
                  : tr("email.connect")}
            </button>
          )}
          {emailStatus?.connected && (
            <button
              onClick={disconnect}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              {tr("email.disconnect")}
            </button>
          )}
        </div>
      </div>

      {msg && (
        <p className={`text-xs ${msg.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
          {msg.text}
        </p>
      )}

      {/* Instrucciones + form para pegar credenciales (siempre visible si no hay creds) */}
      {!emailStatus?.connected && (
        <div className="border-t border-base-700/30 pt-3 space-y-3">
          <details className="text-[11px] text-ink-dim">
            <summary className="cursor-pointer hover:text-ink select-none">
              <span className="text-accent">▸</span> {tr("connections.googleHelp.summary")}
            </summary>
            <ol className="mt-2 space-y-2 pl-5 list-decimal text-ink-faint">
              <li>
                {tr("connections.googleHelp.step1a")}{" "}
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline"
                >
                  console.cloud.google.com/apis/credentials
                </a>{" "}
                {tr("connections.googleHelp.step1b")}
              </li>
              <li>{tr("connections.googleHelp.step2")}</li>
              <li>{tr("connections.googleHelp.step3")}</li>
              <li>{tr("connections.googleHelp.step4")}</li>
              <li>{tr("connections.googleHelp.step5")}</li>
              <li>
                {tr("connections.googleHelp.step6a")}{" "}
                <code className="bg-base-950/50 px-1 rounded">http://localhost:8080</code>{" "}
                {tr("connections.googleHelp.step6b")}
              </li>
              <li>
                {tr("connections.googleHelp.step7a")}{" "}
                <a
                  href="https://console.cloud.google.com/apis/library"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline"
                >
                  API Library
                </a>{" "}
                {tr("connections.googleHelp.step7b")}
              </li>
            </ol>
            <p className="mt-2 text-ink-faint text-[10px] italic">
              {tr("connections.googleHelp.note")}
            </p>
          </details>

          {/* Form: pegar credenciales (alternativa a .env) */}
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[10px] text-ink-faint hover:text-ink underline"
            >
              {showAdvanced ? tr("connections.googleHelp.formHide") : tr("connections.googleHelp.formShow")}
            </button>
            {showAdvanced && (
              <div className="mt-2 space-y-2 p-3 rounded-lg bg-base-900/40">
                <p className="text-[10px] text-ink-faint">
                  {tr("connections.googleHelp.envAlt1")}{" "}
                  <code className="bg-base-950/50 px-1 rounded">backend/.env</code>{" "}
                  {tr("connections.googleHelp.envAlt2")}
                  <br />
                  <code className="bg-base-950/50 px-1 rounded mt-1 inline-block">
                    GOOGLE_CLIENT_ID=tu_client_id
                    <br />
                    GOOGLE_CLIENT_SECRET=tu_client_secret
                  </code>
                  <br />
                  {tr("connections.googleHelp.envRestart")}
                </p>
                <input
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder={tr("connections.googleHelp.clientIdPlaceholder")}
                  className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                />
                <input
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  type="password"
                  placeholder="Client Secret"
                  className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                />
                <button
                  onClick={saveCredentials}
                  disabled={saving}
                  className="text-xs px-3 py-1.5 rounded-lg bg-base-800 text-ink border border-base-700 hover:bg-base-700 disabled:opacity-50"
                >
                  {saving ? tr("agents.saving") : tr("connections.googleHelp.saveToDb")}
                </button>
              </div>
            )}
          </div>

          {/* Boton para limpiar credenciales de la BD si las hay */}
          {emailStatus?.has_credentials && source === "db" && (
            <button
              onClick={clearDbCredentials}
              className="text-[10px] text-ink-faint hover:text-signal-error underline"
            >
              {tr("connections.googleHelp.clearDb")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * V0.8 (Fase 5 Clientes): configuracion del bot de Telegram desde Ajustes.
 * El token se guarda CIFRADO en el backend (DPAPI) y NUNCA se devuelve; aqui
 * solo se ve una mascara. Para cambiarlo se escribe uno nuevo; dejarlo vacio
 * conserva el guardado. Los cambios aplican al reiniciar el backend (el
 * polling del canal se monta en el arranque).
 */
/**
 * V1.0/1.1 (Tools, petición del usuario 2026-07-18): Search Tool combina 2
 * proveedores. [2026-07-22, orden del usuario] SerpAPI (Google) se prueba
 * PRIMERO (plan free sin tarjeta, 250 consultas/mes); Brave Search API es el
 * respaldo (su plan free exige vincular tarjeta de crédito, 1.000/mes). Ambos
 * son opcionales e independientes; basta con configurar uno para que funcione.
 */
function SearchProviderCard({
  label, hint, signupUrl, status, onSave, onDelete,
}: {
  label: string; hint: string; signupUrl: string;
  status: SearchProviderStatus | undefined;
  onSave: (key: string) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const tr = useT();
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <div className="rounded-xl p-3 border border-base-700 bg-base-800/40">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-ink">{label}</span>
        {status?.configured ? (
          <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
            {tr("settings.search.configured", { masked: status.key_masked })}
          </span>
        ) : (
          <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-dim">{tr("settings.search.notConfigured")}</span>
        )}
      </div>
      <p className="text-[11px] text-ink-faint mb-2">
        {hint}{" "}
        <a href={signupUrl} target="_blank" rel="noreferrer" className="text-accent underline">
          {tr("settings.search.getKey")}
        </a>.
      </p>
      <div className="flex gap-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          type="password"
          placeholder={status?.configured ? tr("settings.search.newKeyPlaceholder") : tr("settings.search.pasteKeyPlaceholder")}
          className="flex-1 bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <button
          onClick={async () => { setSaving(true); await onSave(key); setKey(""); setSaving(false); }}
          disabled={saving || !key.trim()}
          className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
        >
          {tr("common.save")}
        </button>
        {status?.configured && (
          <button
            onClick={onDelete}
            className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
          >
            {tr("common.delete")}
          </button>
        )}
      </div>
    </div>
  );
}

function SearchSettings() {
  const tr = useT();
  const [status, setStatus] = useState<SearchStatus | null>(null);

  const refresh = async () => {
    try { setStatus(await api.getSearchStatus()); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">
        {tr("settings.search.intro")}
      </p>
      <SearchProviderCard
        label="SerpAPI (Google)"
        hint={tr("settings.search.serpapiHint")}
        signupUrl="https://serpapi.com/manage-api-key"
        status={status?.serpapi}
        onSave={async (k) => { await api.configureSearchProvider("serpapi", k); refresh(); }}
        onDelete={async () => { await api.deconfigureSearchProvider("serpapi"); refresh(); }}
      />
      <SearchProviderCard
        label="Brave Search API"
        hint={tr("settings.search.braveHint")}
        signupUrl="https://api.search.brave.com/register"
        status={status?.brave}
        onSave={async (k) => { await api.configureSearchProvider("brave", k); refresh(); }}
        onDelete={async () => { await api.deconfigureSearchProvider("brave"); refresh(); }}
      />
      <BrowserModeSettings />
    </div>
  );
}

/**
 * [2026-07-23, petición del usuario] Navegador para tareas web: perfil
 * DEDICADO de Aithera (persistente, recomendado) vs el Chrome HABITUAL del
 * usuario (su sesión real, con aviso de riesgo). Mutuamente excluyentes.
 */
function BrowserModeSettings() {
  const tr = useT();
  const [mode, setMode] = useState<BrowserMode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try { setMode((await api.getBrowserMode()).mode); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  const choose = async (next: BrowserMode) => {
    if (next === mode || busy) return;
    setBusy(true); setError(null);
    try { setMode((await api.setBrowserMode(next)).mode); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.browserMode.errChange")); }
    finally { setBusy(false); }
  };

  return (
    <div className="pt-1 space-y-2">
      <div className="pt-2 border-t border-base-700">
        <p className="text-sm font-medium text-ink mb-1">{tr("settings.browserMode.title")}</p>
        <p className="text-xs text-ink-dim mb-2">
          {tr("settings.browserMode.desc")}
        </p>
      </div>
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
      <button
        type="button"
        onClick={() => choose("aithera")}
        disabled={busy}
        className={`w-full text-left rounded-xl p-3 border transition-colors disabled:opacity-60 ${
          mode === "aithera" ? "border-accent/60 bg-accent/10" : "border-base-700 bg-base-800/40 hover:border-base-600"
        }`}
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-ink">{tr("settings.browserMode.aitheraTitle")}</span>
          {mode === "aithera" && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">{tr("common.active")}</span>
          )}
        </div>
        <p className="text-[11px] text-ink-faint">
          {tr("settings.browserMode.aitheraDesc1")}{" "}
          <span className="text-ink-dim">{tr("settings.browserMode.aitheraDescOnce")}</span>{" "}
          {tr("settings.browserMode.aitheraDesc2")}
        </p>
      </button>
      <button
        type="button"
        onClick={() => choose("user")}
        disabled={busy}
        className={`w-full text-left rounded-xl p-3 border transition-colors disabled:opacity-60 ${
          mode === "user" ? "border-signal-warn/60 bg-signal-warn/10" : "border-base-700 bg-base-800/40 hover:border-base-600"
        }`}
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-ink">{tr("settings.browserMode.userTitle")}</span>
          {mode === "user" && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-signal-warn/15 text-signal-warn">{tr("common.active")}</span>
          )}
        </div>
        <p className="text-[11px] text-ink-faint">
          {tr("settings.browserMode.userDesc")}
        </p>
      </button>
    </div>
  );
}

function TelegramSettings() {
  const tr = useT();
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [token, setToken] = useState("");
  const [chatIds, setChatIds] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const refresh = async () => {
    try {
      const s = await api.getTelegramStatus();
      setStatus(s);
      setChatIds(s.allowed_chat_ids.join(", "));
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const ids = chatIds
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      await api.configureTelegram({
        token: token.trim() || undefined, // vacio => conserva el guardado
        chat_ids: ids,
      });
      setToken("");
      setMsg({
        kind: "ok",
        text: tr("connections.telegramHelp.saved"),
      });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("agents.error.save", { msg: (e as Error).message }) });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm(tr("connections.telegramHelp.removeConfirm"))) return;
    try {
      await api.deconfigureTelegram();
      setToken("");
      setMsg({ kind: "ok", text: tr("connections.telegramHelp.removed") });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("agents.error.delete", { msg: (e as Error).message }) });
    }
  };

  return (
    <div className="space-y-3">
      {/* Estado */}
      <div className="text-xs text-ink-dim">
        {status?.running ? (
          <>
            <span className="text-signal-ok">●</span> {tr("connections.telegramHelp.botActive")}
            {status.allowed_chat_ids.length > 0
              ? ` — ${tr("connections.telegramHelp.chatsAuthorized", { n: status.allowed_chat_ids.length })}`
              : ` — ${tr("connections.telegramHelp.noChats")}`}
          </>
        ) : status?.configured ? (
          <>
            <span className="text-amber-400 light:text-amber-700">●</span>{" "}
            {tr("connections.telegramHelp.tokenSavedInactive", { masked: status.token_masked ?? "" })}
          </>
        ) : (
          <>
            <span className="text-ink-faint">●</span> {tr("connections.telegramHelp.notConfigured")}
          </>
        )}
      </div>

      {/* Formulario */}
      <div className="space-y-2">
        <input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          type="password"
          placeholder={
            status?.configured
              ? tr("connections.telegramHelp.tokenKeepPlaceholder")
              : tr("connections.telegramHelp.tokenPlaceholder")
          }
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <input
          value={chatIds}
          onChange={(e) => setChatIds(e.target.value)}
          placeholder={tr("connections.telegramHelp.chatIdsPlaceholder")}
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
          >
            {saving ? tr("agents.saving") : tr("common.save")}
          </button>
          {status?.configured && (
            <button
              onClick={remove}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              {tr("common.delete")}
            </button>
          )}
        </div>
      </div>

      {msg && (
        <p className={`text-xs ${msg.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
          {msg.text}
        </p>
      )}

      {/* Como obtener el chat_id */}
      <details className="text-[11px] text-ink-dim">
        <summary className="cursor-pointer hover:text-ink select-none">
          <span className="text-accent">▸</span> {tr("connections.telegramHelp.summary")}
        </summary>
        <ol className="mt-2 space-y-1.5 pl-5 list-decimal text-ink-faint">
          <li>
            {tr("connections.telegramHelp.step1a")}{" "}
            <a href="https://t.me/BotFather" target="_blank" rel="noreferrer" className="text-accent underline">
              @BotFather
            </a>{" "}
            {tr("connections.telegramHelp.step1b")}
          </li>
          <li>
            {tr("connections.telegramHelp.step2a")}{" "}
            <code className="bg-base-950/50 px-1 rounded">/start</code>
            {tr("connections.telegramHelp.step2b")}
          </li>
          <li>{tr("connections.telegramHelp.step3")}</li>
        </ol>
        <p className="mt-2 text-ink-faint text-[10px] italic">
          {tr("connections.telegramHelp.security")}
        </p>
      </details>
    </div>
  );
}

/**
 * V0.9 (Automation Engine A3b, doc 20 §A3b): Permisos & Autonomía — la capa
 * de política sobre el ApprovalGate (A1). El gate es el mecanismo HITL en
 * tiempo de ejecución; aquí el usuario decide qué se pre-autoriza (pasa
 * directo) y qué sigue preguntando. Selector de perfil rápido arriba
 * (equivalente a "omitir permisos") + toggles individuales agrupados abajo.
 */
const AUTONOMY_PROFILES: Array<{ id: string; labelKey: string; hintKey: string }> = [
  { id: "manual", labelKey: "settings.permisos.profile.manual.label", hintKey: "settings.permisos.profile.manual.hint" },
  { id: "balanced", labelKey: "settings.permisos.profile.balanced.label", hintKey: "settings.permisos.profile.balanced.hint" },
  { id: "full", labelKey: "settings.permisos.profile.full.label", hintKey: "settings.permisos.profile.full.hint" },
];

/**
 * V1.0 (MEL E2/E2b, doc 22 §3): Inteligencia — qué modelo ejecuta cada tipo de
 * tarea. El usuario elige una POLÍTICA (no un modelo); el MEL decide el resto.
 * E2b (petición del usuario, 2026-07-18): además puede PERSONALIZAR el modelo
 * primario por capacidad en Economía/Calidad/Personalizado, con "Restaurar" a
 * los valores por defecto. "Sin conexión" no es editable (es solo-local).
 */
const MEL_POLICY_META_KEYS: Record<string, { labelKey: string; hintKey: string }> = {
  economy: { labelKey: "settings.mel.policy.economy.label", hintKey: "settings.mel.policy.economy.hint" },
  quality: { labelKey: "settings.mel.policy.quality.label", hintKey: "settings.mel.policy.quality.hint" },
  // [2026-07-22, petición del usuario] Políticas MEDIDAS: Aithera sondea cada
  // modelo conectado (latencia real + calidad verificable) y compila con esos
  // números — el usuario no tiene que probar modelos a mano.
  speed: { labelKey: "settings.mel.policy.speed.label", hintKey: "settings.mel.policy.speed.hint" },
  balanced: { labelKey: "settings.mel.policy.balanced.label", hintKey: "settings.mel.policy.balanced.hint" },
  offline: { labelKey: "settings.mel.policy.offline.label", hintKey: "settings.mel.policy.offline.hint" },
  custom: { labelKey: "settings.mel.policy.custom.label", hintKey: "settings.mel.policy.custom.hint" },
};
const MEL_CAP_LABEL_KEYS: Record<string, string> = {
  chat: "settings.mel.cap.chat", classify: "settings.mel.cap.classify", extract: "settings.mel.cap.extract", summarize: "settings.mel.cap.summarize",
  draft: "settings.mel.cap.draft", reason: "settings.mel.cap.reason", code: "settings.mel.cap.code", analyze: "settings.mel.cap.analyze",
  vision: "settings.mel.cap.vision", learn: "settings.mel.cap.learn",
};
// Orden y whitelist de capacidades activas. `research` y `agentic` siguen sin
// mostrarse a propósito: son internas (el auto-catálogo y el bucle de tools las
// piden solas, el usuario no elige modelo para ellas).
// [B·WEB-2, 2026-08-05] `vision` SÍ se muestra: desde que existe `find_and_click`
// es una capacidad que el usuario usa de verdad, y necesita poder ver qué modelo
// la atiende — o enterarse de que no tiene ninguno.
// [LC1, 2026-08-07] `learn` (Aprendizaje) también se muestra: es el modelo que
// juzga si cada misión sirvió y decide qué merece aprenderse. El usuario tiene
// que poder elegirlo — y le conviene un razonador LOCAL, que trabaja de
// madrugada, sin prisa y sin coste.
const MEL_CAPS_ORDER = ["chat", "classify", "extract", "summarize", "draft", "reason", "code", "analyze", "vision", "learn"];
// Capacidades cuyo "sin modelo" merece decir QUÉ hacer en vez de constatar el
// hueco: son las que exigen un modelo con una propiedad concreta (ver imágenes,
// razonar de verdad) y que un catálogo normal puede no tener.
const MEL_CAP_EMPTY_HINT: Record<string, string> = {
  vision: "settings.mel.visionNoModel",
  learn: "settings.mel.learnNoModel",
};
const MEL_POLICY_ORDER = ["economy", "quality", "speed", "balanced", "offline", "custom"];
const MEL_EDITABLE = new Set(["economy", "quality", "speed", "balanced", "custom"]);

// [2026-07-21] Nombres ABREVIADOS compartidos por toda la app (Inteligencia,
// badges, Sidebar, Hub): lib/modelNames.ts — "MiniMax · M3-highspeed",
// "Claude CLI · Opus 4.8", sin repetir la marca en el modelo.

/** [2026-07-21] Mapa "provider:model" → capacidades donde es el PRIMARIO de la
 *  política ACTIVA — la fuente de verdad de los badges de tipo de tarea en las
 *  tarjetas de proveedores (vinculado a Inteligencia, no al legacy is_active). */
function primaryBadges(policies: MelPolicy[] | null): Record<string, string[]> {
  const active = policies?.find((p) => p.is_active);
  const map: Record<string, string[]> = {};
  if (!active) return map;
  for (const cap of MEL_CAPS_ORDER) {
    const chain = active.compiled[cap] || [];
    // [I18N-7] Devuelve la CLAVE de capacidad, no la etiqueta — el llamador
    // (dentro de un componente, con `tr` disponible) resuelve el idioma.
    if (chain.length) (map[chain[0]] ??= []).push(cap);
  }
  return map;
}

/**
 * V1.0 (Modelos locales especializados): instalar con 1 clic los modelos que
 * corren en el PC del usuario, agrupados por su especialidad. El MEL reparte
 * después cada tarea al especialista (Ornith programa, DeepSeek razona…).
 *
 * La marca "recomendado" es una sugerencia curada por tamaño, NO una medición
 * del equipo: el escáner de hardware llega en una actualización futura. Por eso
 * cada tarjeta muestra los GB reales — el dato con el que el usuario decide hoy.
 */
const CATEGORY_ICON: Record<string, string> = {
  runtime: "⚙️", general: "💬", coding: "💻", reasoning: "🧠", vision: "👁️",
};

function LocalModelsSettings() {
  const tr = useT();
  const [catalog, setCatalog] = useState<LocalModelCatalog | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // [2026-07-21] Familias PLEGADAS por defecto (petición del usuario: ver todas
  // las familias sin que cada una despliegue sus 2-3 variantes). Se auto-abre
  // la que tenga una descarga en curso, para que el progreso nunca quede oculto.
  const [expandedFams, setExpandedFams] = useState<Set<string>>(new Set());
  const toggleFam = (family: string) =>
    setExpandedFams((prev) => {
      const next = new Set(prev);
      if (next.has(family)) next.delete(family);
      else next.add(family);
      return next;
    });

  const load = async () => {
    try {
      setCatalog(await api.getLocalCatalog());
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.local.errLoadCatalog"));
    }
  };
  useEffect(() => { load(); }, []);

  // Mientras haya una descarga viva, refresca solo (el progreso vive en el
  // backend). [P1] Pausado con la ventana oculta — la descarga sigue igual en
  // el backend; solo se deja de preguntar por ella.
  const hasActiveJob = (catalog?.families ?? []).some((f) =>
    f.models.some((m) => m.job?.status === "downloading"));
  usePolling(load, 1500, hasActiveJob);

  const install = async (tag: string) => {
    setBusy(tag); setError(null);
    try { await api.installLocalModel(tag); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.local.errStartDownload")); }
    finally { setBusy(null); }
  };
  const cancel = async (tag: string) => {
    try { await api.cancelLocalInstall(tag); await load(); } catch { /* ya terminó */ }
  };
  // [2026-07-21] La ACTIVACIÓN se movió a Proveedores de IA → En tu equipo
  // (LocalProviderModels); aquí solo descarga, cancelación y eliminación.
  const remove = async (tag: string, label: string) => {
    if (!confirm(tr("settings.local.confirmDelete", { label }))) return;
    setBusy(tag);
    try { await api.deleteLocalModel(tag); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.local.errDelete")); }
    finally { setBusy(null); }
  };

  if (!catalog) return <p className="text-xs text-ink-faint">{tr("common.loading")}</p>;

  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-dim">
        {tr("settings.local.intro")}
      </p>

      {!catalog.runtime_ok && (
        <div className="text-xs text-signal-warn bg-signal-warn/10 border border-signal-warn/30 rounded-lg px-3 py-2">
          {tr("settings.local.ollamaDownIntro")}{" "}
          <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="underline">
            {tr("settings.local.installHere")}
          </a>{" "}{tr("settings.local.andReturn")}
        </div>
      )}
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {catalog.families.filter((f) => !f.is_runtime).map((fam) => {
        const installedCount = fam.models.filter((m) => m.installed).length;
        const downloadingFam = fam.models.some((m) => m.job?.status === "downloading");
        const open = expandedFams.has(fam.family) || downloadingFam;
        return (
        <div key={fam.family} className="rounded-xl border border-base-700 bg-base-800/40 p-3">
          {/* Cabecera clicable: pliega/despliega la familia */}
          <button
            type="button"
            onClick={() => toggleFam(fam.family)}
            className="w-full flex items-center gap-2 text-left"
            aria-expanded={open}
          >
            <span>{CATEGORY_ICON[fam.category] ?? "•"}</span>
            <span className="text-sm font-medium text-ink">{fam.label}</span>
            <span className="text-[10px] text-ink-faint">{tr("settings.local.variants", { n: fam.models.length })}</span>
            {installedCount > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
                {tr("settings.local.installedCount", { n: installedCount })}
              </span>
            )}
            {downloadingFam && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent">{tr("settings.local.downloading")}</span>
            )}
            {/* [2026-07-21] Chevron GRANDE (petición del usuario: el "›"
                minúsculo no se veía como desplegable). SVG 22px con trazo
                grueso, rota 90° al abrir. */}
            <span className={`ml-auto text-ink-dim transition-transform duration-150 ${open ? "rotate-90" : ""}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 5 16 12 9 19" />
              </svg>
            </span>
          </button>
          <p className="text-[11px] text-ink-faint mt-0.5 mb-2">{fam.description}</p>

          {open && (
          <div className="space-y-2">
            {fam.models.map((m) => {
              const job = m.job;
              const downloading = job?.status === "downloading";
              return (
                <div key={m.tag} className="rounded-lg border border-base-700/60 bg-base-900/40 p-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-ink">{m.label}</span>
                        <span className="text-[10px] text-ink-faint">{m.size_gb} GB</span>
                        {m.recommended && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent">{tr("settings.local.recommended")}</span>
                        )}
                        {m.installed && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok">{tr("settings.local.installed")}</span>
                        )}
                      </div>
                      <p className="text-[10px] text-ink-faint mt-0.5">{m.notes}</p>
                    </div>

                    <div className="shrink-0 flex items-center gap-1">
                      {!m.installed && !downloading && (
                        <button
                          onClick={() => install(m.tag)}
                          disabled={busy === m.tag || !catalog.runtime_ok}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
                        >
                          {tr("settings.local.install")}
                        </button>
                      )}
                      {downloading && (
                        <button
                          onClick={() => cancel(m.tag)}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600"
                        >
                          {tr("settings.local.cancel")}
                        </button>
                      )}
                      {/* [2026-07-21] Aquí solo DESCARGA y ELIMINACIÓN — la
                          activación vive en Proveedores de IA → En tu equipo.
                          "Eliminar" borra el modelo de Ollama de verdad
                          (DELETE /api/delete): libera los GB del disco. */}
                      {m.installed && (
                        <button
                          onClick={() => remove(m.tag, m.label)}
                          disabled={busy === m.tag}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-signal-error/10 text-signal-error border border-signal-error/30 hover:bg-signal-error/20 disabled:opacity-50"
                          title={tr("settings.local.deleteTitle")}
                        >
                          {busy === m.tag ? tr("settings.local.deleting") : tr("common.delete")}
                        </button>
                      )}
                    </div>
                  </div>

                  {downloading && (
                    <div className="mt-2">
                      <div className="h-1.5 rounded-full bg-base-700 overflow-hidden">
                        <div
                          className="h-full bg-accent transition-all"
                          style={{ width: `${job?.percent ?? 0}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-ink-faint mt-1">
                        {job?.percent ?? 0}%
                        {job?.total_gb ? ` · ${job.downloaded_gb}/${job.total_gb} GB` : ""}
                        {job?.step ? ` · ${job.step}` : ""}
                      </p>
                    </div>
                  )}
                  {job?.status === "failed" && (
                    <p className="text-[10px] text-signal-error mt-1">{job.error}</p>
                  )}
                </div>
              );
            })}
          </div>
          )}
        </div>
        );
      })}
    </div>
  );
}

/**
 * [2026-07-21] "En tu equipo — modelos locales" (Proveedores de IA): un card
 * por MODELO INSTALADO (Qwen3 8B, Llama 3 8B…), cada uno con su interruptor de
 * activación — que escribe en `LocalModel.enabled`, exactamente lo que el MEL
 * lee para decidir qué locales participan en el enrutado. Sin botón
 * "Configurar": un modelo local jamás necesita API key. La DESCARGA vive en
 * "Modelos locales — descarga e instalación"; aquí solo se activa/desactiva.
 */
function LocalProviderModels({ badges }: { badges: Record<string, string[]> }) {
  const tr = useT();
  const [catalog, setCatalog] = useState<LocalModelCatalog | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setCatalog(await api.getLocalCatalog()); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.local.errLoad")); }
  };
  useEffect(() => { load(); }, []);

  const toggle = async (tag: string, enabled: boolean) => {
    setBusy(tag); setError(null);
    try { await api.setLocalModelEnabled(tag, enabled); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.local.errToggle")); }
    finally { setBusy(null); }
  };

  if (!catalog) return <p className="text-xs text-ink-faint">{tr("common.loading")}</p>;

  const installed = catalog.families
    .filter((f) => !f.is_runtime)
    .flatMap((f) => f.models.filter((m) => m.installed).map((m) => ({ ...m, family_label: f.label })));

  return (
    <div className="space-y-2">
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
      {!catalog.runtime_ok && (
        <p className="text-xs text-signal-warn">{tr("settings.local.ollamaDown")}</p>
      )}
      {installed.length === 0 ? (
        <p className="text-xs text-ink-faint">
          {tr("settings.local.noneInstalled")}
        </p>
      ) : (
        installed.map((m) => {
          const modelBadges = badges[`ollama:${m.tag}`] || [];
          return (
            <div key={m.tag} className="rounded-xl border border-base-700/60 bg-base-900/40 p-3 flex items-center justify-between gap-3">
              <div className="min-w-0 flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-ink">{m.label}</span>
                <span className="text-[10px] text-ink-faint">{m.size_gb} GB</span>
                {m.enabled && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok">{tr("common.active")}</span>
                )}
                {modelBadges.map((c) => (
                  <span
                    key={c}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent"
                    title={tr("settings.mel.primaryBadgeTitle", { cap: tr(MEL_CAP_LABEL_KEYS[c] ?? c) })}
                  >
                    {tr(MEL_CAP_LABEL_KEYS[c] ?? c)}
                  </span>
                ))}
              </div>
              <Toggle
                checked={m.enabled}
                onChange={(v) => toggle(m.tag, v)}
                disabled={busy === m.tag || !catalog.runtime_ok}
                label={tr("settings.local.useInRouting", { label: m.label })}
              />
            </div>
          );
        })
      )}
    </div>
  );
}

function IntelligenceSettings() {
  const tr = useT();
  const [policies, setPolicies] = useState<MelPolicy[] | null>(null);
  const [models, setModels] = useState<MelModel[]>([]);
  const [overrides, setOverrides] = useState<MelOverride[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // [2026-07-21] Fallos EN VIVO por proveedor (breakers del MEL): los modelos
  // de un proveedor caído se marcan en rojo con su motivo.
  const [downDetail, setDownDetail] = useState<Record<string, string>>({});

  const load = async () => {
    try {
      const [pols, mods, ovs, health] = await Promise.all([
        api.getMelPolicies(), api.getMelModels(), api.getMelOverrides(),
        api.getMelHealthSummary().catch(() => null),
      ]);
      setPolicies(pols);
      setModels(mods);
      setOverrides(ovs);
      setDownDetail(health?.down_detail ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.mel.errLoadPolicies"));
    }
  };
  // El proveedor de un model_key, y si está fallando ahora mismo.
  const providerOf = (key: string) => key.split(":")[0];
  const failing = (key: string): string | null => downDetail[providerOf(key)] ?? null;
  const FAIL_REASON: Record<string, string> = {
    transient: tr("settings.mel.failReason.transient"),
    unknown: tr("settings.mel.failReason.unknown"),
  };
  // [2026-07-21] ¿Es apto este modelo para esta capacidad? (unfit del backend:
  // p.ej. Claude CLI no sirve para Chat/Clasificar — fallo real de producción).
  const fitFor = (key: string, cap: string): boolean => {
    const m = models.find((x) => x.key === key);
    return !(m?.unfit ?? []).includes(cap);
  };

  const deleteOverride = async (id: number) => {
    setBusy(true); setError(null);
    try { await api.deleteMelOverride(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.mel.errDeletePin")); }
    finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);

  const activate = async (name: string) => {
    setBusy(true); setError(null);
    try { await api.setActiveMelPolicy(name); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.mel.errChangePolicy")); }
    finally { setBusy(false); }
  };

  const setPrimary = async (name: string, cap: string, modelKey: string | null) => {
    setBusy(true); setError(null);
    try { await api.setMelPolicyPrimary(name, cap, modelKey); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.mel.errChangeModel")); }
    finally { setBusy(false); }
  };

  // [2026-07-21] Edita un RESPALDO concreto (posiciones 1-3; la 4ª solo local).
  const setSlot = async (name: string, cap: string, position: number, modelKey: string) => {
    if (!modelKey) return;
    setBusy(true); setError(null);
    try { await api.setMelPolicySlot(name, cap, position, modelKey); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.mel.errChangeBackup")); }
    finally { setBusy(false); }
  };

  const restore = async (name: string) => {
    setBusy(true); setError(null);
    try { await api.restoreMelPolicy(name); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : tr("settings.mel.errRestore")); }
    finally { setBusy(false); }
  };

  if (!policies) return <p className="text-xs text-ink-faint">{tr("common.loading")}</p>;

  // [2026-07-21] Etiqueta ABREVIADA de un model_key ("Claude CLI · Opus 4.8",
  // "Local · qwen3:8b") — los nombres completos hacían las cadenas ilegibles.
  const modelLabel = (key: string) => shortRef(key);

  // Solo modelos LOCALES: opciones válidas del último eslabón (4ª posición).
  const localModels = models.filter((m) => m.is_local);

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">
        {tr("settings.mel.intro")}
      </p>
      {/* [2026-07-22, orden del usuario] Aviso de la regla de fiabilidad. */}
      <p className="text-[11px] text-ink-faint bg-base-800/40 border border-base-700 rounded-lg px-3 py-2">
        🛡 {tr("settings.mel.reliabilityNote")}
      </p>
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
      {/* [2026-07-21] Panel simple e informativo de FALLOS: qué proveedores
          están fallando ahora mismo y por qué. Los modelos afectados se ven
          además en rojo dentro de cada cadena. */}
      {Object.keys(downDetail).length > 0 && (
        <div className="text-xs bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          <p className="font-medium text-signal-error mb-0.5">⚠ {tr("settings.mel.problemsNow")}</p>
          {Object.entries(downDetail).map(([prov, reason]) => (
            <p key={prov} className="text-signal-error/90">
              • {shortRef(prov)} — {FAIL_REASON[reason] ?? reason}. {tr("settings.mel.fallsBackAuto")}
            </p>
          ))}
        </div>
      )}
      {policies
        .slice()
        .sort((a, b) => MEL_POLICY_ORDER.indexOf(a.name) - MEL_POLICY_ORDER.indexOf(b.name))
        .map((p) => {
        const metaKeys = MEL_POLICY_META_KEYS[p.name];
        const meta = metaKeys ? { label: tr(metaKeys.labelKey), hint: tr(metaKeys.hintKey) } : { label: p.name, hint: "" };
        const isOpen = expanded === p.name;
        const isEditing = editing === p.name;
        const canEdit = MEL_EDITABLE.has(p.name);
        return (
          <div
            key={p.name}
            className={`rounded-xl p-3 border ${p.is_active ? "border-accent/50 bg-accent/5" : "border-base-700 bg-base-800/40"}`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink">{meta.label}</span>
                  {p.is_active && <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">{tr("settings.mel.policyActive")}</span>}
                  {canEdit && !p.pristine && <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-dim">{tr("settings.mel.policyEdited")}</span>}
                </div>
                <p className="text-[11px] text-ink-faint mt-0.5">{meta.hint}</p>
              </div>
              {!p.is_active && (
                <button
                  onClick={() => activate(p.name)}
                  disabled={busy}
                  className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
                >
                  {tr("settings.mel.useThis")}
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => { setExpanded(isOpen ? null : p.name); setEditing(null); }}
                className="text-[10px] text-accent hover:underline"
              >
                {isOpen ? tr("settings.mel.hideDetail") : tr("settings.mel.showDetail")}
              </button>
              {canEdit && (
                <button
                  onClick={() => { setEditing(isEditing ? null : p.name); setExpanded(p.name); }}
                  className="text-[10px] text-accent hover:underline"
                >
                  {isEditing ? tr("settings.mel.finishEditing") : tr("settings.mel.customize")}
                </button>
              )}
              {canEdit && !p.pristine && (
                <button
                  onClick={() => restore(p.name)}
                  disabled={busy}
                  className="text-[10px] text-signal-warn hover:underline disabled:opacity-50"
                >
                  {tr("settings.mel.restore")}
                </button>
              )}
            </div>

            {isOpen && (
              <div className="mt-2 space-y-1">
                {MEL_CAPS_ORDER.filter((cap) => cap in p.compiled).map((cap) => {
                  const chain = p.compiled[cap] || [];
                  return (
                    <div key={cap} className="flex items-center justify-between gap-2 text-[11px] py-1 border-b border-base-700/40">
                      <span className="text-ink-dim shrink-0 w-24">{tr(MEL_CAP_LABEL_KEYS[cap] ?? cap)}</span>
                      {isEditing ? (
                        // [2026-07-21] Las 4 posiciones editables: 1º principal,
                        // 2º-3º respaldos, 4º ÚLTIMO RECURSO (solo modelos
                        // locales — se asume que todo lo demás o la conexión
                        // ha fallado). Petición directa del usuario.
                        <div className="flex items-center gap-1 flex-1 justify-end flex-wrap">
                          {[0, 1, 2, 3].map((pos) => {
                            const isLast = pos === 3;
                            // Solo modelos APTOS para esta capacidad (unfit fuera).
                            const opts = (isLast ? localModels : models)
                              .filter((m) => !(m.unfit ?? []).includes(cap));
                            const value = chain[pos] ?? "";
                            return (
                              <select
                                key={pos}
                                value={value}
                                disabled={busy || (isLast && localModels.length === 0)}
                                onChange={(e) =>
                                  pos === 0
                                    ? setPrimary(p.name, cap, e.target.value || null)
                                    : setSlot(p.name, cap, pos, e.target.value)
                                }
                                className="bg-base-900 border border-base-600 rounded px-1.5 py-1 text-ink text-[10px] max-w-[130px]"
                                title={pos === 0 ? tr("settings.mel.slot.primary") : isLast ? tr("settings.mel.slot.lastResort") : tr("settings.mel.slot.backup", { n: pos })}
                              >
                                {pos === 0 && <option value="">{tr("settings.mel.slot.auto")}</option>}
                                {pos !== 0 && !value && <option value="">—</option>}
                                {pos !== 0 && value && !opts.some((m) => m.key === value) && (
                                  <option value={value}>
                                    {fitFor(value, cap) ? shortRef(value) : `⛔ ${shortRef(value)} (${tr("settings.mel.slot.notFit")})`}
                                  </option>
                                )}
                                {opts.map((m) => (
                                  <option key={m.key} value={m.key}>
                                    {failing(m.key) ? `⚠ ${shortRef(m.key)} (${tr("settings.mel.slot.failing")})` : shortRef(m.key)}
                                  </option>
                                ))}
                              </select>
                            );
                          })}
                        </div>
                      ) : (
                        <span className={`text-ink-faint ml-2 text-right ${
                          // El aviso de visión/aprendizaje sin modelo es una frase
                          // entera: se deja envolver (sin `truncate`) o quedaría
                          // en "…".
                          chain.length === 0 && MEL_CAP_EMPTY_HINT[cap] ? "" : "truncate"
                        }`}>
                          {/* [B·WEB-2 · LC1] En visión y aprendizaje, "sin modelo"
                              no es informativo: lo que el usuario necesita saber
                              es QUÉ hacer para tenerlo. */}
                          {chain.length === 0 && MEL_CAP_EMPTY_HINT[cap] && (
                            <span className="text-signal-warn">
                              {tr(MEL_CAP_EMPTY_HINT[cap])}
                            </span>
                          )}
                          {chain.length === 0 && !MEL_CAP_EMPTY_HINT[cap] && tr("settings.mel.noModel")}
                          {chain.map((k, i) => (
                            <span key={`${k}-${i}`} className={i > 0 ? "opacity-60" : undefined}>
                              {i > 0 && " → "}
                              <span
                                className={
                                  failing(k) ? "text-signal-error font-medium"
                                  : !fitFor(k, cap) ? "text-signal-warn line-through"
                                  : undefined
                                }
                                title={
                                  failing(k) ? tr("settings.mel.failingNow", { reason: FAIL_REASON[failing(k)!] ?? failing(k) })
                                  : !fitFor(k, cap) ? tr("settings.mel.notFitTitle")
                                  : undefined
                                }
                              >
                                {failing(k) && "⚠ "}
                                {!fitFor(k, cap) && "⛔ "}
                                {modelLabel(k)}
                              </span>
                            </span>
                          ))}
                        </span>
                      )}
                    </div>
                  );
                })}
                {isEditing && (
                  // [2026-07-21] Destacado (petición del usuario: no se veía y
                  // es importante): cuerpo mayor + negritas + marco propio.
                  <div className="text-xs text-ink bg-accent/10 border border-accent/30 rounded-lg px-3 py-2 mt-1.5 leading-relaxed">
                    {tr("settings.mel.editHint")}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Pines de modelo por proyecto (override explícito, E2b) — borrables */}
      {overrides.length > 0 && (
        <div className="rounded-xl p-3 border border-base-700 bg-base-800/40">
          <p className="text-xs font-medium text-ink mb-1">{tr("settings.mel.overrides.title")}</p>
          <p className="text-[11px] text-ink-faint mb-2">
            {tr("settings.mel.overrides.desc")}
          </p>
          <div className="space-y-1">
            {overrides.map((o) => (
              <div key={o.id} className="flex items-center justify-between text-[11px] py-1 border-b border-base-700/40">
                <span className="text-ink-dim">
                  {tr("settings.mel.overrides.project", { id: o.project_id })}
                  {o.capability && <span className="text-ink-faint"> · {tr(MEL_CAP_LABEL_KEYS[o.capability] ?? o.capability)}</span>}
                  <span className="text-ink-faint"> → {o.model_id.split(":")[0]}</span>
                </span>
                <button
                  onClick={() => deleteOverride(o.id)}
                  disabled={busy}
                  className="text-signal-warn hover:underline disabled:opacity-50"
                >
                  {tr("common.delete")}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PermissionsSettings() {
  const tr = useT();
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [busyProfile, setBusyProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setCatalog(await api.getPermissions());
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.permisos.errLoad"));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (id: string, enabled: boolean) => {
    setBusyId(id);
    setError(null);
    try {
      setCatalog(await api.setPermission(id, enabled));
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.permisos.errToggle"));
    } finally {
      setBusyId(null);
    }
  };

  const applyProfile = async (profile: string) => {
    setBusyProfile(true);
    setError(null);
    try {
      setCatalog(await api.setAutonomyProfile(profile));
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("settings.permisos.errProfile"));
    } finally {
      setBusyProfile(false);
    }
  };

  if (!catalog) {
    return <p className="text-xs text-ink-faint">{tr("common.loading")}</p>;
  }

  const groups = Array.from(new Set(catalog.permissions.map((p) => p.group)));

  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-dim">
        {tr("settings.permisos.intro")}
      </p>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Selector de perfil — el equivalente a "omitir permisos" */}
      <div className="grid grid-cols-3 gap-2">
        {AUTONOMY_PROFILES.map((opt) => (
          <button
            key={opt.id}
            onClick={() => applyProfile(opt.id)}
            disabled={busyProfile}
            className={`text-left rounded-xl border px-3 py-2.5 transition-colors disabled:opacity-50 ${
              catalog.profile === opt.id ? "border-accent/50 bg-accent/10" : "border-base-700 hover:border-base-600"
            }`}
          >
            <p className={`text-xs font-medium ${catalog.profile === opt.id ? "text-accent" : "text-ink"}`}>
              {tr(opt.labelKey)}
            </p>
            <p className="text-[10px] text-ink-faint mt-0.5">{tr(opt.hintKey)}</p>
          </button>
        ))}
      </div>
      {catalog.profile === "full" && (
        <p className="text-[10px] text-signal-warn">
          {tr("settings.permisos.autonomousNote")}
        </p>
      )}

      {/* [S7·S8-c] `autonomousNote` explica el COMPORTAMIENTO del perfil
          Autónomo (arriba, junto al selector); esta es una nota DISTINTA —
          un aviso único (no uno por toggle) de que los interruptores de abajo
          no tienen ningún efecto mientras ese perfil siga activo. Antes no
          había ninguna señal visible de esto: apagar un permiso individual
          parecía funcionar y no hacía nada. */}
      {catalog.profile === "full" && (
        <p className="text-[10px] text-ink-faint bg-base-800/50 border border-base-700 rounded-lg px-3 py-2">
          {tr("settings.permisos.togglesInertNote")}
        </p>
      )}

      {/* Permisos agrupados por categoría (grupo/label/description vienen del
          backend — catálogo de PermissionDef, fuera del alcance frontend-only
          de esta sesión; ver nota I18N-8 en doc 30). */}
      <div className="space-y-3">
        {groups.map((group) => (
          <div key={group}>
            <h4 className="text-[10px] uppercase tracking-wide text-ink-faint mb-1.5">{group}</h4>
            <div className="divide-y divide-base-700/40">
              {catalog.permissions
                .filter((p) => p.group === group)
                .map((p) => (
                  <div key={p.id} className="flex items-center gap-3 py-2">
                    <div className="min-w-0 flex-1">
                      <p className={`text-xs ${p.available ? "text-ink" : "text-ink-faint"}`}>
                        {p.label}
                        {!p.available && (
                          <span className="ml-1.5 text-[10px] text-ink-faint">{tr("settings.permisos.comingSoon")}</span>
                        )}
                      </p>
                      <p className="text-[10px] text-ink-faint">{p.description}</p>
                    </div>
                    <Toggle
                      checked={p.enabled}
                      onChange={(v) => toggle(p.id, v)}
                      disabled={!p.available || busyId === p.id}
                      label={p.label}
                    />
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>

      <NotifyChannelSetting />
    </div>
  );
}

/**
 * [R5] Por dónde avisa Aithera cuando una misión se para en un entregable.
 *
 * Vive dentro de Permisos porque responde a la misma pregunta que el resto de
 * la sección: cuánto quiere el usuario que Aithera le interrumpa, y cómo.
 *
 * Telegram sólo se ofrece si hay un chat_id autorizado de verdad: prometer un
 * aviso que no va a llegar es peor que no ofrecerlo.
 */
function NotifyChannelSetting() {
  const tr = useT();
  const [channel, setChannel] = useState<string>("ui");
  const [available, setAvailable] = useState<string[]>(["ui"]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getNotifyChannel()
      .then((r) => {
        setChannel(r.channel);
        setAvailable(r.available);
      })
      .catch(() => {});
  }, []);

  const pick = async (next: string) => {
    setSaving(true);
    const previo = channel;
    setChannel(next);
    try {
      const r = await api.setNotifyChannel(next);
      setChannel(r.channel);
    } catch {
      setChannel(previo); // no se guardó: no dejamos la UI mintiendo
    } finally {
      setSaving(false);
    }
  };

  const OPCIONES: Array<{ id: string; labelKey: string; hintKey: string }> = [
    { id: "ui", labelKey: "settings.notify.ui.label", hintKey: "settings.notify.ui.hint" },
    { id: "telegram", labelKey: "settings.notify.telegram.label", hintKey: "settings.notify.telegram.hint" },
  ];

  return (
    <div className="pt-3 border-t border-base-700/40 space-y-2">
      <h4 className="text-[10px] uppercase tracking-wide text-ink-faint">{tr("settings.notify.title")}</h4>
      <p className="text-[11px] text-ink-dim">
        {tr("settings.notify.desc")}
      </p>
      <div className="grid grid-cols-2 gap-2">
        {OPCIONES.map((opt) => {
          const disponible = available.includes(opt.id);
          return (
            <button
              key={opt.id}
              onClick={() => disponible && pick(opt.id)}
              disabled={saving || !disponible}
              title={disponible ? undefined : tr("settings.notify.needTelegram")}
              className={`text-left rounded-xl border px-3 py-2.5 transition-colors disabled:opacity-40 ${
                channel === opt.id ? "border-accent/50 bg-accent/10" : "border-base-700 hover:border-base-600"
              }`}
            >
              <p className={`text-xs font-medium ${channel === opt.id ? "text-accent" : "text-ink"}`}>
                {tr(opt.labelKey)}
              </p>
              <p className="text-[10px] text-ink-faint mt-0.5">{tr(opt.hintKey)}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * V0.83: configuración de la API key de ElevenLabs desde Ajustes. La key se
 * guarda CIFRADA en el backend (secrets.py) y nunca se devuelve; aquí solo se
 * ve una máscara. Con la key puesta, las voces profesionales aparecen en el
 * Centro de Voz. Sin key, Aithera usa eSpeak (offline).
 */
function ElevenLabsSettings() {
  const tr = useT();
  const [status, setStatus] = useState<ElevenLabsCfgStatus | null>(null);
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const refresh = async () => {
    try {
      setStatus(await api.getElevenLabsConfig());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const save = async () => {
    if (!key.trim()) {
      setMsg({ kind: "err", text: tr("settings.elevenlabs.pasteKey") });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      await api.setElevenLabsKey(key.trim());
      setKey("");
      setMsg({ kind: "ok", text: tr("settings.elevenlabs.savedOk") });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("settings.elevenlabs.errSaving", { msg: (e as Error).message }) });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm(tr("settings.elevenlabs.confirmDelete"))) return;
    try {
      await api.deleteElevenLabsKey();
      setKey("");
      setMsg({ kind: "ok", text: tr("settings.elevenlabs.deletedOk") });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: tr("settings.elevenlabs.errDeleting", { msg: (e as Error).message }) });
    }
  };

  return (
    <div className="space-y-3">
      <div className="text-xs text-ink-dim">
        {status?.configured ? (
          <>
            <span className="text-signal-ok">●</span> {tr("settings.elevenlabs.configured")}{" "}
            <span className="text-ink-faint">
              ({status.key_masked}
              {status.source === "env" ? `, ${tr("settings.elevenlabs.fromEnv")}` : ""})
            </span>
          </>
        ) : (
          <>
            <span className="text-ink-faint">●</span> {tr("settings.elevenlabs.notConfigured")}
          </>
        )}
      </div>

      <div className="space-y-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          type="password"
          placeholder={status?.configured ? tr("settings.elevenlabs.newKeyPlaceholder") : tr("settings.elevenlabs.keyPlaceholder")}
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
          >
            {saving ? tr("settings.elevenlabs.saving") : tr("common.save")}
          </button>
          {/* [2026-07-21] "Crear Voz" → web de ElevenLabs para clonar/diseñar
              una voz propia. Abre en el navegador del sistema. */}
          <a
            href="https://elevenlabs.io/app/voice-lab"
            target="_blank"
            rel="noreferrer noopener"
            className="text-xs px-3 py-1.5 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600 hover:text-ink inline-flex items-center gap-1"
            title={tr("settings.elevenlabs.createVoiceTitle")}
          >
            + {tr("settings.elevenlabs.createVoice")} ↗
          </a>
          {status?.configured && status.source === "config" && (
            <button
              onClick={remove}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              {tr("common.delete")}
            </button>
          )}
        </div>
        <p className="text-[10px] text-ink-faint">
          {tr("settings.elevenlabs.createVoiceHint")}
        </p>
      </div>

      {msg && (
        <p className={`text-xs ${msg.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
          {msg.text}
        </p>
      )}

      <details className="text-[11px] text-ink-dim">
        <summary className="cursor-pointer hover:text-ink select-none">
          <span className="text-accent">▸</span> {tr("settings.elevenlabs.howToGetKey")}
        </summary>
        <ol className="mt-2 space-y-1.5 pl-5 list-decimal text-ink-faint">
          <li>
            {tr("settings.elevenlabs.step1a")}{" "}
            <a href="https://elevenlabs.io" target="_blank" rel="noreferrer" className="text-accent underline">
              elevenlabs.io
            </a>{" "}
            {tr("settings.elevenlabs.step1b")}
          </li>
          <li>
            {tr("settings.elevenlabs.step2a")} <span className="text-ink">API Keys</span> ({tr("settings.elevenlabs.step2b")}{" "}
            <span className="text-ink">elevenlabs.io/app/settings/api-keys</span>).
          </li>
          <li>
            {tr("settings.elevenlabs.step3a")} <span className="text-ink">Create API Key</span>, {tr("settings.elevenlabs.step3b")}
          </li>
        </ol>
        <p className="mt-2 text-ink-faint text-[10px] italic">
          {tr("settings.elevenlabs.security")}
        </p>
      </details>
    </div>
  );
}

interface EditState {
  provider: string;
  api_key: string;
  model: string;
  testing: boolean;
  saving: boolean;
  testResult: string | null;
  // [2026-07-21] Para ofrecer el desplegable de modelos también en el modal
  // de "Configurar" (con nombres comerciales), no solo en la tarjeta.
  available_models: string[];
  model_labels: Record<string, string>;
}

export default function Settings() {
  const [providers, setProviders] = useState<AIProviderEntry[]>([]);
  const [providersEnabled, setProvidersEnabled] = useState<Record<string, boolean>>({});
  const [aiStatus, setAiStatus] = useState<{ provider: string | null; model: string | null; healthy: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [editState, setEditState] = useState<EditState | null>(null);
  // V0.6 (Fase 3 Memory System): estado para la seccion Memoria.
  const [memStats, setMemStats] = useState<MemoryStats | null>(null);
  const [memLoading, setMemLoading] = useState(false);
  const [contextItems, setContextItems] = useState<ContextItem[]>([]);
  // [R6.5c] Perfil destilado del chat, distinto de las preferencias manuales de arriba.
  const [profileFacts, setProfileFacts] = useState<ProfileFact[]>([]);
  const [newCtxKey, setNewCtxKey] = useState("");
  const [newCtxContent, setNewCtxContent] = useState("");
  const [newCtxCategory, setNewCtxCategory] = useState("preference");
  const [memMessage, setMemMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const { backendConnected } = useAppStore();
  const chatPrimaryDown = useAppStore((s) => s.chatPrimaryDown);
  const navigate = useNavigate();
  const location = useLocation();
  // [2026-07-21] Pestaña inicial navegable desde fuera (p.ej. el banner de
  // "trabajando en local" enlaza directo a IA y Modelos → Inteligencia).
  const initialTab = (location.state as { tab?: SettingsTab } | null)?.tab;
  const [tab, setTab] = useState<SettingsTab>(
    initialTab && SETTINGS_TABS.some((t) => t.id === initialTab) ? initialTab : "ia",
  );
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  // OB-1 (doc 30 §1): "Repetir bienvenida" — se aplica al reiniciar la app.
  const [onboardingReset, setOnboardingReset] = useState(false);
  const tr = useT();
  // [2026-07-21] Política activa del MEL: alimenta el Estado del Sistema y los
  // badges de tipo de tarea de cada proveedor (vinculado a Inteligencia).
  const [melPolicies, setMelPolicies] = useState<MelPolicy[] | null>(null);
  // [2026-07-25] Guarda de carrera para loadData(): activar Claude Code y Codex
  // en sucesión rápida disparaba DOS loadData() concurrentes (cada "Activar"
  // termina llamando a loadData()); si la petición más ANTIGUA resolvía la
  // ÚLTIMA, sobreescribía el estado fresco con una foto vieja — visualmente
  // parecía que "activar uno desactivaba el otro" cuando en realidad el
  // backend nunca perdió nada (¡confirmado en vivo!: /api/ai/providers/enabled
  // seguía teniendo ambos en true; solo la UI mostraba una respuesta caducada).
  // Con un contador de generación, una respuesta que ya no es la más reciente
  // se descarta en vez de aplicarse.
  const loadDataGen = useRef(0);

  useEffect(() => {
    loadData();
    loadMemory();
  }, []);

  const loadData = async () => {
    const myGen = ++loadDataGen.current;
    setLoading(true);
    try {
      const [providersData, statusData, enabledMap, pols] = await Promise.all([
        api.getConfiguredProviders(),
        api.getAIStatus(),
        // V1.0: qué proveedores participan en el enrutado del MEL. Los que no
        // aparecen en el mapa están activos (apagar es explícito).
        api.getProvidersEnabled().catch(() => ({} as Record<string, boolean>)),
        // [2026-07-21] Política activa → Estado del Sistema + badges de tarea.
        api.getMelPolicies().catch(() => null),
      ]);
      if (myGen !== loadDataGen.current) return;   // ya llegó una más reciente: descartar
      setProviders(providersData);
      setAiStatus(statusData);
      setProvidersEnabled(enabledMap);
      setMelPolicies(pols);
    } catch (e) {
      console.error("Error cargando configuración:", e);
    } finally {
      if (myGen === loadDataGen.current) setLoading(false);
    }
  };

  // V1.0: varios proveedores pueden estar activos A LA VEZ — el MEL reparte
  // entre todos. Este toggle decide quién participa; el chat concreto se elige
  // en la sección Inteligencia.
  const toggleProviderEnabled = async (provider: string, enabled: boolean) => {
    setProvidersEnabled(prev => ({ ...prev, [provider]: enabled }));
    try {
      await api.setProviderEnabled(provider, enabled);
    } catch (e) {
      setProvidersEnabled(prev => ({ ...prev, [provider]: !enabled }));  // revierte
      console.error("No se pudo cambiar el proveedor:", e);
    }
  };

  // V0.6 (Fase 3): carga la seccion Memoria (stats + preferencias).
  const loadMemory = async () => {
    setMemLoading(true);
    try {
      const [stats, ctx, profile] = await Promise.all([
        api.getMemoryStats(),
        api.listContext(),
        api.getProfile(),
      ]);
      setMemStats(stats);
      setContextItems(ctx.items || []);
      setProfileFacts(profile.items || []);
      setMemMessage(null);
    } catch (e) {
      setMemMessage({ kind: "err", text: `Error cargando memoria: ${(e as Error).message}` });
    } finally {
      setMemLoading(false);
    }
  };

  const handleAddContext = async () => {
    if (!newCtxKey.trim() || !newCtxContent.trim()) {
      setMemMessage({ kind: "err", text: tr("settings.memoria.errRequired") });
      return;
    }
    try {
      await api.storeContext({
        key: newCtxKey.trim(),
        content: newCtxContent.trim(),
        category: newCtxCategory.trim() || "preference",
      });
      setNewCtxKey("");
      setNewCtxContent("");
      setMemMessage({ kind: "ok", text: tr("settings.memoria.prefSaved", { key: newCtxKey.trim() }) });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: tr("settings.memoria.errSaving", { msg: (e as Error).message }) });
    }
  };

  const handleDeleteContext = async (key: string) => {
    if (!confirm(tr("settings.memoria.confirmDeletePref", { key }))) return;
    try {
      await api.deleteContext(key);
      setMemMessage({ kind: "ok", text: tr("settings.memoria.prefDeleted", { key }) });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: tr("settings.memoria.errDeleting", { msg: (e as Error).message }) });
    }
  };

  // [R6.5c] Un hecho borrado es reversible: si vuelve a salir en el chat, la
  // próxima pasada nocturna lo vuelve a destilar. No es un "prohibir".
  const handleDeleteProfileFact = async (key: string, label: string) => {
    if (!confirm(tr("settings.memoria.confirmForget", { label }))) return;
    try {
      await api.deleteProfileFact(key);
      setMemMessage({ kind: "ok", text: tr("settings.memoria.forgotten", { label }) });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: tr("settings.memoria.errForgetting", { msg: (e as Error).message }) });
    }
  };

  const handleClearConversations = async () => {
    const before = memStats?.conversations ?? 0;
    if (!confirm(tr("settings.memoria.confirmClearConversations", { n: before }))) return;
    try {
      const r = await api.clearConversations();
      setMemMessage({ kind: "ok", text: tr("settings.memoria.conversationsCleared", { n: r.count_before }) });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: tr("settings.memoria.errDeleting", { msg: (e as Error).message }) });
    }
  };

  const handleActivate = async (provider: string) => {
    try {
      const result = await api.activateProvider(provider);
      setAiStatus(result);
      await loadData();
    } catch (e) {
      console.error("Error activando proveedor:", e);
    }
  };

  // V1.0: cambia el modelo primario de un proveedor sin abrir el modal de
  // edición (una API key da acceso a varios modelos).
  const handleSelectModel = async (provider: string, model: string) => {
    setProviders(prev => prev.map(p => p.provider === provider ? { ...p, model } : p));
    try {
      await api.updateProvider(provider, { model });
    } catch (e) {
      console.error("No se pudo cambiar el modelo:", e);
      await loadData();  // revierte al estado real
    }
  };

  // [2026-07-21 / 2026-07-24] Proveedores por CLI (Claude Code, Codex de OpenAI):
  // botón "Activar" de 1 clic — comprueba que el CLI responde y, si va, lo deja
  // configurado y participando en el enrutado. Sin modal de API key: van con la
  // sesión que el usuario ya abrió en su terminal (`claude` / `codex login`).
  const CLI_PROVIDERS = new Set(["claude_code", "codex"]);
  // Estado por-proveedor: con dos tarjetas CLI a la vez, el "comprobando…" y el
  // mensaje de resultado tienen que pertenecer a la tarjeta correcta.
  const [ccBusyProvider, setCcBusyProvider] = useState<string | null>(null);
  const [ccMsg, setCcMsg] = useState<{ provider: string; msg: string } | null>(null);
  // Clave i18n del mensaje según el proveedor (Claude Code / Codex comparten patrón).
  const cliMsgKey = (provider: string, kind: "notResponding" | "activatedOk" | "errActivating") =>
    provider === "codex" ? `settings.codex.${kind}` : `settings.claudeCode.${kind}`;
  const activateCli = async (p: AIProviderEntry) => {
    setCcBusyProvider(p.provider);
    setCcMsg(null);
    try {
      const t = await api.testProvider(p.provider, { model: p.model || undefined });
      if (!t.healthy) {
        setCcMsg({ provider: p.provider, msg: `✗ ${tr(cliMsgKey(p.provider, "notResponding"))}` });
      } else {
        // model "" = deja que el CLI use su modelo por defecto (Codex); Claude Code
        // conserva su default "sonnet" si no hay uno elegido.
        await api.addOrUpdateProvider({ provider: p.provider, model: p.model || (p.provider === "codex" ? "" : "sonnet") });
        await api.setProviderEnabled(p.provider, true);
        // Persistencia real: la config y el interruptor viven en la BD — queda
        // activado ENTRE SESIONES, como cualquier otro proveedor.
        setCcMsg({ provider: p.provider, msg: `✓ ${tr(cliMsgKey(p.provider, "activatedOk"))}` });
        await loadData();
      }
    } catch (e) {
      setCcMsg({ provider: p.provider, msg: `✗ ${e instanceof Error ? e.message : tr(cliMsgKey(p.provider, "errActivating"))}` });
    } finally {
      setCcBusyProvider(null);
    }
  };

  const openEdit = (p: AIProviderEntry) => {
    setEditState({
      provider: p.provider,
      api_key: "",
      model: p.model || "",
      testing: false,
      saving: false,
      testResult: null,
      available_models: p.available_models || [],
      model_labels: p.model_labels || {},
    });
  };

  const closeEdit = () => setEditState(null);

  const handleTest = async () => {
    if (!editState) return;
    setEditState(prev => prev ? { ...prev, testing: true, testResult: null } : prev);
    try {
      const result = await api.testProvider(editState.provider, {
        api_key: editState.api_key || undefined,
        model: editState.model || undefined,
      });
      setEditState(prev => prev ? { ...prev, testing: false, testResult: result.healthy ? `✓ ${tr("settings.ia.provider.connOk")}` : "✗ " + result.message } : prev);
    } catch (e) {
      setEditState(prev => prev ? { ...prev, testing: false, testResult: `✗ ${tr("settings.ia.provider.networkErr")}` } : prev);
    }
  };

  // [AUTH-2, 2026-07-23] Validar al pegar: en vez de obligar a pulsar "Probar
  // conexión" a mano, si el usuario pega/escribe algo con pinta de key real
  // (>=20 caracteres, todas las keys de estos proveedores lo son de sobra) se
  // dispara la prueba sola tras una pausa de escritura (debounce 700ms) — el
  // botón manual sigue ahí para repetir la prueba cuando se quiera.
  const pasteTestTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (pasteTestTimer.current) {
      clearTimeout(pasteTestTimer.current);
      pasteTestTimer.current = null;
    }
    if (!editState || editState.testing || editState.saving) return;
    if (editState.api_key.trim().length < 20) return;
    pasteTestTimer.current = setTimeout(() => {
      handleTest();
    }, 700);
    return () => {
      if (pasteTestTimer.current) {
        clearTimeout(pasteTestTimer.current);
        pasteTestTimer.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editState?.api_key]);

  const handleSave = async () => {
    if (!editState) return;
    setEditState(prev => prev ? { ...prev, saving: true } : prev);
    try {
      await api.addOrUpdateProvider({
        provider: editState.provider,
        api_key: editState.api_key || undefined,
        model: editState.model || undefined,
      });
      await loadData();
      closeEdit();
    } catch (e) {
      console.error("Error guardando proveedor:", e);
      setEditState(prev => prev ? { ...prev, saving: false } : prev);
    }
  };

  return (
    // fixedHeight: el panel de Ajustes NO cambia de tamaño al saltar entre
    // pestañas cortas y largas (petición del usuario, 2026-07-21).
    <Modal open onClose={() => navigate(-1)} label={tr("settings.modal.title")} fixedHeight>
      {/* Cabecera del panel */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-base-700/60 shrink-0">
        <div>
          <h1 className="text-base font-semibold text-ink">{tr("settings.modal.title")}</h1>
          <p className="text-[11px] text-ink-faint mt-0.5">{tr("settings.modal.subtitle")}</p>
        </div>
        <button
          onClick={() => navigate(-1)}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-ink-dim hover:bg-base-700 hover:text-ink transition-colors"
          aria-label={tr("common.close")}
        >
          ✕
        </button>
      </div>

      {/* Cuerpo: tab-rail + contenido */}
      <div className="flex flex-1 min-h-0">
        {/* Rail de pestañas */}
        <nav className="w-44 shrink-0 border-r border-base-700/60 p-2 overflow-y-auto">
          {SETTINGS_TABS.map((s) => (
            <button
              key={s.id}
              onClick={() => setTab(s.id)}
              className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-0.5 transition-colors ${
                tab === s.id
                  ? "bg-accent/15 text-accent font-medium"
                  : "text-ink-dim hover:bg-base-800 hover:text-ink"
              }`}
            >
              {tr(s.labelKey)}
            </button>
          ))}
        </nav>

        {/* Contenido con scroll propio */}
        <div className="flex-1 overflow-y-auto p-5">

      {/* Modal edición de proveedor */}
      {editState && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-base-800 border border-base-700 rounded-2xl p-6 w-full max-w-sm mx-4 flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-ink">{tr("settings.editModal.title", { provider: editState.provider })}</h3>

            {/* [AUTH-2, 2026-07-23] Enlace directo + instrucción específica del
                proveedor — evita que el usuario tenga que buscar por su cuenta
                dónde crear la key. */}
            {PROVIDER_AUTH_HELP[editState.provider] && (
              <div className="text-xs bg-base-900/60 border border-base-700 rounded-lg p-3 flex flex-col gap-1.5">
                <a
                  href={PROVIDER_AUTH_HELP[editState.provider].url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline font-medium"
                >
                  {tr("settings.ia.authHelp.getKey")}
                </a>
                <p className="text-ink-faint">{tr(PROVIDER_AUTH_HELP[editState.provider].instructionKey)}</p>
              </div>
            )}

            <div className="flex flex-col gap-1">
              <label className="text-xs text-ink-dim">API Key</label>
              <input
                type="password"
                value={editState.api_key}
                onChange={e => setEditState(prev => prev ? { ...prev, api_key: e.target.value, testResult: null } : prev)}
                placeholder={tr("settings.editModal.apiKeyPlaceholder")}
                className="bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-ink-dim">{tr("settings.editModal.modelLabel")}</label>
              {/* [2026-07-21] Desplegable con los modelos principales (nombres
                  comerciales) cuando el catálogo los conoce; "Otro…" mantiene
                  el campo libre por si el proveedor cambia su catálogo. */}
              {editState.available_models.length > 0 ? (
                <>
                  <select
                    value={editState.available_models.includes(editState.model) ? editState.model : "__other__"}
                    onChange={e => {
                      const v = e.target.value;
                      if (v !== "__other__") setEditState(prev => prev ? { ...prev, model: v } : prev);
                      else setEditState(prev => prev ? { ...prev, model: "" } : prev);
                    }}
                    className="bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-accent/50"
                  >
                    {editState.available_models.map(m => (
                      <option key={m} value={m}>{editState.model_labels[m] || m}</option>
                    ))}
                    <option value="__other__">{tr("settings.editModal.otherModel")}</option>
                  </select>
                  {!editState.available_models.includes(editState.model) && (
                    <input
                      type="text"
                      value={editState.model}
                      onChange={e => setEditState(prev => prev ? { ...prev, model: e.target.value } : prev)}
                      placeholder={tr("settings.editModal.modelIdPlaceholder")}
                      className="mt-1 bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                    />
                  )}
                </>
              ) : (
                <input
                  type="text"
                  value={editState.model}
                  onChange={e => setEditState(prev => prev ? { ...prev, model: e.target.value } : prev)}
                  placeholder="ej. MiniMax-M2.7"
                  className="bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                />
              )}
            </div>

            {editState.testResult && (
              <p className={`text-xs ${editState.testResult.startsWith("✓") ? "text-signal-ok" : "text-signal-error"}`}>
                {editState.testResult}
              </p>
            )}

            <div className="flex gap-2">
              <button
                onClick={handleTest}
                disabled={editState.testing || editState.saving}
                className="flex-1 text-xs px-3 py-2 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600 disabled:opacity-50"
              >
                {editState.testing ? tr("settings.editModal.testing") : tr("settings.editModal.testConnection")}
              </button>
              <button
                onClick={handleSave}
                disabled={editState.saving}
                className="flex-1 text-xs px-3 py-2 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
              >
                {editState.saving ? tr("settings.editModal.saving") : tr("common.save")}
              </button>
              <button onClick={closeEdit} className="text-xs px-3 py-2 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600">
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Pestaña IA y Modelos ═══ */}
      {tab === "ia" && (
        <div className="flex flex-col gap-4">
          {/* Estado de IA — [2026-07-21] VINCULADO a Inteligencia: muestra la
              política ACTIVA y quién lleva el chat según ella, no el proveedor
              "activo" legado (que podía contradecir a la política, bug real). */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.ia.status.title")}</h3>
            {(() => {
              const active = melPolicies?.find((p) => p.is_active);
              const chatChain = active?.compiled?.chat || [];
              // [2026-07-21] El punto refleja al MEL, no al proveedor legacy:
              // con política activa, rojo SOLO si el primario del chat está
              // fallando de verdad (breaker abierto) — antes el punto rojo
              // venía del health-check del proveedor legado (minimax), que ya
              // no decide nada cuando la política manda (bug real reportado).
              const dotOk = active ? !chatPrimaryDown : !!aiStatus?.healthy;
              return (
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${dotOk ? "bg-signal-ok" : "bg-signal-error"}`} />
                  <div className="min-w-0">
                    {active ? (
                      <p className="text-sm text-ink">
                        {tr("settings.ia.status.policy")} <b>{active.name && MEL_POLICY_META_KEYS[active.name] ? tr(MEL_POLICY_META_KEYS[active.name].labelKey) : active.name}</b>
                        {chatChain.length > 0 && <> — {tr(MEL_CAP_LABEL_KEYS.chat)}: <b>{shortRef(chatChain[0])}</b></>}
                      </p>
                    ) : (
                      <p className="text-sm text-ink">
                        {aiStatus?.healthy ? tr("settings.ia.status.connected") : tr("settings.ia.status.disconnected")}
                        {aiStatus?.provider && ` — ${aiStatus.provider}`}
                        {aiStatus?.model && ` / ${aiStatus.model}`}
                      </p>
                    )}
                    <p className="text-[10px] text-ink-faint mt-0.5">
                      {tr("settings.ia.status.changeHint")}
                    </p>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* V1.0: Modelos locales especializados (instalación 1 clic).
              [2026-07-21] Título explícito: aquí se DESCARGA/INSTALA; la
              selección de qué modelos usa Aithera vive en Proveedores de IA. */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.ia.local.title")}</h3>
            <p className="text-[11px] text-ink-faint mb-3">
              {tr("settings.ia.local.onlyDownload")} <b>{tr("settings.ia.providers.title")} → {tr("settings.ia.onDevice.title")}</b>.
            </p>
            <LocalModelsSettings />
          </div>

        {loading ? (
          <div className="text-center text-ink-dim py-10">{tr("common.loading")}</div>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.ia.providers.title")}</h3>
              <p className="text-xs text-ink-dim mb-3">
                {tr("settings.ia.providers.desc")}
              </p>

              {/* ═ Marco: EN TU EQUIPO — [2026-07-21] un card por MODELO local
                  instalado (con su toggle de activación real, LocalModel.enabled
                  → enrutado del MEL). Sin "Configurar": un modelo local jamás
                  necesita API key. La descarga vive arriba; aquí se ACTIVA. */}
              <div className="glass-surface rounded-2xl p-4 mb-4">
                <h3 className="text-sm font-medium text-ink mb-0.5">{tr("settings.ia.onDevice.title")}</h3>
                <p className="text-[11px] text-ink-faint mb-3">
                  {tr("settings.ia.onDevice.desc")}
                </p>
                <LocalProviderModels badges={primaryBadges(melPolicies)} />
              </div>

              {/* ═ Marco: EN LA NUBE — ordenados por estado (activados → conectados
                  → sin conectar), para no buscar abajo lo que ya usas. */}
              <div className="glass-surface rounded-2xl p-4 mb-4">
                <h3 className="text-sm font-medium text-ink mb-0.5">{tr("settings.ia.cloud.title")}</h3>
                <p className="text-[11px] text-ink-faint mb-3">
                  {tr("settings.ia.cloud.desc")}
                </p>
              {providers
                .filter((pp) => pp.provider !== "ollama")
                .slice()
                .sort((a, b) => {
                  const rank = (x: AIProviderEntry) => {
                    const en = providersEnabled[x.provider] !== false;
                    if (x.is_configured && en) return 0;   // activados arriba del todo
                    if (x.is_configured) return 1;         // conectados (en pausa)
                    return 2;                              // sin conectar
                  };
                  return rank(a) - rank(b);
                })
                .map(p => {
                // Sin entrada en el mapa = participa (apagar es explícito).
                const enabled = providersEnabled[p.provider] !== false;
                const models = p.available_models || [];
                // [2026-07-21] Badges de TIPO DE TAREA: capacidades donde este
                // proveedor es el primario de la política ACTIVA (Inteligencia).
                const taskBadges = Object.entries(primaryBadges(melPolicies))
                  .filter(([k]) => k.startsWith(`${p.provider}:`));
                return (
                <div key={p.provider} className="rounded-xl border border-base-700/60 bg-base-900/40 p-4 mb-3">
                  <div className="flex items-center justify-between mb-1 gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-wrap">
                      <span className="font-medium text-ink text-sm">{p.label}</span>
                      {p.is_configured && enabled && (
                        <span className="text-xs px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">{tr("settings.ia.provider.active")}</span>
                      )}
                      {p.is_configured && !enabled && (
                        <span className="text-xs px-2 py-0.5 rounded bg-base-700 text-ink-dim">{tr("settings.ia.provider.paused")}</span>
                      )}
                      {/* Badges de tarea VINCULADOS a Inteligencia (política
                          activa) — sustituyen al viejo "Chat" legacy que podía
                          contradecirla (bug real reportado). */}
                      {taskBadges.map(([key, caps]) =>
                        caps.map((c) => (
                          <span
                            key={`${key}-${c}`}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent"
                            title={`${c}: ${shortRef(key)} (política activa)`}
                          >
                            {c}
                          </span>
                        )),
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {/* [2026-07-21 / 2026-07-24] Proveedores CLI (Claude Code,
                          Codex): sin modal de API key — un solo botón "Activar"
                          los configura automáticamente. */}
                      {CLI_PROVIDERS.has(p.provider) ? (
                        <button
                          onClick={() => activateCli(p)}
                          disabled={ccBusyProvider === p.provider}
                          className="text-xs px-2.5 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
                        >
                          {ccBusyProvider === p.provider ? tr("settings.ia.provider.checking") : tr("settings.ia.provider.activate")}
                        </button>
                      ) : (
                        <button onClick={() => openEdit(p)} className="text-xs px-2 py-1 rounded bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600">
                          {p.has_api_key ? tr("settings.ia.provider.edit") : tr("settings.ia.provider.configure")}
                        </button>
                      )}
                      {p.is_configured && (
                        <Toggle
                          checked={enabled}
                          onChange={(v) => toggleProviderEnabled(p.provider, v)}
                          label={tr("settings.ia.provider.useInRouting", { label: p.label })}
                        />
                      )}
                    </div>
                  </div>
                  {/* Línea aclaratoria del proveedor (ej. cómo funciona
                      Claude Code CLI), si el catálogo la trae. */}
                  {p.description && (
                    <p className="text-[10px] text-ink-faint mb-1">{p.description}</p>
                  )}

                  {/* Selector de modelo: una API key da acceso a varios modelos.
                      El elegido aquí es el PRIMARIO del proveedor; el MEL puede
                      usar el resto por capacidad si le convienen.
                      [2026-07-21] Claude Code CLI NO lleva selector: sus 4
                      modelos se asignan por tarea en Inteligencia (petición
                      del usuario). El resto: nombres comerciales, y chips
                      informativos si aún no está conectado. */}
                  {p.provider === "claude_code" ? (
                    <div className="text-[11px] text-ink-dim mt-2 space-y-1">
                      <p>
                        Haiku 4.5, Sonnet 5, Opus 4.8 {tr("common.and")} Fable 5{" "}
                        <span className="text-ink-faint">({tr("settings.ia.claudeCode.fableMaxOnly")})</span>{" "}
                        — {tr("settings.ia.claudeCode.assignHint")} <b>{tr("settings.ia.intelligence.title")}</b> {tr("settings.ia.claudeCode.economize")}
                      </p>
                      <p className="text-signal-warn">
                        ⚠ {tr("settings.ia.claudeCode.unfitWarning")}
                      </p>
                    </div>
                  ) : p.provider === "codex" ? (
                    <div className="text-[11px] text-ink-dim mt-2 space-y-1">
                      <p>{tr("settings.ia.codex.modelHint")}</p>
                      {/* Instalar + iniciar sesión con un botón (o guía manual).
                          Autónomo: NO recibe onReady/loadData a propósito — hacerlo
                          causaba un bucle de remontaje (ver nota en CodexSetup). */}
                      <CodexSetup />
                      <p className="text-signal-warn">
                        ⚠ {tr("settings.ia.claudeCode.unfitWarning")}
                      </p>
                    </div>
                  ) : p.is_configured && models.length > 0 ? (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[11px] text-ink-dim shrink-0">{tr("settings.ia.provider.model")}</span>
                      <select
                        value={p.model || ""}
                        onChange={(e) => handleSelectModel(p.provider, e.target.value)}
                        className="bg-base-900 border border-base-600 rounded px-2 py-1 text-ink text-[11px] flex-1 min-w-0"
                      >
                        {!models.includes(p.model || "") && p.model && (
                          <option value={p.model}>{p.model_labels?.[p.model] || p.model}</option>
                        )}
                        {models.map(m => (
                          <option key={m} value={m}>{p.model_labels?.[m] || m}</option>
                        ))}
                      </select>
                    </div>
                  ) : models.length > 0 ? (
                    <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                      <span className="text-[10px] text-ink-faint">{tr("settings.ia.provider.models")}</span>
                      {models.map((m) => (
                        <span key={m} className="text-[10px] px-1.5 py-0.5 rounded bg-base-700/60 text-ink-dim">
                          {p.model_labels?.[m] || m}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-ink-faint mt-1">{p.model || "—"}</p>
                  )}

                  {p.has_api_key && p.api_key_preview && (
                    <p className="text-[11px] text-ink-faint mt-1 opacity-50">{tr("settings.ia.provider.keyPreview", { preview: p.api_key_preview })}</p>
                  )}
                  {!p.has_api_key && p.requires_key && (
                    <p className="text-xs text-signal-warn mt-1">{tr("settings.ia.provider.noApiKey")}</p>
                  )}
                  {CLI_PROVIDERS.has(p.provider) && ccMsg?.provider === p.provider && (
                    <p className={`text-xs mt-1 ${ccMsg.msg.startsWith("✓") ? "text-signal-ok" : "text-signal-error"}`}>{ccMsg.msg}</p>
                  )}
                </div>
                );
              })}
              </div>
            </div>

            {/* V1.0 (MEL E2): Inteligencia — qué modelo ejecuta cada tarea */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.ia.intelligence.title")}</h3>
              <IntelligenceSettings />
            </div>
          </div>
        )}
        </div>
      )}

      {/* ═══ Pestaña Permisos ═══ */}
      {tab === "permisos" && (
        <div className="glass-surface rounded-2xl p-4">
          <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.permisos.title")}</h3>
          <PermissionsSettings />
        </div>
      )}

      {/* ═══ Pestaña Voz ═══
          [2026-07-21] TODA la configuración de voz vive aquí: voces y proveedor
          TTS (el antiguo Centro de Voz completo) + la API key de ElevenLabs.
          La Presencia visual se movió a su propia pestaña "HUB Visual". */}
      {tab === "voz" && (
        <div className="flex flex-col gap-4">
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.voz.voices.title")}</h3>
            <VoicePanel />
          </div>

          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.voz.elevenlabs.title")}</h3>
            <p className="text-xs text-ink-dim mb-3">
              {tr("settings.voz.elevenlabs.desc")}
            </p>
            <ElevenLabsSettings />
          </div>
        </div>
      )}

      {/* ═══ Pestaña Briefing ═══
          [PU4b, doc 35] Qué menciona el briefing, a qué horas se lanza solo
          (N al día, con preparación previa) y la selección de noticias
          (temas, fuentes, prompt de intereses). */}
      {tab === "briefing" && <BriefingPanel />}

      {/* ═══ Pestaña HUB Visual ═══
          [2026-07-21] Todo lo que gobierna CÓMO SE VE Aithera: tema claro/
          oscuro (antes en Sistema) + partículas del núcleo (antes en Voz). */}
      {tab === "hub" && (
        <div className="flex flex-col gap-4">
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.hub.appearance.title")}</h3>
            <p className="text-xs text-ink-dim mb-3">
              {tr("settings.hub.appearance.desc")}
            </p>
            <div className="grid grid-cols-2 gap-2 max-w-sm">
              {([
                { id: "dark", label: tr("settings.hub.appearance.dark"), hint: tr("settings.hub.appearance.darkHint") },
                { id: "light", label: tr("settings.hub.appearance.light"), hint: tr("settings.hub.appearance.lightHint") },
              ] as const).map((opt) => {
                const active = theme === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setTheme(opt.id)}
                    className={`text-left p-3 rounded-xl border transition-colors ${
                      active ? "border-accent/50 bg-accent/10" : "border-base-700 hover:border-base-600"
                    }`}
                  >
                    <p className={`text-sm font-medium ${active ? "text-accent" : "text-ink"}`}>
                      {opt.label}
                    </p>
                    <p className="text-[11px] text-ink-faint mt-0.5">{opt.hint}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* AVCS S3: rendimiento de la presencia visual (PerformanceManager v0) */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.hub.presence.title")}</h3>
            <AvcsPerformanceSettings />
          </div>
        </div>
      )}

      {/* ═══ Pestaña Conexiones ═══ */}
      {tab === "conexiones" && (
        <div className="flex flex-col gap-4">
          {/* V0.7 (Fase 4): seccion Google (OAuth) */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">
              {tr("connections.google.title")}
            </h3>
            <p className="text-[10px] text-ink-faint mb-3">
              {tr("connections.google.desc")}
            </p>
            <EmailGoogleStatus />
          </div>

          {/* V1.0/1.1 (Tools): seccion Busqueda web (Search Tool) */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">{tr("connections.search.title")}</h3>
            <SearchSettings />
          </div>

          {/* V0.8 (Fase 5 Clientes): seccion Telegram */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">
              {tr("connections.telegram.title")}
            </h3>
            <p className="text-xs text-ink-dim mb-3">
              {tr("connections.telegram.desc")}
            </p>
            <TelegramSettings />
          </div>
        </div>
      )}

      {/* ═══ Pestaña Servicios (MCP) — C1c: pestaña propia, ya no en Conexiones ═══ */}
      {tab === "mcp" && (
        <div className="glass-surface rounded-2xl p-4">
          <h3 className="text-sm font-medium text-ink mb-1">{tr("mcp.title")}</h3>
          <p className="text-[11px] text-ink-faint mb-3">{tr("mcp.subtitle")}</p>
          <McpPanel />
        </div>
      )}

      {/* ═══ Pestaña Sistema ═══
          [2026-07-21] La Apariencia se movió a "HUB Visual". Aquí entra el
          panel INFORMATIVO del escáner de hardware. */}
      {tab === "sistema" && (
        <div className="flex flex-col gap-4">
          {/* I18N-1 (doc 30 §2): selector de idioma de la interfaz. */}
          <div className="glass-surface rounded-2xl p-4">
            <LanguageSelector />
          </div>

          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.sistema.scan.title")}</h3>
            <p className="text-xs text-ink-dim mb-3">
              {tr("settings.sistema.scan.desc")}
            </p>
            <SystemScanPanel />
          </div>

          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">{tr("settings.sistema.local.title")}</h3>
            <div className="text-xs text-ink-dim space-y-2">
              <p>• {tr("settings.sistema.local.backend")} {backendConnected ? "✓" : "✗"}</p>
              <p>• {tr("settings.sistema.local.frontend")}</p>
              <p>• {tr("settings.sistema.local.database")}</p>
              <p className="text-ink-faint pt-1">{tr("settings.sistema.local.fullscreen")} <b>F11</b>.</p>
            </div>
          </div>

          {/* OB-1 (doc 30 §1): rehacer el asistente de bienvenida. */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-1">{tr("settings.sistema.onboarding.title")}</h3>
            <p className="text-xs text-ink-dim mb-3">
              {tr("settings.sistema.onboarding.desc")}
            </p>
            <button
              onClick={async () => {
                try {
                  await api.resetOnboarding();
                  window.localStorage.removeItem("aithera.onboarded");
                  setOnboardingReset(true);
                } catch {
                  /* noop */
                }
              }}
              disabled={onboardingReset}
              className="text-xs px-3 py-2 rounded-lg bg-base-700 text-ink border border-base-600 hover:bg-base-600 disabled:opacity-60"
            >
              {onboardingReset ? tr("settings.sistema.onboarding.willShow") : tr("settings.sistema.onboarding.repeat")}
            </button>
          </div>
        </div>
      )}

      {/* ═══ Pestaña Memoria ═══ */}
      {tab === "memoria" && (
        <div className="flex flex-col gap-4">
            {/* V0.6 (Fase 3 Memory System): seccion Memoria (ChromaDB) */}
            <div className="glass-surface rounded-2xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-ink">{tr("settings.memoria.title")}</h3>
                <button
                  onClick={loadMemory}
                  disabled={memLoading}
                  className="text-xs px-2 py-1 rounded bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600 disabled:opacity-50"
                >
                  {memLoading ? tr("common.loading") : tr("settings.memoria.refresh")}
                </button>
              </div>

              {!memStats ? (
                <p className="text-xs text-ink-dim">{tr("settings.memoria.loadingStats")}</p>
              ) : !memStats.healthy ? (
                <div className="text-xs text-signal-warn space-y-1">
                  <p>{tr("settings.memoria.unavailable")}</p>
                  {memStats.error && <p className="text-ink-faint font-mono">{memStats.error}</p>}
                  <p className="text-ink-faint">{tr("settings.memoria.stillWorks")}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-xs text-ink-dim grid grid-cols-3 gap-2">
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">{tr("settings.memoria.conversations")}</p>
                      <p className="text-ink font-medium text-base">{memStats.conversations}</p>
                    </div>
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">{tr("settings.memoria.preferences")}</p>
                      <p className="text-ink font-medium text-base">{memStats.user_context}</p>
                    </div>
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">{tr("settings.memoria.documents")}</p>
                      <p className="text-ink font-medium text-base">{memStats.documents}</p>
                    </div>
                  </div>

                  {/* Mensaje de feedback */}
                  {memMessage && (
                    <p className={`text-xs ${memMessage.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
                      {memMessage.text}
                    </p>
                  )}

                  {/* Formulario añadir preferencia */}
                  <div className="border-t border-base-700/50 pt-3">
                    <h4 className="text-xs font-medium text-ink mb-2">{tr("settings.memoria.addPref.title")}</h4>
                    <p className="text-[10px] text-ink-faint mb-2">
                      {tr("settings.memoria.addPref.desc")}
                    </p>
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={newCtxKey}
                        onChange={(e) => setNewCtxKey(e.target.value)}
                        placeholder={tr("settings.memoria.addPref.keyPlaceholder")}
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <input
                        type="text"
                        value={newCtxCategory}
                        onChange={(e) => setNewCtxCategory(e.target.value)}
                        placeholder={tr("settings.memoria.addPref.categoryPlaceholder")}
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <textarea
                        value={newCtxContent}
                        onChange={(e) => setNewCtxContent(e.target.value)}
                        placeholder={tr("settings.memoria.addPref.contentPlaceholder")}
                        rows={2}
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <button
                        onClick={handleAddContext}
                        className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
                      >
                        {tr("settings.memoria.addPref.save")}
                      </button>
                    </div>
                  </div>

                  {/* Lista de preferencias */}
                  <div className="border-t border-base-700/50 pt-3">
                    <h4 className="text-xs font-medium text-ink mb-2">
                      {tr("settings.memoria.savedPrefs", { n: contextItems.length })}
                    </h4>
                    {contextItems.length === 0 ? (
                      <p className="text-xs text-ink-faint">{tr("settings.memoria.noPrefs")}</p>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {contextItems.map((c) => (
                          <div key={c.id} className="bg-base-900/40 rounded-lg p-2 flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="text-xs text-ink font-medium truncate">
                                {c.key}{" "}
                                <span className="text-[10px] text-ink-faint">({c.category})</span>
                              </p>
                              <p className="text-[11px] text-ink-dim mt-0.5">{c.content}</p>
                            </div>
                            <button
                              onClick={() => handleDeleteContext(c.key)}
                              className="text-[10px] px-2 py-1 rounded bg-signal-error/10 text-signal-error border border-signal-error/20 hover:bg-signal-error/20 shrink-0"
                            >
                              {tr("common.delete")}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* [R6.5c] Perfil destilado — lo que Aithera cree saber de ti, sola,
                      de tus conversaciones. Distinto de las preferencias de arriba
                      (esas las escribes tú a mano). Visible y borrable: sin esto sería
                      una caja negra acumulando suposiciones sobre datos personales. */}
                  <div className="border-t border-base-700/50 pt-3">
                    <h4 className="text-xs font-medium text-ink mb-1">
                      {tr("settings.memoria.profile.title", { n: profileFacts.length })}
                    </h4>
                    <p className="text-[10px] text-ink-faint mb-2">
                      {tr("settings.memoria.profile.desc")}
                    </p>
                    {profileFacts.length === 0 ? (
                      <p className="text-xs text-ink-faint">{tr("settings.memoria.profile.empty")}</p>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {profileFacts.map((f) => (
                          <div key={f.key} className="bg-base-900/40 rounded-lg p-2 flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="text-xs text-ink font-medium truncate">{f.label}</p>
                              <p className="text-[11px] text-ink-dim mt-0.5">{f.value}</p>
                            </div>
                            <button
                              onClick={() => handleDeleteProfileFact(f.key, f.label)}
                              className="text-[10px] px-2 py-1 rounded bg-signal-error/10 text-signal-error border border-signal-error/20 hover:bg-signal-error/20 shrink-0"
                            >
                              {tr("settings.memoria.profile.forget")}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Acciones globales */}
                  <div className="border-t border-base-700/50 pt-3 flex gap-2">
                    <button
                      onClick={handleClearConversations}
                      disabled={!memStats.conversations}
                      className="text-xs px-3 py-1.5 rounded-lg bg-signal-warn/10 text-signal-warn border border-signal-warn/30 hover:bg-signal-warn/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {tr("settings.memoria.clearHistory", { n: memStats.conversations })}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        </div>
      </div>
    </Modal>
  );
}
