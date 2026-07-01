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

const WEEKDAYS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];
const MONTHS_ES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

// Mapeo de status -> colores Tailwind
const STATUS_COLORS: Record<string, { bg: string; ring: string; text: string; label: string }> = {
  available:   { bg: "bg-emerald-500/15", ring: "ring-emerald-500/40", text: "text-emerald-300", label: "Libre" },
  unavailable: { bg: "bg-rose-500/20",    ring: "ring-rose-500/50",    text: "text-rose-300",    label: "No disponible" },
  busy:        { bg: "bg-amber-500/15",   ring: "ring-amber-500/40",   text: "text-amber-300",   label: "Ocupado" },
  mixed:       { bg: "bg-orange-500/15",  ring: "ring-orange-500/40",  text: "text-orange-300",  label: "Mixto" },
  neutral:     { bg: "bg-base-800/40",    ring: "ring-base-700/30",    text: "text-ink-dim",     label: "Sin config" },
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
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-12
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
    loadMonth(year, month);
  }, [year, month]);

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

  const goToday = () => {
    const d = new Date();
    setYear(d.getFullYear());
    setMonth(d.getMonth() + 1);
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
      setFormMsg("Bloque guardado");
      // Refrescar bloques del dia y el mes
      const data = await api.getDayStatus(selectedDay);
      setDayBlocks((data.blocks || []) as AvailabilityBlock[]);
      loadMonth(year, month);
    } catch (e) {
      setFormMsg(`Error: ${(e as Error).message}`);
    }
  };

  const deleteBlock = async (id: number) => {
    try {
      await api.deleteAvailability(id);
      const data = await api.getDayStatus(selectedDay!);
      setDayBlocks((data.blocks || []) as AvailabilityBlock[]);
      loadMonth(year, month);
    } catch (e) {
      setFormMsg(`Error eliminando: ${(e as Error).message}`);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="h-full p-4 flex flex-col gap-4 overflow-hidden">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Calendario</h1>
          <p className="text-xs text-ink-faint mt-0.5">
            Vista mensual con disponibilidad y eventos
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            className="text-sm px-3 py-1.5 rounded-lg bg-base-800 hover:bg-base-700 text-ink"
          >
            ← Anterior
          </button>
          <button
            onClick={goToday}
            className="text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
          >
            Hoy
          </button>
          <button
            onClick={nextMonth}
            className="text-sm px-3 py-1.5 rounded-lg bg-base-800 hover:bg-base-700 text-ink"
          >
            Siguiente →
          </button>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex items-center gap-3 flex-wrap text-[11px]">
        {Object.entries(STATUS_COLORS).map(([key, c]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className={`inline-block w-3 h-3 rounded ${c.bg}`} />
            <span className="text-ink-dim">{c.label}</span>
          </div>
        ))}
      </div>

      {/* Mes + ano */}
      <div className="text-center text-base font-medium text-ink-dim">
        {MONTHS_ES[month - 1]} {year}
        {loading && <span className="ml-2 text-xs text-ink-faint">cargando...</span>}
      </div>

      {/* Grid del calendario (7 columnas x N filas) */}
      <div className="flex-1 grid grid-cols-7 gap-2 min-h-0">
        {/* Cabeceras de dias de la semana */}
        {WEEKDAYS_ES.map((wd) => (
          <div key={wd} className="text-center text-[10px] uppercase tracking-wider text-ink-faint py-1">
            {wd}
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
                ${colors.bg} ${cell.isCurrentMonth ? colors.text : "opacity-40"}
                ring-1 ${isToday ? "ring-2 ring-accent ring-offset-2 ring-offset-base-950" : colors.ring}
                hover:ring-2
              `}
              title={
                dayInfo
                  ? `${cell.date} - ${colors.label}\n${dayInfo.event_count} evento(s)${
                      dayInfo.event_titles.length ? "\n" + dayInfo.event_titles.join("\n") : ""
                    }`
                  : cell.date
              }
            >
              {/* Numero del dia */}
              <div className="flex items-start justify-between">
                <span className={`text-sm font-medium ${isToday ? "text-accent" : ""}`}>
                  {dayNum}
                </span>
                {isToday && (
                  <span className="text-[8px] uppercase tracking-wider text-accent font-bold">
                    Hoy
                  </span>
                )}
              </div>

              {/* Titulos de eventos + labels de bloques manuales (max 3 total) */}
              {dayInfo && (dayInfo.event_titles.length > 0 || dayInfo.block_labels.length > 0) && (
                <div className="flex-1 min-h-0 space-y-0.5">
                  {/* Eventos reales (de calendar_events) - icono discreto */}
                  {dayInfo.event_titles.slice(0, 3).map((t, i) => (
                    <div
                      key={`ev-${i}`}
                      className="text-[10px] truncate bg-base-950/50 rounded px-1 py-0.5"
                      title={`Evento: ${t}`}
                    >
                      {t}
                    </div>
                  ))}
                  {/* Labels de bloques manuales (de calendar_availability) */}
                  {dayInfo.block_labels.slice(0, Math.max(0, 3 - dayInfo.event_titles.length)).map((l, i) => (
                    <div
                      key={`bl-${i}`}
                      className="text-[10px] truncate bg-base-950/30 rounded px-1 py-0.5 italic text-ink-dim"
                      title={`Bloque manual: ${l}`}
                    >
                      {l}
                    </div>
                  ))}
                  {dayInfo.event_count + dayInfo.block_count > 3 && (
                    <div className="text-[9px] text-ink-faint">
                      +{dayInfo.event_count + dayInfo.block_count - 3} mas
                    </div>
                  )}
                </div>
              )}

              {/* Indicador de bloques si hay mas de los que se muestran */}
              {dayInfo && dayInfo.block_count > dayInfo.block_labels.length && (
                <div className="text-[9px] text-ink-faint">
                  {dayInfo.block_count - dayInfo.block_labels.length} bloque(s) mas
                </div>
              )}
            </motion.button>
          );
        })}
      </div>

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
                  <span className="ml-2 text-xs text-accent">(Hoy)</span>
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
                <p className="text-xs text-ink-faint mb-2">Estado actual:</p>
                <div className="space-y-1.5">
                  {dayBlocks.map((b) => (
                    <div key={b.id} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            STATUS_COLORS[b.status]?.bg || "bg-base-700"
                          } ${STATUS_COLORS[b.status]?.text || "text-ink-dim"}`}
                        >
                          {b.status}
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
                        Eliminar
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Form para anadir bloque */}
            <div className="border-t border-base-700/50 pt-4">
              <h3 className="text-sm font-medium text-ink mb-3">
                Anadir bloque de disponibilidad
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    Desde (hora)
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
                    Hasta (hora)
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
                    Status
                  </label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as "available" | "unavailable" | "busy")}
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink focus:outline-none focus:border-accent/50"
                  >
                    <option value="available">Libre (reuniones OK)</option>
                    <option value="unavailable">No disponible</option>
                    <option value="busy">Ocupado</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-ink-faint mb-1">
                    Etiqueta (opcional)
                  </label>
                  <input
                    type="text"
                    value={formLabel}
                    onChange={(e) => setFormLabel(e.target.value)}
                    placeholder="ej. Reunion cliente X"
                    className="w-full bg-base-700 border border-base-600 rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
                  />
                </div>
              </div>

              {formMsg && (
                <p className={`text-xs mt-2 ${formMsg.startsWith("Error") ? "text-signal-error" : "text-signal-ok"}`}>
                  {formMsg}
                </p>
              )}

              <div className="flex justify-end mt-4">
                <button
                  onClick={saveBlock}
                  className="text-xs px-4 py-2 rounded-lg bg-accent text-base-950 font-medium hover:bg-accent-glow transition-colors"
                >
                  Guardar bloque
                </button>
              </div>
            </div>

            <p className="text-[10px] text-ink-faint mt-4">
              Tip: tambien puedes configurar el calendario desde el chat. Por
              ejemplo: <em>"marca manana de 14 a 18 como no disponible"</em>.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}