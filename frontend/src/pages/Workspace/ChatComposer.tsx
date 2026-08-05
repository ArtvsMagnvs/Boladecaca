// pages/Workspace/ChatComposer.tsx — la barra de escribir del chat de un agente
//
// [2026-08-02, peticiones 6 y 7 del usuario] Todo lo que rodea al cuadro de
// texto, en un solo sitio para que el chat del ORQUESTADOR y el de un AGENTE
// sean idénticos:
//
//   Debajo, a la izquierda:
//     · "+"      → adjuntar archivos o fotos (cualquier formato, sin filtrar)
//     · carpeta+ → dar a este agente acceso a una carpeta concreta
//     · selector → "Aprobar manualmente" | "Omitir todas las aprobaciones"
//   A la derecha del cuadro:
//     · selector de proveedor + modelo (por MENSAJE)
//     · micrófono
//     · enviar
//
// El selector de aprobación es la decisión del usuario sobre shell/powershell:
// en vez de una regla global, cada agente decide si le preguntan. Se persiste
// en el agente (`autonomy`), así que sobrevive a recargar.
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Agent, type MelModel } from "@/lib/api";
import { useT } from "@/store/useI18n";
import { PROVIDER_SHORT } from "@/lib/modelNames";

interface Props {
  agent: Agent | null;
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  sending: boolean;
  /** Modelo elegido para el próximo mensaje ("proveedor:modelo"), o null = el que decida el MEL. */
  model: string | null;
  onModelChange: (v: string | null) => void;
  /** Se llama cuando el agente cambia por fuera (adjunto, carpeta, autonomía). */
  onAgentChanged?: () => void;
  compact?: boolean;
}

const btn =
  "shrink-0 h-7 w-7 flex items-center justify-center rounded-lg border border-base-600 " +
  "text-ink-faint hover:text-ink hover:border-accent/40 disabled:opacity-40 transition-colors";

export function ChatComposer({
  agent, value, onChange, onSend, sending, model, onModelChange, onAgentChanged, compact,
}: Props) {
  const tr = useT();
  const fileRef = useRef<HTMLInputElement>(null);
  const [models, setModels] = useState<MelModel[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);

  // Catálogo de modelos disponibles (los proveedores CONFIGURADOS de verdad).
  useEffect(() => {
    api.getMelModels().then(setModels).catch(() => setModels([]));
  }, []);

  // [2026-08-04] AQUÍ ESTABA EL BUG QUE EL USUARIO REPORTÓ TRES VECES.
  //
  // Este selector tenía un `continue` que BORRABA de la lista, sin decir nada,
  // todo modelo marcado no apto para chat/herramientas. `unfit` se alimenta de
  // dos sitios (ver `mel.list_models`): el CATÁLOGO (los CLI de Claude y Codex,
  // excluidos del bucle de tools por un fallo real de producción) y la MEDICIÓN
  // del task-bench (modelos que fallaron los escenarios reales de uso de
  // herramientas). Como se borraban los dos grupos en silencio, en la máquina
  // del usuario solo sobrevivían los MiniMax — y desde fuera eso parece "faltan
  // modelos", no "están excluidos por un motivo".
  //
  // Y no bastaba con quitar el filtro: el backend RECHAZA DURO un override de
  // un modelo no apto (`ExplicitModelUnfit`, mel/executor.py), así que dejarlos
  // elegibles solo cambiaría "no aparece" por "falla al enviar".
  //
  // Solución: no se oculta NADA. Todos los proveedores y todos sus modelos
  // salen en la lista; los que no puede atender este chat salen desactivados y
  // CON EL MOTIVO a la vista. El usuario ve que existen y por qué no valen aquí.
  const porProveedor = useMemo(() => {
    const m = new Map<string, MelModel[]>();
    for (const x of models) {
      const g = m.get(x.provider) ?? [];
      g.push(x);
      m.set(x.provider, g);
    }
    for (const g of m.values()) g.sort((a, b) => a.model.localeCompare(b.model));
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [models]);

  // [2026-08-04, corrección de diseño del usuario] Claude CLI y Codex SÍ valen
  // en el chat de un AGENTE de proyecto: son agentes completos con SUS propias
  // herramientas, y el backend les delega la tarea entera en la carpeta del
  // proyecto (no entran en el bucle de tools de Aithera). Donde NO sirven es en
  // el chat del ORQUESTADOR (conversación) — ahí siguen vetados.
  const esCliAutosuficiente = (x: MelModel) =>
    x.provider === "claude_code" || x.provider === "codex";
  const esOrquestador = agent?.role === "orchestrator";

  const motivoNoApto = (x: MelModel): string | null => {
    const bloquea = (l?: string[]) => !!l && (l.includes("chat") || l.includes("agentic"));
    if (esCliAutosuficiente(x)) {
      // En un agente de proyecto trabaja con sus propias herramientas: válido.
      // En el orquestador (charla) no, por identidad y latencia.
      return esOrquestador ? tr("workspace.composer.unfitOrchestrator") : null;
    }
    if (bloquea(x.unfit_catalog)) return tr("workspace.composer.unfitCatalog");
    if (bloquea(x.unfit_measured)) return tr("workspace.composer.unfitMeasured");
    // Backend antiguo (sin los campos separados): motivo genérico, nunca ocultar.
    if (bloquea(x.unfit)) return tr("workspace.composer.unfitGeneric");
    return null;
  };

  // Si el modelo elegido deja de estar disponible (el usuario desconectó el
  // proveedor en Ajustes), se limpia: dejarlo puesto mandaría al backend algo
  // que el usuario ya no puede ver ni cambiar.
  useEffect(() => {
    if (!model) return;
    const sigueUsable = porProveedor.some(([, l]) =>
      l.some((m) => m.key === model && motivoNoApto(m) === null));
    if (!sigueUsable) onModelChange(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [porProveedor, model]);

  const autonomy = (agent?.autonomy || "manual") as "manual" | "auto";

  const setAutonomy = async (v: string) => {
    if (!agent) return;
    setBusy("autonomy");
    setError(null);
    try {
      await api.updateAgent(agent.id, { autonomy: v });
      onAgentChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(null);
    }
  };

  const pickFiles = () => fileRef.current?.click();

  const onFiles = async (files: FileList | null) => {
    if (!agent || !files?.length) return;
    setBusy("attach");
    setError(null);
    try {
      const nombres: string[] = [];
      for (const f of Array.from(files)) {
        const r = await api.attachToAgent(agent.id, f);
        nombres.push(r.path);
      }
      // El adjunto se NOMBRA en el mensaje: así el agente sabe que existe y
      // dónde, y puede leerlo con `document`/`filesystem` sin adivinar.
      const ref = nombres.map((p) => `«${p}»`).join(", ");
      onChange(`${value}${value ? "\n" : ""}${tr("workspace.composer.attached", { files: ref })}`);
      onAgentChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const pickFolder = async () => {
    if (!agent) return;
    // Electron: diálogo nativo. Fuera de Electron el botón ni se muestra.
    const ruta = await window.aithera?.pickFolder?.();
    if (!ruta) return;
    setBusy("folder");
    setError(null);
    try {
      await api.grantAgentFolder(agent.id, ruta);
      onAgentChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(null);
    }
  };

  // Dictado por voz: Web Speech API del navegador (Electron la trae). Si no
  // está, el botón no se pinta — mejor que un botón que no hace nada.
  const speech = useMemo(() => {
    const W = window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
    return W.SpeechRecognition || W.webkitSpeechRecognition || null;
  }, []);

  const toggleMic = () => {
    if (!speech) return;
    if (listening) {
      setListening(false);
      return;
    }
    try {
      const Rec = speech as new () => {
        lang: string; interimResults: boolean; continuous: boolean;
        onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
        onend: () => void; onerror: () => void; start: () => void; stop: () => void;
      };
      const rec = new Rec();
      rec.lang = document.documentElement.lang || "es-ES";
      rec.interimResults = false;
      rec.continuous = false;
      rec.onresult = (e) => {
        const dicho = Array.from({ length: e.results.length }, (_, i) => e.results[i][0].transcript).join(" ");
        if (dicho.trim()) onChange(`${value}${value ? " " : ""}${dicho.trim()}`);
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      rec.start();
      setListening(true);
    } catch {
      setListening(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      {error && <p className="text-[10px] text-signal-error break-words">{error}</p>}

      {/* Cuadro de texto + acciones de la derecha */}
      <div className="flex gap-1.5 items-end">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          rows={compact ? 1 : 2}
          className="flex-1 min-w-0 bg-base-800/70 border border-base-600 rounded-lg px-2 py-1.5 text-[11px] text-ink resize-none focus:outline-none focus:border-accent/50"
          placeholder={tr("workspace.orchestrator.placeholder")}
        />
        {/* Selector de proveedor + modelo, POR MENSAJE. [2026-08-02] Siempre
            TODOS los proveedores activos y TODOS sus modelos, con el nombre
            COMPLETO (petición explícita del usuario) — nada de "Modelo IA"
            del agente restringiendo esto. */}
        <select
          value={model ?? ""}
          onChange={(e) => onModelChange(e.target.value || null)}
          title={tr("workspace.composer.modelTitle")}
          className="shrink-0 h-7 max-w-[190px] bg-base-800/70 border border-base-600 rounded-lg px-1 text-[10px] text-ink-dim focus:outline-none focus:border-accent/50"
        >
          <option value="">{tr("workspace.composer.modelAuto")}</option>
          {porProveedor.map(([proveedor, lista]) => (
            <optgroup key={proveedor} label={PROVIDER_SHORT[proveedor] ?? proveedor}>
              {lista.map((m) => {
                const motivo = motivoNoApto(m);
                return (
                  <option key={m.key} value={m.key} disabled={motivo !== null}>
                    {motivo ? `${m.model_label} — ${motivo}` : m.model_label}
                  </option>
                );
              })}
            </optgroup>
          ))}
        </select>
        {speech && (
          <button
            type="button"
            onClick={toggleMic}
            title={tr("workspace.composer.mic")}
            aria-label={tr("workspace.composer.mic")}
            className={`${btn} ${listening ? "border-accent text-accent animate-pulse" : ""}`}
          >
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.6">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
            </svg>
          </button>
        )}
        <button
          type="button"
          onClick={onSend}
          disabled={!value.trim() || sending}
          className="shrink-0 h-7 px-2.5 rounded-lg text-[11px] bg-accent/20 text-accent border border-accent/40 hover:bg-accent/30 disabled:opacity-40"
        >
          {sending ? "…" : tr("chat.send")}
        </button>
      </div>

      {/* Debajo, a la izquierda: adjuntar, carpeta y política de aprobación */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <input ref={fileRef} type="file" multiple className="hidden"
               onChange={(e) => void onFiles(e.target.files)} />
        <button type="button" onClick={pickFiles} disabled={!agent || busy === "attach"}
                title={tr("workspace.composer.attach")} aria-label={tr("workspace.composer.attach")}
                className={btn}>
          <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
        </button>
        {window.aithera?.pickFolder && (
          <button type="button" onClick={() => void pickFolder()} disabled={!agent || busy === "folder"}
                  title={tr("workspace.composer.addFolder")} aria-label={tr("workspace.composer.addFolder")}
                  className={btn}>
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2h9A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z" />
              <path d="M12 11.5v4M10 13.5h4" strokeLinecap="round" />
            </svg>
          </button>
        )}
        <select
          value={autonomy}
          onChange={(e) => void setAutonomy(e.target.value)}
          disabled={!agent || busy === "autonomy"}
          title={tr("workspace.composer.autonomyTitle")}
          className="h-7 bg-base-800/70 border border-base-600 rounded-lg px-1.5 text-[10px] text-ink-dim focus:outline-none focus:border-accent/50"
        >
          <option value="manual">{tr("workspace.composer.autonomyManual")}</option>
          <option value="auto">{tr("workspace.composer.autonomySkip")}</option>
        </select>
        {!!agent?.extra_paths?.length && (
          <span className="text-[10px] text-ink-faint" title={agent.extra_paths.join("\n")}>
            {tr("workspace.composer.extraFolders", { n: agent.extra_paths.length })}
          </span>
        )}
      </div>
    </div>
  );
}

export default ChatComposer;
