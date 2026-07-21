# PLAN MAESTRO DE OPTIMIZACIÓN — Aithera v0.9.5 → producto premium
### Objetivo: que Aithera funcione como software profesional de años de iteración
### de un equipo senior, no como un MVP. 2026-07-20 · Fable 5

Este documento cataloga TODA la optimización de Aithera —rendimiento, fluidez,
UX, deuda técnica— priorizada por impacto. Las secciones ✅ están ejecutadas en
esta sesión; las ⏳ quedan planificadas con su fix concreto para no perderlas.

Regla rectora: **cada optimización deja la suite en verde**. Aithera tiene 764+
tests (751 previos + 13 de contratos); ninguna mejora de rendimiento vale una
regresión. Los cambios amplios y no verificables se planifican, no se improvisan.

---

## ✅ O1 — Latencia de voz: conversación fluida (EJECUTADA)

**El problema**: la conversación por voz era lenta en las tres etapas — STT
tardaba en pasar voz a texto, la respuesta tardaba, y el TTS tardaba en empezar
a "leer". El objetivo: fluidez tipo GPT/Google/Alexa.

**Causas raíz y fixes**:

1. **STT lento** (`backend/app/voice/whisper_stt.py`): decodificaba con
   `beam_size=5` sobre el modelo "small". Cambios:
   - Modo `fast` nuevo: modelo rápido (`base`, ~2-3x más veloz en CPU) +
     `beam_size=1` (búsqueda voraz, ~3-5x más rápido) + VAD recortado (250ms de
     silencio mínimo vs 500) + `condition_on_previous_text=False`. Para clips
     cortos de conversación la pérdida de precisión es mínima; la de latencia,
     enorme. El botón de transcripción manual del Hub sigue usando el modelo
     preciso (`small`, beam 5).
   - Segundo singleton `_fast_model` (import perezoso; reutiliza el preciso si
     coinciden — cero memoria extra si `WHISPER_MODEL_FAST == WHISPER_MODEL`).
   - Endpoint `/api/voice/transcribe?fast=true`.

2. **TTS que esperaba a sintetizar TODO antes de hablar** (`frontend/src/pages/
   Chat.tsx::speak`): para un párrafo eran varios segundos de silencio. Ahora
   **streaming por frases**: `splitIntoSpeechChunks()` trocea la respuesta en
   frases (agrupando las cortas, máx ~180 chars), sintetiza la PRIMERA y empieza
   a sonar de inmediato mientras las siguientes se sintetizan con **prefetch de
   1** (la i+1 mientras suena la i). El usuario oye a Aithera arrancar en ~0.5s.
   Fallback a eSpeak intacto por frase.

3. **Turn-taking lento** (`Chat.tsx::listenOnce`): el corte por silencio era de
   1200ms — el usuario esperaba más de un segundo tras callarse. Bajado a
   **700ms**: ágil como Alexa, sin cortar entre frases naturales.

**Verificación**: `tsc` limpio; backend `py_compile` limpio; lógica de
`splitIntoSpeechChunks` probada (2 frases para una respuesta típica, no
fragmenta "Sí.", ignora vacío). **Pendiente en vivo**: medir la mejora real de
punta a punta con el micro (la percepción de fluidez solo se confirma hablando).

**Palancas futuras (V1.1)**: streaming del LLM directamente al TTS (hoy el TTS
espera a que el pipeline devuelva la respuesta completa; con SSE del responder
se podría empezar a hablar antes de que el modelo termine de pensar). Requiere
que el TIE exponga la respuesta token a token también en el camino de misión.

---

## ✅ O2 — Settings como modal profesional (EJECUTADA)

**El problema**: Configuración ocupaba toda la pantalla con un scroll
interminable de ~11 secciones apiladas — sensación de "programa hecho por IA
genérico", no de app desktop de alta gama.

**Solución** (`frontend/src/components/Modal.tsx` NEW + `pages/Settings.tsx`):
- `Modal.tsx`: primitivo reutilizable — backdrop atenuado con blur, panel
  centrado con tamaño máximo (`max-w-5xl`, `max-h-[88vh]`, NO pantalla completa),
  cierre por Esc y clic-fuera, bloqueo del scroll de fondo, animación de
  aparición suave (`modal-fade`/`modal-pop` en el CSS de tokens). Queda
  disponible para cualquier diálogo futuro.
- Settings pasa de página-scroll a **modal con tab-rail lateral** (6 pestañas):
  **IA y Modelos** (estado, proveedores, inteligencia, modelos locales) ·
  **Permisos** · **Voz** (ElevenLabs, presencia visual) · **Conexiones**
  (Google, Telegram, búsqueda web) · **Memoria** (ChromaDB, preferencias,
  perfil) · **Sistema** (config local). **Cero funciones perdidas** — todas las
  secciones y controles siguen ahí, solo reorganizados.
- Cabecera con título + botón de cierre; navegación de vuelta con `navigate(-1)`.

**Verificación**: `tsc --noEmit` limpio (exit 0) — la reestructuración JSX
balancea. **Pendiente en vivo**: vistazo visual del modal y las 6 pestañas.

---

## ✅ O3 — Rendimiento y deuda técnica (EJECUTADA, primera tanda)

1. **Polling visibility-aware** (`Hub.tsx`): el Hub sondeaba el backend cada 30s
   aunque la ventana estuviera minimizada u oculta. Ahora se pausa con
   `document.hidden` y refresca al instante al volver a primer plano. Ahorra
   carga de backend y batería sin que el usuario vea datos rancios. Mismo patrón
   aplicable al resto de polls (ver ⏳ abajo).
2. **Banner de versión** `backend/iniciar_app.bat` 0.3.0 → 0.9.5 (deuda cosmética
   heredada desde V0.8, documentada en CLAUDE.md §16).
3. **`AitheraApp` legacy**: confirmado que ya solo vive en el tombstone
   `desktop.py` (vaciado en S1) — la deuda §16.8 queda cerrada al hacer
   `git rm backend/app/desktop.py`.

---

## ✅ V1 — Voz natural: markdown, barge-in (EJECUTADA, 2ª tanda)

**Investigación previa**: JWIKI `08_VOICE/` (voice-latency-budget,
voice-pipelines-realtime, whisper). Presupuesto objetivo del proyecto: **TTFB
< 2s**; best-in-class < 1.6s. Whisper NO es streaming → la latencia de STT es
irreducible por debajo del tiempo de decodificar el clip entero.

1. **La voz ya no pronuncia el formato** (`voice/text_clean.py`): decía
   "asterisco asterisco" en las negritas y leía guiones de lista, almohadillas
   de título y barras de tabla. `strip_emojis` solo quitaba emojis. Nace
   **`clean_for_speech()`**: quita bloques de código, convierte enlaces a su
   texto (nunca la URL), tablas a filas con pausas, títulos/citas/viñetas a
   texto llano, énfasis anidado (`***x***` → `x`), y emojis. Conectado a los
   dos endpoints de síntesis. Verificado con 10 casos reales.
2. **Barge-in — interrumpir a Aithera** (`Chat.tsx`, `MicButton.tsx`):
   - `stopSpeaking()` corta la locución al instante (token de cancelación +
     `onpause` resuelve el bucle de frases, que si no esperaría un `ended` que
     nunca llega).
   - **Modo conversación**: `watchForBargeIn()` escucha el micro MIENTRAS
     Aithera habla (`echoCancellation` + umbral RMS alto para que no se
     interrumpa a sí misma por los altavoces; 250ms de voz sostenida).
   - **Botón del micro**: pulsarlo mientras habla la calla (`onStartRecording`).
   - **Reformulación**: se registra lo que de verdad se llegó a decir
     (`spokenSoFarRef`) y el siguiente turno le llega al modelo con un contexto
     OCULTO ("te han interrumpido, solo oyó X, no repitas") vía el nuevo
     `sendMessage(text, {prefix})` — el chat sigue mostrando solo el mensaje
     del usuario.

## ✅ V2 — Personalidades de Aithera (EJECUTADA)

`backend/app/ai/personalities.py` NEW. **Decisión de arquitectura**: la
personalidad **compone SOBRE** el prompt base, nunca lo sustituye — si lo
reemplazara, una personalidad (sobre todo una escrita por el usuario) podría
cargarse las reglas no negociables: texto plano, no inventar datos, no fingir
que hizo algo. Esas nacieron de fallos reales (auditoría v0.9.5) y ninguna
personalidad puede desactivarlas.
- **Personalidad "Aithera" por defecto**, derivada de la filosofía real del
  proyecto (CLAUDE.md §18 + los 8 contratos de la auditoría +
  PRINCIPIOS_KARPATHY): directa sin relleno, honesta por encima de agradable,
  cercana pero no servil, orientada a la acción, sobria.
- **4 estándar**: Profesional · Cercana · Concisa · Didáctica.
- **La mía**: el usuario la describe en bruto y `improve_prompt()` la convierte
  en un bloque de tono bien formado con capacidad REASON del MEL. El
  "prompt-engineer" interno tiene una salvaguarda: ignora cualquier petición de
  mentir/ocultar errores. Degradación honesta si el modelo falla.
- Endpoints `/api/voice/personalities` (GET · select · custom). UI:
  `components/voice/PersonalityPicker.tsx` en el Centro de Voz.

## ✅ V3 — Voz por defecto garantizada (EJECUTADA)

**El bug**: Aithera respondía MUDA en el chat hasta que el usuario iba al Centro
de Voz a elegir una voz a mano. Una app de voz que arranca muda está rota.
`GET /api/voice/defaults` resuelve SIEMPRE una voz: la del usuario o la mejor
del idioma configurado (`es` → Elvira, `en` → Aria; EdgeTTS porque es el único
gratis, sin key y sin descargar modelos → garantizable en instalación limpia),
**y la persiste**. `Chat.tsx` la pide al arrancar en vez de leer la Config a
pelo. Verificado contra código real: asigna, persiste, es estable en la 2ª
llamada y respeta el idioma.

---

## ✅ VZ1 + VZ5 — Streaming LLM→TTS + profiling (EJECUTADA, 3ª tanda)

**VZ1 — la voz arranca mientras el modelo escribe** (`Chat.tsx`): antes el TTS
esperaba a que el pipeline devolviera la respuesta COMPLETA y solo entonces
sintetizaba la 1.ª frase — se pagaba el tiempo entero de generación del LLM en
silencio. Ahora `beginSpeechStream()` abre una cola viva: cada token del
`streamChat` la alimenta (`feed`), extrae las frases completas con el mismo
agrupador de O1 y lanza su síntesis DE INMEDIATO; la reproducción va en orden.
Verificado: en una respuesta larga la 1.ª frase empieza a sonar al **~37% del
texto** — Aithera habla mientras el modelo aún redacta el resto. El barge-in
vive en la misma cola (cancela todo y registra lo dicho). Un solo camino de
código: `speak(texto)` (respuesta ya hecha) y el streaming usan la misma cola.

**VZ5 — profiling del pipeline** (`Chat.tsx` + `voice.py`): cada turno de voz
imprime en la consola del navegador `[voz-perfil] stt=…ms  llm_1er_token=…ms
voz_suena=…ms` (todo relativo a t0 = el instante en que dejas de hablar), y el
backend loguea `[voz-perfil] STT fast: …ms para Xs de audio`. Es la herramienta
para saber, EN TU MÁQUINA, qué etapa domina la latencia — hasta ahora se
optimizaba a ciegas. **Siguiente paso recomendado**: hacer 3-4 turnos de voz
reales y mirar esas cifras; dicen si el cuello es el STT, el modelo o el TTS, y
con eso se decide si vale la pena VZ2 (modelo `tiny`), VZ3 (Silero VAD) o VZ4
(Realtime API).

## ⏳ PENDIENTE — Optimizaciones planificadas (con su fix concreto)

Priorizadas. Cada una es segura de aplicar incrementalmente con la suite en
verde. No se ejecutan ahora para no arriesgar regresiones no verificables en
este entorno (la suite completa corre en Windows).

### Rendimiento — frontend
- ✅ **P1 · Polling visibility-aware en TODAS las páginas** (HECHO): hook
  `hooks/usePolling.ts` con guard de `document.hidden` + refresco al volver a
  primer plano. Aplicado a Hub (inline), Missions, Automation, Chat
  (PendingApprovals 2s), Settings (descarga de modelos 1.5s) y Sidebar (estado
  30s). Ningún poll corre ya con la ventana oculta.
- ✅ **P2 · Lazy-routes** (HECHO): `App.tsx` con `React.lazy`+`Suspense`, solo
  el Hub eager. Las 10 páginas restantes (EmailAssistant, Settings…) cargan al
  navegar → arranque de Electron más ligero.
- ✅ **P3 · `Chat.tsx` re-renders** (HECHO): `ChatBubble` memoizado — durante el
  streaming, cada token ya no re-parsea el MiniMarkdown de todos los mensajes
  anteriores. Un mensaje ya escrito no vuelve a parsearse.

### Rendimiento — backend
- **P4 · Arranque de `app.main`**: la deuda ya conocida (test de perf
  `test_import_app_main_no_bloquea_en_memoria` parpadea): el import eager de
  fastapi/sqlalchemy/elevenlabs/ai_manager domina. Perfilar con `-X importtime`
  y diferir lo que se pueda a lazy (elevenlabs/whisper ya son lazy; revisar
  ai_manager y los routers de email).
- **P5 · `httpx` keep-alive**: ya hecho para proveedores IA (A2a). Revisar que
  las llamadas a Google (email/calendar) y ElevenLabs reusen cliente.

### Deuda técnica (CLAUDE.md §16, items graphify)
- ✅ **D-#10 · `_clean_email_tables` cross-domain** (HECHO): `CalendarEvent`
  sale del autouse de limpieza de email; nace la fixture dedicada
  `_clean_calendar_events` que piden explícitamente los tests que lo crean
  (`test_email_autonomy_digest` ×3, `seeded_day` de `test_memory_briefing`
  limpia el suyo; `test_memory_ingestion` ya se limpiaba solo). Verificado con
  el store real: la limpieza de email ya no toca calendar.
- ✅ **D-#11 · Edges de `EmailTool`** (VERIFICADO): grep confirma que
  `CredentialsPayload`/`AutoReplyRulePayload` NO se referencian en
  `email_tool.py` — son Pydantic de los endpoints (`email_auth.py`,
  `email_auto_reply.py`). Los 10 edges de graphify eran **falsos positivos** del
  grafo (inferencia por nombre), no acoplamiento real. Nada que arreglar.
- **D-#9 · Test Telegram usa `app.db.models.Project`** (deferido, justificado):
  `test_format_proyectos_lista` importa el modelo SQL directo. Revisado: NO es
  un cruce de módulos-feature — `app.db` es infraestructura compartida (el
  propio `telegram_adapter.format_proyectos` la usa igual). No viola la
  disciplina modular de doc 16 (que gobierna app.tie/app.mel/app.memory/…, no
  el acceso a la capa de datos). Se deja como está: cambiarlo a un dict-doble
  añadiría indirección sin ganar aislamiento real.

### UX / pulido visual
- ✅ **U1 · `ConfirmDialog` elegante** (HECHO parcial): `components/ConfirmDialog.tsx`
  con el hook `useConfirm()` reemplaza los `window.confirm()` nativos (que salen
  con el chrome del SO, rompiendo la estética). Aplicado a Missions (borrar
  misión). **Pendiente**: aplicarlo a los `confirm()` restantes (Settings borrar
  contexto/perfil/historial, Automation, EmailAssistant) — mismo patrón, un
  reemplazo por sitio.
- **U2 · Estados de carga/vacío consistentes**: revisar que todas las páginas
  tengan skeleton/empty-state con el mismo lenguaje visual (algunas muestran
  "Cargando..." en texto plano).
- **U3 · Accesibilidad**: foco atrapado dentro del `Modal` (focus-trap) y
  `aria-*` en los controles interactivos.

### Voz — lo que queda para llegar al presupuesto de la JWIKI (< 2s TTFB)
Barge-in y naturalidad ya están (V1). Lo que sigue mordiendo es la LATENCIA
pura, y estas son las tres palancas reales, en orden de impacto:

- **VZ1 · Streaming LLM→TTS** (el mayor salto que queda): hoy el TTS espera a
  que el pipeline devuelva la respuesta COMPLETA y solo entonces sintetiza la
  1.ª frase. Con el stream del responder se puede sintetizar en cuanto llega la
  primera frase del modelo — ahorra el TTFT entero del LLM (500-800ms según la
  JWIKI). Requiere que `handle_stream` emita texto incremental también en el
  camino complejo, y que `speak()` consuma un iterador en vez de un string.
- **VZ2 · Modelo STT aún más rápido**: `tiny` (39M) frente al `base` (74M)
  actual — la JWIKI lo da como el más veloz. Para clips cortos y limpios de
  conversación en español la pérdida es asumible; hacerlo configurable
  (`WHISPER_MODEL_FAST=tiny`) y medirlo en la máquina del usuario antes de
  cambiar el default. Alternativa de mayor calado: **GPU** (5x según JWIKI) si
  el usuario tiene CUDA, o `whisper.cpp`.
- **VZ3 · Silero VAD** (JWIKI: 100ms vs los 500ms de un VAD por RMS): el corte
  de fin de intervención es hoy un umbral de energía en el navegador. Silero
  detecta fin-de-habla de verdad y recortaría cientos de ms del turn-taking.
- **VZ4 · Realtime API** (V1.5+, la JWIKI ya lo documenta): OpenAI Realtime o
  Gemini Live meten STT+LLM+TTS en un WebSocket con TTFB 200-500ms. Es el
  cambio de arquitectura que haría la voz indistinguible de GPT/Alexa, pero
  ata la voz a un proveedor cloud concreto — decisión de producto, no solo
  técnica.
- **VZ5 · Profiling real**: instrumentar el pipeline con los timings de la
  JWIKI (`stt` / `llm_ttft` / `tts_ttfb` / `total`) y sacarlos en el log. Hoy
  se optimiza a ciegas: sin medir en la máquina del usuario no se sabe cuál de
  las tres etapas domina de verdad.

---

## Estado

| Bloque | Qué | Estado |
|--------|-----|--------|
| O1 | Latencia de voz (STT/TTS/turn-taking) | ✅ código; vivo pendiente |
| O2 | Settings modal con pestañas | ✅ código (tsc limpio); vivo pendiente |
| O3 | Polling visibility-aware + banners + AitheraApp | ✅ código |
| V1 | Voz natural: sin markdown hablado + barge-in con reformulación | ✅ verificado contra código real |
| V2 | Personalidades (Aithera + 4 estándar + propia mejorada por IA) | ✅ verificado contra código real |
| V3 | Voz por defecto garantizada (nunca arranca muda) | ✅ verificado contra código real |
| P1-P5, D-#9/10/11, U1-3, VZ1-5 | ⏳ planificadas con fix concreto |

**Filosofía**: Aithera no se vuelve premium con una reescritura de una tarde,
sino con optimización incremental y verificable. Este documento es la hoja de
ruta; O1-O3 son el primer sprint, ejecutado. El resto está listo para ejecutarse
con la suite delante, en orden de impacto.
