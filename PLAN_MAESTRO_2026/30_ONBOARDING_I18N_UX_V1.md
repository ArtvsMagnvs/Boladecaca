# 30 — ONBOARDING, i18n Y PULIDO UX (pre-1.0)
## Plan de las features de experiencia de usuario para 1.0

> **Contexto**: petición del usuario (2026-07-21) — 8 mejoras de UX/producto. Las
> autónomas, verificables y de bajo riesgo se implementaron ya (ver §0); las que
> exceden una sesión (i18n completo, OAuth fácil, Kokoro/Docker autónomo, AVCS
> detrás del Workspace, onboarding con auto-config) se planifican aquí con sus
> sesiones y modelo/esfuerzo. Redactado como equipo senior de producto/UX/infra.

---

## 0. LO QUE YA ESTÁ HECHO (esta sesión, verificado por compilación)

| # | Feature | Estado | Dónde |
|---|---------|--------|-------|
| 1 | **Tema claro / oscuro** con toggle y persistencia | ✅ HECHO | `styles/index.css` (colores como variables CSS por tema) + `store/useThemeStore.ts` + toggle en Ajustes → Sistema. Los componentes no se tocaron (siguen usando `bg-base-950`…). |
| 2 | **Ventana maximizada al abrir + F11 fullscreen** | ✅ HECHO | `electron/main.cjs`: `show:false`+`maximize()` al estar lista; F11 alterna fullscreen total; Esc sale. |
| 6 | **Scanner de hardware + recomendación Ollama/AVCS** | ✅ HECHO (backend) | `core/hardware.py` (CPU/RAM/GPU vía psutil+nvidia-smi) + `GET /api/local-models/hardware`: recomienda modelo óptimo + inferior + superior-solo-si-seguro, y nivel de partículas AVCS. Umbrales distintos para GPU (dedicada) y RAM (compartida). |
| 7 | **AVCS mejor explicado + partículas** | ✅ HECHO | Ajustes → Voz → Presencia visual: 4 niveles con significado, "recomendado para tu PC" (del scanner) y aviso "puede ir justo" en los superiores. |
| 8a | **Voces multilingües + "Crear Voz"** | ✅ HECHO | EdgeTTS gana FR/PT (faltaban); default por idioma cubre ES/EN/FR/PT; Mark-XL usa `en-US-GuyNeural` (ya presente). Botón "Crear Voz" → ElevenLabs Voice Lab. |

**Pendiente de estas (Windows)**: probar el tema en vivo, F11, el scanner con GPU
real, y que las voces FR/PT suenen.

---

## 1. ONBOARDING + AUTO-CONFIGURACIÓN (la pieza que une varias)

**Qué**: la primera vez que se abre Aithera, un asistente de bienvenida que: (a)
elige idioma, (b) escanea el hardware y **auto-configura** el modelo de Ollama y
las partículas del AVCS (con opción de cambiarlo), (c) selecciona una voz por
defecto del idioma, (d) prepara el sistema de voz (§4). Todo antes de que Aithera
termine de abrirse por primera vez.

**Se apoya en lo ya hecho**: el scanner (`/api/local-models/hardware`) ya da las
recomendaciones; el instalador de modelos locales ya existe (`/api/local-models/
install`); la voz por defecto ya se resuelve (`/api/voice/defaults`). El
onboarding es el PEGAMENTO que los orquesta la primera vez.

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **OB-1** | Detección de "primera vez" (flag en Config) + pantalla de bienvenida (idioma → hardware → modelo → voz), llamando a los endpoints que ya existen. Auto-selecciona lo recomendado; el usuario confirma o cambia. | **Opus** | **Alto** |
| **OB-2** | Instalación de Ollama guiada si falta (detecta, enlaza a la descarga, espera) + descarga del modelo recomendado con barra de progreso (reusa `/install/status`). Todo dentro del onboarding, sin salir. | **Opus** | **Alto** |

---

## 2. INTERNACIONALIZACIÓN COMPLETA (i18n) — ES / EN / FR / PT

**Qué**: toda la UI traducida a 4 idiomas, incluidas las explicaciones de cómo
conectar Google/Telegram, los textos de ayuda, etc. Selección en el onboarding y
cambiable en Ajustes.

**Por qué es un bloque grande y no una sesión**: el frontend tiene ~7.700 líneas
con cientos de strings hardcodeados en español. Traducir bien (no máquina) los 4
idiomas es trabajo sostenido. Se hace por fases: framework primero, luego
pantalla por pantalla.

**Enfoque técnico** (decidido, para no improvisar):
- Librería ligera: `react-i18next` (estándar, ~localización por claves) o un
  store propio minimalista (mismo patrón que `useThemeStore`) si se quiere cero
  dependencias. Recomendación: store propio con archivos `locales/{es,en,fr,pt}.json`
  — cero dependencia nueva, control total, suficiente para esta escala.
- Un hook `t("clave")` que lee del idioma activo (persistido, como el tema).
- Migración incremental: cada pantalla se pasa a `t(...)` cuando se toca; las no
  migradas siguen en español (degradación graceful, nunca roto).

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **I18N-1** | Framework: `store/useI18n.ts` + `locales/*.json` + hook `t()`; selector de idioma (onboarding + Ajustes); persistencia; `app_language` en Config (ya lo lee `/api/voice/defaults`). | **Opus** | **Alto** |
| **I18N-2** | Traducir el núcleo: onboarding, Ajustes (todas las secciones, incl. explicaciones Google/Telegram), Sidebar, Hub. ES→EN/FR/PT. | **Sonnet** | **Medio** |
| **I18N-3** | Traducir el resto: Chat, Workspace, Misiones, Automatización, Email, Voz, Agentes. | **Sonnet** | **Medio** |
| **I18N-4** | Revisión de calidad de las traducciones (nativa, no literal) + textos de ayuda de conexión (Google OAuth paso a paso, Telegram /start) por idioma. | **Fable 5** | **Alto** |

---

## 3. AUTENTICACIÓN FÁCIL DE PROVEEDORES (ChatGPT / Google login)

**Qué**: conectar proveedores de IA con "iniciar sesión con Google/cuenta" en vez
de pegar una API key a mano, cuando el proveedor lo permita.

**Realidad técnica (honesta)**: la mayoría de proveedores de IA (OpenAI,
Anthropic…) NO ofrecen "login social" para su API — dan API keys. "ChatGPT con
Google" es login a la app de ChatGPT, no a la API. Lo que SÍ es viable y de alto
valor:
- **OAuth real donde existe**: Google (Gmail/Calendar) ya usa OAuth — pulir su
  flujo para que sea un botón "Conectar con Google" limpio (ya hay base en
  `google_auth.py`). Esto es lo más cercano a lo que el usuario pide y ya
  medio-existe.
- **Detección y pegado asistido de API keys**: para los que solo dan key, un
  flujo guiado ("abre esta página → copia tu key → pégala aquí") con enlace
  directo, en vez de asumir que el usuario sabe dónde está su key.

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **AUTH-1** | Pulir el OAuth de Google a un botón "Conectar con Google" de un clic (flujo limpio, mensajes claros, manejo de token caducado que el usuario ya sufrió). | **Opus** | **Alto** |
| **AUTH-2** | Flujo guiado de API key por proveedor (enlace directo a su página de keys + instrucción por proveedor), para los que no tienen OAuth. Investigar cuáles ofrecen OAuth de verdad. | **Sonnet** | **Medio** |

---

## 4. SISTEMA DE VOZ AUTÓNOMO EN LA INSTALACIÓN (Kokoro/Docker, eSpeak)

**Qué**: que Aithera prepare su voz sola en la primera apertura, sin que el
usuario instale nada, y decidir el destino de Kokoro (Docker) y eSpeak.

**Decisiones a tomar (con recomendación)**:
- **eSpeak**: verificar si funciona de verdad en la máquina del usuario. Si da
  problemas, **quitarlo y quedarse con EdgeTTS** como fallback (gratis, sin key,
  buena calidad, ya es el default). Recomendación del equipo: **EdgeTTS como
  base, eSpeak solo como último recurso offline si de verdad funciona**; si no,
  fuera (menos superficie que mantener).
- **Kokoro (TTS local en Docker)**: es potente pero pesado (Docker + modelo). Si
  se mantiene, Aithera debe crear/instalar el contenedor sola, post-instalación,
  antes de terminar de abrirse la primera vez. **Recomendación**: hacerlo OPCIONAL
  en el onboarding ("¿Quieres voz local de máxima calidad? Requiere Docker, lo
  preparo yo") — no obligatorio, porque EdgeTTS ya cubre el caso base sin Docker.

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **VOZ-1** | Auditar eSpeak en Windows (¿funciona?); decidir mantener/quitar. Garantizar EdgeTTS como base sólida. | **Sonnet** | **Medio** |
| **VOZ-2** | Kokoro autónomo (opcional en onboarding): detectar Docker, crear el contenedor y descargar el modelo en background, con estado en la UI; degradación graceful si Docker falta. | **Opus** | **Alto** |

---

## 5. AVCS REAL DETRÁS DEL WORKSPACE

**Qué**: el fondo del Workspace debe ser el AVCS/AICore real (el del Hub), no la
"bola azul" simple actual.

**Estado**: el `AICore.tsx` (three.js con shaders) ya existe y se usa en el Hub. El
Workspace usa una versión atenuada/simple. La tarea es montar el AICore real como
fondo del Workspace (atenuado, sin robar rendimiento a las tarjetas), respetando
el nivel de partículas del AVCS (§0 item 7) para no sobrecargar.

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **AVCS-W1** | Montar `AICore` real como fondo del Workspace (atenuado, `pointer-events:none`, detrás de las tarjetas), respetando el tier de partículas y pausándose si el equipo va justo. | **Opus** | **Alto** |

---

## 6. ORDEN RECOMENDADO Y NOTA FINAL

Orden por dependencias y valor:
1. **I18N-1** (framework) — desbloquea el onboarding multilingüe.
2. **OB-1/OB-2** (onboarding + auto-config) — la primera impresión; usa el scanner ya hecho.
3. **I18N-2/3/4** (traducciones) — incremental, en paralelo.
4. **VOZ-1** (eSpeak/EdgeTTS) — rápido, cierra una duda.
5. **AVCS-W1** (AICore en Workspace) — pulido visual.
6. **AUTH-1/2** (conexión fácil) — mejora la fricción de setup.
7. **VOZ-2** (Kokoro/Docker) — opcional, el último.

**Nota del equipo (honestidad)**: las 5 features ya implementadas (§0) son las
autónomas y de bajo riesgo. Las de este plan tocan onboarding, i18n masivo, OAuth
y Docker — cada una es un mini-proyecto con superficie de riesgo, y meterlas todas
de golpe en una app pre-1.0 sin verificación visual sería imprudente. Se hacen por
fases, midiendo, con la app siempre funcionando. Es la diferencia entre un equipo
senior y uno que rompe producción por ir rápido.

---
*Plan de UX/onboarding pre-1.0. Las features autónomas (§0) están hechas y
verificadas por compilación; el resto planificado con sesiones y modelo/esfuerzo.
Redactado 2026-07-21.*
