import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { api, type VoiceInfo } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

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

// V0.83: 4 proveedores TTS seleccionables. EdgeTTS por defecto (gratis, sin key,
// funciona en Python 3.13; Kokoro no soporta 3.13 -> queda como "no disponible").
type Provider = "edgetts" | "elevenlabs" | "kokoro" | "espeak";
const PROVIDERS: Provider[] = ["edgetts", "elevenlabs", "kokoro", "espeak"];
const PROVIDER_LABELS: Record<Provider, string> = {
  edgetts: "EdgeTTS",
  elevenlabs: "ElevenLabs",
  kokoro: "Kokoro",
  espeak: "eSpeak",
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
    previewText: DEFAULT_PREVIEW,
  };
}

export default function VoiceCenter() {
  // V0.83 (Paso 3): arrancamos con [], no con hardcoded. Las voces reales
  // llegan del backend en useEffect. selectedVoice arranca null y se elige
  // cuando llegan (o desde la persistencia en Config).
  const [voices, setVoices] = useState<VoiceConfig[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<VoiceConfig | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [activeProvider, setActiveProvider] = useState<Provider>("edgetts");
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [voiceLoadError, setVoiceLoadError] = useState<string | null>(null);
  const [elevenlabsConfigured, setElevenlabsConfigured] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterGender, setFilterGender] = useState<"all" | "male" | "female">("all");
  const [filterLang, setFilterLang] = useState<string>("all");
  const [volume, setVolume] = useState(1);
  // V0.83 (Paso 3): derivado simple. Dot verde solo si ElevenLabs responde
  // Y ya hemos traido las voces.
  const elevenlabsReady = elevenlabsConfigured && voices.length > 0;

  const audioRef = useRef<HTMLAudioElement | null>(null);
  // V0.8.1 (Paso 2): cableado del nucleo al TTS manual (boton "Escuchar muestra").
  // Granular selector para no re-render por cambios de coreState (pitfall #4).
  const setCoreState = useAppStore((s) => s.setCoreState);

  // V0.8.1 (Paso 2): si el usuario sale de VoiceCenter con un preview
  // sonando, devolvemos el nucleo a idle en lugar de dejarlo en "speaking".
  useEffect(() => {
    return () => {
      if (audioRef.current && !audioRef.current.paused) {
        setCoreState("idle");
      }
    };
  }, [setCoreState]);

  // V0.83: carga las voces del proveedor dado y elige la voz inicial. Fuente
  // única, usada tanto en el arranque como al cambiar de proveedor en vivo.
  const loadVoicesFor = useCallback(async (provider: Provider, preferId?: string | null) => {
    setLoadingVoices(true);
    setVoiceLoadError(null);
    try {
      if (provider === "espeak") {
        setVoices([]);
        setSelectedVoice(null);
        setLoadingVoices(false);
        return;
      }
      let list: VoiceConfig[] = [];
      if (provider === "edgetts") {
        const r = await api.getEdgeVoices();
        list = (r.voices || []).map(mapSimpleVoice);
      } else if (provider === "kokoro") {
        try {
          const st = await api.getKokoroStatus();
          if (!st.available) setVoiceLoadError(st.message);
        } catch {
          /* status opcional */
        }
        const r = await api.getKokoroVoices();
        list = (r.voices || []).map(mapSimpleVoice);
      } else {
        // elevenlabs
        const status = await api.getVoiceStatus();
        if (status.configured) {
          setElevenlabsConfigured(true);
          const r = await api.getAccountVoices();
          list = (r.voices || []).map((v) => ({
            voice_id: v.voice_id,
            name: v.name,
            category: (v.category as VoiceConfig["category"]) || "premade",
            lang: langFromVoice({ labels: v.labels, available_languages: v.available_languages }),
            gender: genderFromLabels(v.labels),
            description: v.description || v.labels?.description || "",
            previewText: DEFAULT_PREVIEW,
          }));
        } else {
          setVoiceLoadError("ElevenLabs no configurado. Define la API key en Ajustes.");
        }
      }
      let initial: VoiceConfig | null = null;
      if (preferId) initial = list.find((v) => v.voice_id === preferId) ?? null;
      if (!initial) initial = list[0] ?? null;
      setVoices(list);
      setSelectedVoice(initial);
    } catch (e: unknown) {
      setVoiceLoadError(e instanceof Error ? e.message : String(e));
      setVoices([]);
      setSelectedVoice(null);
    } finally {
      setLoadingVoices(false);
    }
  }, []);

  // Arranque: lee preferencias persistidas (proveedor por defecto EdgeTTS) y
  // carga las voces de ese proveedor.
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

  // V0.83 (Paso 3): persistir voz seleccionada al cambiar.
  const persistSelected = useCallback((voice: VoiceConfig) => {
    api.setConfig(CFG_KEY_SELECTED_VOICE, voice.voice_id).catch(() => {
      // Silenciar: la eleccion sigue en memoria aunque la persistencia
      // falle (p.ej. BD no accesible). El usuario no se entera y al
      // re-arrancar volvera al default.
    });
  }, []);

  // V0.83 (Paso 3): persistir provider al cambiar.
  const persistProvider = useCallback((p: Provider) => {
    api.setConfig(CFG_KEY_ACTIVE_PROVIDER, p).catch(() => {
      // idem
    });
  }, []);

  // V0.83 (Paso 3): toggle favorito persistido.
  const toggleFavorite = useCallback((voiceId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(voiceId)) next.delete(voiceId);
      else next.add(voiceId);
      api
        .setConfig(CFG_KEY_FAVORITE_VOICES, Array.from(next).join(","))
        .catch(() => {
          // idem
        });
      return next;
    });
  }, []);

  const handlePreview = useCallback(async () => {
    if (isPlaying || isLoading) {
      // Detener reproducción actual
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setIsPlaying(false);
      // V0.8.1 (Paso 2): parar = nucleo a idle
      setCoreState("idle");
      return;
    }
    if (!selectedVoice) return;

    setIsLoading(true);
    setError(null);

    try {
      // Obtener audio del backend con el proveedor ACTIVO. ElevenLabs va por
      // el camino por defecto (provider undefined); el resto explícito.
      const prov = activeProvider === "elevenlabs" ? undefined : activeProvider;
      const { buffer, mime } = await api.synthesizeVoice(
        selectedVoice.previewText,
        selectedVoice.voice_id,
        prov,
      );

      // Crear blob y audio con el tipo real (Kokoro=wav, resto=mpeg)
      const blob = new Blob([buffer], { type: mime });
      const url = URL.createObjectURL(blob);

      // Detener anterior si existe
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      // Crear nuevo audio
      const audio = new Audio(url);
      audio.volume = volume;
      audioRef.current = audio;

      audio.onplay = () => {
        // V0.8.1 (Paso 2): nucleo en "speaking" mientras suena el preview
        setCoreState("speaking");
      };

      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
        // V0.8.1 (Paso 2): fin del audio -> nucleo a idle
        setCoreState("idle");
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setError("Error al reproducir audio");
        // V0.8.1 (Paso 2): error de reproduccion -> nucleo a idle
        setCoreState("idle");
      };

      setIsPlaying(true);
      await audio.play();

    } catch (err: any) {
      console.error("Error synthesizing:", err);
      setError(err.message || "Error al sintetizar voz");
      setIsPlaying(false);
      setCoreState("idle");
    } finally {
      setIsLoading(false);
    }
  }, [selectedVoice, volume, isPlaying, isLoading, setCoreState, activeProvider]);

  // V0.83 (Paso 3): handler de seleccion de voz. Ademas de cambiar el
  // state local, persiste en Config para que sobreviva a recargas.
  const handleSelectVoice = useCallback((voice: VoiceConfig) => {
    setSelectedVoice(voice);
    persistSelected(voice);
  }, [persistSelected]);

  // V0.83: cambio de provider EN VIVO. Persiste y recarga las voces del nuevo
  // proveedor al instante (sin re-montar el componente).
  const handleProviderChange = useCallback((p: Provider) => {
    setActiveProvider(p);
    persistProvider(p);
    loadVoicesFor(p);
  }, [persistProvider, loadVoicesFor]);

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
    // V0.8.1 (Paso 2): stop manual -> nucleo a idle
    setCoreState("idle");
  };

  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // V0.83 (Paso 3): orden de la lista. Primero las favoritas, despues
  // el resto dentro del mismo idioma, despues por nombre.
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
    const labels: Record<string, string> = {
      "es": "Español",
      "en": "English",
      "ja": "日本語",
      "fr": "Français",
      "zh": "中文"
    };
    return labels[lang] || lang;
  };

  const getLangFlag = (lang: string) => {
    const flags: Record<string, string> = {
      "es": "🇪🇸",
      "en": "🇬🇧",
      "ja": "🇯🇵",
      "fr": "🇫🇷",
      "zh": "🇨🇳"
    };
    return flags[lang] || "🌐";
  };

  return (
    <div className="h-full flex flex-col gap-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0 gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-semibold text-ink">Centro de Voz</h1>
          <p className="text-xs mt-0.5">
            <span
              className={`inline-block w-2 h-2 rounded-full mr-1 ${
                voices.length > 0 || activeProvider === "espeak" ? "bg-signal-ok" : "bg-signal-warn"
              }`}
            />
            <span className="text-ink-faint">
              {loadingVoices
                ? "Cargando voces..."
                : activeProvider === "espeak"
                  ? "eSpeak (offline)"
                  : voiceLoadError
                    ? voiceLoadError
                    : voices.length > 0
                      ? `${voices.length} voces · ${PROVIDER_LABELS[activeProvider]}`
                      : `Sin voces (${PROVIDER_LABELS[activeProvider]})`}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* V0.83 (Paso 3): switch de provider. Persiste en Config. */}
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
                    ? "Microsoft EdgeTTS (gratis, sin key, requiere internet)"
                    : p === "elevenlabs"
                      ? "Voces profesionales (requiere API key)"
                      : p === "kokoro"
                        ? "TTS local offline (no soportado en Python 3.13)"
                        : "Fallback offline (eSpeak NG)"
                }
              >
                {PROVIDER_LABELS[p]}
              </button>
            ))}
          </div>
          <button
            onClick={handlePreview}
            disabled={isLoading || !selectedVoice}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              isPlaying
                ? "bg-signal-error/15 text-signal-error border border-signal-error/30"
                : "bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
            } disabled:opacity-50`}
          >
            {isLoading
              ? "Generando..."
              : isPlaying
                ? "■ Detener"
                : "▶ Escuchar muestra"}
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-signal-error/10 border border-signal-error/30 rounded-xl p-3 text-sm text-signal-error">
          {error}
        </div>
      )}

      {/* Filtros */}
      {activeProvider !== "espeak" && voices.length > 0 && (
        <div className="flex items-center gap-4 shrink-0 flex-wrap">
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
                {g === "all" ? "Todas" : g === "female" ? "♀ Femeninas" : "♂ Masculinos"}
              </button>
            ))}
          </div>
          <select
            value={filterLang}
            onChange={e => setFilterLang(e.target.value)}
            className="bg-base-800 border border-base-700 rounded-lg px-3 py-1.5 text-xs text-ink"
          >
            <option value="all">🌐 Todos los idiomas</option>
            {Array.from(new Set(voices.map((v) => v.lang))).sort().map((lang) => (
              <option key={lang} value={lang}>
                {getLangFlag(lang)} {getLangLabel(lang)}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-ink-faint">
            {filteredVoices.length} de {voices.length} voces
            {favorites.size > 0 && ` · ${favorites.size} favoritas`}
          </span>
        </div>
      )}

      {/* Lista de voces */}
      <div className="flex-1 overflow-y-auto">
        {activeProvider === "espeak" ? (
          <EspeakFallback onPlay={handlePreview} isPlaying={isPlaying} />
        ) : loadingVoices ? (
          <p className="text-sm text-ink-faint">Cargando voces...</p>
        ) : filteredVoices.length === 0 ? (
          <p className="text-sm text-ink-faint">
            {voices.length === 0
              ? (activeProvider === "elevenlabs"
                  ? "No hay voces. Configura la API key de ElevenLabs en Ajustes."
                  : activeProvider === "kokoro"
                    ? "Kokoro no disponible en este equipo (necesita Python 3.12 o Docker)."
                    : (voiceLoadError || "No hay voces para mostrar."))
              : "Ninguna voz coincide con los filtros."}
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredVoices.map(voice => {
              const isFav = favorites.has(voice.voice_id);
              return (
                <div
                  key={voice.voice_id}
                  onClick={() => handleSelectVoice(voice)}
                  className={`glass-surface rounded-2xl p-4 cursor-pointer transition-all border relative ${
                    selectedVoice?.voice_id === voice.voice_id
                      ? "border-accent/40 shadow-[0_0_20px_rgba(94,168,255,0.15)]"
                      : "border-base-700/40 hover:border-base-600/60"
                  }`}
                >
                  {/* V0.83 (Paso 3): estrella de favorita (esquina sup. izq.) */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(voice.voice_id);
                    }}
                    className={`absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
                      isFav
                        ? "text-amber-300 hover:text-amber-200"
                        : "text-ink-faint hover:text-ink"
                    }`}
                    title={isFav ? "Quitar de favoritas" : "Marcar como favorita"}
                    aria-label={isFav ? "Quitar favorita" : "Marcar favorita"}
                  >
                    {isFav ? "★" : "☆"}
                  </button>
                  <div className="flex items-start justify-between mb-2 pr-8">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-lg shrink-0">{getLangFlag(voice.lang)}</span>
                      <div className="min-w-0">
                        <h3 className="text-sm font-medium text-ink truncate">
                          {voice.name}
                        </h3>
                        <span className="text-[10px] text-ink-faint uppercase tracking-wider flex items-center gap-1 flex-wrap">
                          {voice.gender === "female" ? "♀" : voice.gender === "male" ? "♂" : "·"}
                          {voice.category && (
                            <span
                              className={`px-1.5 py-0.5 rounded ${
                                voice.category === "cloned"
                                  ? "bg-amber-500/15 text-amber-300"
                                  : voice.category === "professional"
                                    ? "bg-purple-500/15 text-purple-300"
                                    : voice.category === "generated"
                                      ? "bg-emerald-500/15 text-emerald-300"
                                      : "bg-base-700/50 text-ink-faint"
                              }`}
                            >
                              {voice.category}
                            </span>
                          )}
                          {voice.description && (
                            <span className="truncate">{voice.description}</span>
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-ink-dim line-clamp-2 italic">
                    "{voice.previewText}"
                  </p>

                  {/* Estado de selección: clic en la tarjeta = fijarla como voz
                      PRINCIPAL (la que usa Aithera al hablar). Distinto de la
                      estrella ☆, que solo marca favorita. */}
                  {selectedVoice?.voice_id === voice.voice_id ? (
                    <div className="mt-3 flex items-center gap-1.5 text-[11px] font-medium text-accent">
                      <span>✓</span> Voz principal
                    </div>
                  ) : (
                    <div className="mt-3 text-[11px] text-ink-faint">
                      Clic para usar como principal
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Controles de volumen */}
      <div className="glass-surface rounded-2xl p-4 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs text-ink-faint w-16 shrink-0">Volumen</span>
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
    </div>
  );
}

// V0.83 (Paso 3): vista simplificada para cuando el provider es eSpeak.
// No muestra lista de voces (eSpeak ya enruta por su propio mapa en el
// backend). El boton de preview reproduce un texto fijo.
function EspeakFallback({ onPlay, isPlaying }: { onPlay: () => void; isPlaying: boolean }) {
  return (
    <div className="glass-surface rounded-2xl p-6 flex flex-col items-center gap-4 text-center">
      <div className="text-3xl">🔊</div>
      <div>
        <h2 className="text-sm font-medium text-ink mb-1">Modo offline activo</h2>
        <p className="text-xs text-ink-faint max-w-md">
          Estas usando eSpeak NG. Las voces son basicas (español, ingles, etc.)
          pero funcionan sin internet y sin API key. Para voces profesionales
          vuelve a la pestana ElevenLabs.
        </p>
      </div>
      <button
        type="button"
        onClick={onPlay}
        disabled={isPlaying}
        className="px-5 py-2 rounded-lg bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 transition-colors disabled:opacity-50"
      >
        {isPlaying ? "■ Reproduciendo..." : "▶ Probar eSpeak"}
      </button>
    </div>
  );
}
