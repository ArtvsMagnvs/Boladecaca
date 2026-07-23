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

## A·VOZ-1 — Retirar eSpeak, garantizar EdgeTTS como base
**Modelo: Sonnet · Esfuerzo: Bajo**

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

## A·VOZ-2 — Pre-clasificador barato: la charla trivial NO paga LLM
**Modelo: Opus · Esfuerzo: Medio** — *(el arreglo de latencia, parte 1)*

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

## A·VOZ-3 — El camino corto conversacional NO crea misión
**Modelo: Sonnet · Esfuerzo: Medio** — *(arreglo de latencia, parte 2 + UX)*

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
| A·VOZ-5 | Voz | Kokoro-onnx opcional (sin Docker) | Opus | Alto | ➖ opcional |
| A·VOZ-6 | Voz | Pulido STT/TTS + medir TTFB<2s | Sonnet | Medio | ✅ |
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

*Creado 2026-07-23. Fundado en: `app/tie/pipeline.py`/`intents.py`/`contracts.py`
(código real), JWIKI `08_VOICE/` + `01_LANDSCAPE/`, revisión del repo Mark-L, y
búsqueda web verificada (Kokoro/Docker, browser-use/Skyvern). Las decisiones
están tomadas para que cada sesión solo ejecute.*
