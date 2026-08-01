// components/settings/MemoriaPanel.tsx — Ajustes → Memoria: pulido visual
// (petición directa del usuario, 2026-08-02: "es la memoria de Aithera,
// quiero que sea bonito, intuitivo y moderno").
//
// Panel AUTÓNOMO (mismo patrón que BriefingPanel.tsx): posee su propio
// estado y su propia carga — Settings.tsx solo lo monta con
// `<MemoriaPanel />`. Sustituye al bloque que antes vivía inline dentro de
// Settings.tsx (V0.6 stats + R6.5c perfil destilado + PU10 mini-chat).
//
// Es una reorganización VISUAL, no funcional: mismos endpoints, mismos
// handlers, mismo comportamiento — solo la presentación cambia (tarjetas
// `glass-surface` con cabecera propia en vez de bloques apilados separados
// por una simple línea, chips de ejemplo en el mini-chat, categorías como
// insignia, formulario manual plegado por defecto, zona de "borrar
// historial" diferenciada como acción sensible).
import { useEffect, useState, type ReactNode } from "react";
import { api, type MemoryStats, type ContextItem, type ProfileFact } from "@/lib/api";
import { useT } from "@/store/useI18n";
import MemoryQuickChat from "./MemoryQuickChat";

// ── Iconografía local (mismo lenguaje que DockIcons.tsx: línea fina,
//    stroke redondeado, currentColor — pero íconos informativos propios de
//    este panel, no de navegación, así que viven aquí y no en el dock). ──

function IconMemoryCore() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.15} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="8.6" opacity={0.45} />
      <circle cx="12" cy="12" r="5.4" opacity={0.75} />
      <circle cx="12" cy="12" r="1.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconRefresh({ spinning }: { spinning?: boolean }) {
  return (
    <svg
      width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      className={spinning ? "animate-spin" : ""}
    >
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </svg>
  );
}

function IconChatBubble() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 4.5h16v11H9l-4.5 4v-4H4v-11Z" />
    </svg>
  );
}

function IconBookmark() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6.5 3.5h11v17l-5.5-4.2-5.5 4.2v-17Z" />
    </svg>
  );
}

function IconDocument() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6.5 3h7l4 4v14h-11V3Z" />
      <path d="M13.5 3v4h4" />
    </svg>
  );
}

function IconSparkle() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.3} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3.5c.5 2.8 1.3 4.4 4.5 5-3.2.6-4 2.2-4.5 5-.5-2.8-1.3-4.4-4.5-5 3.2-.6 4-2.2 4.5-5Z" />
      <path d="M19 14.5c.25 1.4.65 2.2 2.25 2.5-1.6.3-2 1.1-2.25 2.5-.25-1.4-.65-2.2-2.25-2.5 1.6-.3 2-1.1 2.25-2.5Z" />
    </svg>
  );
}

// ── Bloques compartidos ──

function Section({
  title,
  desc,
  icon,
  action,
  children,
}: {
  title: string;
  desc?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="glass-surface rounded-2xl p-4">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          {icon && <span className="shrink-0 text-accent/80">{icon}</span>}
          <h3 className="text-sm font-medium text-ink truncate">{title}</h3>
        </div>
        {action}
      </div>
      {desc && <p className="text-xs text-ink-dim mb-3 leading-relaxed">{desc}</p>}
      {children}
    </section>
  );
}

function StatTile({ icon, value, label }: { icon: ReactNode; value: number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 bg-base-900/40 rounded-xl px-3 py-2.5">
      <div className="shrink-0 w-8 h-8 rounded-lg bg-accent/10 text-accent flex items-center justify-center">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-lg font-semibold text-ink leading-none tabular-nums">{value}</p>
        <p className="text-[10px] text-ink-faint uppercase tracking-wider mt-1 truncate">{label}</p>
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-center py-5 px-4 rounded-xl border border-dashed border-base-600/60">
      <p className="text-xs text-ink-faint">{text}</p>
    </div>
  );
}

function MemoryRow({
  title,
  subtitle,
  badge,
  onDelete,
  deleteLabel,
}: {
  title: string;
  subtitle: string;
  badge?: string;
  onDelete: () => void;
  deleteLabel: string;
}) {
  return (
    <div className="group flex items-start justify-between gap-3 bg-base-900/40 hover:bg-base-900/55 transition-colors rounded-xl px-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <p className="text-xs font-medium text-ink truncate">{title}</p>
          {badge && (
            <span className="shrink-0 text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
              {badge}
            </span>
          )}
        </div>
        <p className="text-[11px] text-ink-dim mt-0.5 leading-snug">{subtitle}</p>
      </div>
      <button
        type="button"
        onClick={onDelete}
        aria-label={deleteLabel}
        title={deleteLabel}
        className="shrink-0 w-6 h-6 rounded-lg flex items-center justify-center text-ink-faint hover:text-signal-error hover:bg-signal-error/10 transition-colors"
      >
        ×
      </button>
    </div>
  );
}

export default function MemoriaPanel() {
  const tr = useT();
  const [memStats, setMemStats] = useState<MemoryStats | null>(null);
  const [memLoading, setMemLoading] = useState(false);
  const [contextItems, setContextItems] = useState<ContextItem[]>([]);
  // [R6.5c] Perfil destilado del chat, distinto de las preferencias manuales.
  const [profileFacts, setProfileFacts] = useState<ProfileFact[]>([]);
  const [newCtxKey, setNewCtxKey] = useState("");
  const [newCtxContent, setNewCtxContent] = useState("");
  const [newCtxCategory, setNewCtxCategory] = useState("preference");
  const [showAddForm, setShowAddForm] = useState(false);
  const [memMessage, setMemMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    loadMemory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      setMemMessage({ kind: "ok", text: tr("settings.memoria.prefSaved", { key: newCtxKey.trim() }) });
      setNewCtxKey("");
      setNewCtxContent("");
      setShowAddForm(false);
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

  return (
    <div className="flex flex-col gap-4">
      {/* ── Cabecera ── */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="shrink-0 w-9 h-9 rounded-xl bg-accent/10 text-accent flex items-center justify-center">
            <IconMemoryCore />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-ink">{tr("settings.memoria.panelTitle")}</h2>
            <p className="text-[11px] text-ink-faint truncate">{tr("settings.memoria.panelSubtitle")}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={loadMemory}
          disabled={memLoading}
          title={tr("settings.memoria.refresh")}
          className="shrink-0 flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-lg bg-base-700/60 text-ink-dim border border-base-600 hover:bg-base-600 hover:text-ink disabled:opacity-50 transition-colors"
        >
          <IconRefresh spinning={memLoading} />
          {tr("settings.memoria.refresh")}
        </button>
      </div>

      {/* ── Mensaje de feedback (transversal a todas las acciones) ── */}
      {memMessage && (
        <div
          className={`text-xs rounded-lg px-3 py-2 border ${
            memMessage.kind === "ok"
              ? "bg-signal-ok/10 text-signal-ok border-signal-ok/30"
              : "bg-signal-error/10 text-signal-error border-signal-error/30"
          }`}
        >
          {memMessage.text}
        </div>
      )}

      {!memStats ? (
        <p className="text-xs text-ink-faint">{tr("settings.memoria.loadingStats")}</p>
      ) : !memStats.healthy ? (
        <Section title={tr("settings.memoria.unavailable")}>
          <div className="text-xs text-signal-warn space-y-1">
            {memStats.error && <p className="text-ink-faint font-mono">{memStats.error}</p>}
            <p className="text-ink-faint">{tr("settings.memoria.stillWorks")}</p>
          </div>
        </Section>
      ) : (
        <>
          {/* ── Resumen ── */}
          <Section title={tr("settings.memoria.summary.title")} icon={<IconSparkle />}>
            <div className="grid grid-cols-3 gap-2.5">
              <StatTile icon={<IconChatBubble />} value={memStats.conversations} label={tr("settings.memoria.conversations")} />
              <StatTile icon={<IconBookmark />} value={memStats.user_context} label={tr("settings.memoria.preferences")} />
              <StatTile icon={<IconDocument />} value={memStats.documents} label={tr("settings.memoria.documents")} />
            </div>
          </Section>

          {/* ── Mini-chat de memoria (PU10) — vía directa y principal para
              hablarle a Aithera de tus preferencias, sin abrir el chat
              completo. */}
          <Section
            title={tr("settings.memoria.quickchat.title")}
            desc={tr("settings.memoria.quickchat.desc")}
            icon={<IconChatBubble />}
          >
            <MemoryQuickChat onChanged={loadMemory} />
          </Section>

          {/* ── Preferencias (manual + guardadas por el mini-chat) ── */}
          <Section
            title={tr("settings.memoria.savedPrefs", { n: contextItems.length })}
            icon={<IconBookmark />}
            action={
              <button
                type="button"
                onClick={() => setShowAddForm((v) => !v)}
                className="shrink-0 text-[11px] px-2.5 py-1 rounded-lg border border-base-600 text-ink-dim hover:text-ink hover:border-accent/50 transition-colors"
              >
                {showAddForm ? tr("common.cancel") : `+ ${tr("settings.memoria.addPref.title")}`}
              </button>
            }
          >
            {showAddForm && (
              <div className="space-y-2 mb-3 p-3 rounded-xl bg-base-900/30 border border-base-700/50">
                <p className="text-[10px] text-ink-faint">{tr("settings.memoria.addPref.desc")}</p>
                <input
                  type="text"
                  value={newCtxKey}
                  onChange={(e) => setNewCtxKey(e.target.value)}
                  placeholder={tr("settings.memoria.addPref.keyPlaceholder")}
                  className="w-full bg-base-800/70 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                />
                <input
                  type="text"
                  value={newCtxCategory}
                  onChange={(e) => setNewCtxCategory(e.target.value)}
                  placeholder={tr("settings.memoria.addPref.categoryPlaceholder")}
                  className="w-full bg-base-800/70 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                />
                <textarea
                  value={newCtxContent}
                  onChange={(e) => setNewCtxContent(e.target.value)}
                  placeholder={tr("settings.memoria.addPref.contentPlaceholder")}
                  rows={2}
                  className="w-full bg-base-800/70 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 resize-y"
                />
                <button
                  onClick={handleAddContext}
                  className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 transition-colors"
                >
                  {tr("settings.memoria.addPref.save")}
                </button>
              </div>
            )}

            {contextItems.length === 0 ? (
              <EmptyState text={tr("settings.memoria.noPrefs")} />
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-0.5">
                {contextItems.map((c) => (
                  <MemoryRow
                    key={c.id}
                    title={c.key}
                    subtitle={c.content}
                    badge={c.category}
                    onDelete={() => handleDeleteContext(c.key)}
                    deleteLabel={tr("common.delete")}
                  />
                ))}
              </div>
            )}
          </Section>

          {/* ── Perfil destilado (R6.5c) — lo que Aithera cree saber de ti,
              sola, de tus conversaciones. Visible y borrable: sin esto sería
              una caja negra acumulando suposiciones sobre datos personales. ── */}
          <Section
            title={tr("settings.memoria.profile.title", { n: profileFacts.length })}
            desc={tr("settings.memoria.profile.desc")}
            icon={<IconSparkle />}
          >
            {profileFacts.length === 0 ? (
              <EmptyState text={tr("settings.memoria.profile.empty")} />
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-0.5">
                {profileFacts.map((f) => (
                  <MemoryRow
                    key={f.key}
                    title={f.label}
                    subtitle={f.value}
                    onDelete={() => handleDeleteProfileFact(f.key, f.label)}
                    deleteLabel={tr("settings.memoria.profile.forget")}
                  />
                ))}
              </div>
            )}
          </Section>

          {/* ── Zona sensible ── */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-signal-warn/25 bg-signal-warn/5 px-4 py-3">
            <div className="min-w-0">
              <p className="text-xs font-medium text-ink">{tr("settings.memoria.clearHistory", { n: memStats.conversations })}</p>
              <p className="text-[10px] text-ink-faint mt-0.5">{tr("settings.memoria.clearHistoryHint")}</p>
            </div>
            <button
              onClick={handleClearConversations}
              disabled={!memStats.conversations}
              className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-signal-warn/10 text-signal-warn border border-signal-warn/30 hover:bg-signal-warn/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {tr("common.delete")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
