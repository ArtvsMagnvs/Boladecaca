// CodexSetup.tsx — instalar + iniciar sesión en Codex CLI desde Ajustes (2026-07-24)
//
// Petición del usuario: que cualquiera pueda activar Codex con un botón. Aquí:
//   · "Instalar Codex" → npm install -g @openai/codex (backend, con progreso).
//   · "Iniciar sesión"  → codex login (abre el navegador del usuario; Aithera
//     NUNCA teclea las credenciales — el usuario inicia sesión con su cuenta de
//     ChatGPT, como en un OAuth normal).
//   · Guía rápida SIEMPRE visible como respaldo (comandos exactos por si algo
//     falla o se prefiere la terminal).
// Se sondea el estado mientras hay una instalación/login en curso.
import { useState } from "react";
import { api } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import { useT } from "@/store/useI18n";

type CodexStatus = Awaited<ReturnType<typeof api.getCodexStatus>>;

export default function CodexSetup() {
  const tr = useT();
  const [st, setSt] = useState<CodexStatus | null>(null);
  const [busy, setBusy] = useState<"install" | "login" | null>(null);

  // NOTA: este componente es AUTÓNOMO — no avisa al padre cuando Codex queda
  // listo. Se probó `onReady={loadData}` y causaba un BUCLE INFINITO: loadData
  // hace setLoading(true), y la sección de proveedores (que contiene esta
  // tarjeta) vive dentro de `{loading ? spinner : …}`; al poner loading=true la
  // tarjeta se DESMONTA y al volver a false se REMONTA → vuelve a sondear →
  // ready → loadData → loading → remonta… sin fin. El estado listo se ve aquí
  // ("✓ … pulsa Activar") y el botón "Activar" del card ya refresca la lista.
  const refresh = async () => {
    try {
      const s = await api.getCodexStatus();
      setSt(s);
      // Al terminar una acción en curso, soltar el "busy".
      if (busy === "install" && s.install_status !== "installing") setBusy(null);
      if (busy === "login" && s.login_status !== "running") setBusy(null);
    } catch { /* silencioso: se reintenta en el próximo poll */ }
  };

  // Sondeo activo solo mientras hay algo en marcha (o aún no sabemos el estado).
  const live = busy !== null || st == null ||
    st.install_status === "installing" || st.login_status === "running";
  usePolling(refresh, 2000, live);

  const doInstall = async () => {
    setBusy("install");
    try { await api.installCodex(); } catch { /* el estado lo refleja el poll */ }
    refresh();
  };
  const doLogin = async () => {
    setBusy("login");
    try { await api.loginCodex(); } catch { /* idem */ }
    refresh();
  };

  const installed = st?.installed ?? false;
  const authed = st?.authenticated ?? false;
  const installing = busy === "install" || st?.install_status === "installing";
  const loggingIn = busy === "login" || st?.login_status === "running";

  return (
    <div className="text-[11px] text-ink-dim mt-2 space-y-2">
      {/* Estado + botones de 1 clic */}
      <div className="flex items-center gap-2 flex-wrap">
        {!installed ? (
          <button
            onClick={doInstall}
            disabled={installing}
            className="text-xs px-2.5 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
          >
            {installing ? tr("settings.codex.installing") : tr("settings.codex.installBtn")}
          </button>
        ) : !authed ? (
          <button
            onClick={doLogin}
            disabled={loggingIn}
            className="text-xs px-2.5 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
          >
            {loggingIn ? tr("settings.codex.loggingIn") : tr("settings.codex.loginBtn")}
          </button>
        ) : (
          <span className="text-signal-ok">✓ {tr("settings.codex.ready")}</span>
        )}
      </div>

      {/* Línea de estado legible */}
      {!authed && (
        <p className="text-ink-faint">
          {!installed
            ? (st?.npm_available === false ? tr("settings.codex.noNpm") : tr("settings.codex.needInstall"))
            : tr("settings.codex.needLogin")}
        </p>
      )}

      {/* Detalle del proceso en curso / error */}
      {installing && st?.install_detail && (
        <p className="text-ink-faint break-words">{st.install_detail}</p>
      )}
      {st?.install_status === "failed" && st?.install_detail && (
        <p className="text-signal-error break-words">✗ {st.install_detail}</p>
      )}
      {loggingIn && st?.login_detail && (
        <p className="text-ink-faint break-words">{st.login_detail}</p>
      )}
      {/* Si el navegador no se abrió solo, la URL para abrirla a mano */}
      {st?.login_url && !authed && (
        <p className="break-all">
          {tr("settings.codex.openUrl")}{" "}
          <a href={st.login_url} target="_blank" rel="noreferrer" className="text-accent underline">
            {st.login_url}
          </a>
        </p>
      )}
      {st?.login_status === "failed" && st?.login_detail && (
        <p className="text-signal-error break-words">✗ {st.login_detail}</p>
      )}

      {/* Guía rápida SIEMPRE visible (respaldo realista) */}
      <details className="mt-1">
        <summary className="cursor-pointer text-ink-faint">{tr("settings.codex.guideTitle")}</summary>
        <div className="mt-1 space-y-1">
          <p>{tr("settings.codex.guideInstall")}</p>
          <pre className="bg-base-900 border border-base-700 rounded px-2 py-1 overflow-x-auto">npm install -g @openai/codex</pre>
          <p>{tr("settings.codex.guideLogin")}</p>
          <pre className="bg-base-900 border border-base-700 rounded px-2 py-1 overflow-x-auto">codex login</pre>
          <p className="text-ink-faint">{tr("settings.codex.guideApiKey")}</p>
        </div>
      </details>
    </div>
  );
}
