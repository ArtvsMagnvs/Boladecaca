// Calendar.tsx - Vista mensual completa (V0.7 Fase 4)
//
// Caracteristicas V0.7:
// - Vista mensual con el mes actual por defecto (ano + mes)
// - Hoy marcado con ring + bg mas intenso
// - Colores segun status: available (verde), unavailable (rojo), busy (amarillo),
//   mixed (naranja), neutral (gris)
// - Titulos de eventos en el tooltip/celda
// - Click en un dia -> modal con detalle + configuracion de bloques
// - Navegacion entre meses (anterior/siguiente/hoy)
// - Configurar bloques manualmente desde la UI (available/unavailable/busy)
// - Sin requerir OAuth de Google: funciona solo con la BD local

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useT } from "@/store/useI18n";

// [I18N-5] Nombres de dia/mes y labels de status ya no son literales fijos:
// se resuelven con t("calendar.weekday.*")/t("calendar.month.*")/etc. Las
// claves de STATUS_COLORS (available/unavailable/busy/mixed/neutral) siguen
// siendo el id interno (coincide con lo que devuelve el backend); el label
// visible se resuelve aparte con `t(STATUS_LABEL_KEY[key])`.
// [PU6b-vent t4] Nombres COMPLETOS (lunes, martes…) — petición del usuario;
// los cortos quedan para pantallas estrechas vía la clase `sm:hidden`.
const WEEKDAY_KEYS = [
  "calendar.weekday.mon", "calendar.weekday.tue", "calendar.weekday.wed",
  "calendar.weekday.thu", "calendar.weekday.fri", "calendar.weekday.sat", "calendar.weekday.sun",
];
const WEEKDAY_FULL_KEYS = [
  "calendar.weekdayFull.mon", "calendar.weekdayFull.tue", "calendar.weekdayFull.wed",
  "calendar.weekdayFull.thu", "calendar.weekdayFull.fri", "calendar.weekdayFull.sat", "calendar.weekdayFull.sun",
];
const MONTH_KEYS = [
  "calendar.month.1", "calendar.month.2", "calendar.month.3", "calendar.month.4",
  "calendar.month.5", "calendar.month.6", "calendar.month.7", "calendar.month.8",
  "calendar.month.9", "calendar.month.10", "calendar.month.11", "calendar.month.12",
];

// Mapeo de status -> colores Tailwind (el color/anillo es visual, no texto).
// [PU6b-vent t4] El TINTE de estado se pinta como capa sobre una base opaca
// común (bg-base-900/90 en la celda): con el AVCS real de fondo en todas las
// páginas, las celdas al 15-40% dejaban pasar las partículas y el calendario
// costaba de leer. El tinte puede ser suave porque ya no compite con el fondo.
// [PU7] `text` lleva siempre su pareja `light:` — los tonos 300 de Tailwind
// están calibrados para fondo oscuro y quedan poco legibles sobre el lienzo
// gris claro del tema `.light` (reportado por el usuario). La variante
// `light:` (tailwind.config.js) solo actúa bajo `.light`, así que el oscuro
// no se toca.
const STATUS_COLORS: Record<string, { bg: string; ring: string; text: string }> = {
  available:   { bg: "bg-emerald-500/20", ring: "ring-emerald-500/40", text: "text-emerald-300 light:text-emerald-800" },
  unavailable: { bg: "bg-rose-500/25",    ring: "ring-rose-500/50",    text: "text-rose-300 light:text-rose-800" },
  busy:        { bg: "bg-amber-500/20",   ring: "ring-amber-500/40",   text: "text-amber-300 light:text-amber-800" },
  mixed:       { bg: "bg-orange-500/20",  ring: "ring-orange-500/40",  text: "text-orange-300 light:text-orange-800" },
  neutral:     { bg: "bg-base-800/50",    ring: "ring-base-700/40",    text: "text-ink-dim" },
};

const STATUS_LABEL_KEY: Record<string, string> = {
  available: "calendar.status.available",
  unavailable: "calendar.status.unavailable",
  busy: "calendar.status.busy",
  mixed: "calendar.status.mixed",
  neutral: "calendar.status.neutral",
};

interface MonthDay {
  date: string;
  status: "available" | "unavailable" | "busy" | "mixed" | "neutral";
  event_count: number;
  event_titles: string[];
  block_count: number;
  block_labels: string[];
}

interface AvailabilityBlock {
  id: number;
  date: string;
  hour_start: number;
  hour_end: number;
  status: string;
  label: string | null;
}

export default function Calendar() {
  const t = useT();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-12
  // [PU6b-vent t4] Tres niveles de vista, patrón estándar de selector de
  // fechas (Google Calendar / date pickers): DÍAS (el mes de siempre) →
  // MESES (los 12 del año) → AÑOS (una docena alrededor del actual). Se sube
  // de nivel clicando el TÍTULO central; se baja eligiendo (un año → sus
  // meses, un mes → sus días). Las flechas ←/→ navegan la unidad de la vista
  // activa (mes / año / bloque de 12 años).
  const [view, setView] = useState<"days" | "months" | "years">("days");
  const [monthData, setMonthData] = useState<MonthDay[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayBlocks, setDayBlocks] = useState<AvailabilityBlock[]>([]);

  // Form para anadir bloque
  const [formHourStart, setFormHourStart] = useState("9");
  const [formHourEnd, setFormHourEnd] = useState("18");
  const [formStatus, setFormStatus] = useState<"available" | "unavailable" | "busy">("unavailable");
  const [formLabel, setFormLabel] = useState("");
  const [formMsg, setFormMsg] = useState<string | null>(null);
  // [I18N-5] Antes se coloreaba mirando si formMsg.startsWith("Error") — con
  // el mensaje traducido ese prefijo ya no es fiable en los otros 3 idiomas.
  const [formIsError, setFormIsError] = useState(false);

  const todayStr = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }, []);

  // ------------------------------------------------------------------
  // Carga del mes
  // ------------------------------------------------------------------

  const loadMonth = async (y: number, m: number) => {
    setLoading(true);
    try {
      const data = await api.getMonthOverview(y, m);
      setMonthData(data.days || []);
    } catch (e) {
      console.error("Error cargando mes:", e);
      setMonthData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Solo la vista de días necesita datos del backend; navegar por meses o
    // años no dispara peticiones (se cargan al bajar de nuevo a días).
    if (view === "days") loadMonth(year, month);
  }, [year, month, view]);

  // ------------------------------------------------------------------
  // Navegacion
  // ------------------------------------------------------------------

  const prevMonth = () => {
    if (month === 1) {
      setYear(year - 1);
      setMonth(12);
    } else {
      setMonth(month - 1);
    }
  };

  const nextMonth = () => {
    if (month === 12) {
      setYear(year + 1);
      setMonth(1);
    } else {
      setMonth(month + 1);
    }
  };

  // [PU6b-vent t4] Las flechas navegan la unidad de la vista activa.
  const goPrev = () => {
    if (view === "days") prevMonth();
    else if (view === "months") setYear(year - 1);
    else setYear(year - 12);
  };
  const goNext = () => {
    if (view === "days") nextMonth();
    else if (view === "months") setYear(year + 1);
    else setYear(year + 12);
  };

  const goToday = () => {
    const d = new Date();
    setYear(d.getFullYear());
    setMonth(d.getMonth() + 1);
    setView("days");
  };

  // ------------------------------------------------------------------
  // Calculo del grid del calendario
  // ------------------------------------------------------------------

  const calendarGrid = useMemo(() => {
    // Primer dia del mes (0=domingo, 1=lunes...)
    const firstDate = new Date(year, month - 1, 1);
    // Convertir a lunes=0, ..., domingo=6
    const firstWeekday = (firstDate.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month, 0).getDate();

    // Construir celdas: antes del mes (de otro mes) + dias del mes + despues
    const cells: Array<{ date: string; isCurrentMonth: boolean }> = [];
    // Celdas antes del primer dia
    for (let i = 0; i < firstWeekday; i++) {
      const d = new Date(year, month - 1, -firstWeekday + i + 1);
      cells.push({
        date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`,
        isCurrentMonth: false,
      });
    }
    // Dias del mes actual
    for (let day = 1; day <= daysInMonth; day++) {
      cells.push({
        date: `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
        isCurrentMonth: true,
      });
    }
    // Celdas despues para completar la ultima semana (multiplo de 7)
    while (cells.length % 7 !== 0) {
      const last = new Date(cells[cells.length - 1].date);
      const next = new Date(last);
      next.setDate(last.getDate() + 1);
      cells.push({
        date: `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`,
        isCurrentMonth: false,
      });
    }
    return cells;
  }, [year, month]);

  const dayMap = useMemo(() => {
    const map: Record<string, MonthDay> = {};
    for (const d of monthData) {
      map[d.date] = d;
    }
    return map;
  }, [monthData]);

  // ------------------------------------------------------------------
  // Modal de detalle de dia
  // ------------------------------------------------------------------

  const openDay = async (date: string) => {
    setSelectedDay(date);
    setFormMsg(null);
    setFormIsError(false);
    setFormHourStart("9");
    setFormHourEnd("18");
    setFormStatus("unavailable");
    setFormLabel("");
    try {
      const data = await api.getDayStatus(date);
      setDayBlocks((data.blocks || []) as AvailabilityBlock[]);
    } catch (e) {
      console.error("Error cargando dia:", e);
      setDayBlocks([]);
    }
  };

  const closeDay = () => {
    setSelectedDay(null);
    setDayBlocks([]);
    setFormMsg(null);
    setFormIsError(false);
  };

  const saveBlock = async () => {
    if (!selectedDay) return;
    try {
      const hs = parseInt(formHourStart);
      const he = parseInt(formHourEnd);
      await api.setAvailability({
        date: selectedDay,
        hour_start: hs,
        hour_end: he,
        status: formStatus,
        label: formLabel.trim() || undefined,
      });
      setFormMsg(t("calendar.modal.blockSaved"));
      setFormIsError(false);
      // Refrescar bloques del dia y el mes
      const data = await api.getDayStatus(selectedDay);
      setDayBlocks((data.blocks || []) as AvailabilityBlock[]);
      loadMonth(year, month);
    } catch (e) {
      setFormMsg(t("calendar.modal.errorPrefix", { msg: (e as Error).message }));
      setFormIsError(true);
    }
  };

  const deleteBlock = async (id: number) => {
    try {
      await api.deleteAvailability(id);
      const data = await api.getDayStatus(selectedDay!);
      setDayBlocks((data.blocks || []) as AvailabilityBlock[]);
      loadMonth(year, month);
    } catch (e) {
      setFormMsg(t("calendar.modal.errorDeleting", { msg: (e as Error).message }));
      setFormIsError(true);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="h-full p-4 flex flex-col gap-4 overflow-hidden">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div className="glass-surface rounded-xl px-4 py-2.5 w-fit">
          <h1 className="text-xl font-semibold text-ink">{t("calendar.title")}</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            {t("calendar.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={goPrev}
            className="text-sm px-3 py-1.5 rounded-lg bg-base-800/90 hover:bg-base-700 text-ink"
          >
            ← {t("calendar.prev")}
          </button>
          <button
            onClick={goToday}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
          >
            {t("calendar.today")}
          </button>
          <button
            onClick={goNext}
            className="text-sm px-3 py-1.5 rounded-lg bg-base-800/90 hover:bg-base-700 text-ink"
          >
            {t("calendar.next")} →
          </button>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex items-center gap-3 flex-wrap text-[11px]">
        {Object.entries(STATUS_COLORS).map(([key, c]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className={`inline-block w-3 h-3 rounded ${c.bg}`} />
            <span className="text-ink-dim">{t(STATUS_LABEL_KEY[key])}</span>
          </div>
        ))}
      </div>

      {/* Título central: MUESTRA la unidad de la vista y SUBE de nivel al
          clicarlo (días → meses → años), patrón de cualquier selector de
          fechas. El chevron indica que es interactivo. */}
      <div className="text-center">
        <button
          type="button"
          onClick={() => setView(view === "days" ? "months" : "years")}
          disabled={view === "years"}
          className={`text-base font-medium px-3 py-1 rounded-lg transition-colors ${
            view === "years" ? "text-ink-dim cursor-default" : "text-ink hover:bg-base-800/80"
          }`}
        >
          {view === "days" && `${t(MONTH_KEYS[month - 1])} ${year}`}
          {view === "months" && `${year}`}
          {view === "years" && `${year - 5} – ${year + 6}`}
          {view !== "years" && <span className="ml-1.5 text-ink-faint text-xs">▾</span>}
        </button>
        {loading && view === "days" && <span className="ml-2 text-xs text-ink-faint">{t("calendar.loading")}</span>}
      </div>

      {/* ── VISTA DE MESES: los 12 del año ─────────────────────────────── */}
      {view === "months" && (
        <div className="flex-1 grid grid-cols-3 sm:grid-cols-4 gap-3 min-h-0 content-start">
          {MONTH_KEYS.map((mk, i) => {
            const isCurrent = i + 1 === now.getMonth() + 1 && year === now.getFullYear();
            return (
              <button
                key={mk}
                onClick={() => { setMonth(i + 1); setView("days"); }}
                className={`rounded-xl py-6 text-sm font-medium bg-base-900/90 backdrop-blur-sm ring-1 transition-all hover:ring-2 hover:bg-base-800/90 ${
                  isCurrent ? "ring-2 ring-accent text-accent" : "ring-base-700/50 text-ink"
                }`}
              >
                {t(mk)}
              </button>
            );
          })}
        </div>
      )}

      {/* ── VISTA DE AÑOS: una docena alrededor del actual ─────────────── */}
      {view === "years" && (
        <div className="flex-1 grid grid-cols-3 sm:grid-cols-4 gap-3 min-h-0 content-start">
          {Array.from({ length: 12 }, (_, i) => year - 5 + i).map((y) => (
            <button
              key={y}
              onClick={() => { setYear(y); setView("months"); }}
              className={`rounded-xl py-6 text-sm font-medium bg-base-900/90 backdrop-blur-sm ring-1 transition-all hover:ring-2 hover:bg-base-800/90 ${
                y === now.getFullYear() ? "ring-2 ring-accent text-accent" : "ring-base-700/50 text-ink"
              }`}
            >
              {y}
            </button>
          ))}
        </div>
      )}

      {/* ── VISTA DE DÍAS: el mes (7 columnas x N filas) ───────────────── */}
      {view === "days" && (
      <div className="flex-1 grid grid-cols-7 gap-2 min-h-0">
        {/* Cabecera de la semana: nombres COMPLETOS sobre fondo con cuerpo
            (antes texto suelto casi invisible sobre el AVCS). En pantallas
            estrechas caen a la abreviatura para no desbordar. */}
        {WEEKDAY_KEYS.map((wk, i) => (
          <div key={wk} className="text-center text-[11px] capitalize tracking-wide text-ink py-1.5 rounded-lg bg-base-800/90 backdrop-blur-sm border border-base-700/50 font-medium">
            <span className="hidden sm:inline">{t(WEEKDAY_FULL_KEYS[i])}</span>
            <span className="sm:hidden uppercase text-[10px]">{t(wk)}</span>
          </div>
        ))}
        {/* Celdas de dias */}
        {calendarGrid.map((cell) => {
          const dayInfo = dayMap[cell.date];
          const colors = STATUS_COLORS[dayInfo?.status || "neutral"];
          const isToday = cell.date === todayStr;
          const isWeekend = new Date(cell.date).getDay() === 0 || new Date(cell.date).getDay() === 6;
          const dayNum = parseInt(cell.date.split("-")[2]);

          return (
            <motion.button
              key={cell.date}
              onClick={() => openDay(cell.date)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`
                relative rounded-xl p-2 text-left min-h-[88px] flex flex-col gap-1 transition-colors
                bg-base-900/90 backdrop-blur-sm
                ${cell.isCurrentMonth ? colors.text : "opacity-40"}
                ring-1 ${isToday ? "ring-2 ring-accent ring-offset-2 ring-offset-base-950" : colors.ring}
                hover:ring-2
              `}
              title={
                dayInfo
                  ? `${cell.date} - ${t(STATUS_LABEL_KEY[dayInfo.status || "neutral"])}\n${t("calendar.tooltip.eventCount", { n: dayInfo.event_count })}${
                      dayInfo.event_titles.length ? "\n" + dayInfo.event_titles.join("\n") : ""
                    }`
                  : cell.date
              }
            >
              {/* Tinte de estado, como capa sobre la base opaca. */}
              <span className={`absolute inset-0 rounded-xl pointer-events-none ${colors.bg}`} />
              {/* Numero del dia */}
              <div className="relative flex items-start justify-between">
                <span className={`text-sm font-medium ${isToday ? "text-accent" : ""}`}>
                  {dayNum}
                </span>
                {isToday && (
                  <span className="text-[8px] uppercase tracking-wider text-accent font-bold">
                    {t("calendar.today")}
                  </span>
                )}
              </div>

              {/* Titulos de eventos + labels de bloques manuales (max 3 total) */}
              {dayInfo && (dayInfo.event_titles.length > 0 || dayInfo.block_labels.length > 0) && (
                <div className="relative flex-1 min-h-0 space-y-0.5">
                  {/* Eventos reales (de calendar_events) - icono discreto */}
                  {dayInfo.event_titles.slice(0, 3).map((evTitle, i) => (
                    <div
                      key={`ev-${i}`}
                      className="text-[10px] truncate bg-base-950/50 rounded px-1 py-0.5"
                      title={t("calendar.tooltip.event", { title: evTitle })}
                    >
                      {evTitle}
                    </div>
                  ))}
                  {/* Labels de bloques manuales (de calendar_availability) */}
                  {dayInfo.block_labels.slice(0, Math.max(0, 3 - dayInfo.event_titles.length)).map((l, i) => (
                    <div
                      key={`bl-${i}`}
                      className="text-[10px] truncate bg-base-950/30 rounded px-1 py-0.5 italic text-ink-dim"
                      title={t("calendar.tooltip.manualBlock", { label: l })}
                    >
                      {l}
                    </div>
                  ))}
                  {dayInfo.event_count + dayInfo.block_count > 3 && (
                    <div className="text-[9px] text-ink-faint">
                      {t("calendar.tooltip.more", { n: dayInfo.event_count + dayInfo.block_count - 3 })}
                    </div>
                  )}
                </div>
              )}

              {/* Indicador de bloques si hay mas de los que se muestran */}
              {dayInfo && dayInfo.block_count > dayInfo.block_labels.length && (
                <div className="text-[9px] text-ink-faint">
                  {t("calendar.tooltip.moreBlocks", { n: dayInfo.block_count - dayInfo.block_labels.length })}
                </div>
              )}
            </motion.button>
          );
        })}
      </div>
      )}

      {/* Modal de detalle de dia */}
      {selectedDay && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
          onClick={closeDay}
        >
          <div
            className="bg-base-900 rounded-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-ink">
                {selectedDay}
                {selectedDay === todayStr && (
                  <span className="ml-2 text-xs text-accent">({t("calendar.today")})</span>
                )}
              </h2>
              <button
                onClick={closeDay}
                className="text-ink-dim hover:text-ink text-xl"
              >
                ×
              </button>
            </div>

            {/* Estado del dia */}
            {dayBlocks.length > 0 && (
              <div className="mb-4 p-3 rounded-lg bg-base-800/50">
                <p className="text-xs text-ink-faint mb-2">{t("calendar.modal.currentStatus")}</p>
                <div className="space-y-1.5">
                  {dayBlocks.map((b) => (
                    <div key={b.id} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            STATUS_COLORS[b.status]?.bg || "bg-base-700"
                          } ${STATUS_COLORS[b.status]?.text || "text-ink-dim"}`}
                        >
                          {STATUS_LABEL_KEY[b.status] ? t(STATUS_LABEL_KEY[b.status]) : b.status}
                        </span>
                        <span className="text-xs text-ink">
                          {b.hour_start}:00 - {b.hour_end}:00
                        </span>
                        {b.label && (
                          <span className="text-xs text-ink-dim truncate">
                            ({b.label})
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => deleteBlock(b.id)}
                        className="text-[10px] px-2 py-0.5 rounded bg-signal-error/10 text-signal-error border border-signal-error/20 hover:bg-signal-error/20"
                      >
                        {t("calendar.modal.delete")}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Form para anadir bloque */}
            <div className="border-t border-base-700/50 pt-4">
              <h3 className="text-sm font-medium text-ink mb-3">
                {t("calendar.modal.addBlock")}
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    {t("calendar.modal.fromHour")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={24}
                    value={formHourStart}
                    onChange={(e) => setFormHourStart(e.target.value)}
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink focus:outline-none focus:border-accent/50"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    {t("calendar.modal.toHour")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={24}
                    value={formHourEnd}
                    onChange={(e) => setFormHourEnd(e.target.value)}
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink focus:outline-none focus:border-accent/50"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    {t("calendar.modal.statusLabel")}
                  </label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as "available" | "unavailable" | "busy")}
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink focus:outline-none focus:border-accent/50"
                  >
                    <option value="available">{t("calendar.option.available")}</option>
                    <option value="unavailable">{t("calendar.option.unavailable")}</option>
                    <option value="busy">{t("calendar.option.busy")}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    {t("calendar.modal.labelField")}
                  </label>
                  <input
                    type="text"
                    value={formLabel}
                    onChange={(e) => setFormLabel(e.target.value)}
                    placeholder={t("calendar.modal.labelPlaceholder")}
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                  />
                </div>
              </div>

              {formMsg && (
                <p className={`text-xs mt-2 ${formIsError ? "text-signal-error" : "text-signal-ok"}`}>
                  {formMsg}
                </p>
              )}

              <div className="flex justify-end mt-4">
                <button
                  onClick={saveBlock}
                  className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow transition-colors"
                >
                  {t("calendar.modal.saveBlock")}
                </button>
              </div>
            </div>

            <p className="text-[10px] text-ink-faint mt-4">
              {t("calendar.modal.tip")} <em>"{t("calendar.modal.tipExample")}"</em>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}