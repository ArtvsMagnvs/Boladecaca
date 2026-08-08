// components/settings/McpPanel.tsx — servidores MCP externos (V1.2 C1)
//
// La UI de "conectar un servidor MCP": lista de servidores con estado real
// (conectado / error / desactivado), botón Probar (la única llamada cara —
// lanza el proceso o abre la URL y descubre las tools), y formulario de alta
// PLEGADO por defecto (revelación progresiva, patrón PU10-visual). Los
// secretos (tokens en variables de entorno / headers) se ENVÍAN y no vuelven:
// el backend solo devuelve los NOMBRES de las claves guardadas.
import { useEffect, useState } from "react";

import { api, McpServer, McpServerIn } from "@/lib/api";
import { useT } from "@/store/useI18n";

function parseKeyValueLines(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0) {
      const k = line.slice(0, idx).trim();
      const v = line.slice(idx + 1).trim();
      if (k) out[k] = v;
    }
  }
  return out;
}

const EMPTY_FORM = {
  name: "", transport: "stdio" as "stdio" | "sse" | "http",
  command: "", args: "", url: "", description: "", env: "", headers: "",
};

export default function McpPanel() {
  const tr = useT();
  const [servers, setServers] = useState<McpServer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try { setServers(await api.getMcpServers()); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  const save = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const data: McpServerIn = {
        name: form.name.trim().toLowerCase(),
        transport: form.transport,
        command: form.command.trim(),
        args: form.args.split(/\s+/).filter(Boolean),
        url: form.url.trim(),
        description: form.description.trim(),
        enabled: true,
      };
      const env = parseKeyValueLines(form.env);
      const headers = parseKeyValueLines(form.headers);
      if (Object.keys(env).length || Object.keys(headers).length) {
        data.env = env;
        data.headers = headers;
      }
      await api.upsertMcpServer(data);
      setForm({ ...EMPTY_FORM });
      setShowForm(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setBusy(false);
    }
  };

  const test = async (name: string) => {
    if (testing) return;
    setTesting(name); setError(null);
    try {
      await api.testMcpServer(name);
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setTesting(null);
      await refresh();
    }
  };

  const toggle = async (srv: McpServer) => {
    try {
      await api.upsertMcpServer({
        name: srv.name, transport: srv.transport, command: srv.command,
        args: srv.args, url: srv.url, description: srv.description,
        enabled: !srv.enabled,
      });
      await refresh();
    } catch (e) { console.error(e); }
  };

  const remove = async (name: string) => {
    if (!window.confirm(tr("connections.mcp.confirmDelete"))) return;
    try { await api.deleteMcpServer(name); await refresh(); }
    catch (e) { console.error(e); }
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">{tr("connections.mcp.desc")}</p>
      <p className="text-[10px] text-ink-faint">{tr("connections.mcp.gateNote")}</p>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {servers.length === 0 && !showForm && (
        <div className="border border-dashed border-base-700 rounded-xl p-4 text-center text-xs text-ink-faint">
          {tr("connections.mcp.empty")}
        </div>
      )}

      {servers.map((srv) => (
        <div key={srv.name}
             className="rounded-xl p-3 border border-base-700 bg-base-800/40 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-medium text-ink truncate">{srv.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-base-700 text-ink-dim uppercase">
                {srv.transport}
              </span>
              {!srv.enabled ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-faint">
                  {tr("connections.mcp.disabled")}
                </span>
              ) : srv.connected ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
                  {tr("common.connected")}
                </span>
              ) : null}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <button type="button" onClick={() => test(srv.name)}
                      disabled={!srv.enabled || testing !== null}
                      className="text-[11px] px-2 py-1 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-base-500 disabled:opacity-50">
                {testing === srv.name
                  ? tr("connections.mcp.testing") : tr("connections.mcp.test")}
              </button>
              <button type="button" onClick={() => toggle(srv)}
                      className="text-[11px] px-2 py-1 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-base-500">
                {srv.enabled ? tr("common.disable") : tr("common.enable")}
              </button>
              <button type="button" onClick={() => remove(srv.name)}
                      className="text-[11px] px-2 py-1 rounded-lg border border-signal-error/40 text-signal-error hover:bg-signal-error/10">
                {tr("common.delete")}
              </button>
            </div>
          </div>
          {srv.description && (
            <p className="text-[11px] text-ink-faint">{srv.description}</p>
          )}
          <p className="text-[10px] text-ink-faint">
            {srv.tools_count > 0 && (
              <span>{srv.tools_count} {tr("connections.mcp.tools")} · </span>
            )}
            {srv.transport === "stdio"
              ? <span className="font-mono">{srv.command} {srv.args.join(" ")}</span>
              : <span className="font-mono">{srv.url}</span>}
          </p>
          {(srv.secret_keys.env.length > 0 || srv.secret_keys.headers.length > 0) && (
            <p className="text-[10px] text-ink-faint">
              {tr("connections.mcp.secrets")}:{" "}
              {[...srv.secret_keys.env, ...srv.secret_keys.headers].join(", ")}
            </p>
          )}
          {srv.last_error && (
            <p className="text-[10px] text-signal-error">{srv.last_error}</p>
          )}
        </div>
      ))}

      {!showForm ? (
        <button type="button" onClick={() => setShowForm(true)}
                className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-base-500">
          {tr("connections.mcp.add")}
        </button>
      ) : (
        <div className="rounded-xl p-3 border border-base-700 bg-base-800/40 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-ink-dim">
              {tr("connections.mcp.name")}
              <input value={form.name}
                     onChange={(e) => setForm({ ...form, name: e.target.value })}
                     placeholder="github"
                     className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink" />
            </label>
            <label className="text-[11px] text-ink-dim">
              {tr("connections.mcp.transport")}
              <select value={form.transport}
                      onChange={(e) => setForm({ ...form, transport: e.target.value as "stdio" | "sse" | "http" })}
                      className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink">
                <option value="stdio">stdio ({tr("connections.mcp.stdioHint")})</option>
                <option value="http">HTTP ({tr("connections.mcp.httpHint")})</option>
                <option value="sse">SSE</option>
              </select>
            </label>
          </div>
          {form.transport === "stdio" ? (
            <div className="grid grid-cols-2 gap-2">
              <label className="text-[11px] text-ink-dim">
                {tr("connections.mcp.command")}
                <input value={form.command}
                       onChange={(e) => setForm({ ...form, command: e.target.value })}
                       placeholder="npx"
                       className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono" />
              </label>
              <label className="text-[11px] text-ink-dim">
                {tr("connections.mcp.args")}
                <input value={form.args}
                       onChange={(e) => setForm({ ...form, args: e.target.value })}
                       placeholder="-y @modelcontextprotocol/server-github"
                       className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono" />
              </label>
            </div>
          ) : (
            <label className="block text-[11px] text-ink-dim">
              {tr("connections.mcp.url")}
              <input value={form.url}
                     onChange={(e) => setForm({ ...form, url: e.target.value })}
                     placeholder="https://mcp.example.com/mcp"
                     className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono" />
            </label>
          )}
          <label className="block text-[11px] text-ink-dim">
            {tr("connections.mcp.serverDesc")}
            <input value={form.description}
                   onChange={(e) => setForm({ ...form, description: e.target.value })}
                   placeholder={tr("connections.mcp.serverDescPh")}
                   className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink" />
          </label>
          <label className="block text-[11px] text-ink-dim">
            {tr("connections.mcp.env")}
            <textarea value={form.env} rows={2}
                      onChange={(e) => setForm({ ...form, env: e.target.value })}
                      placeholder={"GITHUB_TOKEN=ghp_..."}
                      className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono" />
          </label>
          {form.transport !== "stdio" && (
            <label className="block text-[11px] text-ink-dim">
              {tr("connections.mcp.headers")}
              <textarea value={form.headers} rows={2}
                        onChange={(e) => setForm({ ...form, headers: e.target.value })}
                        placeholder={"Authorization=Bearer ..."}
                        className="mt-1 w-full bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink font-mono" />
            </label>
          )}
          <p className="text-[10px] text-ink-faint">{tr("connections.mcp.envHint")}</p>
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={save} disabled={busy}
                    className="text-xs px-3 py-1.5 rounded-lg bg-accent/20 border border-accent/50 text-ink hover:bg-accent/30 disabled:opacity-50">
              {tr("common.save")}
            </button>
            <button type="button"
                    onClick={() => { setShowForm(false); setForm({ ...EMPTY_FORM }); setError(null); }}
                    className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink">
              {tr("common.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
