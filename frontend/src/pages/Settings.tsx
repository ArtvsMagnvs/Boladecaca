// FIX V0.2: Página de Configuración completamente reescrita.
// Ahora incluye formulario para introducir API keys directamente desde la UI,
// sin necesidad de editar el .env ni llamar a la API manualmente.
// V0.6 (Fase 3 Memory System): nueva seccion "Memoria" con stats, gestion
// de preferencias del usuario y borrado del historial de ChromaDB.
import { useState, useEffect } from "react";
import { api, type AIProviderEntry, type ContextItem, type MemoryStats } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";


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
      const [providersData, statusData] = await Promise.all([
        api.getConfiguredProviders(),
        api.getAIStatus()
      ]);
      setProviders(providersData);
      setAiStatus(statusData);
    } catch (e) {
      console.error("Error cargando configuración:", e);
    } finally {
      setLoading(false);
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

      {/* Proveedores */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="text-center text-ink-dim py-10">Cargando...</div>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-medium text-ink mb-3">Proveedores de IA</h3>
              {providers.map(p => (
                <div key={p.provider} className="glass-surface rounded-xl p-4 mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-ink text-sm">{p.label}</span>
                      {p.is_active && <span className="text-xs px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">Activo</span>}
                      {p.has_api_key && !p.is_active && <span className="text-xs px-2 py-0.5 rounded bg-base-700 text-ink-dim">Configurado</span>}
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(p)} className="text-xs px-2 py-1 rounded bg-base-700 text-ink-dim border border-base-600 hover:bg-base-600">
                        {p.has_api_key ? "Editar" : "Configurar"}
                      </button>
                      {!p.is_active && p.is_configured && (
                        <button onClick={() => handleActivate(p.provider)} className="text-xs px-2 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25">
                          Activar
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-ink-faint">
                    {p.model || "—"}
                    {p.has_api_key && p.api_key_preview && <span className="ml-2 opacity-50">key: {p.api_key_preview}</span>}
                  </p>
                  {!p.has_api_key && p.requires_key && (
                    <p className="text-xs text-signal-warn mt-1">Sin API key — pulsa "Configurar"</p>
                  )}
                </div>
              ))}
            </div>

            <div className="glass-surface rounded-2xl p-4">
              <h3 className="text-sm font-medium text-ink mb-3">Configuración local</h3>
              <div className="text-xs text-ink-dim space-y-2">
                <p>• Backend: http://localhost:8000 {backendConnected ? "✓" : "✗"}</p>
                <p>• Frontend: http://localhost:5173</p>
                <p>• Base de datos: %APPDATA%/Aithera/aithera.db</p>
              </div>
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
  );
}
