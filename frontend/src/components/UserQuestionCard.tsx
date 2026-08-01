// components/UserQuestionCard.tsx — LA VENTANA DE PREGUNTA
// [2026-08-02, petición explícita del usuario: "exactamente igual que la que
// hay aquí en Claude Code"]
//
// QUÉ RESUELVE: hasta ahora Aithera no tenía forma de preguntar. Cuando le
// faltaba un dato (el caso real: "¿el stack es Unity o genérico?", "¿A, B o
// C?"), lo único que podía hacer era terminar la misión y escribir la pregunta
// en el resumen final — donde ya no sirve para nada, porque nadie la contesta y
// el trabajo se queda sin hacer.
//
// LA FORMA (igual que en Claude Code): etiqueta corta del tema · el enunciado ·
// las opciones sugeridas numeradas, la 1.ª marcada como recomendada · y SIEMPRE
// una última opción en blanco para escribir una respuesta propia, porque las
// sugerencias del modelo pueden no servir o quedarse cortas.
//
// LA ESPERA ES INDEFINIDA (decisión del usuario, PU3): esta tarjeta puede estar
// en pantalla horas o días. No hay cuenta atrás ni caducidad — el backend
// (`toolloop.ask_user`) sigue esperando hasta que se responda.
import { useEffect, useRef, useState } from "react";
import { api, type Approval } from "@/lib/api";
import { useT } from "@/store/useI18n";

interface Props {
  question: Approval;
  /** Se llama tras responder, para que el contenedor refresque su lista. */
  onAnswered?: () => void;
  /** `true` en superficies estrechas (tarjeta de proyecto/agente). */
  compact?: boolean;
}

export function UserQuestionCard({ question, onAnswered, compact = false }: Props) {
  const tr = useT();
  const [custom, setCustom] = useState("");
  const [writing, setWriting] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const options = question.options ?? [];
  const enunciado = question.question || question.summary || question.title;

  useEffect(() => {
    if (writing) inputRef.current?.focus();
  }, [writing]);

  const answer = async (texto: string) => {
    const limpio = texto.trim();
    if (!limpio || sending) return;
    setSending(true);
    setError(null);
    try {
      // Una respuesta SIEMPRE es `approved`: el veredicto no es sí/no, es el
      // texto. Descartar la pregunta (rechazarla) es el botón aparte de abajo.
      await api.resolveApproval(question.gate_id, true, limpio);
      onAnswered?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("question.failed"));
      setSending(false);
    }
  };

  const discard = async () => {
    if (sending) return;
    setSending(true);
    setError(null);
    try {
      await api.resolveApproval(question.gate_id, false, tr("question.discarded"));
      onAnswered?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr("question.failed"));
      setSending(false);
    }
  };

  // Atajos 1..9 para elegir opción, como en Claude Code. Se desactivan
  // mientras se escribe una respuesta propia (si no, teclear "1" elegiría).
  useEffect(() => {
    if (writing || sending) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      const n = Number(e.key);
      if (Number.isInteger(n) && n >= 1 && n <= options.length) {
        e.preventDefault();
        void answer(options[n - 1]);
      } else if (Number.isInteger(n) && n === options.length + 1) {
        e.preventDefault();
        setWriting(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, writing, sending]);

  const rowCls =
    "w-full text-left flex items-start gap-2.5 rounded-lg border border-base-700 " +
    "bg-base-800/40 px-3 py-2 hover:border-accent/60 hover:bg-accent/10 " +
    "transition-colors disabled:opacity-50 disabled:cursor-default";
  const numCls =
    "shrink-0 mt-0.5 h-5 w-5 rounded border border-base-600 text-[10px] " +
    "flex items-center justify-center text-ink-faint font-mono";

  return (
    <section
      className="glass-surface holo-frame rounded-xl border border-accent/40 p-3.5"
      aria-label={tr("question.aria")}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/15 text-accent border border-accent/30">
          {question.header?.trim() || tr("question.badge")}
        </span>
        <span className="text-[10px] text-ink-faint">{tr("question.waiting")}</span>
      </div>

      <p className={`${compact ? "text-xs" : "text-sm"} text-ink font-medium mb-3 whitespace-pre-wrap break-words`}>
        {enunciado}
      </p>

      <div className="flex flex-col gap-1.5">
        {options.map((op, i) => (
          <button key={i} type="button" disabled={sending} onClick={() => void answer(op)} className={rowCls}>
            <span className={numCls}>{i + 1}</span>
            <span className="text-xs text-ink-dim break-words">
              {op}
              {i === 0 && (
                <span className="ml-1.5 text-[10px] text-accent">{tr("question.recommended")}</span>
              )}
            </span>
          </button>
        ))}

        {/* La opción en blanco: SIEMPRE presente, incluso sin sugerencias —
            es la que permite responder algo que el modelo no previó, o
            completar una de las suyas. */}
        {!writing ? (
          <button type="button" disabled={sending} onClick={() => setWriting(true)} className={rowCls}>
            <span className={numCls}>{options.length + 1}</span>
            <span className="text-xs text-ink-dim italic">{tr("question.other")}</span>
          </button>
        ) : (
          <div className="rounded-lg border border-accent/40 bg-base-800/40 p-2">
            <textarea
              ref={inputRef}
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void answer(custom);
                } else if (e.key === "Escape") {
                  e.preventDefault();
                  setWriting(false);
                }
              }}
              rows={compact ? 2 : 3}
              placeholder={tr("question.otherPlaceholder")}
              className="w-full bg-transparent text-xs text-ink resize-y focus:outline-none placeholder:text-ink-faint"
            />
            <div className="flex items-center justify-end gap-2 mt-1.5">
              <button
                type="button"
                onClick={() => setWriting(false)}
                className="text-[11px] text-ink-faint hover:text-ink px-2 py-1"
              >
                {tr("common.cancel")}
              </button>
              <button
                type="button"
                disabled={!custom.trim() || sending}
                onClick={() => void answer(custom)}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-40"
              >
                {sending ? "…" : tr("question.send")}
              </button>
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-[11px] text-signal-error mt-2">{error}</p>}

      <div className="flex items-center justify-between mt-2.5">
        <span className="text-[10px] text-ink-faint">{tr("question.hint")}</span>
        <button
          type="button"
          disabled={sending}
          onClick={() => void discard()}
          className="text-[10px] text-ink-faint hover:text-signal-error px-1.5 py-0.5"
        >
          {tr("question.discard")}
        </button>
      </div>
    </section>
  );
}
