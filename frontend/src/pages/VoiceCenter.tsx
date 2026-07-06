import { useState, useRef, useEffect, useCallback } from "react";
import { api, type VoiceInfo } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

interface VoiceConfig {
  id: string;
  name: string;
  previewText: string;
  lang: string;
  gender: "male" | "female";
  description: string;
}

// Voces profesionales predefinidas de ElevenLabs
const PREDEFINED_VOICES: VoiceConfig[] = [
  // Español
  { id: "XB0fDUnXU5powGXd8GSW", name: "María (Español)", previewText: "Hola, soy María. Tu asistente de inteligencia artificial.", lang: "es", gender: "female", description: "Profesional, cálida" },
  { id: "VRgBjM5LWMVLQdJBADuO", name: "Sara (Español MX)", previewText: "Hola, soy Sara. ¿En qué puedo ayudarte hoy?", lang: "es", gender: "female", description: "Amigable, moderna" },
  { id: "pFZInIHuG2YLLnwAkyrJ", name: "Alejandro (Español)", previewText: "Buenos días, soy Alejandro. ¿Qué necesitas hoy?", lang: "es", gender: "male", description: "Profesional, serio" },
  
  // Inglés
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella (English)", previewText: "Hello, I'm Bella. How can I assist you today?", lang: "en", gender: "female", description: "Young, expressive" },
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel (English)", previewText: "Hello, I'm Rachel. I'm here to help you.", lang: "en", gender: "female", description: "Clear, professional" },
  { id: "TxGEqnHWrfWFTfGW9Uj1", name: "Arnold (English)", previewText: "Good morning, I'm Arnold. How may I help you?", lang: "en", gender: "male", description: "Strong, deep" },
  { id: "CYw3kZ02XxukaQ43fj0C", name: "Josh (English)", previewText: "Hello, I'm Josh. What can I do for you today?", lang: "en", gender: "male", description: "Casual, friendly" },
  
  // Japonés
  { id: "M0XMcJl3aMSh0bL3V0tX", name: "Airi (日本語)", previewText: "こんにちは，我是Airです。何かお手伝いできることはありますか？", lang: "ja", gender: "female", description: "Femenina, joven" },
  { id: "Xb7hH8MSDhxAmzVbBvjN", name: "Kenji (日本語)", previewText: "こんにちは、健です。何かお手伝いしますか？", lang: "ja", gender: "male", description: "Masculino, formal" },
  
  // Francés
  { id: "GMwe3DBXQwAEkbqiQDhK", name: "Antoine (Français)", previewText: "Bonjour, je suis Antoine. Comment puis-je vous aider?", lang: "fr", gender: "male", description: "Masculino, elegante" },
  
  // Chino
  { id: "TxhqxN7eKXvBdrCDK0Kz", name: "Fei (中文)", previewText: "你好，我是林。有什么我可以帮助你的吗？", lang: "zh", gender: "female", description: "Femenina, moderna" },
];

export default function VoiceCenter() {
  const [voices, setVoices] = useState<VoiceConfig[]>(PREDEFINED_VOICES);
  const [selectedVoice, setSelectedVoice] = useState<VoiceConfig>(PREDEFINED_VOICES[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voiceReady, setVoiceReady] = useState(false);
  const [filterGender, setFilterGender] = useState<"all" | "male" | "female">("all");
  const [filterLang, setFilterLang] = useState<string>("all");
  const [volume, setVolume] = useState(1);

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

  // Verificar estado de ElevenLabs
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await api.getVoiceStatus();
        if (status.configured) {
          setVoiceReady(true);
          console.log("ElevenLabs configurado con", status.voices_count, "voces");
        } else {
          setVoiceReady(false);
          console.log("Usando voces predefinidas - ElevenLabs no configurado");
        }
      } catch {
        setVoiceReady(false);
      }
    };
    checkStatus();
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

    setIsLoading(true);
    setError(null);

    try {
      // Obtener audio del backend (ElevenLabs)
      const audioBuffer = await api.synthesizeVoice(selectedVoice.previewText, selectedVoice.id);

      // Crear blob y audio
      const blob = new Blob([audioBuffer], { type: "audio/mpeg" });
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
  }, [selectedVoice, volume, isPlaying, isLoading, setCoreState]);

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

  const filteredVoices = voices.filter(v => {
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
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold text-ink">Centro de Voz</h1>
          <p className="text-xs mt-0.5">
            <span className={`inline-block w-2 h-2 rounded-full mr-1 ${voiceReady ? "bg-signal-ok" : "bg-signal-warn"}`} />
            <span className="text-ink-faint">
              {voiceReady 
                ? `ElevenLabs activo - Voces profesionales`
                : `Demo mode - Configura ELEVENLABS_API_KEY para voces profesionales`
              }
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handlePreview}
            disabled={isLoading}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              isPlaying
                ? "bg-signal-error/15 text-signal-error border border-signal-error/30"
                : "bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25"
            } disabled:opacity-50`}
          >
            {isLoading ? "Generando..." : isPlaying ? "■ Detener" : "▶ Escuchar muestra"}
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
      <div className="flex items-center gap-4 shrink-0">
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
          <option value="es">🇪🇸 Español</option>
          <option value="en">🇬🇧 English</option>
          <option value="ja">🇯🇵 日本語</option>
          <option value="fr">🇫🇷 Français</option>
          <option value="zh">🇨🇳 中文</option>
        </select>
      </div>

      {/* Lista de voces */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVoices.map(voice => (
            <div
              key={voice.id}
              onClick={() => setSelectedVoice(voice)}
              className={`glass-surface rounded-2xl p-4 cursor-pointer transition-all border ${
                selectedVoice.id === voice.id
                  ? "border-accent/40 shadow-[0_0_20px_rgba(94,168,255,0.15)]"
                  : "border-base-700/40 hover:border-base-600/60"
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getLangFlag(voice.lang)}</span>
                  <div>
                    <h3 className="text-sm font-medium text-ink">{voice.name}</h3>
                    <span className="text-[10px] text-ink-faint uppercase tracking-wider">
                      {voice.gender === "female" ? "♀" : "♂"} {voice.description}
                    </span>
                  </div>
                </div>
                {selectedVoice.id === voice.id && (
                  <span className="h-2 w-2 rounded-full bg-accent shrink-0 mt-1" />
                )}
              </div>
              
              <p className="text-xs text-ink-dim line-clamp-2 italic">
                "{voice.previewText}"
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Controles de volumen */}
      <div className="glass-surface rounded-2xl p-4 shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-xs text-ink-faint w-16">Volumen</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={e => setVolume(parseFloat(e.target.value))}
            className="flex-1 accent-accent"
          />
          <span className="text-xs text-ink w-12 text-right">{Math.round(volume * 100)}%</span>
        </div>
      </div>
    </div>
  );
}
