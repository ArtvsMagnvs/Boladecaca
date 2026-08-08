// components/settings/McpPanel.tsx — servidores MCP externos (V1.2 C1 + C1b)
//
// Dos pestañas:
//   DIRECTORIO   — catálogo CURADO (mcpCatalog.json, estático y verificado)
//                  con «Conectar» de un clic, más búsqueda en el registro
//                  OFICIAL para lo que no esté en la lista.
//   CONECTADOS   — lo que el usuario ya tiene, con su estado real, «Probar»,
//                  activar/desactivar, borrar, y el alta manual de siempre.
//
// El catálogo es local a propósito (mismo patrón que `skillsCatalog.json`,
// PU2): el panel funciona sin red, y solo el segundo nivel — la búsqueda en el
// registro — necesita internet.
import { useEffect, useMemo, useState } from "react";

import catalog from "@/data/mcpCatalog.json";
import { api, McpDirectoryEntry, McpServer, McpServerIn } from "@/lib/api";
import { useT } from "@/store/useI18n";

import McpConnectForm, { ConnectTarget } from "./McpConnectForm";

type CatalogServer = {
  slug: string;
  category: string;
  title: string;
  description_es: string;
  config: { transport: "stdio" | "sse" | "http"; command?: string; args?: string[]; url?: string };
  secrets: { key: string; kind: "env" | "header"; label_es: string;
             help_url?: string; required?: boolean; prefix?: string }[];
  context_hints: string;
};

const CATALOG = catalog as unknown as {
  categories: { id: string; label_es: string }[];
  servers: CatalogServer[];
};

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
  const [tab, setTab] = useState<"directorio" | "conectados">("directorio");
  const [servers, setServers] = useState<McpServer[]>([]);
  const [target, setTarget] = useState<ConnectTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  const refresh = async () => {
    try { setServers(await api.getMcpServers()); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  const conectados = useMemo(() => new Set(servers.map((s) => s.name)), [servers]);

  const afterConnect = async () => {
    setTarget(null);
    await refresh();
    setTab("conectados");
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-dim">{tr("connections.mcp.desc")}</p>
      <p className="text-[10px] text-ink-faint">{tr("connections.mcp.gateNote")}</p>

      <div className="flex gap-1">
        {(["directorio", "conectados"] as const).map((id) => (
          <button key={id} type="button" onClick={() => { setTab(id); setTarget(null); }}
                  className={`text-[11px] px-3 py-1.5 rounded-lg border transition-colors ${
                    tab === id ? "border-accent/50 bg-accent/10 text-ink"
                               : "border-base-700 text-ink-dim hover:text-ink"}`}>
            {id === "directorio"
              ? tr("connections.mcp.tabDirectory")
              : `${tr("connections.mcp.tabConnected")} (${servers.length})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {target && (
        <McpConnectForm target={target} onDone={afterConnect} onCancel={() => setTarget(null)} />
      )}

      {tab === "directorio" && !target && (
        <Directory conectados={conectados} onPick={setTarget} onError={setError} />
      )}

      {tab === "conectados" && !target && (
        <Connected servers={servers} refresh={refresh} testing={testing}
                   setTesting={setTesting} onError={setError} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DIRECTORIO — catálogo curado + búsqueda en el registro oficial
// ---------------------------------------------------------------------------
function Directory({ conectados, onPick, onError }: {
  conectados: Set<string>;
  onPick: (t: ConnectTarget) => void;
  onError: (e: string | null) => void;
}) {
  const tr = useT();
  const [cat, setCat] = useState<string>("todas");
  const [q, setQ] = useState("");
  const [results, setResults] = useState<McpDirectoryEntry[] | null>(null);
  const [searching, setSearching] = useState(false);

  const visibles = CATALOG.servers.filter((s) => cat === "todas" || s.category === cat);

  const fromCatalog = (s: CatalogServer): ConnectTarget => ({
    slug: s.slug, title: s.title, description: s.description_es,
    transport: s.config.transport, command: s.config.command,
    args: s.config.args, url: s.config.url,
    secrets: s.secrets.map((x) => ({
      key: x.key, kind: x.kind, label: x.label_es,
      help_url: x.help_url, required: x.required, prefix: x.prefix,
    })),
  });

  const fromRegistry = (e: McpDirectoryEntry): ConnectTarget => ({
    slug: e.suggested_slug, title: e.title, description: e.description,
    transport: (e.transport || "stdio") as "stdio" | "sse" | "http",
    command: e.command, args: e.args, url: e.url,
    secrets: e.secrets.map((s) => ({
      key: s.key, kind: s.kind, label: s.description || s.key, required: s.required,
    })),
    provenance: e.repository_url || e.name,
  });

  const search = async () => {
    if (!q.trim() || searching) return;
    setSearching(true); onError(null);
    try {
      setResults((await api.searchMcpDirectory(q.trim())).results);
    } catch (e) {
      onError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1">
        {[{ id: "todas", label_es: tr("connections.mcp.allCategories") }, ...CATALOG.categories]
          .map((c) => (
            <button key={c.id} type="button" onClick={() => setCat(c.id)}
                    className={`text-[10px] px-2 py-1 rounded-full border transition-colors ${
                      cat === c.id ? "border-accent/50 bg-accent/10 text-ink"
                                   : "border-base-700 text-ink-faint hover:text-ink-dim"}`}>
              {c.label_es}
            </button>
          ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {visibles.map((s) => {
          const ya = conectados.has(s.slug);
          return (
            <div key={s.slug}
                 className="rounded-xl p-3 border border-base-700 bg-base-800/40 flex flex-col gap-1.5">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium text-ink">{s.title}</span>
                {ya ? (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok shrink-0">
                    {tr("connections.mcp.alreadyConnected")}
                  </span>
                ) : (
                  <button type="button" onClick={() => onPick(fromCatalog(s))}
                          className="text-[11px] px-2 py-1 rounded-lg bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 shrink-0">
                    {tr("connections.mcp.connect")}
                  </button>
                )}
              </div>
              <p className="text-[11px] text-ink-faint leading-snug">{s.description_es}</p>
            </div>
          );
        })}
      </div>

      <div className="pt-2 border-t border-base-700 space-y-2">
        <p className="text-[11px] text-ink-dim">{tr("connections.mcp.notListed")}</p>
        <div className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") search(); }}
                 placeholder={tr("connections.mcp.searchPlaceholder")}
                 className="flex-1 bg-base-900/60 border border-base-700 rounded-lg px-2 py-1.5 text-xs text-ink" />
          <button type="button" onClick={search} disabled={searching || !q.trim()}
                  className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink disabled:opacity-50">
            {searching ? tr("connections.mcp.searching") : tr("connections.mcp.search")}
          </button>
        </div>

        {results !== null && results.length === 0 && !searching && (
          <p className="text-[11px] text-ink-faint">{tr("connections.mcp.noResults")}</p>
        )}
        {results !== null && results.length > 0 && (
          <>
            <p className="text-[10px] text-ink-faint">{tr("connections.mcp.registryWarning")}</p>
            <div className="space-y-1.5">
              {results.map((e) => (
                <div key={e.name}
                     className="rounded-lg p-2.5 border border-base-700 bg-base-800/30 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs text-ink truncate">{e.title}</p>
                    <p className="text-[10px] text-ink-faint line-clamp-2">{e.description}</p>
                    <p className="text-[10px] text-ink-faint mt-0.5 truncate">
                      {e.repository_url || e.name}
                    </p>
                    {!e.connectable && (
                      <p className="text-[10px] text-signal-warn mt-0.5">{e.reason}</p>
                    )}
                  </div>
                  {e.connectable && !conectados.has(e.suggested_slug) && (
                    <button type="button" onClick={() => onPick(fromRegistry(e))}
                            className="text-[11px] px-2 py-1 rounded-lg bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 shrink-0">
                      {tr("connections.mcp.connect")}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CONECTADOS — estado real + alta manual (lo de C1)
// ---------------------------------------------------------------------------
function Connected({ servers, refresh, testing, setTesting, onError }: {
  servers: McpServer[];
  refresh: () => Promise<void>;
  testing: string | null;
  setTesting: (v: string | null) => void;
  onError: (e: string | null) => void;
}) {
  const tr = useT();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (busy) return;
    setBusy(true); onError(null);
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
      onError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setBusy(false);
    }
  };

  const test = async (name: string) => {
    if (testing) return;
    setTesting(name); onError(null);
    try {
      await api.testMcpServer(name);
    } catch (e) {
      onError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
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
    <div className="space-y-2">
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
            <span className="font-mono">
              {srv.transport === "stdio" ? `${srv.command} ${srv.args.join(" ")}` : srv.url}
            </span>
          </p>
          <p className="text-[10px] text-ink-faint">
            {tr("connections.mcp.useIt", { slug: srv.name })}
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
                       placeholder="-y @modelcontextprotocol/server-memory"
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
                    onClick={() => { setShowForm(false); setForm({ ...EMPTY_FORM }); onError(null); }}
                    className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink">
              {tr("common.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
