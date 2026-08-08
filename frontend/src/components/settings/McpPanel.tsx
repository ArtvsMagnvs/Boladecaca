// components/settings/McpPanel.tsx — pestaña «Servicios» (MCP) (V1.2 C1/C1b/C1c)
//
// Pestaña PROPIA en Ajustes (petición del usuario, 2026-08-08): esto ya no es
// un rincón de «Conexiones». La página, de arriba abajo:
//
//   1. Qué es esto, en dos frases y sin jerga.
//   2. EL BUSCADOR, arriba del todo: filtra el catálogo al teclear y, si no
//      hay nada, ofrece buscar en el registro oficial (miles de servicios).
//   3. Lo ya conectado (solo si hay algo), para que se vea de un vistazo.
//   4. El catálogo por categorías, con «Conectar» de un clic.
//
// La mayoría de servicios se conectan con un botón: se abre su propia web,
// el usuario pulsa «Authorize» y vuelve. Los que no lo permiten piden una
// clave, con enlace a dónde conseguirla.
import { useEffect, useMemo, useRef, useState } from "react";

import catalog from "@/data/mcpCatalog.json";
import { api, McpDirectoryEntry, McpServer, McpServerIn } from "@/lib/api";
import { useT } from "@/store/useI18n";

import McpConnectForm, { ConnectTarget } from "./McpConnectForm";

type CatalogServer = {
  slug: string;
  category: string;
  title: string;
  description_es: string;
  auth: "oauth" | "token" | "none";
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

const norm = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

export default function McpPanel() {
  const tr = useT();
  const [servers, setServers] = useState<McpServer[]>([]);
  const [target, setTarget] = useState<ConnectTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<McpDirectoryEntry[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [showManual, setShowManual] = useState(false);
  const topRef = useRef<HTMLDivElement>(null);

  const refresh = async () => {
    try { setServers(await api.getMcpServers()); } catch (e) { console.error(e); }
  };
  useEffect(() => { refresh(); }, []);

  const conectados = useMemo(() => new Set(servers.map((s) => s.name)), [servers]);

  // El buscador filtra el catálogo local al teclear (instantáneo, sin red).
  const filtrados = useMemo(() => {
    const t = norm(q.trim());
    if (!t) return CATALOG.servers;
    return CATALOG.servers.filter((s) =>
      norm(s.title).includes(t) || norm(s.description_es).includes(t) ||
      norm(s.context_hints).includes(t) || s.slug.includes(t));
  }, [q]);

  const porCategoria = useMemo(() => {
    const m = new Map<string, CatalogServer[]>();
    for (const s of filtrados) {
      if (!m.has(s.category)) m.set(s.category, []);
      m.get(s.category)!.push(s);
    }
    return m;
  }, [filtrados]);

  const fromCatalog = (s: CatalogServer): ConnectTarget => ({
    slug: s.slug, title: s.title, description: s.description_es,
    transport: s.config.transport, auth: s.auth, command: s.config.command,
    args: s.config.args, url: s.config.url,
    secrets: s.secrets.map((x) => ({
      key: x.key, kind: x.kind, label: x.label_es,
      help_url: x.help_url, required: x.required, prefix: x.prefix,
    })),
  });

  const fromRegistry = (e: McpDirectoryEntry): ConnectTarget => ({
    slug: e.suggested_slug, title: e.title, description: e.description,
    transport: (e.transport || "stdio") as "stdio" | "sse" | "http",
    auth: e.secrets.length ? "token" : "none",
    command: e.command, args: e.args, url: e.url,
    secrets: e.secrets.map((s) => ({
      key: s.key, kind: s.kind, label: s.description || s.key, required: s.required,
    })),
    provenance: e.repository_url || e.name,
  });

  const pick = (t: ConnectTarget) => {
    setTarget(t);
    topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const buscarEnRegistro = async () => {
    if (!q.trim() || searching) return;
    setSearching(true); setError(null);
    try {
      setResults((await api.searchMcpDirectory(q.trim())).results);
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div ref={topRef} className="space-y-4">
      {/* 1. Qué es esto */}
      <div>
        <p className="text-xs text-ink-dim leading-relaxed">{tr("mcp.intro")}</p>
        <p className="text-[10px] text-ink-faint mt-1.5">{tr("connections.mcp.gateNote")}</p>
      </div>

      {/* 2. EL BUSCADOR, arriba del todo */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setResults(null); }}
            onKeyDown={(e) => { if (e.key === "Enter" && filtrados.length === 0) buscarEnRegistro(); }}
            placeholder={tr("mcp.searchPlaceholder")}
            className="flex-1 bg-base-900/60 border border-base-700 rounded-lg px-3 py-2 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/40"
          />
          {q.trim() && (
            <button type="button" onClick={buscarEnRegistro} disabled={searching}
                    className="text-xs px-3 py-2 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-base-500 disabled:opacity-50 whitespace-nowrap">
              {searching ? tr("connections.mcp.searching") : tr("mcp.searchRegistry")}
            </button>
          )}
        </div>
        {q.trim() && <p className="text-[10px] text-ink-faint">{tr("mcp.searchHint")}</p>}
      </div>

      {error && (
        <div className="text-xs text-signal-error bg-signal-error/10 border border-signal-error/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {target && (
        <McpConnectForm
          target={target}
          onDone={async () => { setTarget(null); await refresh(); }}
          onCancel={() => setTarget(null)}
        />
      )}

      {/* Resultados del registro oficial (solo si se buscó) */}
      {results !== null && (
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-ink">{tr("mcp.registryResults")}</p>
          {results.length === 0 ? (
            <p className="text-[11px] text-ink-faint">{tr("connections.mcp.noResults")}</p>
          ) : (
            <>
              <p className="text-[10px] text-ink-faint">{tr("connections.mcp.registryWarning")}</p>
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
                    <button type="button" onClick={() => pick(fromRegistry(e))}
                            className="text-[11px] px-2 py-1 rounded-lg bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 shrink-0">
                      {tr("connections.mcp.connect")}
                    </button>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* 3. Lo ya conectado */}
      {servers.length > 0 && (
        <Connected servers={servers} refresh={refresh} testing={testing}
                   setTesting={setTesting} onError={setError} />
      )}

      {/* 4. El catálogo por categorías */}
      {filtrados.length === 0 ? (
        <p className="text-[11px] text-ink-faint">{tr("mcp.noneInCatalog")}</p>
      ) : (
        CATALOG.categories
          .filter((c) => porCategoria.has(c.id))
          .map((c) => (
            <div key={c.id} className="space-y-2">
              <p className="text-[11px] font-medium text-ink-dim uppercase tracking-wide">
                {c.label_es}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {(porCategoria.get(c.id) || []).map((s) => {
                  const ya = conectados.has(s.slug);
                  return (
                    <div key={s.slug}
                         className="rounded-xl p-3 border border-base-700 bg-base-800/40 flex flex-col gap-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <span className="text-sm font-medium text-ink">{s.title}</span>
                          <span className="ml-2 text-[9px] px-1.5 py-0.5 rounded bg-base-700 text-ink-faint align-middle">
                            {s.auth === "oauth" ? tr("mcp.badgeOneClick")
                             : s.auth === "token" ? tr("mcp.badgeToken")
                             : tr("mcp.badgeFree")}
                          </span>
                        </div>
                        {ya ? (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok shrink-0">
                            {tr("connections.mcp.alreadyConnected")}
                          </span>
                        ) : (
                          <button type="button" onClick={() => pick(fromCatalog(s))}
                                  className="text-[11px] px-2.5 py-1 rounded-lg bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 shrink-0">
                            {tr("connections.mcp.connect")}
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] text-ink-faint leading-snug">
                        {s.description_es}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
      )}

      {/* Alta manual, al final: para un servidor propio o de un tercero */}
      <div className="pt-2 border-t border-base-700">
        {!showManual ? (
          <button type="button" onClick={() => setShowManual(true)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-base-500">
            {tr("connections.mcp.add")}
          </button>
        ) : (
          <ManualForm onDone={async () => { setShowManual(false); await refresh(); }}
                      onCancel={() => setShowManual(false)} onError={setError} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lo ya conectado — estado real, probar, activar/desactivar, borrar
// ---------------------------------------------------------------------------
function Connected({ servers, refresh, testing, setTesting, onError }: {
  servers: McpServer[];
  refresh: () => Promise<void>;
  testing: string | null;
  setTesting: (v: string | null) => void;
  onError: (e: string | null) => void;
}) {
  const tr = useT();

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
        enabled: !srv.enabled, auth: srv.auth,
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
      <p className="text-[11px] font-medium text-ink-dim uppercase tracking-wide">
        {tr("mcp.yoursTitle")} ({servers.length})
      </p>
      {servers.map((srv) => (
        <div key={srv.name}
             className="rounded-xl p-3 border border-base-700 bg-base-800/40 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-medium text-ink truncate">{srv.name}</span>
              {!srv.enabled ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-base-700 text-ink-faint">
                  {tr("connections.mcp.disabled")}
                </span>
              ) : srv.connected ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/15 text-signal-ok">
                  {tr("common.connected")}
                </span>
              ) : srv.authorized ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-signal-ok/10 text-signal-ok">
                  {tr("mcp.authorized")}
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
            {tr("connections.mcp.useIt", { slug: srv.name })}
          </p>
          {srv.last_error && (
            <p className="text-[10px] text-signal-error">{srv.last_error}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alta manual — un servidor propio o uno que no está en ningún catálogo
// ---------------------------------------------------------------------------
function ManualForm({ onDone, onCancel, onError }: {
  onDone: () => Promise<void>;
  onCancel: () => void;
  onError: (e: string | null) => void;
}) {
  const tr = useT();
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (busy) return;
    setBusy(true); onError(null);
    try {
      const env = parseKeyValueLines(form.env);
      const headers = parseKeyValueLines(form.headers);
      const data: McpServerIn = {
        name: form.name.trim().toLowerCase(),
        transport: form.transport,
        command: form.command.trim(),
        args: form.args.split(/\s+/).filter(Boolean),
        url: form.url.trim(),
        description: form.description.trim(),
        enabled: true,
        auth: (Object.keys(env).length || Object.keys(headers).length) ? "token" : "none",
      };
      if (Object.keys(env).length || Object.keys(headers).length) {
        data.env = env;
        data.headers = headers;
      }
      await api.upsertMcpServer(data);
      await onDone();
    } catch (e) {
      onError(e instanceof Error ? e.message : tr("connections.mcp.errGeneric"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl p-3 border border-base-700 bg-base-800/40 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <label className="text-[11px] text-ink-dim">
          {tr("connections.mcp.name")}
          <input value={form.name}
                 onChange={(e) => setForm({ ...form, name: e.target.value })}
                 placeholder="mi-servicio"
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
                   placeholder="-y mi-paquete-mcp"
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
                  placeholder={"MI_TOKEN=..."}
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
        <button type="button" onClick={onCancel}
                className="text-xs px-3 py-1.5 rounded-lg border border-base-600 text-ink-dim hover:text-ink">
          {tr("common.cancel")}
        </button>
      </div>
    </div>
  );
}
