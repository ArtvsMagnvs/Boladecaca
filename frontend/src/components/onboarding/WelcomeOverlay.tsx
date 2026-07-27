// components/onboarding/WelcomeOverlay.tsx — Asistente de bienvenida (OB-1, doc 30 §1)
//
// La PRIMERA impresión de Aithera. La primera vez que se abre (flag en BD,
// `onboarding_completed`), un asistente guía: idioma → hardware → modelo → voz,
// auto-seleccionando lo que el escáner de hardware recomienda para ESTE equipo,
// con opción de cambiarlo. Todo el trabajo real lo hacen endpoints que YA
// existen (`/local-models/hardware`, `/voice/defaults`, `/onboarding/*`); este
// componente es el pegamento visual.
//
// Alcance OB-1: el modelo elegido se DEJA ANOTADO (pending_model), la descarga
// guiada con progreso es OB-2. Aquí no se descarga nada pesado.
//
// El texto del propio asistente va en los 4 idiomas (diccionario local `TXT`),
// para que elegir idioma en el paso 1 localice ya la bienvenida — NO es el
// framework i18n global (eso es I18N-1): es la copia de esta única pantalla.
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useI18n } from "@/store/useI18n";
import type { QualityTier } from "@/avcs";

// Cache local para no volver a preguntar al backend en cada arranque una vez
// completado (el backend sigue siendo la fuente de verdad; esto solo evita el
// parpadeo/latencia del primer render).
const DONE_CACHE = "aithera.onboarded";

type Lang = "es" | "en" | "fr" | "pt";

const LANGS: { code: Lang; flag: string; name: string }[] = [
  { code: "es", flag: "🇪🇸", name: "Español" },
  { code: "en", flag: "🇬🇧", name: "English" },
  { code: "fr", flag: "🇫🇷", name: "Français" },
  { code: "pt", flag: "🇵🇹", name: "Português" },
];

// Copia del asistente por idioma. Claves compartidas; interpolación con {x}.
const TXT: Record<Lang, Record<string, string>> = {
  es: {
    welcome: "Te damos la bienvenida",
    subtitle: "Soy Aithera, tu sistema operativo personal de IA. Vamos a dejarlo todo listo en un minuto.",
    pickLang: "Elige tu idioma",
    next: "Siguiente",
    back: "Atrás",
    finish: "Empezar a usar Aithera",
    stepHw: "Tu equipo",
    hwScanning: "Analizando tu hardware…",
    hwCpu: "Procesador",
    hwRam: "Memoria",
    hwGpu: "Gráfica",
    hwNoGpu: "Sin GPU dedicada",
    hwModel: "Modelo de IA local recomendado",
    hwModelWhy: "Elegido para tu equipo. Podrás cambiarlo cuando quieras.",
    hwNone: "Sin modelo local (usaré la nube o lo eliges luego)",
    hwParticles: "Núcleo visual (partículas)",
    hwParticlesWhy: "Nivel recomendado para que vaya fluido en tu equipo.",
    stepVoice: "Mi voz",
    voiceResolving: "Preparando la voz…",
    voiceReady: "Voz lista para {lang}",
    voiceTest: "Escuchar",
    voiceTesting: "Reproduciendo…",
    voiceSample: "Hola, soy Aithera. Encantada de acompañarte.",
    voiceNote: "Puedes cambiar la voz y el idioma cuando quieras en Ajustes.",
    saving: "Guardando…",
    modelSizeGb: "{n} GB",
    stepInstall: "Modelo de IA local",
    instNoModel: "No has elegido modelo local. Aithera usará la nube o podrás instalar uno luego desde Ajustes.",
    instChecking: "Comprobando Ollama…",
    instNeedOllama: "Necesitas Ollama, el motor que ejecuta los modelos locales en tu PC. Instálalo y vuelve aquí.",
    instGetOllama: "Descargar Ollama",
    instRetry: "Ya lo instalé, comprobar de nuevo",
    instDownloading: "Descargando {model}…",
    instDone: "{model} instalado y listo",
    instFailed: "No se pudo descargar. Puedes reintentarlo o hacerlo luego desde Ajustes.",
    instRetryDl: "Reintentar descarga",
    instBackground: "La descarga sigue en segundo plano. Puedes empezar a usar Aithera.",
    finishBg: "Empezar (seguir descargando)",
  },
  en: {
    welcome: "Welcome",
    subtitle: "I'm Aithera, your personal AI operating system. Let's get everything ready in a minute.",
    pickLang: "Choose your language",
    next: "Next",
    back: "Back",
    finish: "Start using Aithera",
    stepHw: "Your machine",
    hwScanning: "Scanning your hardware…",
    hwCpu: "Processor",
    hwRam: "Memory",
    hwGpu: "Graphics",
    hwNoGpu: "No dedicated GPU",
    hwModel: "Recommended local AI model",
    hwModelWhy: "Picked for your machine. You can change it anytime.",
    hwNone: "No local model (I'll use the cloud, or pick one later)",
    hwParticles: "Visual core (particles)",
    hwParticlesWhy: "Recommended level so it runs smoothly on your machine.",
    stepVoice: "My voice",
    voiceResolving: "Preparing the voice…",
    voiceReady: "Voice ready for {lang}",
    voiceTest: "Listen",
    voiceTesting: "Playing…",
    voiceSample: "Hi, I'm Aithera. Glad to be with you.",
    voiceNote: "You can change the voice and language anytime in Settings.",
    saving: "Saving…",
    modelSizeGb: "{n} GB",
    stepInstall: "Local AI model",
    instNoModel: "You didn't pick a local model. Aithera will use the cloud, or you can install one later from Settings.",
    instChecking: "Checking Ollama…",
    instNeedOllama: "You need Ollama, the engine that runs local models on your PC. Install it and come back here.",
    instGetOllama: "Download Ollama",
    instRetry: "I installed it, check again",
    instDownloading: "Downloading {model}…",
    instDone: "{model} installed and ready",
    instFailed: "Download failed. You can retry or do it later from Settings.",
    instRetryDl: "Retry download",
    instBackground: "The download continues in the background. You can start using Aithera.",
    finishBg: "Start (keep downloading)",
  },
  fr: {
    welcome: "Bienvenue",
    subtitle: "Je suis Aithera, votre système d'exploitation IA personnel. Préparons tout en une minute.",
    pickLang: "Choisissez votre langue",
    next: "Suivant",
    back: "Retour",
    finish: "Commencer à utiliser Aithera",
    stepHw: "Votre machine",
    hwScanning: "Analyse de votre matériel…",
    hwCpu: "Processeur",
    hwRam: "Mémoire",
    hwGpu: "Carte graphique",
    hwNoGpu: "Pas de GPU dédié",
    hwModel: "Modèle d'IA local recommandé",
    hwModelWhy: "Choisi pour votre machine. Modifiable à tout moment.",
    hwNone: "Aucun modèle local (j'utiliserai le cloud, ou choisissez plus tard)",
    hwParticles: "Cœur visuel (particules)",
    hwParticlesWhy: "Niveau recommandé pour une fluidité optimale sur votre machine.",
    stepVoice: "Ma voix",
    voiceResolving: "Préparation de la voix…",
    voiceReady: "Voix prête pour {lang}",
    voiceTest: "Écouter",
    voiceTesting: "Lecture…",
    voiceSample: "Bonjour, je suis Aithera. Ravie de vous accompagner.",
    voiceNote: "Vous pouvez changer la voix et la langue à tout moment dans les Réglages.",
    saving: "Enregistrement…",
    modelSizeGb: "{n} Go",
    stepInstall: "Modèle d'IA local",
    instNoModel: "Vous n'avez pas choisi de modèle local. Aithera utilisera le cloud, ou vous pourrez en installer un plus tard dans les Réglages.",
    instChecking: "Vérification d'Ollama…",
    instNeedOllama: "Vous avez besoin d'Ollama, le moteur qui exécute les modèles locaux sur votre PC. Installez-le et revenez ici.",
    instGetOllama: "Télécharger Ollama",
    instRetry: "Je l'ai installé, revérifier",
    instDownloading: "Téléchargement de {model}…",
    instDone: "{model} installé et prêt",
    instFailed: "Échec du téléchargement. Réessayez ou faites-le plus tard dans les Réglages.",
    instRetryDl: "Réessayer le téléchargement",
    instBackground: "Le téléchargement continue en arrière-plan. Vous pouvez commencer à utiliser Aithera.",
    finishBg: "Commencer (continuer le téléchargement)",
  },
  pt: {
    welcome: "Boas-vindas",
    subtitle: "Sou a Aithera, o teu sistema operativo pessoal de IA. Vamos deixar tudo pronto num minuto.",
    pickLang: "Escolhe o teu idioma",
    next: "Seguinte",
    back: "Voltar",
    finish: "Começar a usar a Aithera",
    stepHw: "O teu equipamento",
    hwScanning: "A analisar o teu hardware…",
    hwCpu: "Processador",
    hwRam: "Memória",
    hwGpu: "Placa gráfica",
    hwNoGpu: "Sem GPU dedicada",
    hwModel: "Modelo de IA local recomendado",
    hwModelWhy: "Escolhido para o teu equipamento. Podes mudar quando quiseres.",
    hwNone: "Sem modelo local (uso a nuvem, ou escolhes mais tarde)",
    hwParticles: "Núcleo visual (partículas)",
    hwParticlesWhy: "Nível recomendado para correr fluido no teu equipamento.",
    stepVoice: "A minha voz",
    voiceResolving: "A preparar a voz…",
    voiceReady: "Voz pronta para {lang}",
    voiceTest: "Ouvir",
    voiceTesting: "A reproduzir…",
    voiceSample: "Olá, sou a Aithera. É um gosto acompanhar-te.",
    voiceNote: "Podes mudar a voz e o idioma quando quiseres nas Definições.",
    saving: "A guardar…",
    modelSizeGb: "{n} GB",
    stepInstall: "Modelo de IA local",
    instNoModel: "Não escolheste um modelo local. A Aithera usará a nuvem, ou podes instalar um mais tarde nas Definições.",
    instChecking: "A verificar o Ollama…",
    instNeedOllama: "Precisas do Ollama, o motor que executa os modelos locais no teu PC. Instala-o e volta aqui.",
    instGetOllama: "Descarregar Ollama",
    instRetry: "Já o instalei, verificar de novo",
    instDownloading: "A descarregar {model}…",
    instDone: "{model} instalado e pronto",
    instFailed: "Não foi possível descarregar. Podes tentar de novo ou fazê-lo mais tarde nas Definições.",
    instRetryDl: "Tentar descarregar de novo",
    instBackground: "A descarga continua em segundo plano. Podes começar a usar a Aithera.",
    finishBg: "Começar (continuar a descarregar)",
  },
};

const TIER_LABEL: Record<Lang, Record<QualityTier, string>> = {
  es: { Q1: "Mínimo", Q2: "Medio", Q3: "Alto", Q4: "Máximo" },
  en: { Q1: "Minimum", Q2: "Medium", Q3: "High", Q4: "Maximum" },
  fr: { Q1: "Minimum", Q2: "Moyen", Q3: "Élevé", Q4: "Maximum" },
  pt: { Q1: "Mínimo", Q2: "Médio", Q3: "Alto", Q4: "Máximo" },
};
const TIER_ORDER: QualityTier[] = ["Q1", "Q2", "Q3", "Q4"];

type Phase = "checking" | "show" | "done";
type Step = 0 | 1 | 2 | 3;
const STEPS: Step[] = [0, 1, 2, 3];

type HwData = Awaited<ReturnType<typeof api.getHardwareRecommendation>>;
type ModelChoice = "optimal" | "lower" | "higher" | "none";
type InstallJob = Awaited<ReturnType<typeof api.getLocalInstallStatus>>;

export default function WelcomeOverlay() {
  const [phase, setPhase] = useState<Phase>("checking");
  const [step, setStep] = useState<Step>(0);
  const [lang, setLang] = useState<Lang>("es");
  const setAvcsTier = useAppStore((s) => s.setAvcsTier);

  // Paso 2 — hardware
  const [hw, setHw] = useState<HwData | null>(null);
  const [modelChoice, setModelChoice] = useState<ModelChoice>("optimal");
  const [tier, setTier] = useState<QualityTier>("Q2");

  // Paso 3 — voz
  const [voice, setVoice] = useState<{ provider: string; voice_id: string; language: string } | null>(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Paso 4 — instalación del modelo (OB-2)
  const [runtime, setRuntime] = useState<{ ok: boolean; install_url: string | null } | null>(null);
  const [runtimeBusy, setRuntimeBusy] = useState(false);
  const [installJob, setInstallJob] = useState<InstallJob | null>(null);
  const installStartedRef = useRef(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const t = (k: string, vars?: Record<string, string | number>) => {
    let s = TXT[lang][k] ?? k;
    if (vars) for (const [key, val] of Object.entries(vars)) s = s.replace(`{${key}}`, String(val));
    return s;
  };

  // --- Boot: ¿mostrar el asistente? ---
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (window.localStorage.getItem(DONE_CACHE) === "true") {
          if (!cancelled) setPhase("done");
          return;
        }
      } catch {
        /* localStorage no disponible: seguimos con el backend */
      }
      try {
        const s = await api.getOnboardingStatus();
        if (cancelled) return;
        if (s.completed) {
          try { window.localStorage.setItem(DONE_CACHE, "true"); } catch { /* noop */ }
          setPhase("done");
        } else {
          if (s.language && ["es", "en", "fr", "pt"].includes(s.language)) setLang(s.language as Lang);
          setPhase("show");
        }
      } catch {
        // Backend caído durante el arranque: NO mostramos el asistente a medias
        // (pediría un escaneo que fallaría). Se mostrará en el próximo arranque.
        if (!cancelled) setPhase("done");
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Al entrar al paso 2, escanea hardware una vez.
  useEffect(() => {
    if (step !== 1 || hw) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api.getHardwareRecommendation();
        if (cancelled) return;
        setHw(data);
        const rec = (data.avcs.recommended_tier as QualityTier) || "Q2";
        setTier(rec);
        // Si no hay modelo óptimo recomendado (hardware desconocido), por
        // defecto "ninguno" para no forzar una descarga a ciegas.
        setModelChoice(data.ollama.optimal ? "optimal" : "none");
      } catch {
        if (!cancelled) setHw(null);
      }
    })();
    return () => { cancelled = true; };
  }, [step, hw]);

  // Al entrar al paso 3, fija el idioma en BD y resuelve la voz por defecto.
  useEffect(() => {
    if (step !== 2) return;
    let cancelled = false;
    (async () => {
      setVoiceBusy(true);
      try {
        await api.setConfig("app_language", lang);
        const v = await api.getVoiceDefaults();
        if (!cancelled) setVoice(v);
      } catch {
        if (!cancelled) setVoice(null);
      } finally {
        if (!cancelled) setVoiceBusy(false);
      }
    })();
    return () => { cancelled = true; };
  }, [step, lang]);

  const chosenModelTag = (): string | null => {
    if (!hw || modelChoice === "none") return null;
    const m = hw.ollama[modelChoice];
    return m ? m.tag : null;
  };

  const chosenModelLabel = (): string => {
    if (!hw || modelChoice === "none") return "";
    return hw.ollama[modelChoice]?.label || chosenModelTag() || "";
  };

  // --- Paso 4: instalación (OB-2) ---
  const startInstall = async (tag: string) => {
    if (installStartedRef.current) return;
    installStartedRef.current = true;
    try {
      const job = await api.installLocalModel(tag);
      setInstallJob(job);
    } catch {
      installStartedRef.current = false;
      return;
    }
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const st = await api.getLocalInstallStatus(tag);
        setInstallJob(st);
        if (st.status === "done") {
          if (pollRef.current) clearInterval(pollRef.current);
          // Deja el modelo LISTO para el enrutado del MEL (no solo en disco).
          try { await api.setLocalModelEnabled(tag, true); } catch { /* noop */ }
        } else if (st.status === "failed" || st.status === "cancelled") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        /* un fallo puntual de sondeo no cancela la descarga (sigue en backend) */
      }
    }, 1500);
  };

  const checkRuntime = async () => {
    const tag = chosenModelTag();
    if (!tag) return;
    setRuntimeBusy(true);
    try {
      const r = await api.getRuntimeStatus();
      setRuntime(r);
      if (r.ok) await startInstall(tag);
    } catch {
      setRuntime({ ok: false, install_url: null });
    } finally {
      setRuntimeBusy(false);
    }
  };

  // Al entrar al paso 4, comprueba el runtime y (si hay) arranca la descarga.
  useEffect(() => {
    if (step !== 3) return;
    if (!chosenModelTag()) return; // sin modelo elegido: nada que instalar
    void checkRuntime();
    // El sondeo se limpia solo al terminar (done/failed) o al desmontar (abajo);
    // no aquí, para que volver atrás y adelante no corte una descarga en curso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // Limpieza dura del sondeo al cerrar el asistente.
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const testVoice = async () => {
    if (!voice || voiceBusy) return;
    setVoiceBusy(true);
    try {
      const prov = voice.provider === "elevenlabs" ? undefined : (voice.provider as "edgetts" | "kokoro");
      const { buffer, mime } = await api.synthesizeVoice(t("voiceSample"), voice.voice_id, prov);
      const url = URL.createObjectURL(new Blob([buffer], { type: mime }));
      if (audioRef.current) { audioRef.current.pause(); try { URL.revokeObjectURL(audioRef.current.src); } catch { /* noop */ } }
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(url); };
      await audio.play();
    } catch {
      /* la prueba de voz es opcional: si falla, no bloquea el onboarding */
    } finally {
      setVoiceBusy(false);
    }
  };

  const finish = async () => {
    setSaving(true);
    // Aplica el tier del AVCS ya (persiste en el store/localStorage, igual que Ajustes).
    setAvcsTier(tier);
    // Fija el idioma global de la app (I18N-1). sync:false porque el backend ya
    // recibe app_language por completeOnboarding + el setConfig del paso de voz.
    useI18n.getState().setLang(lang, { sync: false });
    try {
      await api.completeOnboarding({ language: lang, model_tag: chosenModelTag() });
    } catch {
      /* aunque el backend falle al sellar, no reabrimos en bucle: cache local */
    }
    try { window.localStorage.setItem(DONE_CACHE, "true"); } catch { /* noop */ }
    if (audioRef.current) audioRef.current.pause();
    // La descarga (si sigue) continúa en el backend; solo dejamos de sondear.
    if (pollRef.current) clearInterval(pollRef.current);
    setPhase("done");
  };

  if (phase !== "show") return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 sm:p-6">
      {/* Escenario oscuro fijo (identidad de marca; nunca blanco), con un
          degradado sutil hacia el acento — la presencia del Hub queda detrás,
          este overlay la cubre en su primera apertura. */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(120% 120% at 50% 0%, #12131b 0%, #0a0a0f 60%, #08080c 100%)" }}
      />
      <div
        className="relative w-full max-w-lg rounded-2xl modal-panel bg-base-900/95 flex flex-col overflow-hidden"
        style={{ animation: "modal-pop var(--duration-base) var(--ease-smooth)" }}
      >
        {/* Progreso */}
        <div className="flex gap-1.5 px-6 pt-5">
          {STEPS.map((i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? "bg-accent" : "bg-base-700"}`}
            />
          ))}
        </div>

        <div className="px-6 py-6 min-h-[22rem] flex flex-col">
          {step === 0 && (
            <div className="flex-1 flex flex-col">
              <div className="text-2xl font-semibold text-ink">{t("welcome")}</div>
              <p className="text-sm text-ink-dim mt-1.5 leading-relaxed">{t("subtitle")}</p>
              <div className="text-xs font-medium text-ink-faint uppercase tracking-wide mt-6 mb-2">
                {t("pickLang")}
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                {LANGS.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => setLang(l.code)}
                    className={`flex items-center gap-3 rounded-xl px-4 py-3 border transition-colors text-left ${
                      lang === l.code
                        ? "border-accent bg-accent/10 text-ink"
                        : "border-base-700 hover:border-base-600 text-ink-dim"
                    }`}
                  >
                    <span className="text-2xl leading-none">{l.flag}</span>
                    <span className="font-medium">{l.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="flex-1 flex flex-col">
              <div className="text-lg font-semibold text-ink mb-3">{t("stepHw")}</div>
              {!hw ? (
                <div className="flex-1 flex items-center justify-center text-sm text-ink-dim">
                  {t("hwScanning")}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <HwStat label={t("hwCpu")} value={hw.hardware.cpu.name?.split(" ").slice(0, 3).join(" ") || `${hw.hardware.cpu.cores ?? "?"} cores`} />
                    <HwStat label={t("hwRam")} value={hw.hardware.ram_gb ? `${Math.round(hw.hardware.ram_gb)} GB` : "?"} />
                    <HwStat label={t("hwGpu")} value={hw.hardware.gpu.present ? (hw.hardware.gpu.vram_gb ? `${Math.round(hw.hardware.gpu.vram_gb)} GB` : (hw.hardware.gpu.name?.split(" ").slice(0, 2).join(" ") || "✓")) : t("hwNoGpu")} />
                  </div>

                  {/* Modelo local recomendado */}
                  <div>
                    <div className="text-xs font-medium text-ink-faint uppercase tracking-wide mb-1.5">{t("hwModel")}</div>
                    <div className="space-y-1.5">
                      {(["optimal", "lower", "higher"] as const).map((k) => {
                        const m = hw.ollama[k];
                        if (!m) return null;
                        return (
                          <ModelRow
                            key={k}
                            active={modelChoice === k}
                            onClick={() => setModelChoice(k)}
                            title={m.label}
                            sub={t("modelSizeGb", { n: m.size_gb })}
                            why={k === "optimal" ? t("hwModelWhy") : m.why}
                          />
                        );
                      })}
                      <ModelRow
                        active={modelChoice === "none"}
                        onClick={() => setModelChoice("none")}
                        title={t("hwNone")}
                        sub=""
                        why=""
                      />
                    </div>
                  </div>

                  {/* Núcleo visual */}
                  <div>
                    <div className="text-xs font-medium text-ink-faint uppercase tracking-wide mb-1.5">{t("hwParticles")}</div>
                    <div className="flex gap-1.5">
                      {TIER_ORDER.map((tt) => {
                        const isRec = (hw.avcs.recommended_tier as QualityTier) === tt;
                        return (
                          <button
                            key={tt}
                            type="button"
                            onClick={() => setTier(tt)}
                            className={`flex-1 rounded-lg px-2 py-2 border text-xs transition-colors ${
                              tier === tt ? "border-accent bg-accent/10 text-ink" : "border-base-700 hover:border-base-600 text-ink-dim"
                            }`}
                          >
                            <div className="font-medium">{TIER_LABEL[lang][tt]}</div>
                            {isRec && <div className="text-[9px] text-accent mt-0.5">★</div>}
                          </button>
                        );
                      })}
                    </div>
                    <p className="text-[11px] text-ink-faint mt-1.5">{t("hwParticlesWhy")}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="flex-1 flex flex-col">
              <div className="text-lg font-semibold text-ink mb-3">{t("stepVoice")}</div>
              {voiceBusy && !voice ? (
                <div className="flex-1 flex items-center justify-center text-sm text-ink-dim">{t("voiceResolving")}</div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-accent/15 border border-accent/40 flex items-center justify-center text-3xl">
                    🎙️
                  </div>
                  <div className="text-sm text-ink">
                    {t("voiceReady", { lang: LANGS.find((l) => l.code === lang)?.name || lang })}
                  </div>
                  <button
                    type="button"
                    onClick={testVoice}
                    disabled={voiceBusy || !voice}
                    className="rounded-xl px-5 py-2.5 bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 transition-colors disabled:opacity-50 text-sm font-medium"
                  >
                    {voiceBusy ? t("voiceTesting") : `▶ ${t("voiceTest")}`}
                  </button>
                  <p className="text-[11px] text-ink-faint max-w-xs">{t("voiceNote")}</p>
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="flex-1 flex flex-col">
              <div className="text-lg font-semibold text-ink mb-3">{t("stepInstall")}</div>

              {!chosenModelTag() ? (
                // No se eligió modelo local: nada que descargar.
                <div className="flex-1 flex items-center justify-center text-center">
                  <p className="text-sm text-ink-dim max-w-xs">{t("instNoModel")}</p>
                </div>
              ) : runtimeBusy && !runtime ? (
                <div className="flex-1 flex items-center justify-center text-sm text-ink-dim">{t("instChecking")}</div>
              ) : runtime && !runtime.ok ? (
                // Ollama no detectado: enlace de descarga + reintento.
                <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-signal-warn/15 border border-signal-warn/40 flex items-center justify-center text-3xl">⚙️</div>
                  <p className="text-sm text-ink-dim max-w-xs">{t("instNeedOllama")}</p>
                  {runtime.install_url && (
                    <button
                      type="button"
                      onClick={() => window.open(runtime.install_url as string, "_blank")}
                      className="rounded-xl px-5 py-2.5 bg-accent text-base-950 hover:bg-accent-glow transition-colors text-sm font-medium"
                    >
                      ↓ {t("instGetOllama")}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => { setRuntime(null); void checkRuntime(); }}
                    disabled={runtimeBusy}
                    className="text-xs text-ink-dim hover:text-ink transition-colors disabled:opacity-50"
                  >
                    {t("instRetry")}
                  </button>
                </div>
              ) : (
                // Runtime OK: progreso de la descarga.
                <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
                  {installJob?.status === "done" ? (
                    <>
                      <div className="w-16 h-16 rounded-full bg-accent/15 border border-accent/40 flex items-center justify-center text-3xl">✓</div>
                      <p className="text-sm text-ink">{t("instDone", { model: chosenModelLabel() })}</p>
                    </>
                  ) : installJob?.status === "failed" ? (
                    <>
                      <div className="w-16 h-16 rounded-full bg-signal-error/15 border border-signal-error/40 flex items-center justify-center text-3xl">✕</div>
                      <p className="text-sm text-ink-dim max-w-xs">{t("instFailed")}</p>
                      {installJob.error && <p className="text-[10px] text-signal-error max-w-xs break-words">{installJob.error}</p>}
                      <button
                        type="button"
                        onClick={() => { installStartedRef.current = false; setInstallJob(null); const tag = chosenModelTag(); if (tag) void startInstall(tag); }}
                        className="rounded-xl px-4 py-2 bg-accent/15 border border-accent/40 text-ink hover:bg-accent/25 transition-colors text-sm"
                      >
                        {t("instRetryDl")}
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="w-full max-w-xs">
                        <div className="text-sm text-ink mb-2">{t("instDownloading", { model: chosenModelLabel() })}</div>
                        <div className="h-2 w-full rounded-full bg-base-700 overflow-hidden">
                          <div
                            className="h-full bg-accent transition-all duration-500"
                            style={{ width: `${installJob?.percent ?? 0}%` }}
                          />
                        </div>
                        <div className="text-[11px] text-ink-faint mt-1.5">
                          {Math.round(installJob?.percent ?? 0)}%{installJob?.step ? ` · ${installJob.step}` : ""}
                        </div>
                      </div>
                      <p className="text-[11px] text-ink-faint max-w-xs">{t("instBackground")}</p>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Barra de navegación */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-base-700/60">
          <button
            type="button"
            onClick={() => setStep((s) => (s > 0 ? ((s - 1) as Step) : s))}
            className={`text-sm text-ink-dim hover:text-ink transition-colors ${step === 0 ? "invisible" : ""}`}
          >
            ← {t("back")}
          </button>
          {step < 3 ? (
            <button
              type="button"
              onClick={() => setStep((s) => ((s + 1) as Step))}
              className="rounded-xl px-5 py-2.5 bg-accent text-base-950 hover:bg-accent-glow transition-colors text-sm font-medium"
            >
              {t("next")} →
            </button>
          ) : (
            <button
              type="button"
              onClick={finish}
              disabled={saving}
              className="rounded-xl px-5 py-2.5 bg-accent text-base-950 hover:bg-accent-glow transition-colors text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {saving ? t("saving") : installJob?.status === "downloading" ? t("finishBg") : t("finish")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function HwStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-base-800/60 px-2 py-2.5">
      <div className="text-[10px] text-ink-faint uppercase tracking-wide">{label}</div>
      <div className="text-xs text-ink font-medium mt-0.5 truncate" title={value}>{value}</div>
    </div>
  );
}

function ModelRow({
  active, onClick, title, sub, why,
}: { active: boolean; onClick: () => void; title: string; sub: string; why: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full flex items-center gap-3 rounded-lg px-3 py-2 border text-left transition-colors ${
        active ? "border-accent bg-accent/10" : "border-base-700 hover:border-base-600"
      }`}
    >
      <div className={`w-3.5 h-3.5 rounded-full border shrink-0 ${active ? "border-accent bg-accent" : "border-base-600"}`} />
      <div className="flex-1 min-w-0">
        <div className="text-sm text-ink font-medium truncate">
          {title}{sub && <span className="text-ink-faint font-normal"> · {sub}</span>}
        </div>
        {why && <div className="text-[11px] text-ink-faint truncate">{why}</div>}
      </div>
    </button>
  );
}
