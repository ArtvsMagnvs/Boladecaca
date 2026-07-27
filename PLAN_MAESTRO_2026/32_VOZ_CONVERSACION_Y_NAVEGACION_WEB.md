# 32 — VOZ AUTÓNOMA + CONVERSACIÓN FLUIDA + NAVEGACIÓN WEB

> **Plan de sesiones ejecutable.** Cada sesión indica **modelo** y **esfuerzo**,
> y está descrita para que el modelo de trabajo **solo ejecute** — las
> decisiones ya están tomadas aquí. Fundado en auditoría del código real
> (`app/tie/pipeline.py`, `intents.py`, `contracts.py`), la JWIKI
> (`08_VOICE/`, `01_LANDSCAPE/`) y la revisión del repo Mark-L (FatihMakes).
>
> **Orden de bloques (pedido por el usuario):**
> 1. **BLOQUE A — Voz + Conversación + Orquestador** (incluye el arreglo de
>    latencia; es la antigua "§4 Sistema de voz autónomo", ampliada).
> 2. **BLOQUE B — Navegación web básica** (abrir medios/URL + clic por visión).
> 3. **BLOQUE C — Web profunda / agentic** (compra, citas, descargas, research).
>
> Versión objetivo: los bloques A y B (parcial) entran **antes de 1.0**; el
> bloque C es mayormente **post-1.0** salvo lo marcado.

---

## 0. Diagnóstico de latencia (CONFIRMADO en código, no hipótesis)

**Síntoma del usuario**: la conversación por voz tarda ~1 minuto en responder;
cualquier input ("hola", "gracias") aparece en Misiones como una misión
("Responder al saludo / Completado"); se ve "thinking" → "analizando" antes de
cada respuesta.

**Causa raíz (auditada)**:

1. **`handle_stream` clasifica SIEMPRE con el LLM antes de responder.**
   `app/tie/pipeline.py:154` → `intents.classify(text)` es una llamada LLM
   completa (prompt de sistema de ~120 líneas, salida JSON) que se **espera**
   (`await intent_task`) antes de arrancar el streaming del camino corto. Es un
   round-trip LLM extra que paga **el 100% de los mensajes**, incluida la charla
   trivial. Si la capacidad `classify` cae en un modelo lento o razonador
   (`<think>`), son decenas de segundos **antes del primer token**.

2. **Cada mensaje crea misión + traza.** `handle_stream` hace
   `new_mission(...)` + `tracer.record_start(...)` + `record_intent` +
   `emit_started` **incondicionalmente** (`pipeline.py:171-175`), incluso en el
   camino corto conversacional. Por eso los saludos aparecen en Misiones y por
   eso hay escrituras a `orchestrator_traces` en el hot path de una simple
   charla.

3. **El presupuesto de voz de la JWIKI** (`08_VOICE/voice-latency-budget.md`)
   asume **UNA** llamada LLM (TTFT 500ms). Nosotros hacemos `classify` + la
   respuesta = mínimo 2 llamadas secuenciales. El win original del usuario (TTS
   por frases, que sí sigue en el código) quedó enmascarado por este round-trip.

**Principio de la solución** (lo que el usuario describió, y es correcto): el
Orquestador debe decidir **rápido y barato** si un mensaje es (a) charla trivial
→ responder ya sin clasificar con LLM, (b) misión mecánica rápida → un bucle de
tool-use, (c) misión que necesita planning completo (TIE/MEL). Y una misión
**no debe bloquear la conversación**: se acusa recibo ("Vale, me pongo a ello")
y se ejecuta en segundo plano reportando avances/fallos por el canal, como hace
Claude Code.

---

# BLOQUE A — VOZ AUTÓNOMA + CONVERSACIÓN FLUIDA

## A·VOZ-1 — Retirar eSpeak, garantizar EdgeTTS como base ✅ HECHO (commit c61df78)
**Modelo: Sonnet · Esfuerzo: Bajo**

> Cerrado 2026-07-23. `espeak_voice.py` eliminado; `/synthesize` y
> `/synthesize/base64` caen a EdgeTTS; `/status` sin "espeak"; `/espeak/install`
> retirado (404). Bug de paso: el `voice_id` por defecto (ID de ElevenLabs) se
> colaba al fallback de Edge y lo rompía — arreglado con `_edge_voice_or_default`.
> Frontend actualizado (sin commitear, entrelazado con Cowork). Suite: 888.

Decisión tomada (usuario): eSpeak fuera. EdgeTTS es la base (gratis, sin key,
sin instalar nada, ya es el default).

Pasos exactos:
1. Borrar el motor eSpeak: `app/voice/espeak_voice.py` → `git rm`. Quitar su
   import y cualquier rama `espeak` de la cadena de fallback del TTS
   (buscar con `grep -rn "espeak\|eSpeak\|ESpeak" app/voice/ app/api/endpoints/voice.py`).
2. `GET /api/voice/defaults` (V3, doc 26): asegurar que **nunca** devuelve
   espeak; el orden de preferencia queda EdgeTTS → (Kokoro si instalado) →
   ElevenLabs si hay key. Si el usuario tenía espeak persistido como voz por
   defecto, migrar a EdgeTTS al arrancar (best-effort, sin romper).
3. `requirements.txt`: quitar cualquier dependencia exclusiva de eSpeak
   (pyttsx3 / py-espeak-ng si existiera). **NO** confundir con el `espeak-ng`
   que necesitará Kokoro-onnx en A·VOZ-5 (eso es un G2P bundleado, otra cosa).
4. Actualizar `08_VOICE/espeak.md` de la JWIKI con una nota "retirado en V1.0,
   EdgeTTS cubre el caso base" (no borrar el doc, es histórico).
5. Tests: quitar/ajustar los de espeak; `test_voice_*` en verde. Verificar en
   vivo que el TTS sigue sonando con EdgeTTS.

**Criterio de cierre**: la palabra `espeak` no aparece en `app/` fuera de un
comentario histórico; síntesis de voz funciona con EdgeTTS; suite verde.

---

## A·VOZ-2 — Pre-clasificador barato: la charla trivial NO paga LLM ✅ HECHO
**Modelo: Opus · Esfuerzo: Medio** — *(el arreglo de latencia, parte 1)*

> Cerrado 2026-07-23. `intents.fast_precheck()` (0 LLM, determinista,
> conservador) cableado al inicio de `classify()` — así se benefician TODOS los
> caminos (orquestador, pipeline, decomposer), no solo `handle_stream`, porque
> el orquestador es quien llama a `classify()` primero. Verificado EN VIVO
> contra el backend real: **"hola"/"gracias"/"qué tal" → 0.1-0.2 ms (0 LLM)**
> frente a **"abre YouTube…" → 160 s** por el clasificador LLM — la magnitud
> exacta de la queja del usuario. Tests: `test_fast_precheck.py` (63) + 3 de
> contrato actualizados (usaban "hola" como input genérico del camino LLM).

El corazón del arreglo. Un heurístico determinista (0 LLM) resuelve la
clasificación de la charla obvia **antes** de tocar el modelo.

Pasos exactos:
1. En `app/tie/intents.py`, añadir `fast_precheck(text) -> Optional[Intent]`
   (función pura, sin LLM, testeable):
   - Devuelve un `Intent` conversacional (`type=conversational`,
     `is_short_path=True`, `requires_*=False`, `confidence=1.0`,
     `raw_text=text`) cuando el mensaje es **claramente charla**: saludos,
     despedidas, agradecimientos, cortesías, confirmaciones cortas ("vale",
     "ok", "gracias", "adiós", "buenas", "qué tal"), y mensajes muy cortos
     (≤ N palabras) **sin ningún verbo/《marca》de acción ni de herramienta**.
   - Devuelve `None` (→ hay que clasificar con LLM) si detecta cualquier marca
     de acción: verbos imperativos de tarea (abre, busca, envía, crea, pon,
     descarga, reserva, pide, rellena…), nombres de dominio (email, calendario,
     YouTube, web, archivo…), URLs, o longitud/estructura no trivial.
   - Listas de marcas en **ES + EN** (el usuario habla español; el sistema es
     bilingüe). Conservadora: ante la duda, `None` (que clasifique el LLM) — un
     falso "no es charla" solo cuesta el round-trip de siempre; un falso "es
     charla" perdería una acción, así que se evita.
2. En `handle_stream` (`pipeline.py`), ANTES del bloque `if intent is None:`
   (línea ~153), intentar `pre = intents.fast_precheck(text)`; si `pre` no es
   `None`, usarlo como `intent` y **saltarse la llamada `classify`**. El
   prefetch de contexto (`_prefetch_context`) sí se lanza en paralelo (barato,
   presupuesto 300ms, no bloquea).
3. Métrica: loguear `[tie-perfil] precheck HIT/MISS` para medir el % de charla
   que se ahorra el LLM en la máquina real.
4. Tests (`test_tie_intents.py` o nuevo `test_fast_precheck.py`): "hola",
   "gracias", "adiós", "qué tal" → HIT conversacional; "abre YouTube y pon X",
   "búscame un vuelo", "manda un email a Ana" → MISS (None); casos frontera
   ("gracias, y ahora búscame…") → MISS (contiene acción).

**Criterio de cierre**: un "hola" responde sin ninguna llamada LLM de
clasificación (confirmado por el log `precheck HIT` y por medición de latencia);
las acciones siguen clasificándose con LLM igual que antes.

---

## A·VOZ-3 — El camino corto conversacional NO crea misión ✅ HECHO
**Modelo: Sonnet · Esfuerzo: Medio**

> Cerrado 2026-07-24. `_run_pipeline` (handle) y `handle_stream` comprueban
> `is_short_path` ANTES de `new_mission`/`tracer.record_start` — para la charla
> se salta directo a `_short_path`/`_short_path_stream` sin crear fila en
> `orchestrator_traces`. Hallazgo clave durante el diseño: `tracer.record_start`
> también fija el contexto de misión de la telemetría (`_mission_ctx`) — pero su
> propio código ya documentaba `(None, None)` como default para "llamada suelta
> (chat corto)", así que saltárselo no rompe nada, es el caso ya previsto.
> Verificado en vivo contra Postgres real: 77 trazas antes y después de un
> "hola" real. Tests: 3 nuevos + 2 actualizados (uno medía justo lo contrario:
> que la charla SÍ dejaba traza — invertido a propósito). — *(arreglo de latencia, parte 2 + UX)*

La charla no es una misión. No debe ensuciar Misiones ni escribir trazas en el
hot path.

Pasos exactos:
1. En `_stream_body` / `handle_stream`, **diferir la creación de misión+traza**:
   no llamar a `new_mission`/`record_start`/`emit_started` para el camino corto
   conversacional. Solo se crea traza cuando el flujo entra en
   `is_direct_action` o en `_complex_path` (misiones de verdad).
   - Cuidado con las dependencias: hoy `_stream_body` recibe `mission`/`trace_id`
     ya creados. Refactor: crear la misión **dentro** de cada rama que la
     necesita (directa/compleja), no arriba. El camino corto pasa a no tener
     `mission`.
   - Conservar el fix de traza zombi (`_close_if_orphan`) SOLO para las ramas
     que crean traza.
2. La conversación sí se persiste como conversación (el `session_id` de R6.5b y
   `ChatMessage`) — eso no cambia; lo que se retira es la **traza de misión** y
   su fila en `orchestrator_traces`.
3. Verificar que Misiones (`Missions.tsx`) deja de mostrar saludos/charla.
4. Tests: un mensaje conversacional no crea fila en `orchestrator_traces`; una
   acción directa y una misión compleja SÍ la crean (no-regresión).

**Criterio de cierre**: tras charlar, `orchestrator_traces` no tiene filas de
saludos; la vista de Misiones solo muestra acciones/misiones reales.

---

## A·VOZ-4 — Misiones en segundo plano: "me pongo a ello" + reporte async
**Modelo: Opus · Esfuerzo: Alto** — *(la pieza arquitectónica grande)*

Lo que pidió el usuario: en conversación, dar una misión no debe cortar el
diálogo. Aithera acusa recibo al instante, ejecuta detrás, y reporta cuando
termina o falla — como Claude Code.

Decisiones tomadas:
- **Modo conversación** = el canal es voz, o un flag de sesión "conversación"
  activo. En modo conversación, las misiones (directa o compleja) van a segundo
  plano con acuse inmediato. En modo texto/misión clásico, se mantiene el
  comportamiento actual (plan inline, aprobar plan, etc.) — no se rompe nada.
- El reporte usa el canal de origen: en chat de texto, un `ChatMessage` nuevo
  empujado a la sesión; en voz, una locución. Se apoya en `core/notify.py` (R5)
  y en los eventos `mission.*` ya existentes.

Pasos exactos:
1. `Intent`/pipeline: detectar "modo conversación" (parámetro nuevo
   `conversational: bool` que `handle_stream` recibe del endpoint; el chat de
   voz lo pone `True`, el de texto puede elegir). Append-only, default `False`
   (no rompe el contrato).
2. Cuando `conversational and (is_direct_action or es misión compleja)`:
   - Emitir de inmediato `("text", "<acuse>")` — un acuse corto generado por el
     modelo RÁPIDO o plantilla ("Vale, me pongo a ello. ¿Necesitas algo más?").
     Cerrar el stream de este turno **sin esperar** a la ejecución.
   - Lanzar la ejecución real (`_direct_action_path` o `_complex_path`) como
     **tarea de fondo** (`asyncio.create_task`, patrón fire-and-forget ya usado
     por `AgentTaskAction`), con su propia traza/misión (creada aquí, no en el
     hot path del acuse).
   - Suscribir un handler a `mission.completed`/`mission.failed` (bus de
     `core/events.py`) que, al resolverse esa misión, empuja un mensaje natural
     por el canal: "Ya está: [resumen]" / "No pude con [X]: [motivo]". Para
     avances intermedios opcionales (V1.1), reusar `mission.*` por nodo.
3. Reglas de seguridad intactas: si la misión toca algo sensible y el usuario NO
   está en Autónomo, el ApprovalGate sigue pidiendo permiso — pero el aviso de
   "necesito tu permiso para X" llega **por el canal** (notify), no bloquea el
   diálogo. En modo conversación, un gate pendiente se comunica hablando.
4. Frontend (`Chat.tsx`): un mensaje que vino de una misión de fondo se muestra
   como burbuja normal con enlace "ver la misión" (ya existe el patrón T4b).
   Nada nuevo mayor.
5. Tests: en modo conversación, una acción emite acuse inmediato y NO bloquea;
   la ejecución corre detrás y al terminar emite un evento de reporte
   (monkeypatch de `notify`/bus); en modo texto, comportamiento clásico
   inalterado.

**Criterio de cierre (en vivo)**: por voz, "abre YouTube y pon X" → Aithera dice
"me pongo a ello" en < 2s y sigo pudiendo hablar; cuando la canción está puesta
(o falla), me lo dice sin que yo pregunte. Una charla intercalada no espera a la
misión.

> **✅ HECHO (backend, 2026-07-24)**. Implementación:
> - `ChatRequest.conversational: bool = False` (append-only) → hilo por el
>   endpoint `/api/chat/stream` → `orchestrator.handle_stream(conversational=)` →
>   `tie.handle_stream(conversational=)`. Default `False` = modo texto clásico
>   intacto (no-regresión verificada por test).
> - **`app/tie/conversation.py`** (NEW, interno del TIE, vigilado por
>   `test_module_boundaries`): registro de misiones de fondo (mission_id →
>   contexto de entrega) + acuse determinista (0 LLM, para el < 2 s) + UN handler
>   suscrito a `mission.completed`/`mission.failed` que, SOLO para misiones
>   registradas, construye el reporte NL desde el outcome de la traza y lo
>   entrega. Las misiones de primer plano/AE/WPMS (que emiten los mismos eventos)
>   se ignoran.
> - **Decisión de diseño clave — event-driven, no `await` inline**: una misión
>   con paso sensible se PAUSA en el gate del plan y termina MUCHO después (otra
>   petición HTTP, tras aprobar). El bus captura esa terminación tardía igual de
>   bien que la inmediata; un `await` inline no podría. El caso "waiting" se avisa
>   aparte (`on_gate_pending`: "necesito tu permiso para X", sin bloquear el
>   diálogo) y la misión se mantiene registrada para el reporte final al aprobar.
> - **Entrega por el canal**: Telegram/externo vía `core/notify.py` (R5); chat
>   web (Electron, sin push por SSE ya cerrado) vía cola sondeable +
>   `ChatMessage` persistido → `GET /api/chat/pending-reports?session_id=&after=`
>   (cursor `seq`). En voz, ese mismo texto se locuta.
> - Multi-objetivo (Orquestador) en conversación: acuse YA + orquestación entera
>   en 2.º plano + reporte del `run.outcome` consolidado por el canal.
> - Tests: `test_voz4_background.py` (6 — acuse sin esperar a la misión, reporte
>   al terminar por cola+notify+ChatMessage, modo texto clásico inalterado, charla
>   sin crear misión, el bus ignora misiones no registradas, gate del plan avisa
>   sin bloquear). Suite backend: **992 passed**.
> - **PENDIENTE (frontend, entrelazado con el onboarding/i18n de doc 30)**: el
>   chat de VOZ debe poner `conversational: true`, y `Chat.tsx` debe sondear
>   `/api/chat/pending-reports` (patrón de `Missions.tsx`) para pintar el reporte
>   como burbuja con enlace "ver la misión". El backend está completo y testeado;
>   solo falta el cableado de UI.

---

## A·VOZ-5 — Kokoro-onnx opcional (voz local de máxima calidad, SIN Docker)
**Modelo: Opus · Esfuerzo: Alto**

Decisión tomada (investigada, ver §Anexo Kokoro): **nada de Docker.** Kokoro
corre en Python puro vía `kokoro-onnx` (ONNX Runtime, sin PyTorch). Docker
(kokoro-fastapi) queda descartado: en Windows exige admin + WSL2 + reinicio +
virtualización BIOS, imposible de preparar en silencio. `kokoro-onnx` = `pip
install` + descargar el modelo, cero admin, cero reboot — misma disciplina que
winocr/pypdf.

Pasos exactos:
1. Reemplazar el stub actual de instalación de Kokoro (que usa el paquete
   `kokoro` de **PyTorch**, riesgo de romper el torch de sentence-transformers)
   por `kokoro-onnx`:
   - Onboarding/Ajustes → Voz: opción "Voz local de máxima calidad (Kokoro)"
     con nota "se descarga ~80–300 MB una vez, no requiere nada más".
   - Al aceptar: hilo de instalación con `pip install kokoro-onnx soundfile`
     (salida capturada, estados idle/installing/done/failed — el patrón que ya
     existe para Kokoro y para modelos Ollama), + descarga del modelo
     `kokoro-v1.0.onnx` (usar la versión **cuantizada ~80 MB** por defecto) y
     `voices-v1.0.bin` a `%APPDATA%/Aithera/kokoro/`, con barra de progreso.
2. G2P: empaquetar `espeak-ng.exe` + `libespeak-ng.dll` + `espeak-ng-data`
   junto a la app (o usar `misaki[en]`/`misaki[es]` como diccionario primario
   con espeak-ng como fallback). **No** requiere que el usuario instale nada.
   Resolver el conocido "espeak not installed" en Windows apuntando la DLL por
   PATH/dir de trabajo. (Verificar en vivo con una frase con nombres propios.)
3. Motor `app/voice/kokoro_voice.py` (nuevo): carga perezosa del modelo ONNX
   (no en el arranque del backend), síntesis por frases (encaja con el TTS
   streaming existente), detección CPU (sin CUDA obligatorio). Registrarlo en la
   factoría/cadena de TTS por debajo de EdgeTTS (Kokoro solo si instalado y
   sano; si falla, EdgeTTS).
4. Degradación graciosa: sin Kokoro instalado, todo funciona con EdgeTTS. Con
   Kokoro instalado pero fallo de carga, fallback a EdgeTTS con log, nunca voz
   muda.
5. Tests: instalación mockeada (sin red), factoría elige Kokoro si "instalado",
   fallback si falla; sin romper `test_voice_*`.

**Criterio de cierre**: en un equipo sin Kokoro, la opción del onboarding lo
instala sola (pip + modelo, con progreso) sin Docker/admin/reboot; la voz local
suena; desactivarlo vuelve a EdgeTTS.

> **Cierre A·VOZ-5 (2026-07-24, Opus)** — hecho desde Cowork; commit desde
> Claude Code. **La pregunta clave ("¿hay problemas serios para que Kokoro
> funcione sin Docker?") — respondida y verificada en vivo: NO los hay.** La
> investigación del stub anterior (paquete `kokoro` de PyTorch) daba dos miedos
> reales: (a) conflicto de numpy y cadena `misaki→spacy→thinc→blis` que no
> compila en 3.13; (b) la fricción "espeak not installed" en Windows. **Ambos
> desaparecen con `kokoro-onnx` 0.5.0**, confirmado instalándolo de verdad en
> el sandbox:
> - **Deps alineadas, no en conflicto**: `kokoro-onnx` requiere `numpy>=2.0.2`
>   y `onnxruntime>=1.20.1` — exactamente lo que el backend YA corre (chromadb
>   trae onnxruntime, el stack va en numpy 2.x). Instala **sin torch, sin spacy,
>   sin misaki** (verificado: `find_spec('torch'|'spacy'|'misaki')` → None).
>   Python 3.10–3.13 ✅.
> - **espeak empaquetado**: la dep `espeakng-loader` trae la librería espeak-ng
>   como wheel por plataforma (**incluye `win_amd64`**, 9.2 MB). El usuario NO
>   instala espeak aparte. Y `kokoro-onnx` cablea la DLL+datos **por sí solo**
>   (su `tokenizer.py` llama a `EspeakWrapper.set_data_path`/`set_library` con
>   las rutas de `espeakng_loader`) → el "phontab not found" que aparece si se
>   hace a mano ya está resuelto dentro de la librería.
> - **G2P verificado en vivo** con una frase ES con nombres propios (criterio
>   del doc): "Hola Alejandro, soy Aithera. Nos vemos en Madrid el jueves." →
>   IPA correcta `ola alexandɾo soɪ aɪteɾa nos βemos en maðɾið el xweβes`.
>
> **Implementación**: (1) `app/voice/kokoro_voice.py` reescrito sobre
> `kokoro_onnx.Kokoro` — carga PEREZOSA (no en el arranque), thread-safe, modelo
> en `%APPDATA%/Aithera/kokoro/` (override `AITHERA_KOKORO_DIR`), `is_available()`
> = librería instalada **Y** modelo descargado, `synthesize_wav` → WAV 24 kHz
> mono; mapa voz→idioma; voces curadas (ES primero) + FR/PT. (2)
> `endpoints/voice.py`: instalador en 2 fases con seguimiento real —
> `pip install kokoro-onnx soundfile` + descarga del modelo **cuantizado int8
> ~80 MB** y voces ~28 MB con **barra de progreso** (estados
> idle/installing/downloading/done/failed), descarga atómica (.part→rename);
> `/kokoro/status` expone `library_installed`/`model_downloaded`/`progress`. (3)
> **Degradación graciosa**: `provider=kokoro` que falla (sin lib, sin modelo, o
> fallo de carga) **cae a EdgeTTS con log**, ya no devuelve 502 — nunca voz muda.
> (4) Frontend `VoicePanel.tsx`: comentario obsoleto ("Kokoro no soporta 3.13")
> corregido; el banner de instalación ya consumía `status.message` (que ahora
> lleva el progreso). **Tests**: `test_kokoro_voice.py` (17 — disponibilidad
> lib+modelo, mapa de idiomas, síntesis WAV con doble de kokoro-onnx, error
> paths, `/kokoro/status` en 3 estados, idempotencia del instalador, worker
> mockeado SIN red llega a `done`, y el fallback a EdgeTTS en `/synthesize` y
> `/synthesize/base64`). Suite de voz: **44 passed** (kokoro + voice + text_clean
> + elevenlabs), sin romper nada. `py_compile` limpio. `requirements.txt`
> actualizado (nota vieja de "Kokoro imposible" reemplazada por la realidad
> kokoro-onnx). **Pendiente de verificación EN VIVO en Windows** (criterio de
> cierre "la voz local suena"): la síntesis de audio real con el modelo
> descargado — en el sandbox el modelo (~108 MB) excede el throughput/tiempo por
> llamada, así que la inferencia ONNX end-to-end se prueba en la máquina del
> usuario (instalar desde Ajustes → Voz, sintetizar una frase, confirmar que
> suena y que al desactivar Kokoro vuelve EdgeTTS). Todo lo que era RIESGO
> (deps, numpy, G2P/espeak en Windows) está cerrado; lo que queda es la
> comprobación auditiva, que por naturaleza es en vivo.

---

## A·VOZ-6 — Pulido de latencia STT/TTS y verificación del win recuperado
**Modelo: Sonnet · Esfuerzo: Medio**

Con A·VOZ-2/3/4 el cuello de botella (classify) desaparece; aquí se recupera y
mide el resto del presupuesto (JWIKI `voice-latency-budget.md`).

Pasos exactos:
1. **Verificar** que el TTS streaming por frases (`Chat.tsx::beginSpeechStream`,
   VZ1 doc 26) sigue funcionando tras los cambios de A·VOZ-4 (la 1.ª frase debe
   sonar al ~30-40% del texto). Si el modo conversación cambió el flujo de
   stream, re-cablear el arranque de voz.
2. **STT**: exponer modelo `tiny` (39M) además de `base` para equipos flojos
   (Ajustes → Voz); mantener `fast` (beam_size=1). Opcional GPU si hay CUDA.
3. **VAD**: evaluar Silero VAD (end-of-speech 500→~100ms) frente al actual;
   solo adoptar si baja latencia real medida sin cortar al usuario.
4. **Profiling**: confirmar que `[voz-perfil]` (VZ5 doc 26) reporta stt /
   llm_1er_token / voz_suena y que el LLM ya no lleva el sobrecoste de classify.
5. Objetivo medido: TTFB conversacional **< 2s** en la máquina del usuario para
   una charla trivial; documentar el número real alcanzado.

**Criterio de cierre**: medición `[voz-perfil]` con TTFB < 2s en charla; la 1.ª
frase de voz suena antes de terminar de generar el texto.

> **Cierre A·VOZ-6 (2026-07-24, Opus)** — hecho desde Cowork; commit desde Claude
> Code. **Bug real del usuario cazado y corregido de raíz**: "preguntas simples
> como '¿cómo estás?' seguían entrando en misiones, se quedaban en 'analizando'
> y tardaban muchísimo". La auditoría del flujo `chat.py → orchestrator.handle_stream
> → tie.handle_stream` reveló DOS regresiones de latencia en el hot path del
> chat/voz que el fast-path de A·VOZ-2 no cubría del todo:
> 1. **"analizando" prematuro y engañoso**: `orchestrator.handle_stream` emitía
>    `("status","analizando")` SIEMPRE, ANTES de clasificar — así que hasta un
>    saludo mostraba "analizando" y parecía una misión. Y `tie.handle_stream`
>    lo emitía OTRA VEZ. **Fix**: el orquestador hace ahora `fast_precheck`
>    (0 LLM, exportado en el barrel) PRIMERO — la charla obvia se delega directa
>    al TIE con el intent ya resuelto, **sin "analizando" y sin tocar el
>    clasificador LLM**. `tie.handle_stream` mueve el `("status","analizando")`
>    a DESPUÉS del check de camino corto: solo las MISIONES lo muestran (donde
>    cubre la latencia real del planner). Un "¿cómo estás?" ya no dice
>    "analizando" — arranca a responder.
> 2. **Prefetch del MOS desperdiciado**: `tie.handle_stream` hacía
>    `await _prefetch_context(text)` (consulta al MOS, presupuesto 300 ms) ANTES
>    de decidir el camino corto, y el camino corto **lo descartaba** (arma su
>    propio contexto dentro de `NullRuntime.stream_task`/`build_system_prompt`).
>    Latencia muerta en CADA turno de charla. **Fix**: el prefetch se computa
>    solo cuando la ejecución ya es una misión (camino complejo/de fondo, que sí
>    lo consume). El camino corto no lo paga.
> **Profiling añadido** (para "verificar el win recuperado", el objetivo de esta
> sesión): `[tie-perfil] classify LLM: {ms}ms modelo=...` (en `intents.classify`
> — si un mensaje NO trivial tarda, se ve si es que el modelo de `classify` está
> mal enrutado: debería ser rápido/local) y `[tie-perfil] camino corto, primer
> token: {ms}ms` (en `_short_path_stream` — el TTFT real; si es alto en charla,
> el cuello es el modelo de CHAT, ya NO el TIE, que en ese camino no pone traza,
> status ni prefetch). Junto al `[voz-perfil]` del frontend (VZ5) dan el desglose
> completo STT / classify / primer token / voz. **UI de Voz** (petición del
> usuario, misma sesión): cada sistema de voz (EdgeTTS/ElevenLabs/Kokoro) muestra
> etiquetas "de un vistazo" (Gratis · Voces básicas · Sin descargas / Voces
> premium · Suscripción / Gratis · Voces avanzadas · Requiere descarga), cada
> una EN SU MARCO para no mezclarse, color por TIPO de rasgo (verde=gratis,
> ámbar=fricción, acento=nivel de voz, neutro=sin fricción), proveedor activo
> resaltado; se quitó "sin Docker" de los textos visibles y el tooltip obsoleto
> de Kokoro ("no soportado en Python 3.13"). Tests: `test_charla_obvia_no_clasifica_
> ni_muestra_analizando` (orquestador), `test_handle_stream_camino_corto_solo_
> tokens_sin_status` + `test_camino_corto_no_paga_prefetch_de_contexto` (TIE) +
> el test existente de no-reclasificar actualizado a un mensaje no-trivial. Suite
> tie/orchestrator: **106 passed** (72 + 34), `py_compile`/`tsc` limpios.
> **Pendiente de medición EN VIVO en Windows** (criterio de cierre): con el
> backend relanzado (código nuevo), mirar `[tie-perfil]`/`[voz-perfil]` en una
> charla real — TTFB < 2 s. **Nota importante de diagnóstico**: si tras estos
> cambios "¿cómo estás?" SIGUE lento en la máquina del usuario, el cuello ya NO
> es el TIE (código probado sin status/prefetch/misión en charla) sino el modelo
> de CHAT de la política MEL activa — el `[tie-perfil] camino corto, primer token`
> lo dirá; la acción sería enrutar CHAT a un modelo rápido/local en Ajustes →
> Inteligencia. Pasos 2 (STT `tiny`) y 3 (Silero VAD) del plan quedan como mejora
> incremental opcional, no bloqueante: el cuello estructural (classify/status/
> prefetch en el hot path) es lo que esta sesión eliminó.

---

## A·VOZ-7 — Contexto de sesión cacheado (no re-consultar el MOS cada turno)
**Modelo: Opus · Esfuerzo: Medio** — *(idea robada de Hermes Agent, ver Anexo competitivo)*

Origen: la investigación competitiva (Hermes Agent de Nous Research). Hermes
**congela su memoria en un snapshot una vez por sesión** y la renderiza como un
bloque estático en el system prompt para el resto de la sesión — a propósito,
para NO invalidar el caché de prompt del proveedor en cada turno. Cita textual
de su `AGENTS.md`: *"el caché de prompt por conversación es sagrado… todo lo que
mute el contexto pasado… multiplica el coste del usuario"*.

El problema en Aithera: `enricher.py` pide contexto al MOS en CADA turno del
chat (con presupuesto duro de 300 ms). En el camino corto conversacional eso es
(a) una consulta al MOS por mensaje que casi siempre devuelve lo mismo dentro de
una sesión, y (b) un system prompt que cambia turno a turno → invalida el caché
de prompt de los proveedores que lo soportan (Anthropic 90% descuento, etc.),
multiplicando coste y latencia del primer token.

Decisión tomada: en el camino corto (charla), cachear el contexto del MOS **por
sesión** (`session_id`), no por mensaje — refrescándolo solo cuando cambia de
sesión o pasa un TTL prudente. El presupuesto de 300 ms sigue siendo el tope de
la PRIMERA consulta de la sesión; los turnos siguientes reusan el snapshot.

Matiz importante (project_memory_should_never_skip, memoria del proyecto): el
timeout de 300 ms del M4 se marcó como parche, no como objetivo — esta sesión NO
lo elimina, pero sí reduce cuántas veces se paga, que es una mejora real sin
tocar la corrección. El contexto de una MISIÓN (camino complejo/acción directa)
NO se cachea así: cada nodo puede pedir tipos de memoria distintos (el enricher
ya tiene su propia caché de 60 s por (query, tipos) de T2) — esto es solo para
la charla, donde el contexto es estable dentro del hilo.

Pasos exactos:
1. En el camino corto (`_short_path`/`_short_path_stream` de A·VOZ-3, y el
   `build_system_prompt` que usan vía `NullRuntime`): resolver el contexto del
   MOS UNA vez por `session_id` y guardarlo (dict en memoria keyed by session_id,
   con TTL configurable, p.ej. `TIE_SESSION_CTX_TTL_S` default 600).
2. La primera consulta de la sesión respeta el presupuesto de 300 ms (igual que
   hoy); un HIT de caché de sesión no consulta el MOS ni espera nada.
3. Invalidación: al cambiar de sesión, al pasar el TTL, o si el usuario guarda
   algo en memoria a mitad de sesión (evento `memory.ingested`/`save_memory` →
   invalida el snapshot de esa sesión para que el nuevo dato entre en el
   siguiente turno — nunca dejar memoria fresca "invisible", C-1b/fiabilidad).
4. Métrica: `[voz-perfil] ctx-sesión HIT/MISS` para medir el ahorro real.
5. Tests: dos turnos de la misma sesión → 1 sola consulta al MOS; cambiar de
   sesión → nueva consulta; guardar en memoria a mitad → el siguiente turno
   refresca (la memoria nueva NO queda invisible).

**Criterio de cierre**: en una charla de varios turnos, el MOS se consulta 1 vez
por sesión (no por mensaje), medido por `ctx-sesión HIT`; una memoria guardada a
mitad de sesión aparece en el siguiente turno (no se pierde).

> **Cierre A·VOZ-7 (2026-07-24, Opus)** — hecho desde Cowork; commit desde Claude
> Code. Implementado como **superset SEGURO del "1 vez por sesión" literal**, por
> el "matiz importante" del propio plan (project_memory_should_never_skip): se
> cachea el contexto del MOS por sesión, pero con guardas que impiden que una
> memoria relevante quede fuera. **Implementación**:
> - `chat_service._mos_context_session(query, session_id, project_id)`: envuelve
>   la llamada real al MOS (`_mos_context_block`, presupuesto 300 ms intacto) con
>   una caché `_SESSION_CTX[session_id] = (query, ctx, expiry, mem_version)`. Un
>   turno es **HIT** (0 consultas al MOS, reusa el snapshot) solo si: no ha
>   expirado (TTL `TIE_SESSION_CTX_TTL_S`, default 600 s), la **versión de
>   escritura de memoria no cambió**, y el **tema de la consulta es el mismo**
>   (Jaccard ≥ 0.5 de tokens de contenido, `_same_topic`). Si algo de eso falla →
>   **MISS**: re-consulta y refresca. Emite `[voz-perfil] ctx-sesión HIT/MISS`.
> - `memory_router.write_version()` (NEW): contador monótono que sube en CADA
>   `store()` (usuario, agente, ingesta, resumen nocturno — el punto único de
>   escritura). Es lo que hace que una memoria guardada a mitad de charla entre
>   en el turno siguiente (la regla "memoria fresca nunca invisible", C-1b). Es
>   un CONTADOR, no un evento: funciona en contexto sync y no depende de que un
>   handler llegue a tiempo.
> - `session_id` enhebrado hasta `build_system_prompt` desde los 4 caminos de
>   chat: `answer()` (no-stream), `chat.py::/stream`, `NullRuntime.stream_task`
>   (el camino real del chat de Electron) y `NullRuntime.execute_task`. Solo la
>   **charla general** cachea así (con `session_id` y **sin** `project_id`): las
>   misiones usan el enricher por-nodo (su propia caché de 60 s de T2) y los
>   chats de proyecto no comparten el caché de charla (aislamiento C-1b intacto).
> **Por qué el superset y no el literal**: congelar el contexto de la sesión al
> PRIMER turno haría que, tras un "hola" (contexto casi vacío), una pregunta
> posterior "¿cómo va mi proyecto X?" reutilizara ese vacío y se saltara la
> memoria del proyecto — justo lo que el plan advierte que no debe pasar. Con la
> guarda de tema + versión, una charla de varios turnos SOBRE LO MISMO paga UNA
> consulta (el win real y medible: HITs consecutivos), y un cambio de tema o una
> memoria nueva vuelven a consultar (la corrección). El perfil del usuario
> (`_profile_block`, hechos deterministas) NO se cachea aquí — se lee entero cada
> turno, así que la identidad del usuario siempre está fresca. Tests:
> `test_session_context.py` (10 — HIT mismo tema/sesión = 1 consulta; MISS por
> cambio de sesión, cambio de tema, escritura en memoria, y TTL expirado; sin
> `session_id` o con `project_id` no cachea; unidad de `_same_topic`). Suite
> chat/tie/orchestrator: **75 passed** (+10 skip de ChromaDB del entorno).
> `py_compile` limpio. **Pendiente de medición EN VIVO en Windows** (criterio de
> cierre): con el backend relanzado, ver `[voz-perfil] ctx-sesión HIT` a partir
> del 2.º turno de una charla y confirmar que guardar algo en memoria a mitad
> aparece en el turno siguiente. **Beneficio esperado, además de menos consultas
> al MOS**: al no cambiar el bloque de memoria turno a turno, el prefijo del
> system prompt es estable → los proveedores con caché de prompt (Anthropic, etc.)
> dejan de invalidarlo cada turno, bajando coste y TTFT (la razón original de
> Hermes). Con esto, **el BLOQUE A (voz/conversación) queda completo** salvo las
> mejoras incrementales opcionales de A·VOZ-6 (STT `tiny`, Silero VAD).

---

## A·VOZ-8 — Idioma real y latencia de voz: causas raíz (2026-07-24, Opus)
**Modelo: Opus · Esfuerzo: Alto** — *(petición directa del usuario tras 7+ sesiones
de voz: "busca los motivos reales y soluciónalos de raíz, no parches")*

Dos quejas persistentes, auditadas hasta la causa raíz (no síntoma):

**(1) "El chat SIEMPRE responde en español (con acento del idioma elegido), y las
voces de prueba de otros idiomas leen español con acento".** Tres causas reales
distintas, las tres arregladas:
- **Directiva de idioma ineficaz** (causa del chat en español): I18N-9 SÍ inyectaba
  "responde SIEMPRE en English", pero (a) escrita EN ESPAÑOL y (b) enterrada tras un
  prompt 95% español (base + personalidad `_AITHERA_PROMPT` + capacidades, todo en
  español). Un modelo local (llama3, etc.) ancla al idioma dominante e ignora una
  orden suelta. **Fix**: `language.py::language_directive()` reescrita EN EL IDIOMA
  OBJETIVO ("You MUST write EVERY response in English…", "tu DOIS écrire…", "DEVES
  escrever…") y `build_system_prompt` la coloca LA PRIMERA del prompt. Verificado:
  el prompt empieza por `CRITICAL — RESPONSE LANGUAGE` / `CRITIQUE` / `CRÍTICO`.
- **STT forzado a español** (`Chat.tsx` bucle de conversación línea 592 hardcodeaba
  `transcribeVoice(blob, "es", …)`): al hablar en inglés, Whisper transcribía como
  español mal fonetizado. **Fix**: usa `uiLangRef.current` (idioma de interfaz), vía
  un ref para que el `useCallback` del bucle no quede con un idioma obsoleto.
- **Preview de voces siempre en español** (`VoicePanel`: `previewText: DEFAULT_PREVIEW`
  fijo): probar una voz francesa leía la frase ESPAÑOLA con acento francés — justo
  lo reportado. **Fix**: `previewForLang(lang)` — cada voz lee una frase de SU idioma
  (es/en/fr/pt/ja/zh).

**(2) "La voz va lenta tras 7 sesiones".** Dos causas estructurales reales:
- **I/O de memoria bloqueante y en serie en el hot path**: `build_system_prompt`
  llamaba `_preferences_block` (búsqueda ChromaDB SÍNCRONA, ~150 ms embebiendo la
  query) y `_profile_block` (lectura de BD síncrona) DIRECTAMENTE dentro de una
  función async — bloqueaban el event loop Y corrían en serie con la consulta al MOS.
  Cada turno pagaba la SUMA. **Fix**: `_memory_blocks_session` calcula los tres
  bloques con `asyncio.gather` y las lecturas sync van a `to_thread` — coste = MÁXIMO,
  no suma, y sin bloquear el loop. (Además unifica la caché por sesión de A·VOZ-7:
  el bundle entero se cachea, no solo el MOS; `_mos_context_session` → `_memory_blocks_session`).
- **La voz usaba el modelo PESADO de la política de calidad del usuario**: si el chat
  está en "custom→claude/opus" o un local lento, cada respuesta hablada tardaba
  segundos. El propio código ya sabía que "en la máquina del usuario el local barato
  tarda 100s+/paso" (por eso `TIE_TOOL_POLICY="speed"`). **Fix**: la respuesta de VOZ
  (`conversational=True`) se enruta por `VOICE_CHAT_POLICY` (default **"speed"**, el
  modelo más rápido MEDIDO de esa máquina) vía `policy_override`; el chat de TEXTO
  mantiene la política de calidad del usuario. `AgentTask.conversational` (append-only)
  lleva el flag desde el camino corto hasta `NullRuntime.stream_task`. Un modelo
  explícito del usuario (`model_hint`) siempre manda sobre la política de voz.

Tests: `test_voice_latency.py` (3 — voz usa política rápida, texto no, modelo
explícito manda) + `test_i18n_language.py` actualizado (directiva nativa por idioma,
prompt empieza por ella) + `test_session_context.py` migrado al bundle
`_memory_blocks_session`. Suite chat/tie/orchestrator/voz: **126 passed** (49 + 77),
`py_compile`/`tsc` limpios. Verificado en el sandbox: la directiva sale la primera y
en el idioma correcto en en/fr/pt. **Pendiente de medición EN VIVO en Windows**:
`[voz-perfil]` con la política de voz activa (esperado: `llm_1er_token` mucho menor
si su chat estaba en un modelo pesado), y confirmar que al elegir inglés/francés el
chat responde y la voz lee EN ESE idioma. **Honestidad sobre el límite**: si el
usuario NO tiene ningún modelo rápido conectado (solo un local lento y sin nube), la
latencia del propio modelo es un límite de hardware que ninguna optimización de
software elimina — pero el reparto a "speed" garantiza que se usa el más rápido
disponible, y el `[voz-perfil]` lo hará visible.

---

## A·VOZ-9 — Arreglo de RAÍZ: proyectos reales, self-operación, voz↔idioma (2026-07-24, Opus)
**Petición furiosa del usuario tras que A·VOZ-8 NO arreglara los problemas de fondo.**
Auditoría honesta de por qué "7+ sesiones y sigue roto": las sesiones optimizaron el
*overhead* del pipeline pero nunca cablearon dos huecos estructurales. Corregidos de raíz:

1. **Aithera inventaba proyectos ("Proyecto 1/2") en vez de ver los reales** (OT Saas,
   Waterquest, Quicky Dungeons…). CAUSA: el system prompt decía "conoces los proyectos
   del usuario" pero NUNCA se los inyectaba — el modelo los alucinaba desde memoria
   semántica vacía, o escalaba a una misión que se perdía buscando "código AZUL". FIX:
   `chat_service._workspace_block()` lee la tabla SQL `projects` (fuente de verdad del
   WPMS) y la mete SIEMPRE en el prompt, fresca cada turno (query barata, en hilo,
   paralela). Cabecera "NO inventes proyectos que no estén en esta lista".
2. **El clasificador NO conocía la tool `aithera`** (self-operación) y **el toolloop NO
   mostraba sus acciones al modelo** (`build_catalog` usaba `list_tools()` SIN
   `include_internal=True` — la tool estaba permitida pero invisible). Así, "crea un
   proyecto/agente/regla", "abre X", "cambia el idioma", "pon Minimax de modelo" no
   llegaban nunca a `aithera_tool`. FIX: (a) `build_catalog(include_internal=True)` — el
   cable que faltaba; (b) el clasificador conoce "aithera" y enruta las peticiones de
   self-operación al camino de acción directa (rápido); (c) `aithera_tool` gana
   `set_language` y `set_chat_model` (las dos que faltaban de la lista del usuario; el
   resto —proyectos/agentes/reglas/cron— ya existían).
3. **La voz no seguía al idioma** (acento portugués con español seleccionado). CAUSA:
   `/voice/defaults` devolvía la voz guardada SIN comprobar el idioma — una voz pt
   heredada se quedaba. FIX: si la voz guardada es de otro idioma (deducible en
   EdgeTTS/Kokoro), se reasigna a la del idioma actual; una voz propia del idioma o una
   de ElevenLabs (opaca/multilingüe) se conserva.

Tests: `test_projects_and_config.py` (11 — workspace block con proyectos reales, prompt
los incluye, toolloop muestra las acciones de aithera, clasificador conoce aithera,
`set_language` real, voz reasigna por idioma en 3 casos + detección de idioma de voz).
Suite tie/orquestador/memoria/voz/mel: **126 passed** (los 6 fallos de `test_new_tools`
son de `pyautogui`/desktop sin display, preexistentes y ajenos). `app.main` importa OK,
`tsc` limpio. Verificado en vivo (SQLite real): con OT Saas/Waterquest/Quicky Dungeons en
la BD, `build_system_prompt` y `aithera.list_projects` devuelven los REALES; `set_language`
cambia el Config; la voz portuguesa heredada se reasigna a española. **Método corregido**:
esta vez la verificación es DEL FLUJO (dato real → prompt/tool → resultado), no pieza a
pieza. **Límite honesto**: el cumplimiento del modelo (responder en el idioma, elegir la
tool correcta) depende del modelo activo; el prompt y el cableado ya son correctos, que era
lo que fallaba de raíz.

---

## A·VOZ-10 — Respuestas DETERMINISTAS de datos propios + acuse de misión (2026-07-24, Opus)
**El arreglo DEFINITIVO tras el segundo fallo reportado** ("Dime qué proyectos tengo" →
"no tengo acceso a la lista de proyectos", aun con el workspace inyectado en el prompt
de A·VOZ-9). Lección aceptada: **confiar en que el LLM lea bien el prompt NO es un
arreglo de raíz** — es el patrón que usan los asistentes de producción (Alexa/Siri/
las actions de GPT) el correcto: una pregunta sobre DATOS PROPIOS del sistema se
responde con SQL + plantilla, jamás con un LLM.

- **`app/tie/quick_answers.py`** (NEW): `try_answer(text)` — si el mensaje es un
  LISTADO claro sobre datos propios (proyectos / agentes / reglas / tareas, en
  es/en/fr/pt), responde DIRECTO de la BD: 0 LLM, 0 alucinación, instantáneo, en el
  idioma de la app (catálogo `strings.py`, claves `quick.*` en 4 idiomas).
  Conservador (mismo criterio que `fast_precheck`): exige sustantivo + indicador de
  pregunta, rechaza verbos de acción ("crea/abre/borra/renombra…" van al
  clasificador → `aithera_tool`), y ante la duda devuelve None. Cableado en los 3
  puntos de entrada: `orchestrator.handle_stream` (el camino real del chat, ANTES
  de clasificar), `tie.handle_stream` y `_run_pipeline` (Gateway/Telegram).
- **Acuse INMEDIATO de misión** (petición explícita): en modo texto, `_stream_body`
  emite YA `"Entendido, me pongo con ello: {goal}. Te cuento en cuanto lo tenga."`
  (clave `pipeline.ack_mission`, 4 idiomas) ANTES de ejecutar — tanto en acción
  directa como en el camino complejo. El chat NUNCA se queda mudo mientras una
  misión tarda minutos. (El modo conversación/voz ya tenía su acuse de A·VOZ-4.)
- **Paridad i18n reparada de paso**: las claves `conversation.*` (A·VOZ-4) faltaban
  en PT — añadidas; test de paridad del catálogo ahora pasa con las 4 lenguas
  idénticas en claves.

Tests: `test_quick_answers.py` (17 — 6 variantes de listado devuelven los proyectos
REALES; sin proyectos lo dice sin inventar; respuesta en idioma de la app; 7 frases
de acción NO disparan; el flujo REAL del orquestador responde sin llamar al
clasificador —monkeypatch que explota si se llama—, sin "analizando" y sin misión;
el acuse es el PRIMER texto de una misión). Regresión completa:
**126 passed** (quick + projects_config + tie_handle + orchestrator_chat +
boundaries + i18n_strings + orchestrator + gateway) + 45 (voice_latency +
session_context + i18n_language + tie_contracts). `app.main` importa OK.
Verificado end-to-end con datos reales (OT Saas/Waterquest/Quicky Dungeons en BD):
el mensaje EXACTO del usuario ("Dime qué proyectos tengo.") devuelve los 3 con
estado y progreso, instantáneo. Un test de A·VOZ-6 se actualizó (su mensaje de
ejemplo "enséñame el estado del proyecto Aithera" ahora lo cubre el fast-path
determinista — comportamiento deseado, mensaje del test cambiado a uno de email).

---

## A·VOZ-11 — Las acciones NUNCA degradan a charla, y Aithera nunca finge (2026-07-25, Opus)
**Fallo real con log del usuario.** Creó el proyecto "Cordyceps" bien, pero al pedir
"crea en este proyecto una milestone MVP y un agente Investigador" Aithera **dijo que
lo había hecho y era falso**; al preguntarle, **volvió a mentir** tirando del historial.
El log da la causa exacta:

```
17:35:20 classify LLM: 5781ms modelo='llama3'
17:35:20 [intents] sin JSON parseable, fallback conversational
```

**Causa raíz (tres defectos encadenados, los tres arreglados de forma GLOBAL):**

1. **Las acciones dependían de que un LLM frágil produjera JSON.** El clasificador
   (llama3 local) falló → el fail-safe `conversational` (correcto para charla) tiró la
   intención de ACCIÓN → el turno acabó en chat **sin herramientas** → el modelo fingió.
   **FIX**: `app/tie/action_intent.py` (NEW) — detector DETERMINISTA (0 LLM) de "esto es
   una orden sobre Aithera": verbo de acción (es/en/fr/pt, por prefijo, cubre conjugaciones
   y enclíticos: "créame", "ponle", "asígnale") **+** sustantivo de dominio (proyecto,
   hito/milestone, tarea, agente, regla/recordatorio, idioma, modelo). Cableado como RED DE
   SEGURIDAD en `intents.classify`, en **los 4 caminos** donde se perdía la intención:
   sin JSON · error del proveedor · excepción · **y clasificación floja** (el LLM dice
   "conversational" para una orden, o acierta el tipo pero olvida la tool `aithera` → se
   corrige/añade sin pisar lo que sí detectó). **No es un parche**: los sustantivos se
   mapean a las acciones del catálogo y `assert_covers_catalog()` + un test verifican la
   cobertura CONTRA el catálogo real — si mañana se añade una acción a `aithera_tool` sin
   mapear, **el test falla** en vez de degradar en silencio. El planner, el grafo, el MEL,
   el orquestador y el multi-objetivo siguen intactos: la versatilidad no se toca.
2. **El chat podía fingir ejecución e inventar datos.** **FIX**: `DEFAULT_SYSTEM_PROMPT`
   gana dos reglas absolutas — *"NUNCA FINJAS HABER ACTUADO"* (con los ejemplos exactos
   prohibidos: "he creado", "ya está hecho", "creo la milestone"…, y la instrucción de
   decir la verdad si la ejecución no se pudo hacer) y *"NO INVENTES DATOS"* (solo existen
   los proyectos/agentes/reglas del contexto; **no** dar por hecho algo porque se hablara
   antes en la conversación — exactamente la segunda mentira del log).
3. **El bucle de herramientas no podía ejecutar "en ESTE proyecto".** No sabía a qué
   proyecto se refería ni tenía los IDs (`create_milestone` exige `project_id`), así que
   agotaba iteraciones. **FIX**: `_direct_action_path` inyecta en `task.context` (a) el
   workspace REAL con IDs y (b) los últimos turnos de la conversación → resuelve
   referencias ("este proyecto", "ese agente") sin adivinar. Genérico para cualquier
   acción, presente o futura. `session_id` enhebrado hasta ahí (también en misiones de fondo).

**Verificado reproduciendo el fallo exacto**: con el clasificador devolviendo texto no-JSON
(el caso del log), la orden ahora sale como `EXECUTE` + `requires_tools=['aithera']` +
`is_direct_action=True` — va a las herramientas, ya no a charla. Y el bucle recibe
`[id 1] Cordyceps` + el historial. Tests: `test_action_intent.py` (36 — cobertura del
catálogo, 17 órdenes detectadas, 9 mensajes de charla/listado que NO se fuerzan, los 4
caminos de fallo del clasificador, corrección de tipo, tool olvidada, contra-prueba de
charla intacta, contexto real en el bucle, prompt anti-mentira). Regresión: **76 passed**
(action_intent + quick_answers + projects_config + checkpoints) + **112** (con tie_handle,
orchestrator_chat, boundaries) + **108** (contracts, i18n, session_ctx, voice_latency,
orchestrator, gateway, audit_s2). `app.main` importa. Nota: un fallo de `test_checkpoints`
era `apscheduler` ausente del sandbox — instalado, **12/12 passed**.

---

# BLOQUE B — NAVEGACIÓN WEB BÁSICA (pre-1.0)

> Origen: revisión de Mark-L. Su fiabilidad en YouTube/música viene de **NO
> automatizar**: abre la URL en el navegador real del usuario. Robamos eso.

## B·WEB-1 — Abrir medios/URL en el navegador por defecto ⭐
**Modelo: Sonnet · Esfuerzo: Bajo** — *(el mayor impacto por el menor cambio)*

Decisión tomada: reproducir un medio NO necesita un navegador pilotado; necesita
abrir una URL en el navegador real (logueado, con autoplay y cookies ya
resueltas). Playwright headless lo bloquea Google; esto lo esquiva.

Pasos exactos:
1. Nueva acción en `browser_tool` (o `media`): `open_in_default_browser(url)` —
   Windows `os.startfile(url)` (o `subprocess start ""`), con validación de que
   es http(s). Devuelve `{ok, url}`.
2. Acción de conveniencia `play_media(query)` — usa `search` (Brave/SerpAPI, que
   YA tenemos y es fiable) para resolver la 1.ª URL de vídeo/canción, y la abre
   con `open_in_default_browser`. **No** usar `browser.google_search` (Google
   bloquea headless — limitación conocida) ni scraping por regex (frágil, es lo
   que hace Mark-L; nosotros usamos API de búsqueda de verdad).
3. Enrutado: en `_direct_action_tools`/prompt del toolloop, para intenciones de
   "reproduce / pon / abre [medio/URL]", preferir `open_in_default_browser` /
   `play_media` sobre el contexto Playwright. El clasificador ya marca
   `requires_browser`; añadir el matiz "reproducir/abrir → navegador real".
4. Permisos: `open_in_default_browser` cae bajo `browser.use` (abre una web) —
   sin confirmación adicional más allá del permiso ya existente.
5. Tests: `play_media` mockeando `search` → resuelve URL → llama a
   `open_in_default_browser` (sin abrir nada real en CI). Verificación en vivo:
   "pon [canción] en YouTube" abre el vídeo en el Chrome real y suena.

**Criterio de cierre (en vivo)**: "pon X canción" reproduce de verdad en el
navegador real, sin muro de cookies que frene la misión.

---

## B·WEB-2 — Clic por visión como fallback (screenshot → modelo → coordenadas)
**Modelo: Opus · Esfuerzo: Alto**

Decisión tomada: cuando los selectores DOM fallan, localizar el elemento por
visión. Técnica de Mark-L (`computer_control._screen_find`) pero enrutada por
nuestro MEL (capacidad `vision`) y con nuestros permisos.

Pasos exactos:
1. Activar la capacidad `vision` del MEL (hoy reservada en `contracts.py`):
   darla de alta en catálogo/políticas, asignar un modelo multimodal disponible
   (Gemini Flash / GPT multimodal / un local con visión). Fail-closed si no hay
   modelo con visión: la acción devuelve error claro, no inventa coordenadas.
2. `desktop_tool` (o `browser_tool`): acción
   `find_and_click(description)` → screenshot → `mel.complete(capability=vision,
   image=…, prompt="dame las coordenadas x,y del elemento: <desc>")` → parsear
   `"x,y"` → clic. Reusar `desktop.click` (que YA pide confirmación / gate).
3. Recomendado (más robusto que píxeles crudos, patrón browser-use/Skyvern):
   **set-of-mark** opcional — si hay DOM, numerar los elementos interactivos y
   pasar el screenshot con las marcas; el modelo elige por índice. En apps sin
   DOM (escritorio), caer a coordenadas puras.
4. Uso: el toolloop lo invoca como fallback cuando `smart_click` por DOM no
   encuentra el elemento (no como primera opción — el DOM es más barato y
   preciso cuando existe).
5. Límites conocidos a respetar: multi-monitor / escala de pantalla (documentado
   en Mark-L como frágil); registrar la resolución/escala en el prompt.
6. Tests: con un screenshot fijo y un MEL de visión fake que devuelve "x,y",
   `find_and_click` parsea y llama a `desktop.click` con esas coords; sin modelo
   de visión → error claro.

**Criterio de cierre**: en una web donde el DOM no basta, Aithera localiza y
clica el elemento correcto por visión (verificado en vivo en 1-2 casos reales).

---

# BLOQUE C — WEB PROFUNDA / AGENTIC (mayormente post-1.0)

> Para lo que el usuario quiere de verdad a medio plazo: comprar en
> Carrefour/Mercadona, pedir cita en Hacienda/dentista, descargar un juego de
> gogunlocked, buscar la API key de una IA nueva, investigación profunda en
> foros. Esto requiere consistencia y precisión que la navegación básica no da.
>
> **Referencia investigada** (2026): [**browser-use**](https://github.com/browser-use/browser-use)
> (89.1% WebVoyager, 93K★, YC W25 — el estándar OSS) y
> [**Skyvern**](https://github.com/Skyvern-AI/skyvern) (85.85%, líder en
> rellenar formularios). Ambos usan un **bucle agentic DOM+visión con
> set-of-mark**: extraen los elementos interactivos del DOM, los indexan,
> muestran un screenshot con cajas numeradas, y el modelo elige por índice +
> acción. Es la clave de su fiabilidad en flujos multi-paso.

## C·WEB-3 — Spike de decisión + bucle agentic de navegación
**Modelo: Opus · Esfuerzo: Muy Alto**

Decisión tomada (para que el ejecutor no decida): **construir un bucle agentic
propio y ligero sobre nuestro `browser_tool` (Playwright + perfil real) copiando
la técnica set-of-mark de browser-use**, en vez de integrar browser-use como
dependencia. Motivo: browser-use arrastra su propio stack LLM (langchain/su
router) que **pelearía con nuestro MEL, nuestros permisos (A3b) y nuestra traza
(TIE)** — perderíamos la arquitectura que nos diferencia. Copiamos la idea, no
el paquete.

Pasos exactos:
1. Spike corto (dentro de la misma sesión): leer cómo browser-use construye el
   "DOM state" (elementos interactivos + índices) y el prompt set-of-mark
   (`browser_use/dom/` y su system prompt). Anotar el formato exacto.
2. `browser_tool`: acción `page_state()` que devuelve, para la pestaña activa:
   lista de elementos interactivos (rol, texto, índice) + screenshot con marcas
   numeradas (overlay dibujado con JS/Playwright). Reusa el perfil persistente y
   el `_dismiss_consent` que YA tenemos (ventaja sobre Mark-L, que no maneja
   cookies).
3. Bucle agentic (`app/tie/webloop.py` o extensión de `toolloop.py`): observar
   (`page_state`) → el modelo elige `{índice, acción, texto?}` → ejecutar
   (`click`/`type`/`select` por índice) → repetir hasta objetivo o límite de
   pasos. Enrutado por MEL (capacidad `agentic` rápida para elegir, `vision`
   cuando haga falta mirar). Checkpoints del TIE en pasos sensibles (pago,
   envío de formulario) reusando el ApprovalGate.
4. Autoridad y seguridad: acciones sensibles (comprar, pagar, enviar, confirmar
   cita) SIEMPRE por el ApprovalGate salvo Autónomo; nunca introducir
   credenciales/pagos automáticamente (política del proyecto — el usuario los
   pone). Documentar esta frontera explícitamente.
5. Tests sin red (dobles de Page/Context, como `test_audit_s3_browser.py`):
   `page_state` produce índices+marcas; el bucle elige por índice y ejecuta;
   un paso sensible abre gate.

**Criterio de cierre**: un flujo multi-paso de prueba (p.ej. buscar un producto
y llegar hasta el carrito **sin** confirmar la compra) se completa por índices
de forma repetible en un sitio real de prueba.

## C·WEB-4 — Casos de uso reales sobre el bucle agentic
**Modelo: Opus · Esfuerzo: Alto** (varias sub-sesiones, una por caso)

Sobre C·WEB-3, cablear los casos concretos que pidió el usuario, cada uno como
una verificación en vivo con su checkpoint de seguridad:
- **Compra** (Carrefour/Mercadona): buscar productos, añadir al carrito;
  **parar en el pago** (gate obligatorio, el usuario paga).
- **Citas** (Hacienda/dentista): rellenar el formulario multi-paso; **parar
  antes de confirmar** (gate).
- **Descargas** (gogunlocked u otros): navegar hasta el enlace real y pasar a
  `download_tool`; avisar de fuentes no confiables (política de seguridad — no
  ejecutar lo descargado).
- **Buscar API key de una IA nueva**: navegar a la doc/consola del proveedor,
  localizar dónde se genera; **no** teclear credenciales (el usuario las
  introduce).
- **Research profundo en foros**: buscar dentro de un foro/sitio sobre un tema,
  leer hilos, sintetizar (reusa los patrones de deep-research + el bucle
  agentic para paginar/entrar en hilos).

Cada caso: un test de humo del flujo (mock) + una verificación en vivo
documentada, respetando SIEMPRE los gates de acción sensible.

**Criterio de cierre**: al menos compra-hasta-carrito y research-en-foro
verificados en vivo, con los gates disparando en los puntos sensibles.

---

## Resumen de sesiones

| Sesión | Bloque | Objetivo | Modelo | Esfuerzo | Pre-1.0 |
|---|---|---|---|---|---|
| A·VOZ-1 | Voz | Retirar eSpeak, EdgeTTS base | Sonnet | Bajo | ✅ |
| A·VOZ-2 | Voz/Orq | Pre-clasificador barato (charla sin LLM) | **Opus** | Medio | ✅ **prioritario** |
| A·VOZ-3 | Voz/Orq | Charla no crea misión/traza | Sonnet | Medio | ✅ |
| A·VOZ-4 | Voz/Orq | Misiones en 2.º plano + reporte async | **Opus** | Alto | ✅ **prioritario** |
| ✅ A·VOZ-5 | Voz | Kokoro-onnx opcional (sin Docker) | Opus | Alto | ➖ opcional |
| ✅ A·VOZ-6 | Voz | Pulido STT/TTS + medir TTFB<2s | Sonnet | Medio | ✅ |
| ✅ A·VOZ-7 | Voz/Orq | Contexto de sesión cacheado (no re-consultar el MOS cada turno) | **Opus** | Medio | ✅ |
| B·WEB-1 | Web | Abrir medios/URL en navegador real ⭐ | Sonnet | Bajo | ✅ **prioritario** |
| B·WEB-2 | Web | Clic por visión (fallback) | Opus | Alto | ✅ |
| C·WEB-3 | Web+ | Bucle agentic DOM+visión (set-of-mark) | Opus | Muy Alto | ➖ post-1.0 |
| C·WEB-4 | Web+ | Casos reales (compra/citas/descargas/research) | Opus | Alto | ➖ post-1.0 |

**Ruta crítica de latencia (hazlo primero)**: A·VOZ-2 → A·VOZ-3 → A·VOZ-4.
Con eso la conversación por voz vuelve a ser fluida. B·WEB-1 es el otro
quick-win de alto impacto. El resto se escalona.

---

## Anexo — Kokoro / Docker (investigación, hechos verificados)

- **Docker NO es necesario.** Kokoro corre en Python puro con
  [`kokoro-onnx`](https://pypi.org/project/kokoro-onnx/) (ONNX Runtime, sin
  PyTorch). `pip install kokoro-onnx` + modelo `kokoro-v1.0.onnx` (~300 MB, o
  ~80 MB cuantizado) + `voices-v1.0.bin`. Python 3.10–3.13 (nuestro backend es
  3.13 ✅).
- **Docker en Windows es inviable en silencio**: exige admin (UAC), WSL2
  (`wsl --install` → reinicio), virtualización en BIOS y licencia comercial.
  El `--quiet --accept-license` sigue necesitando admin + WSL2 + reboot.
- **Matiz G2P**: Kokoro necesita grafema→fonema. `misaki[en]`/`misaki[es]`
  (diccionario Python) con `espeak-ng` como fallback (DLL + datos
  **bundleables**, NO el motor de voz eSpeak que retiramos). Hay una fricción
  conocida en Windows ("espeak not installed") que se resuelve empaquetando la
  DLL — manejable, sin que el usuario instale nada.
- El stub actual de Aithera usa el paquete `kokoro` de **PyTorch** → riesgo de
  romper el torch de sentence-transformers/ChromaDB (mismo miedo que easyocr).
  `kokoro-onnx` lo elimina de raíz.

Fuentes: [kokoro-onnx PyPI](https://pypi.org/project/kokoro-onnx/) ·
[thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) ·
[Kokoro-82M ONNX (HF)](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX) ·
Docker Desktop [unattended install (roadmap #307)](https://github.com/docker/roadmap/issues/307).

## Anexo — Qué robamos de Mark-L (y qué no)

- ✅ **Abrir medios/URL en el navegador real** (B·WEB-1) — su truco más útil.
- ✅ **Clic por visión** screenshot→modelo→coords (B·WEB-2) — su
  `computer_control`, pero por nuestro MEL.
- ❌ Su forma de hacer Kokoro (PyTorch en caliente) — usamos kokoro-onnx.
- ❌ Su discovery de YouTube por regex — usamos API de búsqueda (Brave/SerpAPI).
- ❌ Su ausencia de permisos/planner/memoria — mantenemos ApprovalGate + TIE +
  MOS, que son nuestra ventaja.
- ⚠️ Su voz full-duplex (Gemini Live) da baja latencia pero ata a un proveedor
  — en contra de nuestra filosofía multi-proveedor; seguimos con streaming por
  etapas + barge-in.

---

## Anexo — Comparativa competitiva: OpenJarvis · OpenClaw · Hermes Agent (2026-07-24)

Investigación verificada con DATOS PRIMARIOS (API de GitHub, código fuente crudo
vía `raw.githubusercontent.com`, no resúmenes de terceros) de los tres sistemas
"Jarvis-like" OSS más usados, además de Mark-L. **Este anexo es la fuente del
"por qué" de las decisiones de roadmap derivadas** (ver §"Decisiones de roadmap"
abajo); doc 03 y doc 27 las colocan en su versión, apuntando aquí.

**Cifras verificadas hoy** (recontadas, no las de la JWIKI a ciegas):
OpenClaw 383.989★ (licencia "Other"/NOASSERTION, no MIT puro pese al marketing),
Hermes Agent 219.802★ (MIT; la única cifra no auditable del todo — ratio
fork/star normal y 7.303 archivos con SECURITY.md serio argumentan contra que
sea humo), OpenJarvis 7.893★ (Apache-2.0, arXiv 2605.17172, el más "papers-real").

**El hallazgo central**: NINGUNO de los tres tiene planificador/grafo. Los tres
—independientemente— resuelven "cómo ejecuta una tarea" con un **bucle plano
ReAct** (el LLM decide turno a turno, sin DAG, sin checkpoint por nodo, sin gate
a nivel de plan). Un análisis académico forense de OpenClaw (arXiv 2604.05589)
lo critica por "descomposición de tareas limitada" y "pérdida de continuidad en
procedimientos multi-paso" — justo lo que el TIE de Aithera resuelve. **La
orquestación de Aithera (planner→DAG validado→executor con checkpoints/gates/
kill-switch/recovery) es objetivamente más rigurosa que la de los tres, según
sus propios análisis externos.** No es un área a mejorar: es nuestra ventaja.

**Dónde Aithera ya va por delante** (confirmado, no imitar): muro de cookies
(3 capas aprendidas — ninguno lo resuelve así; OpenJarvis ni lo maneja), postura
de seguridad conservadora (OpenClaw tiene historial público malo: auditoría de
512 vulns, exfiltración confirmada por Cisco, prohibido en China, incidente
"MoltMatch"), y el MEL eligiendo modelo por capacidad MEDIDA (nadie más lo hace).

**Qué SÍ merece robar** (cada uno con su decisión de roadmap ya tomada):

| De | Idea | Dónde va | Nota |
|---|---|---|---|
| Hermes | Congelar contexto de memoria por SESIÓN (no por turno) para no invalidar el caché de prompt | **A·VOZ-7** (este doc) | cita: "el caché de prompt es sagrado" |
| Todos | Instalador un-comando + auto-start + onboarding hardware-aware | **V1.0 MVP-beta** (ya planeado, doc 27 B1-B4) | los tres lo tienen; valida la prioridad, no cambia el plan |
| OpenClaw/Hermes | Sandboxing REAL de ejecución (Docker/contenedor) para shell/desktop/browser | **V1.4** (hardening antes de v1.5) | nuestra whitelist es más débil en profundidad; 2 de 3 lo tratan como imprescindible |
| OpenClaw/Hermes/OJ | 2 canales más del Gateway (Discord/WhatsApp) | **V1.4** (post-1.0) | nuestro `ChannelAdapter` ya está pensado para esto |
| Hermes | `/learn`: el agente redacta su propio `SKILL.md` desde conversación/URL/notas | **V1.1 LLL** (doc 09/15) | idea concreta de implementación del LLL, no un pivote |
| Hermes | "Narrow waist": UN contrato `provider+registry+plugin` para TODO lo pluggable (modelos/voz/navegador/memoria/canales), no solo modelos | **V1.3** (con Hermes, su ejemplo) | refactor arquitectónico; Hermes es el caso de uso que lo justifica |
| OpenClaw | Memoria humano-legible/editable (tipo `MEMORY.md`) | **V1.4** (retoque MOS/UX) | extiende `memory/profile.py` (ya visible en Ajustes) hacia legibilidad plena |
| OpenClaw/Hermes/OJ | MCP cliente+servidor (interop) | **V1.2** (YA planeado, doc 27 C1/C2) | la comparativa confirma que es el estándar de interop del sector |

**Qué NO copiar** (con evidencia): el bucle plano de los tres (nuestro TIE ya es
superior, dicho por sus propios análisis); la postura "cooperativo, no
adversarial" de OpenClaw sin red de contención real (es el patrón detrás de sus
incidentes); el "self-evolving" de Hermes tal cual (solo la Fase 1 funciona y
exige revisión humana — aspirar, no replicar ya).

---

*Creado 2026-07-23 · comparativa competitiva añadida 2026-07-24. Fundado en:
`app/tie/pipeline.py`/`intents.py`/`contracts.py`
(código real), JWIKI `08_VOICE/` + `01_LANDSCAPE/`, revisión del repo Mark-L, y
búsqueda web verificada (Kokoro/Docker, browser-use/Skyvern). Las decisiones
están tomadas para que cada sesión solo ejecute.*
