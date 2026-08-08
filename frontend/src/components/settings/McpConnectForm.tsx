// components/settings/McpConnectForm.tsx — conectar UN servicio (V1.2 C1b/C1c)
//
// DOS CAMINOS, según lo que ofrezca el servicio:
//
//   OAUTH (el bueno, y el que se usa siempre que se puede): un botón. Se abre
//   la página del PROPIO servicio, el usuario pulsa «Authorize» allí, y
//   vuelve. Aithera nunca ve su contraseña ni le pide ningún token.
//
//   TOKEN (solo cuando el servicio no ofrece lo anterior): se piden las claves
//   que el servidor declara necesitar, con su enlace de «¿dónde consigo esto?».
//
// DOS REGLAS DE LA UI, las dos deliberadas:
//   1. El comando o la URL se MUESTRAN siempre antes de conectar. Es código
//      externo: el usuario tiene derecho a ver qué se va a ejecutar.
//   2. Los secretos se envían y no vuelven (el backend solo devuelve los
//      NOMBRES de las claves guardadas).
import { useEffect, useRef, useState } from "react";

import { api, McpServerIn } from "@/lib/api";
import { useT } from "@/store/useI18n";

export interface ConnectTarget {
  slug: string;
  title: string;
  description: string;
  transport: "stdio" | "sse" | "http";
  auth: "oauth" | "token" | "none";
  command?: string;
  args?: string[];
  url?: string;
  secrets: {
    key: string;
    kind: "env" | "header";
    label: string;
    help_url?: string;
    required?: boolean;
    prefix?: string;      // p.ej. "Bearer " — se antepone al valor tecleado
  }[];
  provenance?: string;    // repo/origen, para lo que viene del registro
}

export default function McpConnectForm({
  target, onDone, onCancel,
}: {
  target: ConnectTarget;
  onDone: () => void;
  onCancel: () => void;
}) {
  const tr = useT();
  const [slug, setSlug] = useState(target.slug);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"form" | "testing" | "waiting">("form");
  const [authorizeUrl, setAuthorizeUrl] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => () => { if (pollRef.current) window.clearInterval(pollRef.current); }, []);

  const faltan = target.secrets.filter(
    (s) => s.required && !(values[s.key] || "").trim());

  // --- Camino OAuth: un botón, y el usuario autoriza en la web del servicio ---
  const authorize = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const r = await api.startMcpOAuth({
        name: slug.trim().toLowerCase(),
        url: target.url || "",
        description: target.description,
      });
      setAuthorizeUrl(r.authorize_url);
      setStep("waiting");
      window.open(r.authorize_url, "_blank", "noopener,noreferrer");
      // Esperar a que el servicio quede conectado (la autorización la
      // completa el usuario fuera de aquí; esto solo mira el resultado).
      pollRef.current = window.setInterval(async () => {
        try {
          const servers = await api.getMcpServers();
          const yo = servers.find((s) => s.name === r.name);
          if (yo?.connected || yo?.authorized) {
            if (pollRef.current) window.clearInterval(pollRef.current);
            onDone();
          }
        } catch { /* seguimos esperando */ }
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
      setStep("form");
    } finally {
      setBusy(false);
    }
  };

  // --- Camino token / sin credenciales ---
  const connect = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const env: Record<string, string> = {};
      const headers: Record<string, string> = {};
      for (const s of target.secrets) {
        const v = (values[s.key] || "").trim();
        if (!v) continue;
        const final = (s.prefix || "") + v;
        if (s.kind === "header") headers[s.key] = final;
        else env[s.key] = final;
      }
      const body: McpServerIn = {
        name: slug.trim().toLowerCase(),
        transport: target.transport,
        command: target.command || "",
        args: target.args || [],
        url: target.url || "",
        description: target.description,
        enabled: true,
        auth: target.auth,
        env,
        headers,
      };
      await api.upsertMcpServer(body);
      // Probar AUTOMÁTICAMENTE: conectar sin comprobar que funciona deja al
      // usuario con la duda hasta la primera misión que lo necesite.
      setStep("testing");
      try {
        await api.testMcpServer(body.name);
      } catch (e) {
        setError(tr("connections.mcp.savedButFailed") + " " +
                 (e instanceof Error ? e.message : ""));
        setBusy(false);
        return;
      }
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
      setStep("form");
    } finally {
      setBusy(false);
    }
  };

  const comando = target.transport === "stdio"
    ? `${target.command} ${(target.args || []).join(" ")}`.trim()
    : target.url || "";

  // --- Esperando a que el usuario autorice en su navegador ---
  if (step === "waiting") {
    return (
      <div className="rounded-xl p-4 border border-accent/40 bg-accent/5 space-y-3">
        <p className="text-sm font-medium text-ink">{target.title}</p>
        <p className="text-xs text-ink-dim">{tr("connections.mcp.waitingAuth")}</p>
        {authorizeUrl && (
          <p className="text-[10px] text-ink-faint break-all">
            {tr("connections.mcp.didntOpen")}{" "}
            <a href={authorizeUrl} target="_blank" rel="noreferrer"
               className="text-accent hover:underline">{authorizeUrl}</a>
          </p>
        )}
        <button type="button" onClick={onCancel}
                className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink">
          {tr("common.cancel")}
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-4 border border-accent/40 bg-accent/5 space-y-3">
      <div>
        <p className="text-sm font-medium text-ink">{target.title}</p>
        {target.description && (
          <p className="text-[11px] text-ink-dim mt-0.5 leading-snug">{target.description}</p>
        )}
      </div>

      {/* Qué se va a ejecutar / a dónde se va a conectar — SIEMPRE visible. */}
      <div>
        <p className="text-[10px] text-ink-faint mb-1">
          {target.transport === "stdio"
            ? tr("connections.mcp.willRun") : tr("connections.mcp.willConnect")}
        </p>
        <code className="block text-[10px] text-ink-dim bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 break-all">
          {comando}
        </code>
        {target.provenance && (
          <p className="text-[10px] text-ink-faint mt-1">
            {tr("connections.mcp.source")}:{" "}
            <span className="text-ink-dim break-all">{target.provenance}</span>
          </p>
        )}
      </div>

      <label className="block text-[11px] text-ink-dim">
        {tr("connections.mcp.commandName")}
        <input
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono"
        />
        <span className="text-[10px] text-ink-faint">
          {tr("connections.mcp.commandNameHint", { slug: slug || "servicio" })}
        </span>
      </label>

      {target.auth === "oauth" ? (
        <p className="text-[11px] text-ink-dim bg-base-900/40 border border-base-700 rounded-lg px-3 py-2">
          {tr("connections.mcp.oauthExplain")}
        </p>
      ) : (
        target.secrets.map((s) => (
          <label key={s.key} className="block text-[11px] text-ink-dim">
            {s.label}
            {s.required && <span className="text-signal-warn"> *</span>}
            <input
              type="password"
              autoComplete="off"
              value={values[s.key] || ""}
              onChange={(e) => setValues({ ...values, [s.key]: e.target.value })}
              className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono"
            />
            {s.help_url && (
              <a href={s.help_url} target="_blank" rel="noreferrer"
                 className="text-[10px] text-accent hover:underline">
                {tr("connections.mcp.whereToGet")}
              </a>
            )}
          </label>
        ))
      )}

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        {target.auth === "oauth" ? (
          <button type="button" onClick={authorize} disabled={busy}
                  className="text-xs px-3 py-1.5 rounded-lg bg-accent/20 border border-accent/50 text-ink hover:bg-accent/30 disabled:opacity-50">
            {busy ? tr("connections.mcp.opening") : tr("connections.mcp.authorize")}
          </button>
        ) : (
          <button type="button" onClick={connect} disabled={busy || faltan.length > 0}
                  className="text-xs px-3 py-1.5 rounded-lg bg-accent/20 border border-accent/50 text-ink hover:bg-accent/30 disabled:opacity-50">
            {step === "testing" ? tr("connections.mcp.testing") : tr("connections.mcp.connect")}
          </button>
        )}
        <button type="button" onClick={onCancel} disabled={busy}
                className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink">
          {tr("common.cancel")}
        </button>
      </div>
    </div>
  );
}
