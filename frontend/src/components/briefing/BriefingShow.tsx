// components/briefing/BriefingShow.tsx — el "show" visual del briefing (PU4b, doc 35)
//
// Petición literal del usuario (2026-08-01): "quiero que el Briefing muestre
// las cosas de las que habla" — tarjetas de proyecto que se abren en una
// esquina según los menciona, emails en pantalla, el calendario con los días
// remarcados, y para las noticias una PANTALLA COMPLETA con titulares
// agrupados por secciones/columnas donde lo que se está locutando queda
// enmarcado con un efecto visual; interactiva (scroll por noticia, vídeo
// reproducible, enlaces).
//
// ARQUITECTURA: este componente solo PINTA lo que dice `useBriefingShow`
// (scene = segmento actual, focus = paso que se está locutando). Quien
// conduce es Chat.tsx (dueño de la voz). Las tarjetas van a la IZQUIERDA
// (el panel del chat vive a la derecha); las noticias cubren la pantalla
// (z-40, por encima del chat z-30). Esc o ✕ paran el briefing entero.
import { useEffect, useMemo, useRef, useState } from "react";
import { useBriefingShow } from "@/store/useBriefingShow";
import { useT, useI18n } from "@/store/useI18n";
import type { NewsItem, SpokenSegment } from "@/lib/api";

// ---------------------------------------------------------------------------
// Estilos propios (keyframes + clase de foco). Inyectados aquí para que el
// componente sea autocontenido — mismas variables de tema que el resto.
// ---------------------------------------------------------------------------
const STYLE = `
@keyframes bshow-in {
  from { opacity: 0; transform: translateX(-18px) scale(0.97); }
  to   { opacity: 1; transform: translateX(0) scale(1); }
}
@keyframes bshow-wall-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes bshow-daypulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(232, 185, 94, 0.55); }
  50%      { box-shadow: 0 0 0 5px rgba(232, 185, 94, 0); }
}
.bshow-card { animation: bshow-in 380ms cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.bshow-wall { animation: bshow-wall-in 300ms ease-out both; }
.bshow-focus {
  border-color: rgba(94, 168, 255, 0.85) !important;
  box-shadow: 0 0 0 1px rgba(94, 168, 255, 0.5), 0 0 22px rgba(94, 168, 255, 0.28);
  transform: scale(1.015);
}
.bshow-card, .bshow-news-item { transition: box-shadow 260ms ease, border-color 260ms ease, transform 260ms ease; }
`;

function youtubeId(url: string): string | null {
  const m =
    url.match(/youtube\.com\/watch\?v=([\w-]{6,})/) || url.match(/youtu\.be\/([\w-]{6,})/);
  return m ? m[1] : null;
}

function initialOf(sender: string | null): string {
  const s = (sender || "?").trim();
  return (s.match(/[A-Za-zÀ-ÿ0-9]/)?.[0] || "?").toUpperCase();
}

export default function BriefingShow() {
  const active = useBriefingShow((s) => s.active);
  const scene = useBriefingShow((s) => s.scene);
  const focus = useBriefingShow((s) => s.focus);
  const requestStop = useBriefingShow((s) => s.requestStop);
  const t = useT();
  const lang = useI18n((s) => s.lang);

  // Mapa focus-id → elemento, para resaltar y hacer scroll al paso locutado.
  const focusEls = useRef<Map<string, HTMLElement>>(new Map());
  const bindFocus = (id: string | null | undefined) => (el: HTMLElement | null) => {
    if (!id) return;
    if (el) focusEls.current.set(id, el);
    else focusEls.current.delete(id);
  };
  useEffect(() => {
    if (!focus) return;
    const el = focusEls.current.get(focus);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [focus]);

  // Esc para el show entero (la voz incluida). El contenedor de noticias
  // lleva role="dialog", así el Esc global de AppLayout se inhibe y decide
  // este listener.
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestStop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, requestStop]);

  if (!active || !scene) return null;

  const focusCls = (id: string | null | undefined) => (focus && id === focus ? " bshow-focus" : "");

  return (
    <>
      <style>{STYLE}</style>

      {/* Pill de control: siempre visible durante el show */}
      <div className="fixed left-5 top-5 z-[46] flex items-center gap-2 pointer-events-auto">
        <div className="glass-surface rounded-full pl-3 pr-1.5 py-1.5 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-signal-warn animate-pulse" />
          <span className="text-xs font-medium text-ink">{t("briefing.show.title")}</span>
          <button
            type="button"
            onClick={requestStop}
            aria-label={t("briefing.show.stop")}
            title={t("briefing.show.stop")}
            className="w-6 h-6 rounded-full flex items-center justify-center text-ink-dim hover:text-ink hover:bg-ink/10"
          >
            ×
          </button>
        </div>
      </div>

      {/* Escenas de tarjeta (esquina izquierda; el chat vive a la derecha) */}
      {scene.kind !== "news" && (
        <div className="fixed left-5 top-16 bottom-28 w-[360px] max-w-[calc(100vw_-_2.5rem)] z-20 flex flex-col gap-3 overflow-y-auto pr-1 pointer-events-auto">
          {scene.kind === "email" && <EmailScene scene={scene} bindFocus={bindFocus} focusCls={focusCls} />}
          {scene.kind === "calendar" && (
            <CalendarScene scene={scene} lang={lang} focus={focus} bindFocus={bindFocus} focusCls={focusCls} />
          )}
          {scene.kind === "projects" && <ProjectsScene scene={scene} bindFocus={bindFocus} focusCls={focusCls} />}
          {scene.kind === "tasks" && <TasksScene scene={scene} bindFocus={bindFocus} focusCls={focusCls} />}
          {scene.kind === "yesterday" && (
            <div className="bshow-card glass-surface rounded-2xl p-4 border border-base-700">
              <p className="text-[11px] uppercase tracking-wider text-ink-faint mb-1.5">
                {t("briefing.show.yesterday")}
              </p>
              <p className="text-sm text-ink leading-relaxed">{scene.steps[0]?.text}</p>
            </div>
          )}
        </div>
      )}

      {/* Noticias: pantalla completa, columnas por tema, foco siguiendo la voz */}
      {scene.kind === "news" && (
        <NewsWall scene={scene} bindFocus={bindFocus} focusCls={focusCls} onClose={requestStop} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Escenas
// ---------------------------------------------------------------------------
type SceneProps = {
  scene: SpokenSegment;
  bindFocus: (id: string | null | undefined) => (el: HTMLElement | null) => void;
  focusCls: (id: string | null | undefined) => string;
};

function EmailScene({ scene, bindFocus, focusCls }: SceneProps) {
  const t = useT();
  const items = scene.refs.items || [];
  const total = scene.refs.total ?? items.length;
  return (
    <>
      <div className="bshow-card glass-surface rounded-2xl px-4 py-3 border border-base-700 flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-wider text-ink-faint">{t("briefing.show.email")}</p>
        <span className="text-[11px] font-bold text-signal-error bg-signal-error/15 border border-signal-error/30 rounded-full px-2 py-0.5">
          {total}
        </span>
      </div>
      {items.map((it, i) => (
        <div
          key={it.email_id || i}
          ref={bindFocus(it.email_id)}
          style={{ animationDelay: `${i * 110}ms` }}
          className={`bshow-card glass-surface rounded-2xl p-3.5 border border-base-700 flex gap-3${focusCls(it.email_id)}`}
        >
          <div className="shrink-0 w-9 h-9 rounded-full bg-signal-error/15 border border-signal-error/30 flex items-center justify-center text-sm font-semibold text-signal-error">
            {initialOf(it.sender)}
          </div>
          <div className="min-w-0">
            <p className="text-xs text-ink-dim truncate">{(it.sender || "—").split("<")[0].trim()}</p>
            <p className="text-sm text-ink font-medium leading-snug break-words">
              {it.subject || t("briefing.show.noSubject")}
            </p>
          </div>
        </div>
      ))}
    </>
  );
}

function CalendarScene({
  scene,
  lang,
  focus,
  bindFocus,
  focusCls,
}: SceneProps & { lang: string; focus: string | null }) {
  const t = useT();
  const events = scene.refs.events || [];
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  const { monthLabel, weekdays, cells, eventDays, focusDay } = useMemo(() => {
    const monthLabel = new Intl.DateTimeFormat(lang, { month: "long", year: "numeric" }).format(now);
    // Semana empezando en lunes (convención local).
    const base = new Date(2024, 0, 1); // lunes
    const weekdays = Array.from({ length: 7 }, (_, i) =>
      new Intl.DateTimeFormat(lang, { weekday: "narrow" }).format(
        new Date(base.getTime() + i * 86400000),
      ),
    );
    const firstOffset = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells: (number | null)[] = [
      ...Array.from({ length: firstOffset }, () => null),
      ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
    ];
    const dayOf = (start: string | null) => {
      const d = start ? new Date(start) : null;
      return d && !isNaN(d.getTime()) && d.getMonth() === month ? d.getDate() : null;
    };
    const eventDays = new Set(events.map((e) => dayOf(e.start)).filter((d): d is number => d !== null));
    let focusDay: number | null = null;
    if (focus?.startsWith("ev:")) {
      const idx = Number(focus.slice(3));
      focusDay = dayOf(events[idx]?.start ?? null);
    }
    return { monthLabel, weekdays, cells, eventDays, focusDay };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, events, focus]);

  return (
    <>
      <div className="bshow-card glass-surface rounded-2xl p-4 border border-base-700">
        <p className="text-[11px] uppercase tracking-wider text-ink-faint mb-2">
          {t("briefing.show.calendar")} · <span className="capitalize">{monthLabel}</span>
        </p>
        <div className="grid grid-cols-7 gap-1 text-center">
          {weekdays.map((w, i) => (
            <span key={`w${i}`} className="text-[10px] text-ink-faint uppercase">{w}</span>
          ))}
          {cells.map((d, i) => {
            const isToday = d === now.getDate();
            const has = d !== null && eventDays.has(d);
            const isFocus = d !== null && d === focusDay;
            return (
              <span
                key={i}
                style={isFocus ? { animation: "bshow-daypulse 1.2s ease-in-out infinite" } : undefined}
                className={`h-7 rounded-lg text-[11px] flex items-center justify-center ${
                  d === null
                    ? ""
                    : isFocus
                      ? "bg-signal-warn/25 text-signal-warn font-bold border border-signal-warn/60"
                      : has
                        ? "bg-accent/15 text-accent font-semibold border border-accent/40"
                        : isToday
                          ? "border border-ink/25 text-ink"
                          : "text-ink-dim"
                }`}
              >
                {d ?? ""}
              </span>
            );
          })}
        </div>
      </div>
      {events.map((ev, i) => {
        const id = `ev:${i}`;
        const hora = ev.start && ev.start.includes("T") ? ev.start.split("T")[1]?.slice(0, 5) : "";
        return (
          <div
            key={id}
            ref={bindFocus(id)}
            style={{ animationDelay: `${i * 90}ms` }}
            className={`bshow-card glass-surface rounded-xl px-3.5 py-2.5 border border-base-700 flex items-center gap-3${focusCls(id)}`}
          >
            <span className="shrink-0 text-[11px] font-mono text-accent w-10">{hora || "—"}</span>
            <span className="text-sm text-ink truncate">{ev.title || "…"}</span>
          </div>
        );
      })}
    </>
  );
}

function ProjectsScene({ scene, bindFocus, focusCls }: SceneProps) {
  const t = useT();
  const projects = scene.refs.projects || [];
  return (
    <>
      <div className="bshow-card glass-surface rounded-2xl px-4 py-3 border border-base-700">
        <p className="text-[11px] uppercase tracking-wider text-ink-faint">{t("briefing.show.projects")}</p>
      </div>
      {projects.map((p, i) => {
        const id = `proj:${p.project_id}`;
        const pct = Math.round((p.ratio || 0) * 100);
        return (
          <div
            key={id}
            ref={bindFocus(id)}
            style={{ animationDelay: `${i * 110}ms` }}
            className={`bshow-card glass-surface rounded-2xl p-4 border border-base-700${focusCls(id)}`}
          >
            <div className="flex items-baseline justify-between gap-2 mb-1">
              <p className="text-sm font-semibold text-ink truncate">{p.project_name}</p>
              <span className="text-xs font-mono text-accent shrink-0">{pct}%</span>
            </div>
            {(p.milestone || p.version) && (
              <p className="text-[11px] text-ink-dim mb-2 truncate">
                {[p.milestone, p.version].filter(Boolean).join(" · ")}
                {p.done != null && p.total != null ? ` · ${p.done}/${p.total}` : ""}
              </p>
            )}
            <div className="h-1.5 rounded-full bg-base-700 overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-[width] duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </>
  );
}

function TasksScene({ scene, bindFocus, focusCls }: SceneProps) {
  const t = useT();
  const deadlines = scene.refs.deadlines || [];
  const blocked = scene.refs.blocked || [];
  return (
    <>
      {deadlines.length > 0 && (
        <div
          ref={bindFocus("deadlines")}
          className={`bshow-card glass-surface rounded-2xl p-4 border border-base-700${focusCls("deadlines")}`}
        >
          <p className="text-[11px] uppercase tracking-wider text-signal-warn mb-2">
            {t("briefing.show.deadlines")}
          </p>
          <div className="flex flex-col gap-1.5">
            {deadlines.map((task) => (
              <div key={task.task_id} className="flex items-center justify-between gap-2 text-sm">
                <span className="text-ink truncate">{task.title}</span>
                <span className="text-[11px] font-mono text-signal-warn shrink-0">
                  {task.due_date ? task.due_date.slice(5) : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {blocked.length > 0 && (
        <div
          ref={bindFocus("blocked")}
          className={`bshow-card glass-surface rounded-2xl p-4 border border-base-700${focusCls("blocked")}`}
        >
          <p className="text-[11px] uppercase tracking-wider text-signal-error mb-2">
            {t("briefing.show.blocked")}
          </p>
          <div className="flex flex-col gap-1.5">
            {blocked.map((task) => (
              <p key={task.task_id} className="text-sm text-ink truncate">{task.title}</p>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// La pantalla completa de noticias
// ---------------------------------------------------------------------------
function NewsWall({
  scene,
  bindFocus,
  focusCls,
  onClose,
}: SceneProps & { onClose: () => void }) {
  const t = useT();
  const topics = scene.refs.topics || [];
  const prepared = scene.refs.prepared_at;

  return (
    <div
      role="dialog"
      aria-label={t("briefing.show.newsTitle")}
      className="bshow-wall fixed inset-0 z-40 bg-base-950/92 backdrop-blur-md flex flex-col pointer-events-auto"
    >
      <div className="shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-baseline gap-3">
          <h2 className="text-base font-semibold text-ink">{t("briefing.show.newsTitle")}</h2>
          {prepared && (
            <span className="text-[11px] text-ink-faint">
              {t("briefing.show.updated")} {prepared.replace("T", " · ").slice(0, 18)}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("briefing.show.stop")}
          className="w-8 h-8 rounded-full flex items-center justify-center text-ink-dim hover:text-ink hover:bg-ink/10 text-lg"
        >
          ×
        </button>
      </div>

      <div
        className="flex-1 min-h-0 overflow-y-auto px-6 py-5 grid gap-5 items-start"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(270px, 1fr))" }}
      >
        {topics.map((topic) => (
          <section key={topic.id} className="flex flex-col gap-3 min-w-0">
            <h3 className="text-[11px] uppercase tracking-widest font-semibold text-signal-warn border-b border-signal-warn/25 pb-1.5">
              {topic.label}
            </h3>
            {topic.items.map((item) => (
              <NewsCard key={item.id} item={item} bindFocus={bindFocus} focusCls={focusCls} />
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}

function NewsCard({
  item,
  bindFocus,
  focusCls,
}: {
  item: NewsItem;
  bindFocus: SceneProps["bindFocus"];
  focusCls: SceneProps["focusCls"];
}) {
  const t = useT();
  const [playing, setPlaying] = useState(false);
  const yt = item.url ? youtubeId(item.url) : null;

  return (
    <article
      ref={bindFocus(item.id)}
      className={`bshow-news-item glass-surface rounded-2xl border border-base-700 overflow-hidden${focusCls(item.id)}`}
    >
      {playing && yt ? (
        <div className="aspect-video bg-black">
          <iframe
            className="w-full h-full"
            src={`https://www.youtube.com/embed/${yt}?autoplay=1`}
            title={item.title}
            allow="autoplay; encrypted-media; picture-in-picture"
            allowFullScreen
          />
        </div>
      ) : item.image ? (
        <div className="relative">
          <img src={item.image} alt="" loading="lazy" className="w-full h-28 object-cover" />
          {yt && <PlayButton onClick={() => setPlaying(true)} />}
        </div>
      ) : yt ? (
        <div className="relative h-20 bg-base-800/70">
          <PlayButton onClick={() => setPlaying(true)} />
        </div>
      ) : null}

      <div className="p-3.5">
        <h4 className="text-sm font-medium text-ink leading-snug mb-1.5">{item.title}</h4>
        {/* Scroll propio si el resumen no cabe — la pantalla es interactiva. */}
        {item.summary && (
          <p className="text-xs text-ink-dim leading-relaxed max-h-24 overflow-y-auto">{item.summary}</p>
        )}
        <div className="flex items-center justify-between gap-2 mt-2.5">
          <span className="text-[10px] text-ink-faint truncate">
            {item.source}
            {item.published ? ` · ${item.published}` : ""}
          </span>
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-accent hover:underline shrink-0"
            >
              {t("briefing.show.open")}
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

function PlayButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Play"
      className="absolute inset-0 flex items-center justify-center group"
    >
      <span className="w-11 h-11 rounded-full bg-base-950/70 border border-white/25 flex items-center justify-center text-ink group-hover:scale-110 group-hover:border-accent/60 transition-transform">
        ▶
      </span>
    </button>
  );
}
