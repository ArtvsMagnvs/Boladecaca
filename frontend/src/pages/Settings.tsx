// FIX V0.2: Página de Configuración completamente reescrita.
// Ahora incluye formulario para introducir API keys directamente desde la UI,
// sin necesidad de editar el .env ni llamar a la API manualmente.
// V0.6 (Fase 3 Memory System): nueva seccion "Memoria" con stats, gestion
// de preferencias del usuario y borrado del historial de ChromaDB.
import { useState, useEffect } from "react";
import { api, type AIProviderEntry, type ContextItem, type MemoryStats, type TelegramStatus, type SearchStatus, type SearchProviderStatus, type ElevenLabsCfgStatus, type PermissionCatalog, type MelPolicy, type MelModel, type MelOverride, type LocalModelCatalog } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { QualityTier } from "@/avcs";
import { Toggle } from "@/components/Toggle";

/**
 * AVCS S3 (doc 13 §16 PerformanceManager v0): selector manual de tier de
 * calidad Q1-Q3 ("tiers manuales Q1-Q3" — Q4 queda fuera de Fase 0, es el
 * nivel "equipos gaming"). Escribe en el store (persistido en localStorage,
 * ver useAppStore.setAvcsTier) y AitheraPresence lo aplica EN VIVO sin
 * recargar — la escalera dinámica sigue pudiendo degradar/subir por encima
 * de este punto de partida.
 */
const TIER_INFO: Record<Exclude<QualityTier, "Q4">, { label: string; hint: string }> = {
  Q1: { label: "Q1 — Brasa", hint: "equipos modestos, máxima fluidez" },
  Q2: { label: "Q2 — Llama", hint: "equilibrado" },
  Q3: { label: "Q3 — Aurora", hint: "escritorio moderno (recomendado)" },
};

function AvcsPerformanceSettings() {
  const avcsTier = useAppStore((s) => s.avcsTier);
  const setAvcsTier = useAppStore((s) => s.setAvcsTier);

  return (
    <div className="flex flex-col gap-2">
      {(Object.keys(TIER_INFO) as Array<keyof typeof TIER_INFO>).map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => setAvcsTier(t)}
          className={`text-left px-3 py-2 rounded-lg border text-xs transition-colors ${
            avcsTier === t
              ? "bg-accent/15 text-accent border-accent/30"
              : "bg-base-700 text-ink-dim border-base-600 hover:bg-base-600"
          }`}
        >
          <span className="font-medium">{TIER_INFO[t].label}</span>
          <span className="ml-2 opacity-70">{TIER_INFO[t].hint}</span>
        </button>
      ))}
      <p className="text-[10px] text-ink-faint mt-1">
        Aithera baja de nivel sola si el equipo no aguanta el ritmo, y sube de
        nuevo en cuanto puede — esto solo fija el punto de partida.
      </p>
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
  const [emailStatus, setEmailStatus] = useState<{
    connected: boolean;
    email: string | null;
    has_credentials: boolean;
    libs_available: boolean;
    credentials_source: "env" | "db" | "none";
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
      setMsg({ kind: "err", text: "client_id y client_secret son obligatorios" });
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
        text: "Credenciales guardadas en la BD. Ya puedes pulsar 'Conectar con Google'.",
      });
      setClientSecret("");
      setClientId("");
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error guardando: ${(e as Error).message}` });
    } finally {
      setSaving(false);
    }
  };

  const connect = async () => {
    setConnecting(true);
    setMsg(null);
    try {
      const r = await api.startEmailOAuth();
      setMsg({ kind: "ok", text: `Conectado como ${r.email || "Google account"}` });
      refresh();
    } catch (e) {
      const errMsg = (e as Error).message;
      if (errMsg.includes("Falta configurar")) {
        setMsg({
          kind: "err",
          text: "Aun no hay credenciales. Pegalas abajo o usa el metodo .env.",
        });
      } else {
        setMsg({ kind: "err", text: `Error conectando: ${errMsg}` });
      }
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async () => {
    if (!confirm("Desconectar Google? Se borrara el token local.")) return;
    try {
      await api.disconnectEmail();
      setMsg({ kind: "ok", text: "Google desconectado" });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error desconectando: ${(e as Error).message}` });
    }
  };

  const clearDbCredentials = async () => {
    if (!confirm("Borrar las credenciales guardadas en la BD? Si tienes .env, esas seguiran activas.")) return;
    try {
      // Reutilizamos saveClientCredentials pasando strings vacios NO funciona,
      // asi que usamos un endpoint DELETE directo.
      const r = await fetch("/api/email/auth/credentials", { method: "DELETE" });
      if (r.ok) {
        setMsg({ kind: "ok", text: "Credenciales de la BD borradas." });
      }
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error borrando: ${(e as Error).message}` });
    }
  };

  const source = emailStatus?.credentials_source || "none";
  const sourceLabel = {
    env: "leidas de .env (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)",
    db: "guardadas en la BD",
    none: "no configuradas",
  }[source];

  return (
    <div className="space-y-3">
      {/* Estado + boton principal */}
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-ink-dim min-w-0 flex-1">
          {emailStatus?.connected ? (
            <>
              <span className="text-signal-ok">●</span> Conectado como{" "}
              <span className="text-ink font-medium">{emailStatus.email}</span>
            </>
          ) : emailStatus?.has_credentials ? (
            <>
              <span className="text-amber-400">●</span> Credenciales{" "}
              <span className="text-ink">({sourceLabel})</span>. Pulsa{" "}
              <span className="text-ink">"Conectar con Google"</span> para abrir el browser.
            </>
          ) : (
            <>
              <span className="text-ink-faint">●</span> No hay credenciales configuradas.{" "}
              <span className="text-ink-faint">
                Sigue las instrucciones de abajo para obtenerlas.
              </span>
            </>
          )}
          {emailStatus && !emailStatus.libs_available && (
            <div className="mt-1 text-signal-error">
              ⚠ Librerias de Google no instaladas en el backend.
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
                  ? "Primero configura credenciales (ver instrucciones abajo)"
                  : "Abrir el browser para autorizar a Aithera"
              }
              className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {connecting ? "Abriendo browser..." : "Conectar con Google"}
            </button>
          )}
          {emailStatus?.connected && (
            <button
              onClick={disconnect}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              Desconectar
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
              <span className="text-accent">▸</span> Como obtener Client ID y Client Secret
              de Google Cloud Console
            </summary>
            <ol className="mt-2 space-y-2 pl-5 list-decimal text-ink-faint">
              <li>
                Ve a{" "}
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline"
                >
                  console.cloud.google.com/apis/credentials
                </a>{" "}
                y selecciona tu proyecto (o crea uno).
              </li>
              <li>
                Arriba, pulsa <span className="text-ink">+ CREATE CREDENTIALS</span> →
                <span className="text-ink">OAuth client ID</span>.
              </li>
              <li>
                Si te pide configurar la pantalla de consentimiento, hazlo (solo
                email y nombre de la app, lo demas se puede dejar vacio).
              </li>
              <li>
                Tipo de aplicacion: elige <span className="text-ink">Desktop app</span> (es
                lo que usa Aithera localmente). Dale un nombre cualquiera.
              </li>
              <li>
                Pulsa <span className="text-ink">Create</span>. Te apareceran el{" "}
                <strong>Client ID</strong> y el <strong>Client secret</strong> en pantalla
                (ambos visibles). Copialos aqui abajo.
              </li>
              <li>
                (Opcional pero recomendado) Configura el redirect URI como{" "}
                <code className="bg-base-950/50 px-1 rounded">http://localhost:8080</code>{" "}
                en la seccion <span className="text-ink">Authorized redirect URIs</span>{" "}
                de la credencial.
              </li>
              <li>
                Habilita las APIs necesarias: ve a{" "}
                <a
                  href="https://console.cloud.google.com/apis/library"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline"
                >
                  API Library
                </a>{" "}
                y activa <strong>Gmail API</strong> y <strong>Google Calendar API</strong>.
              </li>
            </ol>
            <p className="mt-2 text-ink-faint text-[10px] italic">
              Nota: El "Client Secret" SI aparece al crear credenciales tipo OAuth.
              Si estas mirando "API Keys" en su lugar, eso es otra cosa (no sirve
              para Gmail/Calendar OAuth, que es lo que usa Aithera).
            </p>
          </details>

          {/* Form: pegar credenciales (alternativa a .env) */}
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[10px] text-ink-faint hover:text-ink underline"
            >
              {showAdvanced ? "▾ Ocultar" : "▸ Mostrar"} formulario para pegar credenciales
              manualmente
            </button>
            {showAdvanced && (
              <div className="mt-2 space-y-2 p-3 rounded-lg bg-base-900/40">
                <p className="text-[10px] text-ink-faint">
                  Alternativa: si prefieres no usar el formulario, edita{" "}
                  <code className="bg-base-950/50 px-1 rounded">backend/.env</code> y anade:
                  <br />
                  <code className="bg-base-950/50 px-1 rounded mt-1 inline-block">
                    GOOGLE_CLIENT_ID=tu_client_id
                    <br />
                    GOOGLE_CLIENT_SECRET=tu_client_secret
                  </code>
                  <br />
                  (luego reinicia el backend)
                </p>
                <input
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="Client ID (termina en .apps.googleusercontent.com)"
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
                  {saving ? "Guardando..." : "Guardar en la BD"}
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
              Borrar credenciales de la BD
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
 * proveedores — Brave Search API se prueba primero (plan gratuito de 2000
 * consultas/mes); si falla o no está configurado, cae a SerpAPI. Ambos son
 * opcionales e independientes; basta con configurar uno para que funcione.
 */
function SearchProviderCard({
  label, hint, signupUrl, status, onSave, onDelete,
}: {
  label: string; hint: string; signupUrl: string;
  status: SearchProviderStatus | undefined;
  onSave: (key: string) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <div className="rounded-xl p-3 border border-base-700 bg-base-800/40">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-ink">{label}</span>
        {status?.configured ? (
          <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
            Configurado ({status.key_masked})
          </span>
        ) : (
          <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-dim">Sin configurar</span>
        )}
      </div>
      <p className="text-[11px] text-ink-faint mb-2">
        {hint}{" "}
        <a href={signupUrl} target="_blank" rel="noreferrer" className="text-accent underline">
          Consigue tu API key aquí
        </a>.
      </p>
      <div className="flex gap-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          type="password"
          placeholder={status?.configured ? "Nueva key (deja vacío para no cambiarla)" : "Pega tu API key"}
          className="flex-1 bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <button
          onClick={async () => { setSaving(true); await onSave(key); setKey(""); setSaving(false); }}
          disabled={saving || !key.trim()}
          className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
        >
          Guardar
        </button>
        {status?.configured && (
          <button
            onClick={onDelete}
            className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
          >
            Borrar
          </button>
        )}
      </div>
    </div>
  );
}

function SearchSettings() {
  const [status, setStatus] = useState<SearchStatus | null>(null);

  const refresh = async () => {
    try { setStatus(await api.getSearchStatus()); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">
        Aithera prueba primero Brave; si falla o no está configurado, usa SerpAPI. Con uno
        solo ya funciona — configura los dos si quieres respaldo automático.
      </p>
      <SearchProviderCard
        label="Brave Search API" hint="Gratis hasta 2.000 consultas/mes."
        signupUrl="https://api.search.brave.com/register"
        status={status?.brave}
        onSave={async (k) => { await api.configureSearchProvider("brave", k); refresh(); }}
        onDelete={async () => { await api.deconfigureSearchProvider("brave"); refresh(); }}
      />
      <SearchProviderCard
        label="SerpAPI (Google)" hint="Resultados de Google reales. Plan gratuito limitado (~100/mes)."
        signupUrl="https://serpapi.com/manage-api-key"
        status={status?.serpapi}
        onSave={async (k) => { await api.configureSearchProvider("serpapi", k); refresh(); }}
        onDelete={async () => { await api.deconfigureSearchProvider("serpapi"); refresh(); }}
      />
    </div>
  );
}

function TelegramSettings() {
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
        text: "Guardado. Reinicia el backend para que el bot tome los cambios.",
      });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error guardando: ${(e as Error).message}` });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm("Borrar la configuracion de Telegram? El bot dejara de responder tras reiniciar.")) return;
    try {
      await api.deconfigureTelegram();
      setToken("");
      setMsg({ kind: "ok", text: "Configuracion de Telegram borrada." });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error borrando: ${(e as Error).message}` });
    }
  };

  return (
    <div className="space-y-3">
      {/* Estado */}
      <div className="text-xs text-ink-dim">
        {status?.running ? (
          <>
            <span className="text-signal-ok">●</span> Bot activo
            {status.allowed_chat_ids.length > 0
              ? ` — ${status.allowed_chat_ids.length} chat autorizado(s)`
              : " — sin chats autorizados todavia"}
          </>
        ) : status?.configured ? (
          <>
            <span className="text-amber-400">●</span> Token guardado{" "}
            <span className="text-ink-faint">({status.token_masked})</span>, bot no
            activo. Reinicia el backend para arrancarlo.
          </>
        ) : (
          <>
            <span className="text-ink-faint">●</span> Sin configurar. Pega el token de
            tu bot de BotFather.
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
              ? "Token guardado (dejar vacio para conservarlo)"
              : "Token del bot (de @BotFather)"
          }
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <input
          value={chatIds}
          onChange={(e) => setChatIds(e.target.value)}
          placeholder="chat_id autorizados, separados por comas (ej: 123456789)"
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
          {status?.configured && (
            <button
              onClick={remove}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              Borrar
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
          <span className="text-accent">▸</span> Como obtener tu chat_id
        </summary>
        <ol className="mt-2 space-y-1.5 pl-5 list-decimal text-ink-faint">
          <li>
            Crea el bot con{" "}
            <a href="https://t.me/BotFather" target="_blank" rel="noreferrer" className="text-accent underline">
              @BotFather
            </a>{" "}
            y copia el token aqui arriba. Guarda (sin chat_id todavia) y reinicia el backend.
          </li>
          <li>
            Abre tu bot en Telegram y escribele <code className="bg-base-950/50 px-1 rounded">/start</code>.
            Te respondera con tu <strong>chat_id</strong>.
          </li>
          <li>
            Pega ese numero en el campo de chat_id de arriba, guarda y reinicia el backend
            otra vez. Listo: ya puedes chatear con Aithera por Telegram.
          </li>
        </ol>
        <p className="mt-2 text-ink-faint text-[10px] italic">
          Seguridad: solo los chat_id de la lista pueden usar el bot. El token se guarda
          cifrado (DPAPI) en la BD local, nunca en texto plano.
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
const AUTONOMY_PROFILES: Array<{ id: string; label: string; hint: string }> = [
  { id: "manual", label: "Preguntar siempre", hint: "Aithera pide tu aprobación para cada acción sensible." },
  { id: "balanced", label: "Equilibrado", hint: "Autoriza lo de bajo riesgo, sigue preguntando para lo delicado." },
  { id: "full", label: "Autónomo", hint: "Aithera actúa sin preguntar. Revisa el historial cuando quieras." },
];

/**
 * V1.0 (MEL E2/E2b, doc 22 §3): Inteligencia — qué modelo ejecuta cada tipo de
 * tarea. El usuario elige una POLÍTICA (no un modelo); el MEL decide el resto.
 * E2b (petición del usuario, 2026-07-18): además puede PERSONALIZAR el modelo
 * primario por capacidad en Economía/Calidad/Personalizado, con "Restaurar" a
 * los valores por defecto. "Sin conexión" no es editable (es solo-local).
 */
const MEL_POLICY_META: Record<string, { label: string; hint: string }> = {
  economy: { label: "Economía", hint: "Prioriza el coste: usa el modelo local para tareas simples y el mejor de pago solo cuando hace falta." },
  quality: { label: "Calidad", hint: "El mejor modelo para cada tarea, sin importar el coste." },
  offline: { label: "Sin conexión", hint: "Solo modelos locales (sin internet). Puede no cubrir todas las tareas." },
  custom: { label: "Personalizado", hint: "Tú decides el modelo de cada tarea. Parte de Calidad; edita lo que quieras y restaura cuando quieras." },
};
const MEL_CAP_LABEL: Record<string, string> = {
  chat: "Chat", classify: "Clasificar", extract: "Extraer datos", summarize: "Resumir",
  draft: "Redactar", reason: "Razonar", code: "Programar", analyze: "Analizar",
};
// Orden y whitelist de capacidades activas (las reservadas research/vision/
// agentic existen en el backend pero no se muestran — no aportan al usuario aún).
const MEL_CAPS_ORDER = ["chat", "classify", "extract", "summarize", "draft", "reason", "code", "analyze"];
const MEL_POLICY_ORDER = ["economy", "quality", "offline", "custom"];
const MEL_EDITABLE = new Set(["economy", "quality", "custom"]);

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
  const [catalog, setCatalog] = useState<LocalModelCatalog | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setCatalog(await api.getLocalCatalog());
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el catálogo de modelos.");
    }
  };
  useEffect(() => { load(); }, []);

  // Mientras haya una descarga viva, refresca solo (el progreso vive en el backend).
  const hasActiveJob = (catalog?.families ?? []).some((f) =>
    f.models.some((m) => m.job?.status === "downloading"));
  useEffect(() => {
    if (!hasActiveJob) return;
    const id = setInterval(load, 1500);
    return () => clearInterval(id);
  }, [hasActiveJob]);

  const install = async (tag: string) => {
    setBusy(tag); setError(null);
    try { await api.installLocalModel(tag); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo iniciar la descarga."); }
    finally { setBusy(null); }
  };
  const cancel = async (tag: string) => {
    try { await api.cancelLocalInstall(tag); await load(); } catch { /* ya terminó */ }
  };
  const toggle = async (tag: string, enabled: boolean) => {
    setBusy(tag);
    try { await api.setLocalModelEnabled(tag, enabled); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo cambiar el estado."); }
    finally { setBusy(null); }
  };
  const remove = async (tag: string, label: string) => {
    if (!confirm(`¿Eliminar "${label}"? Se liberará el espacio en disco.`)) return;
    setBusy(tag);
    try { await api.deleteLocalModel(tag); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo eliminar."); }
    finally { setBusy(null); }
  };

  if (!catalog) return <p className="text-xs text-ink-faint">Cargando…</p>;

  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-dim">
        Modelos que corren en tu ordenador, cada uno bueno en algo distinto. Instala los que
        quieras y Aithera repartirá cada tarea al que mejor la hace.
      </p>

      {!catalog.runtime_ok && (
        <div className="text-xs text-signal-warn bg-signal-warn/10 border border-signal-warn/30 rounded-lg px-3 py-2">
          Ollama no responde. Es el motor que ejecuta estos modelos —{" "}
          <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="underline">
            instálalo aquí
          </a>{" "}y vuelve a esta pantalla.
        </div>
      )}
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {catalog.families.filter((f) => !f.is_runtime).map((fam) => (
        <div key={fam.family} className="rounded-xl border border-base-700 bg-base-800/40 p-3">
          <div className="flex items-center gap-2">
            <span>{CATEGORY_ICON[fam.category] ?? "•"}</span>
            <span className="text-sm font-medium text-ink">{fam.label}</span>
          </div>
          <p className="text-[11px] text-ink-faint mt-0.5 mb-2">{fam.description}</p>

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
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent">sugerido</span>
                        )}
                        {m.installed && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-signal-ok/15 text-signal-ok">instalado</span>
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
                          Instalar
                        </button>
                      )}
                      {downloading && (
                        <button
                          onClick={() => cancel(m.tag)}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600"
                        >
                          Cancelar
                        </button>
                      )}
                      {m.installed && (
                        <>
                          <Toggle
                            checked={m.enabled}
                            onChange={(v) => toggle(m.tag, v)}
                            disabled={busy === m.tag}
                          />
                          <button
                            onClick={() => remove(m.tag, m.label)}
                            disabled={busy === m.tag}
                            className="text-[11px] px-2 py-1 rounded-lg text-signal-error hover:bg-signal-error/10 disabled:opacity-50"
                            title="Eliminar del disco"
                          >
                            ×
                          </button>
                        </>
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
        </div>
      ))}
    </div>
  );
}

function IntelligenceSettings() {
  const [policies, setPolicies] = useState<MelPolicy[] | null>(null);
  const [models, setModels] = useState<MelModel[]>([]);
  const [overrides, setOverrides] = useState<MelOverride[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [pols, mods, ovs] = await Promise.all([
        api.getMelPolicies(), api.getMelModels(), api.getMelOverrides(),
      ]);
      setPolicies(pols);
      setModels(mods);
      setOverrides(ovs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las políticas.");
    }
  };

  const deleteOverride = async (id: number) => {
    setBusy(true); setError(null);
    try { await api.deleteMelOverride(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo borrar el pin."); }
    finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);

  const activate = async (name: string) => {
    setBusy(true); setError(null);
    try { await api.setActiveMelPolicy(name); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo cambiar la política."); }
    finally { setBusy(false); }
  };

  const setPrimary = async (name: string, cap: string, modelKey: string | null) => {
    setBusy(true); setError(null);
    try { await api.setMelPolicyPrimary(name, cap, modelKey); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo cambiar el modelo."); }
    finally { setBusy(false); }
  };

  const restore = async (name: string) => {
    setBusy(true); setError(null);
    try { await api.restoreMelPolicy(name); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo restaurar."); }
    finally { setBusy(false); }
  };

  if (!policies) return <p className="text-xs text-ink-faint">Cargando…</p>;

  // Etiqueta legible de un model_key: el label del proveedor si lo conocemos.
  // Etiqueta legible de un model_key. Marca "(local)" porque una misma familia
  // (Qwen, DeepSeek…) puede estar a la vez en el PC y por API de pago, y el
  // usuario necesita distinguirlas de un vistazo.
  const modelLabel = (key: string) => {
    const m = models.find((x) => x.key === key);
    if (!m) return key.split(":")[0];
    return `${m.label}${m.is_local ? " (local)" : ""} · ${m.model}`;
  };

  // Modelos agrupados por proveedor para el selector en cascada. El nombre del
  // grupo ya lleva "(local)", así que las opciones solo muestran el modelo.
  const groupedModels = (() => {
    const groups = new Map<string, MelModel[]>();
    for (const m of models) {
      const groupLabel = `${m.label}${m.is_local ? " (local)" : ""}`;
      const list = groups.get(groupLabel);
      if (list) list.push(m);
      else groups.set(groupLabel, [m]);
    }
    return Array.from(groups.entries());
  })();

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">
        Elige cómo Aithera reparte las tareas entre tus modelos. Tú eliges la estrategia;
        Aithera decide qué modelo concreto usa para cada cosa — o personaliza el modelo de cada tarea.
      </p>
      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
      {policies
        .slice()
        .sort((a, b) => MEL_POLICY_ORDER.indexOf(a.name) - MEL_POLICY_ORDER.indexOf(b.name))
        .map((p) => {
        const meta = MEL_POLICY_META[p.name] ?? { label: p.name, hint: "" };
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
                  {p.is_active && <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">Activa</span>}
                  {canEdit && !p.pristine && <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-dim">Editada</span>}
                </div>
                <p className="text-[11px] text-ink-faint mt-0.5">{meta.hint}</p>
              </div>
              {!p.is_active && (
                <button
                  onClick={() => activate(p.name)}
                  disabled={busy}
                  className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
                >
                  Usar esta
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => { setExpanded(isOpen ? null : p.name); setEditing(null); }}
                className="text-[10px] text-accent hover:underline"
              >
                {isOpen ? "ocultar detalle" : "ver qué modelo hace cada tarea"}
              </button>
              {canEdit && (
                <button
                  onClick={() => { setEditing(isEditing ? null : p.name); setExpanded(p.name); }}
                  className="text-[10px] text-accent hover:underline"
                >
                  {isEditing ? "terminar de editar" : "personalizar"}
                </button>
              )}
              {canEdit && !p.pristine && (
                <button
                  onClick={() => restore(p.name)}
                  disabled={busy}
                  className="text-[10px] text-signal-warn hover:underline disabled:opacity-50"
                >
                  Restaurar
                </button>
              )}
            </div>

            {isOpen && (
              <div className="mt-2 space-y-1">
                {MEL_CAPS_ORDER.filter((cap) => cap in p.compiled).map((cap) => {
                  const chain = p.compiled[cap] || [];
                  return (
                    <div key={cap} className="flex items-center justify-between gap-2 text-[11px] py-1 border-b border-base-700/40">
                      <span className="text-ink-dim shrink-0 w-24">{MEL_CAP_LABEL[cap] ?? cap}</span>
                      {isEditing ? (
                        <div className="flex items-center gap-2 flex-1 justify-end">
                          <select
                            value={chain[0] ?? ""}
                            disabled={busy}
                            onChange={(e) => setPrimary(p.name, cap, e.target.value || null)}
                            className="bg-base-900 border border-base-600 rounded px-2 py-1 text-ink text-[11px] max-w-[60%]"
                          >
                            <option value="">Automático</option>
                            {/* Agrupado por PROVEEDOR y luego modelo: una misma
                                familia (p.ej. Qwen) puede estar en local y por
                                API, así que el grupo marca cuál es cuál. */}
                            {groupedModels.map(([groupLabel, items]) => (
                              <optgroup key={groupLabel} label={groupLabel}>
                                {items.map((m) => (
                                  <option key={m.key} value={m.key}>{m.model}</option>
                                ))}
                              </optgroup>
                            ))}
                          </select>
                        </div>
                      ) : (
                        <span className="text-ink-faint truncate ml-2 text-right">
                          {chain.length ? modelLabel(chain[0]) : "— (sin modelo)"}
                          {chain.length > 1 && <span className="opacity-50"> → {chain.slice(1).map(modelLabel).join(" → ")}</span>}
                        </span>
                      )}
                    </div>
                  );
                })}
                {isEditing && (
                  <p className="text-[10px] text-ink-faint pt-1">
                    "Automático" deja que Aithera elija según el catálogo. Los respaldos (→) se
                    añaden solos para que nunca te quedes sin respuesta si un modelo falla.
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Pines de modelo por proyecto (override explícito, E2b) — borrables */}
      {overrides.length > 0 && (
        <div className="rounded-xl p-3 border border-base-700 bg-base-800/40">
          <p className="text-xs font-medium text-ink mb-1">Modelo fijado por proyecto</p>
          <p className="text-[11px] text-ink-faint mb-2">
            Cuando le pides a Aithera "usa este modelo para todo el proyecto", queda fijado aquí.
            Bórralo para volver a la política normal.
          </p>
          <div className="space-y-1">
            {overrides.map((o) => (
              <div key={o.id} className="flex items-center justify-between text-[11px] py-1 border-b border-base-700/40">
                <span className="text-ink-dim">
                  Proyecto #{o.project_id}
                  {o.capability && <span className="text-ink-faint"> · {MEL_CAP_LABEL[o.capability] ?? o.capability}</span>}
                  <span className="text-ink-faint"> → {o.model_id.split(":")[0]}</span>
                </span>
                <button
                  onClick={() => deleteOverride(o.id)}
                  disabled={busy}
                  className="text-signal-warn hover:underline disabled:opacity-50"
                >
                  Borrar
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
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [busyProfile, setBusyProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setCatalog(await api.getPermissions());
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar los permisos.");
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
      setError(e instanceof Error ? e.message : "No se pudo cambiar el permiso.");
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
      setError(e instanceof Error ? e.message : "No se pudo aplicar el perfil.");
    } finally {
      setBusyProfile(false);
    }
  };

  if (!catalog) {
    return <p className="text-xs text-ink-faint">Cargando…</p>;
  }

  const groups = Array.from(new Set(catalog.permissions.map((p) => p.group)));

  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-dim">
        Decide qué puede hacer Aithera sin preguntarte primero. Ajusta cada permiso por
        separado o elige un perfil rápido.
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
              {opt.label}
            </p>
            <p className="text-[10px] text-ink-faint mt-0.5">{opt.hint}</p>
          </button>
        ))}
      </div>
      {catalog.profile === "full" && (
        <p className="text-[10px] text-signal-warn">
          Modo autónomo: Aithera ejecutará acciones sensibles sin pedirte confirmación.
          Puedes volver a "Preguntar siempre" cuando quieras.
        </p>
      )}

      {/* Permisos agrupados por categoría */}
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
                          <span className="ml-1.5 text-[10px] text-ink-faint">(próximamente)</span>
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

  const OPCIONES: Array<{ id: string; label: string; hint: string }> = [
    { id: "ui", label: "Solo en Aithera", hint: "Lo ves al abrir la app" },
    { id: "telegram", label: "Telegram", hint: "Además te escribe al móvil" },
  ];

  return (
    <div className="pt-3 border-t border-base-700/40 space-y-2">
      <h4 className="text-[10px] uppercase tracking-wide text-ink-faint">Avisos</h4>
      <p className="text-[11px] text-ink-dim">
        Cuando Aithera termina algo que puedes comprobar, se para y te avisa. Elige por dónde.
      </p>
      <div className="grid grid-cols-2 gap-2">
        {OPCIONES.map((opt) => {
          const disponible = available.includes(opt.id);
          return (
            <button
              key={opt.id}
              onClick={() => disponible && pick(opt.id)}
              disabled={saving || !disponible}
              title={disponible ? undefined : "Configura Telegram más abajo para poder elegirlo"}
              className={`text-left rounded-xl border px-3 py-2.5 transition-colors disabled:opacity-40 ${
                channel === opt.id ? "border-accent/50 bg-accent/10" : "border-base-700 hover:border-base-600"
              }`}
            >
              <p className={`text-xs font-medium ${channel === opt.id ? "text-accent" : "text-ink"}`}>
                {opt.label}
              </p>
              <p className="text-[10px] text-ink-faint mt-0.5">{opt.hint}</p>
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
      setMsg({ kind: "err", text: "Pega tu API key de ElevenLabs." });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      await api.setElevenLabsKey(key.trim());
      setKey("");
      setMsg({ kind: "ok", text: "Guardada y cifrada. Ya puedes elegir voces en el Centro de Voz." });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error guardando: ${(e as Error).message}` });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm("¿Borrar la API key de ElevenLabs?")) return;
    try {
      await api.deleteElevenLabsKey();
      setKey("");
      setMsg({ kind: "ok", text: "API key borrada." });
      refresh();
    } catch (e) {
      setMsg({ kind: "err", text: `Error borrando: ${(e as Error).message}` });
    }
  };

  return (
    <div className="space-y-3">
      <div className="text-xs text-ink-dim">
        {status?.configured ? (
          <>
            <span className="text-signal-ok">●</span> Configurada{" "}
            <span className="text-ink-faint">
              ({status.key_masked}
              {status.source === "env" ? ", desde .env" : ""})
            </span>
          </>
        ) : (
          <>
            <span className="text-ink-faint">●</span> Sin configurar. Pega tu API key de
            ElevenLabs para usar voces profesionales.
          </>
        )}
      </div>

      <div className="space-y-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          type="password"
          placeholder={status?.configured ? "Nueva key (dejar vacío para conservar)" : "API key de ElevenLabs"}
          className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
        />
        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
          {status?.configured && status.source === "config" && (
            <button
              onClick={remove}
              className="text-xs px-3 py-1.5 rounded-lg bg-signal-error/15 text-signal-error border border-signal-error/30 hover:bg-signal-error/25"
            >
              Borrar
            </button>
          )}
        </div>
      </div>

      {msg && (
        <p className={`text-xs ${msg.kind === "ok" ? "text-signal-ok" : "text-signal-error"}`}>
          {msg.text}
        </p>
      )}

      <details className="text-[11px] text-ink-dim">
        <summary className="cursor-pointer hover:text-ink select-none">
          <span className="text-accent">▸</span> Cómo obtener tu API key de ElevenLabs
        </summary>
        <ol className="mt-2 space-y-1.5 pl-5 list-decimal text-ink-faint">
          <li>
            Entra en{" "}
            <a href="https://elevenlabs.io" target="_blank" rel="noreferrer" className="text-accent underline">
              elevenlabs.io
            </a>{" "}
            y crea una cuenta (el plan gratuito ya trae voces).
          </li>
          <li>
            Arriba a la derecha, abre tu perfil → <span className="text-ink">API Keys</span> (o
            ve directo a <span className="text-ink">elevenlabs.io/app/settings/api-keys</span>).
          </li>
          <li>
            Pulsa <span className="text-ink">Create API Key</span>, cópiala y pégala aquí arriba.
            Guarda: se cifra en local. Luego elige tu voz en el Centro de Voz.
          </li>
        </ol>
        <p className="mt-2 text-ink-faint text-[10px] italic">
          Seguridad: la key se guarda cifrada (DPAPI) en la BD local, nunca en texto plano.
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
  const [newCtxKey, setNewCtxKey] = useState("");
  const [newCtxContent, setNewCtxContent] = useState("");
  const [newCtxCategory, setNewCtxCategory] = useState("preference");
  const [memMessage, setMemMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const { backendConnected } = useAppStore();

  useEffect(() => {
    loadData();
    loadMemory();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [providersData, statusData, enabledMap] = await Promise.all([
        api.getConfiguredProviders(),
        api.getAIStatus(),
        // V1.0: qué proveedores participan en el enrutado del MEL. Los que no
        // aparecen en el mapa están activos (apagar es explícito).
        api.getProvidersEnabled().catch(() => ({} as Record<string, boolean>)),
      ]);
      setProviders(providersData);
      setAiStatus(statusData);
      setProvidersEnabled(enabledMap);
    } catch (e) {
      console.error("Error cargando configuración:", e);
    } finally {
      setLoading(false);
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
      const [stats, ctx] = await Promise.all([
        api.getMemoryStats(),
        api.listContext(),
      ]);
      setMemStats(stats);
      setContextItems(ctx.items || []);
      setMemMessage(null);
    } catch (e) {
      setMemMessage({ kind: "err", text: `Error cargando memoria: ${(e as Error).message}` });
    } finally {
      setMemLoading(false);
    }
  };

  const handleAddContext = async () => {
    if (!newCtxKey.trim() || !newCtxContent.trim()) {
      setMemMessage({ kind: "err", text: "key y contenido son obligatorios" });
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
      setMemMessage({ kind: "ok", text: `Preferencia '${newCtxKey.trim()}' guardada` });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: `Error guardando: ${(e as Error).message}` });
    }
  };

  const handleDeleteContext = async (key: string) => {
    if (!confirm(`Eliminar la preferencia '${key}'?`)) return;
    try {
      await api.deleteContext(key);
      setMemMessage({ kind: "ok", text: `Preferencia '${key}' eliminada` });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: `Error eliminando: ${(e as Error).message}` });
    }
  };

  const handleClearConversations = async () => {
    const before = memStats?.conversations ?? 0;
    if (!confirm(`Borrar ${before} conversaciones de ChromaDB? Esta accion no se puede deshacer.`)) return;
    try {
      const r = await api.clearConversations();
      setMemMessage({ kind: "ok", text: `Borradas ${r.count_before} conversaciones` });
      await loadMemory();
    } catch (e) {
      setMemMessage({ kind: "err", text: `Error borrando: ${(e as Error).message}` });
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

  const openEdit = (p: AIProviderEntry) => {
    setEditState({
      provider: p.provider,
      api_key: "",
      model: p.model || "",
      testing: false,
      saving: false,
      testResult: null,
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
      setEditState(prev => prev ? { ...prev, testing: false, testResult: result.healthy ? "✓ Conexión correcta" : "✗ " + result.message } : prev);
    } catch (e) {
      setEditState(prev => prev ? { ...prev, testing: false, testResult: "✗ Error de red" } : prev);
    }
  };

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
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ink">Configuración</h1>
          <p className="text-xs text-ink-faint mt-0.5">Proveedores de IA y configuración del sistema</p>
        </div>
      </div>

      {/* Modal edición de proveedor */}
      {editState && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-base-800 border border-base-700 rounded-2xl p-6 w-full max-w-sm mx-4 flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-ink">Configurar {editState.provider}</h3>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-ink-dim">API Key</label>
              <input
                type="password"
                value={editState.api_key}
                onChange={e => setEditState(prev => prev ? { ...prev, api_key: e.target.value, testResult: null } : prev)}
                placeholder="Pega tu API key aquí…"
                className="bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-ink-dim">Modelo</label>
              <input
                type="text"
                value={editState.model}
                onChange={e => setEditState(prev => prev ? { ...prev, model: e.target.value } : prev)}
                placeholder="ej. MiniMax-M2.7"
                className="bg-base-700 border border-base-600 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
              />
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
                {editState.testing ? "Probando…" : "Probar conexión"}
              </button>
              <button
                onClick={handleSave}
                disabled={editState.saving}
                className="flex-1 text-xs px-3 py-2 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
              >
                {editState.saving ? "Guardando…" : "Guardar"}
              </button>
              <button onClick={closeEdit} className="text-xs px-3 py-2 rounded-lg bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600">
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Contenido con scroll — todo lo que no es cabecera/modal vive aquí,
          para que "Estado"/"Permisos" no le roben altura fija al resto
          (bug real: antes vivían fuera de este contenedor y, al crecer
          Permisos en A3b, dejaban el área scrolleable con 0px de alto). */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col gap-4">
          {/* Estado de IA */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">Estado del Sistema de IA</h3>
            <div className="flex items-center gap-4">
              <div className={`w-3 h-3 rounded-full ${aiStatus?.healthy ? "bg-signal-ok" : "bg-signal-error"}`} />
              <div>
                <p className="text-sm text-ink">
                  {aiStatus?.healthy ? "Conectado" : "Desconectado"}
                  {aiStatus?.provider && ` — ${aiStatus.provider}`}
                  {aiStatus?.model && ` / ${aiStatus.model}`}
                </p>
              </div>
            </div>
          </div>

          {/* V1.0: Modelos locales especializados (instalación 1 clic) */}
          <div className="glass-surface rounded-2xl p-4">
            <h3 className="text-sm font-medium text-ink mb-3">Modelos locales</h3>
            <LocalModelsSettings />
          </div>

        {loading ? (
          <div className="text-center text-ink-dim py-10">Cargando...</div>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-medium text-ink mb-1">Proveedores de IA</h3>
              <p className="text-xs text-ink-dim mb-3">
                Puedes tener varios proveedores activos a la vez: Aithera reparte cada tarea
                entre todos según su fuerza. El modelo del chat se elige en <b>Inteligencia</b>.
              </p>
              {providers.map(p => {
                // Sin entrada en el mapa = participa (apagar es explícito).
                const enabled = providersEnabled[p.provider] !== false;
                const models = p.available_models || [];
                return (
                <div key={p.provider} className="glass-surface rounded-xl p-4 mb-3">
                  <div className="flex items-center justify-between mb-1 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-medium text-ink text-sm">{p.label}</span>
                      {p.is_configured && enabled && (
                        <span className="text-xs px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">Activo</span>
                      )}
                      {p.is_configured && !enabled && (
                        <span className="text-xs px-2 py-0.5 rounded bg-base-700 text-ink-dim">En pausa</span>
                      )}
                      {p.is_active && (
                        <span className="text-xs px-2 py-0.5 rounded bg-accent/15 text-accent" title="Proveedor del chat directo (legacy)">
                          Chat
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button onClick={() => openEdit(p)} className="text-xs px-2 py-1 rounded bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600">
                        {p.has_api_key ? "Editar" : "Configurar"}
                      </button>
                      {p.is_configured && (
                        <Toggle
                          checked={enabled}
                          onChange={(v) => toggleProviderEnabled(p.provider, v)}
                          label={`Usar ${p.label} en el enrutado`}
                        />
                      )}
                    </div>
                  </div>

                  {/* Selector de modelo: una API key da acceso a varios modelos.
                      El elegido aquí es el PRIMARIO del proveedor; el MEL puede
                      usar el resto por capacidad si le convienen. */}
                  {p.is_configured && models.length > 0 ? (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[11px] text-ink-dim shrink-0">Modelo</span>
                      <select
                        value={p.model || ""}
                        onChange={(e) => handleSelectModel(p.provider, e.target.value)}
                        className="bg-base-900 border border-base-600 rounded px-2 py-1 text-ink text-[11px] flex-1 min-w-0"
                      >
                        {!models.includes(p.model || "") && p.model && (
                          <option value={p.model}>{p.model}</option>
                        )}
                        {models.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                  ) : (
                    <p className="text-xs text-ink-faint mt-1">{p.model || "—"}</p>
                  )}

                  {p.has_api_key && p.api_key_preview && (
                    <p className="text-[11px] text-ink-faint mt-1 opacity-50">key: {p.api_key_preview}</p>
                  )}
                  {!p.has_api_key && p.requires_key && (
                    <p className="text-xs text-signal-warn mt-1">Sin API key — pulsa "Configurar"</p>
                  )}
                </div>
                );
              })}
            </div>

            {/* V1.0 (MEL E2): Inteligencia — qué modelo ejecuta cada tarea */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Inteligencia</h3>
              <IntelligenceSettings />
            </div>

            {/* V0.9 (Automation Engine A3b): Permisos & Autonomía */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Permisos</h3>
              <PermissionsSettings />
            </div>

            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Configuración local</h3>
              <div className="text-xs text-ink-dim space-y-2">
                <p>• Backend: http://localhost:8000 {backendConnected ? "✓" : "✗"}</p>
                <p>• Frontend: http://localhost:5173</p>
                <p>• Base de datos: %APPDATA%/Aithera/aithera.db</p>
              </div>
            </div>

            {/* AVCS S3: rendimiento de la presencia visual (PerformanceManager v0) */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Presencia visual</h3>
              <AvcsPerformanceSettings />
            </div>

            {/* V0.7 (Fase 4): seccion Google (OAuth) */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">
                Google (Gmail + Calendar)
              </h3>
              <p className="text-[10px] text-ink-faint mb-3">
                Configura las credenciales OAuth para conectar Aithera con
                Google. Las reglas de auto-respuesta funcionan SIN OAuth, solo
                la lectura/envio de emails reales lo requiere.
              </p>
              <EmailGoogleStatus />
            </div>

            {/* V0.83: seccion ElevenLabs (API key para voces profesionales) */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">
                ElevenLabs (voz)
              </h3>
              <p className="text-xs text-ink-dim mb-3">
                API key para las voces profesionales de Aithera. Se guarda cifrada. Sin
                key, la voz usa eSpeak (offline).
              </p>
              <ElevenLabsSettings />
            </div>

            {/* V1.0/1.1 (Tools): seccion Busqueda web (Search Tool) */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Búsqueda web</h3>
              <SearchSettings />
            </div>

            {/* V0.8 (Fase 5 Clientes): seccion Telegram */}
            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">
                Telegram (bot)
              </h3>
              <p className="text-xs text-ink-dim mb-3">
                Chatea con Aithera desde Telegram. El token se guarda cifrado y solo
                los chat_id que autorices pueden usar el bot.
              </p>
              <TelegramSettings />
            </div>

            {/* V0.6 (Fase 3 Memory System): seccion Memoria (ChromaDB) */}
            <div className="glass-surface rounded-2xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-ink">Memoria semantica (ChromaDB)</h3>
                <button
                  onClick={loadMemory}
                  disabled={memLoading}
                  className="text-xs px-2 py-1 rounded bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600 disabled:opacity-50"
                >
                  {memLoading ? "Cargando..." : "Refrescar"}
                </button>
              </div>

              {!memStats ? (
                <p className="text-xs text-ink-dim">Cargando estadisticas...</p>
              ) : !memStats.healthy ? (
                <div className="text-xs text-signal-warn space-y-1">
                  <p>⚠ Memory system no disponible.</p>
                  {memStats.error && <p className="text-ink-faint font-mono">{memStats.error}</p>}
                  <p className="text-ink-faint">El chat sigue funcionando, pero sin memoria semantica.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-xs text-ink-dim grid grid-cols-3 gap-2">
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">Conversaciones</p>
                      <p className="text-ink font-medium text-base">{memStats.conversations}</p>
                    </div>
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">Preferencias</p>
                      <p className="text-ink font-medium text-base">{memStats.user_context}</p>
                    </div>
                    <div className="bg-base-900/40 rounded-lg p-2">
                      <p className="text-ink-faint text-[10px] uppercase tracking-wider">Documentos</p>
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
                    <h4 className="text-xs font-medium text-ink mb-2">Anadir preferencia / hecho</h4>
                    <p className="text-[10px] text-ink-faint mb-2">
                      Aithera usara esto como contexto automatico en futuros chats.
                    </p>
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={newCtxKey}
                        onChange={(e) => setNewCtxKey(e.target.value)}
                        placeholder="key (ej. meeting_preference)"
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <input
                        type="text"
                        value={newCtxCategory}
                        onChange={(e) => setNewCtxCategory(e.target.value)}
                        placeholder="categoria (default: preference)"
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <textarea
                        value={newCtxContent}
                        onChange={(e) => setNewCtxContent(e.target.value)}
                        placeholder="Contenido (ej. Prefiero reuniones por la tarde)"
                        rows={2}
                        className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                      />
                      <button
                        onClick={handleAddContext}
                        className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
                      >
                        Guardar preferencia
                      </button>
                    </div>
                  </div>

                  {/* Lista de preferencias */}
                  <div className="border-t border-base-700/50 pt-3">
                    <h4 className="text-xs font-medium text-ink mb-2">
                      Preferencias guardadas ({contextItems.length})
                    </h4>
                    {contextItems.length === 0 ? (
                      <p className="text-xs text-ink-faint">No hay preferencias guardadas aun.</p>
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
                              Eliminar
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
                      Borrar historial de conversaciones ({memStats.conversations})
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
