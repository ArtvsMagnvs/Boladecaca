// components/voice/VoicePanel.tsx — TODA la configuración de voz, dentro de
// Configuración → Voz (petición del usuario, 2026-07-21: antes vivía dispersa
// entre el "Centro de Voz" del sidebar y Ajustes; ahora hay UN solo sitio).
// Es el antiguo pages/VoiceCenter.tsx adaptado a vivir dentro del modal de
// Ajustes: flujo natural (el modal scrollea) en vez de h-full/overflow propio,
// y la lista de voces con altura acotada para no comerse la pestaña entera.
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import PersonalityPicker from "@/components/voice/PersonalityPicker";
import { useT } from "@/store/useI18n";

// V0.83 (Paso 3): claves de la tabla Config para persistir preferencias TTS.
// NO son secretos: son voice_ids publicos de ElevenLabs y elecciones del
// usuario, asi que texto plano. El unico secreto (la API key) va por DPAPI
// via el path de proveedores IA (patron V0.8 hardening).
const CFG_KEY_SELECTED_VOICE = "tts_selected_voice";
const CFG_KEY_ACTIVE_PROVIDER = "tts_active_provider";
const CFG_KEY_FAVORITE_VOICES = "tts_favorite_voice_ids";

interface VoiceConfig {
  voice_id: string;
  name: string;
  category: "premade" | "cloned" | "professional" | "generated";
  /** Idioma deducido de labels o available_languages. */
  lang: string;
  gender: "male" | "female" | "unknown";
  description?: string;
  previewText: string;
}

// Preview por defecto cuando la voz no trae uno propio.
const DEFAULT_PREVIEW = "Hola, soy tu asistente de voz de Aithera. ¿En qué puedo ayudarte hoy?";

// [A·VOZ-8] Texto de muestra EN EL IDIOMA DE CADA VOZ. Antes se sintetizaba
// siempre una frase en español: al probar una voz francesa/inglesa/portuguesa,
// esa voz leía el español con su acento ("español con acento francés"), que es
// justo lo que el usuario reportó. Cada voz debe leer una frase de SU idioma.
const PREVIEW_BY_LANG: Record<string, string> = {
  es: "Hola, soy tu asistente de voz de Aithera. ¿En qué puedo ayudarte hoy?",
  en: "Hi, I'm your Aithera voice assistant. How can I help you today?",
  fr: "Bonjour, je suis ton assistant vocal Aithera. Comment puis-je t'aider aujourd'hui ?",
  pt: "Olá, sou o teu assistente de voz da Aithera. Como posso ajudar-te hoje?",
  ja: "こんにちは、Aithera の音声アシスタントです。今日はどのようにお手伝いしましょうか？",
  zh: "你好，我是你的 Aithera 语音助手。今天我能帮你什么？",
};

/** Frase de prueba acorde al idioma de la voz (fallback: español). */
function previewForLang(lang: string): string {
  return PREVIEW_BY_LANG[(lang || "es").slice(0, 2).toLowerCase()] || DEFAULT_PREVIEW;
}

// Mapeo de genero segun el label "gender" de ElevenLabs (que en cuentas
// reales suele venir como descriptor, no como label oficial).
function genderFromLabels(labels?: Record<string, string>): VoiceConfig["gender"] {
  if (!labels) return "unknown";
  const g = (labels.gender || labels.sex || "").toLowerCase();
  if (g.startsWith("f") || g.includes("female") || g.includes("mujer")) return "female";
  if (g.startsWith("m") || g.includes("male") || g.includes("hombre")) return "male";
  // Heuristica adicional: el nombre de la voz suele delatar el genero.
  const desc = (labels.description || "").toLowerCase();
  if (desc.includes("female") || desc.includes("femenin")) return "female";
  if (desc.includes("male") || desc.includes("masculin")) return "male";
  return "unknown";
}

// Mapeo de idioma segun labels o available_languages.
function langFromVoice(v: { labels?: Record<string, string>; available_languages?: string[] }): string {
  const langs = v.available_languages || [];
  if (langs.length > 0) {
    // ElevenLabs devuelve ISO 639-1 (e.g. "es", "en", "pt-BR"). Tomamos
    // los 2 primeros chars para tener el idioma base.
    const l = langs[0].slice(0, 2).toLowerCase();
    if (l) return l;
  }
  const lbl = (v.labels?.language || v.labels?.lang || v.labels?.accent || "").toLowerCase();
  if (lbl.startsWith("es")) return "es";
  if (lbl.startsWith("en")) return "en";
  if (lbl.startsWith("pt")) return "pt";
  return "other";
}

// V0.83: proveedores TTS seleccionables. EdgeTTS por defecto (gratis, sin key).
// [A·VOZ-5, doc 32] Kokoro = voz local de máxima calidad SIN Docker vía
// `kokoro-onnx` (ONNX Runtime, sin PyTorch): SÍ funciona en Python 3.13; se
// instala con un botón (pip + descarga del modelo ~108 MB, cero admin/reboot).
// [A·VOZ-1] eSpeak retirado: EdgeTTS es el fallback siempre disponible.
type Provider = "edgetts" | "elevenlabs" | "kokoro";
const PROVIDERS: Provider[] = ["edgetts", "elevenlabs", "kokoro"];
const PROVIDER_LABELS: Record<Provider, string> = {
  edgetts: "EdgeTTS",
  elevenlabs: "ElevenLabs",
  kokoro: "Kokoro",
};

// [2026-07-24] Etiquetas de "de un vistazo" por proveedor (petición del
// usuario): cada proveedor lleva 2-3 chips diminutos que resumen sus rasgos
// clave (coste / calidad de voz / requisito técnico) sin tener que leer nada.
// El COLOR se asigna por TIPO de rasgo, no por proveedor — así el usuario
// aprende el código de un vistazo (verde=gratis, ámbar=fricción de coste o
// descarga, acento=nivel de voz, neutro=sin fricción) y lo reconoce en
// cualquier proveedor. Solo 4 tonos, reusando las variables de tema
// existentes (signal-ok/warn + accent) — cero colores nuevos, cero peso visual.
type TagTone = "ok" | "warn" | "accent" | "neutral";
const PROVIDER_TAGS: Record<Provider, { key: string; tone: TagTone }[]> = {
  edgetts: [
    { key: "free", tone: "ok" },
    { key: "basicVoices", tone: "accent" },
    { key: "noDownload", tone: "neutral" },
  ],
  elevenlabs: [
    { key: "premiumVoices", tone: "accent" },
    { key: "subscription", tone: "warn" },
  ],
  kokoro: [
    { key: "free", tone: "ok" },
    { key: "advancedVoices", tone: "accent" },
    { key: "requiresDownload", tone: "warn" },
  ],
};
const TAG_TONE_CLASSES: Record<TagTone, string> = {
  ok: "bg-signal-ok/15 text-signal-ok",
  warn: "bg-signal-warn/15 text-signal-warn",
  accent: "bg-accent/15 text-accent",
  // 'neutral' antes usaba text-ink-faint sobre base-700: apenas se leía. Sube
  // a text-ink-dim con un fondo/borde un poco más presentes — visible sin
  // gritar (mismo peso perceptual que los demás chips).
  neutral: "bg-base-700/70 text-ink-dim",
};

// Voces "simples" (EdgeTTS / Kokoro vienen como {id, name, lang}) -> VoiceConfig.
function mapSimpleVoice(v: { id: string; name: string; lang: string }): VoiceConfig {
  const n = v.name || v.id;
  const gender: VoiceConfig["gender"] =
    n.includes("♀") ? "female" : n.includes("♂") ? "male" : "unknown";
  return {
    voice_id: v.id,
    name: n,
    category: "premade",
    lang: v.lang || "es",
    gender,
    description: "",
    previewText: previewForLang(v.lang || "es"),
  };
}

export default function VoicePanel() {
  const t = useT();
  const [voices, setVoices] = useState<VoiceConfig[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<VoiceConfig | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [activeProvider, setActiveProvider] = useState<Provider>("edgetts");
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [voiceLoadError, setVoiceLoadError] = useState<string | null>(null);
  const [, setElevenlabsConfigured] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterGender, setFilterGender] = useState<"all" | "male" | "female">("all");
  const [filterLang, setFilterLang] = useState<string>("all");
  const [volume, setVolume] = useState(1);
  // [2026-07-21] Estado de Kokoro (instalado / instalando / fallo) + botón
  // "Instalar Kokoro": el backend YA tenía el endpoint de instalación (pip),
  // pero el botón nunca existió en la UI. Ahora existe y el progreso se sondea.
  const [kokoroStatus, setKokoroStatus] = useState<{ available: boolean; install_status?: string; message: string } | null>(null);
  const [kokoroInstalling, setKokoroInstalling] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  // V0.8.1 (Paso 2): cableado del nucleo al TTS manual (boton "Escuchar muestra").
  const setCoreState = useAppStore((s) => s.setCoreState);

  // [PU1, doc 35] Guardas anti-carrera: si el usuario cambia de proveedor
  // antes de que la peticion anterior responda, esa respuesta vieja NO debe
  // pisar el estado de la pestana nueva (bug reportado: "Kokoro muestra voces
  // de ElevenLabs" — la peticion de ElevenLabs tardaba mas y llegaba DESPUES
  // de haber cambiado a Kokoro). `loadRequestId` numera cada llamada a
  // `loadVoicesFor`; solo la mas reciente puede escribir en `voices`.
  // `activeProviderRef` cubre la segunda via del mismo bug: el sondeo de
  // instalacion de Kokoro recarga sus voces al terminar aunque el usuario ya
  // este viendo otra pestana.
  const loadRequestId = useRef(0);
  const activeProviderRef = useRef<Provider>(activeProvider);
  useEffect(() => {
    activeProviderRef.current = activeProvider;
  }, [activeProvider]);

  // Si el usuario cierra Ajustes con un preview sonando, nucleo a idle.
  useEffect(() => {
    return () => {
      if (audioRef.current && !audioRef.current.paused) {
        setCoreState("idle");
      }
    };
  }, [setCoreState]);

  // V0.83: carga las voces del proveedor dado y elige la voz inicial.
  const loadVoicesFor = useCallback(async (provider: Provider, preferId?: string | null) => {
    // [PU1, doc 35] Esta llamada se numera; si al terminar ya no es la mas
    // reciente (el usuario cambio de proveedor mientras tanto), se descarta
    // en vez de escribir sobre el estado de la pestana actual.
    const requestId = ++loadRequestId.current;
    const isStale = () => requestId !== loadRequestId.current;

    setLoadingVoices(true);
    setVoiceLoadError(null);
    try {
      let list: VoiceConfig[] = [];
      if (provider === "edgetts") {
        const r = await api.getEdgeVoices();
        if (isStale()) return;
        list = (r.voices || []).map(mapSimpleVoice);
      } else if (provider === "kokoro") {
        try {
          const st = await api.getKokoroStatus();
          if (isStale()) return;
          setKokoroStatus(st);
          if (!st.available) setVoiceLoadError(st.message);
        } catch {
          /* status opcional */
        }
        if (isStale()) return;
        const r = await api.getKokoroVoices();
        if (isStale()) return;
        list = (r.voices || []).map(mapSimpleVoice);
      } else {
        // elevenlabs
        const status = await api.getVoiceStatus();
        if (isStale()) return;
        if (status.configured) {
          setElevenlabsConfigured(true);
          const r = await api.getAccountVoices();
          if (isStale()) return;
          list = (r.voices || []).map((v) => ({
            voice_id: v.voice_id,
            name: v.name,
            category: (v.category as VoiceConfig["category"]) || "premade",
            lang: langFromVoice({ labels: v.labels, available_languages: v.available_languages }),
            gender: genderFromLabels(v.labels),
            description: v.description || v.labels?.description || "",
            previewText: previewForLang(langFromVoice({ labels: v.labels, available_languages: v.available_languages })),
          }));
        } else {
          setVoiceLoadError(t("settings.voz.panel.elevenlabsNotConfigured"));
        }
      }
      if (isStale()) return;
      let initial: VoiceConfig | null = null;
      if (preferId) initial = list.find((v) => v.voice_id === preferId) ?? null;
      if (!initial) initial = list[0] ?? null;
      setVoices(list);
      setSelectedVoice(initial);
    } catch (e: unknown) {
      if (isStale()) return;
      setVoiceLoadError(e instanceof Error ? e.message : String(e));
      setVoices([]);
      setSelectedVoice(null);
    } finally {
      if (!isStale()) setLoadingVoices(false);
    }
  }, []);

  // Arranque: lee preferencias persistidas y carga las voces de ese proveedor.
  useEffect(() => {
    (async () => {
      let persistedId: string | null = null;
      let persistedProvider: Provider = "edgetts";
      let persistedFavs: string[] = [];
      try {
        const all = await api.getConfig();
        for (const row of all) {
          if (row.key === CFG_KEY_SELECTED_VOICE) persistedId = row.value;
          else if (row.key === CFG_KEY_ACTIVE_PROVIDER) {
            if ((PROVIDERS as string[]).includes(row.value)) persistedProvider = row.value as Provider;
          } else if (row.key === CFG_KEY_FAVORITE_VOICES) {
            persistedFavs = row.value.split(",").map((s) => s.trim()).filter(Boolean);
          }
        }
      } catch {
        /* sin config = defaults */
      }
      setActiveProvider(persistedProvider);
      setFavorites(new Set(persistedFavs));
      loadVoicesFor(persistedProvider, persistedId);
    })();
  }, [loadVoicesFor]);

  const persistSelected = useCallback((voice: VoiceConfig) => {
    api.setConfig(CFG_KEY_SELECTED_VOICE, voice.voice_id).catch(() => {
      /* la eleccion sigue en memoria aunque la persistencia falle */
    });
  }, []);

  const persistProvider = useCallback((p: Provider) => {
    api.setConfig(CFG_KEY_ACTIVE_PROVIDER, p).catch(() => {
      /* idem */
    });
  }, []);

  const toggleFavorite = useCallback((voiceId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(voiceId)) next.delete(voiceId);
      else next.add(voiceId);
      api.setConfig(CFG_KEY_FAVORITE_VOICES, Array.from(next).join(",")).catch(() => {
        /* idem */
      });
      return next;
    });
  }, []);

  const handlePreview = useCallback(async () => {
    if (isPlaying || isLoading) {
      if (audioRef.current) {
        audioRef.current.pause();
        try { URL.revokeObjectURL(audioRef.current.src); } catch { /* noop */ }
        audioRef.current = null;
      }
      setIsPlaying(false);
      setCoreState("idle");
      return;
    }
    if (!selectedVoice) return;

    setIsLoading(true);
    setError(null);

    try {
      const prov = activeProvider === "elevenlabs" ? undefined : activeProvider;
      const { buffer, mime } = await api.synthesizeVoice(
        selectedVoice.previewText,
        selectedVoice.voice_id,
        prov,
      );

      const blob = new Blob([buffer], { type: mime });
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const audio = new Audio(url);
      audio.volume = volume;
      audioRef.current = audio;

      audio.onplay = () => setCoreState("speaking");
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
        setCoreState("idle");
      };
      audio.onerror = () => {
        setIsPlaying(false);
        setError(t("settings.voz.panel.playbackError"));
        URL.revokeObjectURL(url);
        setCoreState("idle");
      };

      setIsPlaying(true);
      await audio.play();
    } catch (err: unknown) {
      console.error("Error synthesizing:", err);
      setError(err instanceof Error ? err.message : t("settings.voz.panel.synthesisError"));
      setIsPlaying(false);
      setCoreState("idle");
    } finally {
      setIsLoading(false);
    }
  }, [selectedVoice, volume, isPlaying, isLoading, setCoreState, activeProvider]);

  const handleSelectVoice = useCallback((voice: VoiceConfig) => {
    setSelectedVoice(voice);
    persistSelected(voice);
  }, [persistSelected]);

  const handleProviderChange = useCallback((p: Provider) => {
    setActiveProvider(p);
    persistProvider(p);
    loadVoicesFor(p);
  }, [persistProvider, loadVoicesFor]);

  // [2026-07-21] Lanza la instalación de Kokoro (pip en el backend) y activa el
  // sondeo del progreso.
  const handleInstallKokoro = useCallback(async () => {
    try {
      const r = await api.installKokoro();
      setKokoroInstalling(true);
      setKokoroStatus((prev) => prev ? { ...prev, install_status: "installing", message: r.message } : { available: false, install_status: "installing", message: r.message });
    } catch (e) {
      setError(e instanceof Error ? e.message : t("settings.voz.panel.kokoroLaunchError"));
    }
  }, [t]);

  // Sondeo del estado de la instalación (cada 4s, solo mientras instala).
  useEffect(() => {
    if (!kokoroInstalling) return;
    const id = window.setInterval(async () => {
      try {
        const st = await api.getKokoroStatus();
        setKokoroStatus(st);
        if (st.available || st.install_status === "failed" || st.install_status === "done") {
          setKokoroInstalling(false);
          // [PU1, doc 35] Solo recarga la lista si el usuario SIGUE en la
          // pestana Kokoro — si ya cambio a otra, recargar aqui pisaria las
          // voces del proveedor que esta viendo ahora (mismo bug, otra via).
          if (st.available && activeProviderRef.current === "kokoro") loadVoicesFor("kokoro");
        }
      } catch {
        /* siguiente tick */
      }
    }, 4000);
    return () => window.clearInterval(id);
  }, [kokoroInstalling, loadVoicesFor]);

  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        try { URL.revokeObjectURL(audioRef.current.src); } catch { /* noop */ }
      }
    };
  }, []);

  // Orden: primero favoritas, despues por idioma, despues por nombre.
  const sortedVoices = useMemo(() => {
    return [...voices].sort((a, b) => {
      const aFav = favorites.has(a.voice_id) ? 0 : 1;
      const bFav = favorites.has(b.voice_id) ? 0 : 1;
      if (aFav !== bFav) return aFav - bFav;
      if (a.lang !== b.lang) return a.lang.localeCompare(b.lang);
      return a.name.localeCompare(b.name);
    });
  }, [voices, favorites]);

  const filteredVoices = sortedVoices.filter(v => {
    const genderMatch = filterGender === "all" || v.gender === filterGender;
    const langMatch = filterLang === "all" || v.lang === filterLang;
    return genderMatch && langMatch;
  });

  const getLangLabel = (lang: string) => {
    // Nombres de idioma nativos (describen la VOZ, no la interfaz) —
    // se muestran igual sea cual sea el idioma de la app, por eso no pasan
    // por t(): "日本語" no cambia si la interfaz está en francés.
    const labels: Record<string, string> = {
      "es": "Español", "en": "English", "ja": "日本語",
      "fr": "Français", "pt": "Português", "zh": "中文",
    };
    return labels[lang] || lang;
  };

  const getLangFlag = (lang: string) => {
    const flags: Record<string, string> = {
      "es": "🇪🇸", "en": "🇬🇧", "ja": "🇯🇵", "fr": "🇫🇷", "pt": "🇧🇷", "zh": "🇨🇳",
    };
    return flags[lang] || "🌐";
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Estado + proveedor + preview.
          [2026-07-21] Posición FIJA de los botones: el texto de estado vive en
          su propia columna (flex-1 min-w-0) y hace 2 líneas si es largo (caso
          Kokoro); los controles van en shrink-0 — nunca se desplazan. */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs flex-1 min-w-0">
          <span
            className={`inline-block w-2 h-2 rounded-full mr-1 ${
              voices.length > 0 ? "bg-signal-ok" : "bg-signal-warn"
            }`}
          />
          <span className="text-ink-faint break-words">
            {loadingVoices
              ? t("settings.voz.panel.loadingVoices")
              : voiceLoadError
                ? voiceLoadError
                : voices.length > 0
                  ? t("settings.voz.panel.voiceCount", { n: voices.length, provider: PROVIDER_LABELS[activeProvider] })
                  : t("settings.voz.panel.noVoices", { provider: PROVIDER_LABELS[activeProvider] })}
          </span>
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex bg-base-900/60 rounded-xl p-0.5 border border-base-700/60">
            {PROVIDERS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handleProviderChange(p)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  activeProvider === p
                    ? "bg-accent/15 text-accent"
                    : "text-ink-faint hover:text-ink"
                }`}
                title={
                  p === "edgetts"
                    ? t("settings.voz.panel.providerTitle.edgetts")
                    : p === "elevenlabs"
                      ? t("settings.voz.panel.providerTitle.elevenlabs")
                      : t("settings.voz.panel.providerTitle.kokoro")
                }
              >
                {PROVIDER_LABELS[p]}
              </button>
            ))}
          </div>
          <button
            onClick={handlePreview}
            disabled={isLoading || !selectedVoice}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
              isPlaying
                ? "bg-signal-error/15 text-signal-error border border-signal-error/30"
                : "bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
            } disabled:opacity-50`}
          >
            {isLoading ? t("settings.voz.panel.generating") : isPlaying ? `■ ${t("settings.voz.panel.stop")}` : `▶ ${t("settings.voz.panel.listenSample")}`}
          </button>
        </div>
      </div>

      {/* [2026-07-24] Etiquetas "de un vistazo" por proveedor (petición del
          usuario): al abrir la pestaña de Voz se ven de golpe las cualidades de
          los 3 sistemas (coste / calidad / si hay que descargar algo), sin tener
          que entrar en cada uno. Cada proveedor va EN SU PROPIO MARCO para que no
          se mezclen los chips de uno con los del siguiente. El proveedor activo
          resalta con borde de acento; los demás quedan atenuados. */}
      <div className="flex flex-wrap items-stretch gap-2 -mt-1">
        {PROVIDERS.map((p) => (
          <div
            key={p}
            className={`flex items-center gap-1.5 rounded-lg border px-2 py-1.5 transition-all ${
              activeProvider === p
                ? "border-accent/40 bg-accent/5 opacity-100"
                : "border-base-700/60 bg-base-900/30 opacity-60"
            }`}
          >
            <span className="text-[10px] font-semibold text-ink-dim">{PROVIDER_LABELS[p]}</span>
            {PROVIDER_TAGS[p].map((tag) => (
              <span
                key={tag.key}
                className={`text-[9px] leading-none px-1.5 py-1 rounded-full font-medium whitespace-nowrap ${TAG_TONE_CLASSES[tag.tone]}`}
              >
                {t(`settings.voz.panel.tag.${tag.key}`)}
              </span>
            ))}
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-signal-error/10 border border-signal-error/30 rounded-xl p-3 text-sm text-signal-error">
          {error}
        </div>
      )}

      {/* [2026-07-21] Kokoro sin instalar: banner con el botón de instalación
          (endpoint pip del backend, con seguimiento de estado real). */}
      {activeProvider === "kokoro" && kokoroStatus && !kokoroStatus.available && (
        <div className="rounded-xl border border-signal-warn/30 bg-signal-warn/10 p-3 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-ink mb-0.5">{t("settings.voz.panel.kokoroTitle")}</p>
            <p className={`text-[11px] break-words ${kokoroStatus.install_status === "failed" ? "text-signal-error" : "text-ink-dim"}`}>
              {kokoroStatus.message}
            </p>
          </div>
          <button
            type="button"
            onClick={handleInstallKokoro}
            disabled={kokoroInstalling || kokoroStatus.install_status === "installing"}
            className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 disabled:opacity-50"
          >
            {kokoroInstalling || kokoroStatus.install_status === "installing"
              ? t("settings.voz.panel.kokoroInstalling")
              : kokoroStatus.install_status === "failed"
                ? t("settings.voz.panel.kokoroRetry")
                : t("settings.voz.panel.kokoroInstall")}
          </button>
        </div>
      )}

      {/* [V2] Personalidad: CÓMO habla Aithera (distinto de CON QUÉ VOZ). */}
      <div className="rounded-xl border border-base-700/60 bg-base-900/40 p-3">
        <h4 className="text-xs font-medium text-ink mb-2">{t("settings.voz.panel.personality")}</h4>
        <PersonalityPicker />
      </div>

      {/* Filtros */}
      {voices.length > 0 && (
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-2">
            {(["all", "female", "male"] as const).map(g => (
              <button
                key={g}
                onClick={() => setFilterGender(g)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  filterGender === g
                    ? "bg-accent/15 border-accent/30 text-ink"
                    : "border-base-700/40 text-ink-faint hover:text-ink hover:border-base-600/50"
                }`}
              >
                {g === "all" ? t("settings.voz.panel.genderAll") : g === "female" ? `♀ ${t("settings.voz.panel.genderFemale")}` : `♂ ${t("settings.voz.panel.genderMale")}`}
              </button>
            ))}
          </div>
          <select
            value={filterLang}
            onChange={e => setFilterLang(e.target.value)}
            className="bg-base-800 border border-base-700 rounded-lg px-3 py-1.5 text-xs text-ink"
          >
            <option value="all">🌐 {t("settings.voz.panel.allLanguages")}</option>
            {Array.from(new Set(voices.map((v) => v.lang))).sort().map((lang) => (
              <option key={lang} value={lang}>
                {getLangFlag(lang)} {getLangLabel(lang)}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-ink-faint">
            {t("settings.voz.panel.filteredCount", { n: filteredVoices.length, total: voices.length })}
            {favorites.size > 0 && ` · ${t("settings.voz.panel.favoritesCount", { n: favorites.size })}`}
          </span>
        </div>
      )}

      {/* Lista de voces — altura acotada con scroll propio para no comerse la
          pestaña entera del modal. */}
      <div className="max-h-[380px] overflow-y-auto pr-1">
        {loadingVoices ? (
          <p className="text-sm text-ink-faint">{t("settings.voz.panel.loadingVoices")}</p>
        ) : filteredVoices.length === 0 ? (
          <p className="text-sm text-ink-faint">
            {voices.length === 0
              ? (activeProvider === "elevenlabs"
                  ? t("settings.voz.panel.noVoicesElevenlabs")
                  : activeProvider === "kokoro"
                    ? t("settings.voz.panel.noVoicesKokoro")
                    : (voiceLoadError || t("settings.voz.panel.noVoicesGeneric")))
              : t("settings.voz.panel.noVoicesMatchFilters")}
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredVoices.map(voice => {
              const isFav = favorites.has(voice.voice_id);
              return (
                <div
                  key={voice.voice_id}
                  onClick={() => handleSelectVoice(voice)}
                  className={`rounded-xl p-3 cursor-pointer transition-all border relative bg-base-900/40 ${
                    selectedVoice?.voice_id === voice.voice_id
                      ? "border-accent/40 shadow-[0_0_20px_rgba(94,168,255,0.15)]"
                      : "border-base-700/40 hover:border-base-600/60"
                  }`}
                >
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(voice.voice_id);
                    }}
                    className={`absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
                      isFav ? "text-amber-300 light:text-amber-700 hover:text-amber-200 light:hover:text-amber-800" : "text-ink-faint hover:text-ink"
                    }`}
                    title={isFav ? t("settings.voz.panel.unfavorite") : t("settings.voz.panel.favorite")}
                    aria-label={isFav ? t("settings.voz.panel.unfavorite") : t("settings.voz.panel.favorite")}
                  >
                    {isFav ? "★" : "☆"}
                  </button>
                  <div className="flex items-start justify-between mb-1 pr-8">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-lg shrink-0">{getLangFlag(voice.lang)}</span>
                      <div className="min-w-0">
                        <h3 className="text-sm font-medium text-ink truncate">{voice.name}</h3>
                        <span className="text-[10px] text-ink-faint uppercase tracking-wider flex items-center gap-1 flex-wrap">
                          {voice.gender === "female" ? "♀" : voice.gender === "male" ? "♂" : "·"}
                          {voice.category && (
                            <span
                              className={`px-1.5 py-0.5 rounded ${
                                voice.category === "cloned"
                                  ? "bg-amber-500/15 text-amber-300 light:text-amber-800"
                                  : voice.category === "professional"
                                    ? "bg-purple-500/15 text-purple-300 light:text-purple-800"
                                    : voice.category === "generated"
                                      ? "bg-emerald-500/15 text-emerald-300 light:text-emerald-800"
                                      : "bg-base-700/50 text-ink-faint"
                              }`}
                            >
                              {voice.category}
                            </span>
                          )}
                          {voice.description && <span className="truncate">{voice.description}</span>}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Clic en la tarjeta = fijarla como voz PRINCIPAL. */}
                  {selectedVoice?.voice_id === voice.voice_id ? (
                    <div className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-accent">
                      <span>✓</span> {t("settings.voz.panel.primaryVoice")}
                    </div>
                  ) : (
                    <div className="mt-2 text-[11px] text-ink-faint">{t("settings.voz.panel.clickToUse")}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Volumen del preview */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-ink-faint w-16 shrink-0">{t("settings.voz.panel.volume")}</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={volume}
          onChange={e => setVolume(parseFloat(e.target.value))}
          className="w-1/3 accent-accent"
        />
        <span className="text-xs text-ink w-12 text-right shrink-0">{Math.round(volume * 100)}%</span>
      </div>
    </div>
  );
}

