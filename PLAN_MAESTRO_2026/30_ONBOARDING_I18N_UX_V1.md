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
| **OB-1 ✅** | Detección de "primera vez" (flag en Config) + pantalla de bienvenida (idioma → hardware → modelo → voz), llamando a los endpoints que ya existen. Auto-selecciona lo recomendado; el usuario confirma o cambia. | **Opus** | **Alto** |
| **OB-2 ✅** | Instalación de Ollama guiada si falta (detecta, enlaza a la descarga, espera) + descarga del modelo recomendado con barra de progreso (reusa `/install/status`). Todo dentro del onboarding, sin salir. | **Opus** | **Alto** |

> **✅ OB-1 + OB-2 hechos (2026-07-22, Fable 5)** — verificados por `tsc`/`py_compile`;
> pendiente prueba en vivo en Windows (escaneo real de GPU, voz sonando, descarga de
> Ollama con progreso). Backend: router `app/api/endpoints/onboarding.py`
> (`/status`·`/complete`·`/reset`, estado key-value en `Config`, sin migración) +
> `GET /local-models/runtime` (chequeo ligero de Ollama). Frontend:
> `components/onboarding/WelcomeOverlay.tsx` (asistente de 4 pasos —idioma·hardware+
> modelo·voz·instalación—, auto-selección de lo recomendado por el escáner, su propia
> copia en ES/EN/FR/PT que NO es el i18n global de I18N-1), montado en `AppLayout`
> (se auto-decide si mostrarse; caché `aithera.onboarded` en localStorage + fuente de
> verdad en BD). Paso 4: si falta Ollama → enlace de descarga + reintento; si está →
> `POST /install` + sondeo de `/install/status` con barra de progreso; al terminar
> `setLocalModelEnabled(tag,true)` (deja el modelo listo para el MEL, no solo en
> disco). "Repetir bienvenida" en Ajustes → Sistema.

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
| **I18N-1 ✅** | Framework: `store/useI18n.ts` + `locales/*.json` + hook `t()`; selector de idioma (onboarding + Ajustes); persistencia; `app_language` en Config (ya lo lee `/api/voice/defaults`). | **Opus** | **Alto** |

> **✅ I18N-1 hecho (2026-07-22, Fable 5)** — verificado por `tsc` (exit 0);
> pendiente prueba en vivo (cambiar idioma y ver Sidebar/tabs traducirse).
> `store/useI18n.ts` (zustand, CERO dependencia nueva): `Lang` es/en/fr/pt,
> `LANGUAGES`, `translate()` puro (fallback idioma→es→clave, interpolación
> `{var}`), hook REACTIVO `useT()`, `setLang()` persiste en localStorage
> (`aithera.lang`) + sincroniza `Config.app_language` (best-effort) + IIFE de
> reconciliación de arranque (toma el `app_language` del backend si nunca se
> guardó local). Locales `i18n/locales/{es,en,fr,pt}.json` sembrados con
> `common.*` + `language.*` + `nav.*` + `settings.tab.*` (base para I18N-2/3;
> migración INCREMENTAL — claves ausentes caen a español, nunca rompen).
> `components/LanguageSelector.tsx` (reutilizable) en Ajustes → Sistema.
> **Demostración del framework**: Sidebar migrado a `labelKey`+`useT()` (nav
> completa + "Configuración"). `main.tsx` importa el store al arranque.
> Onboarding (OB-1) fija el idioma global al terminar. El grueso de pantallas
> (Chat/Workspace/Misiones/Email/Voz/Agentes/Ajustes internos) es I18N-2/3.
| **I18N-2 ✅ (parcial, ver nota)** | Traducir el núcleo: onboarding, Ajustes (todas las secciones, incl. explicaciones Google/Telegram), Sidebar, Hub. ES→EN/FR/PT. | **Sonnet** | **Medio** |

> **✅ I18N-2 hecho — Hub completo + tab-rail de Ajustes + Conexiones
> (2026-07-22, Fable 5)**, verificado por `tsc` (exit 0). `Hub.tsx` migrado
> ÍNTEGRAMENTE a `t()` (paneles Proyectos/Tareas/Agentes/Eventos/Chat/Email/
> Memoria, barra de estado inferior, `coreStateLabel`/`formatEventDate`
> convertidas a recibir `t`); ~90 claves `hub.*` nuevas en los 4 locales.
> Ajustes: tab-rail (`settings.tab.*`, ya sembradas en I18N-1) + pestaña
> Conexiones (títulos/descripciones de Google, Búsqueda web y Telegram — lo
> que el alcance original pedía explícitamente). **Nota de alcance honesta**:
> el resto de Ajustes (secciones internas de IA y Modelos/Permisos/Voz/HUB
> Visual/Memoria/Sistema — Settings.tsx tiene 2716 líneas) NO se migró en
> esta pasada; es deliberadamente el resto de I18N-2/I18N-3 (doc 30 ya lo
> preveía como trabajo incremental multi-sesión, no de una sola vez). El
> onboarding (OB-1) ya tenía su propia copia en los 4 idiomas desde antes.

| **I18N-2b** ✅ (2026-07-22) | Cierra el hueco de I18N-2: secciones internas de Ajustes que se quedaron sin sesión asignada (IA y Modelos, Permisos, Voz, HUB Visual, Memoria, Sistema — encabezados/descripciones/botones principales). No estaba nombrada en I18N-3/I18N-4. | **Sonnet** | **Medio** |

> **I18N-2b completado (2026-07-22)**: ~70 claves nuevas (`settings.ia.*`,
> `settings.permisos.*`, `settings.voz.*`, `settings.hub.*`,
> `settings.sistema.*`, `settings.memoria.*`) en los 4 locales. Migrado con
> `tr()`: pestaña IA y Modelos (estado del sistema, "Modelos locales —
> descarga e instalación", "Proveedores de IA" + los 2 marcos "En tu
> equipo"/"En la nube", badges de proveedor Activo/En pausa/Comprobando/
> Activar/Editar/Configurar/Modelo/Modelos:/Sin API key, toggle "Usar {label}
> en el enrutado", cabecera de Inteligencia); pestaña Permisos (cabecera);
> pestaña Voz (Voces + ElevenLabs); pestaña HUB Visual (Apariencia con
> Oscuro/Claro + hints, Presencia visual); pestaña Sistema (escáner de
> hardware, Configuración local con las 4 líneas, Asistente de bienvenida
> incl. botón "Repetir bienvenida"); pestaña Memoria completa (estadísticas,
> formulario de añadir preferencia con placeholders, lista de preferencias,
> perfil destilado "Lo que Aithera sabe de ti", borrar historial). **Alcance
> honesto**: se dejó en español, a propósito, el contenido MUY dinámico o con
> JSX embebido (p.ej. "Política **X** — Chat: **Y**" y "Se cambia en
> **Inteligencia**..." del estado de IA, el párrafo explicativo + aviso de
> Claude Code CLI) — exige restructurar la interpolación con componentes, no
> solo texto; queda para una pasada de pulido, no bloquea el resto de I18N-3.
> Los 4 sub-componentes grandes (`LocalModelsSettings`, `LocalProviderModels`,
> `IntelligenceSettings`, `VoicePanel`, `ElevenLabsSettings`,
> `AvcsPerformanceSettings`, `SystemScanPanel`, `PermissionsSettings`)
> mantienen sus propios textos internos en español — cada uno es un
> mini-proyecto de traducción en sí mismo, deliberadamente fuera de esta
> sesión (degradación graceful, nunca roto). Verificado con `tsc --noEmit`
> (EXIT=0) y validación JSON de los 4 locales.
| **I18N-3** ✅ (2026-07-22, parcial, ver nota) | Traducir el resto: Chat, Workspace, Misiones, Automatización, Email, Voz, Agentes. | **Sonnet** | **Medio** |

> **I18N-3 completado — núcleo (2026-07-22)**: migradas a `t()` las páginas
> completas de **Chat.tsx** (título, pestañas de sesión, input/enviar/parar,
> micro/conversación continua/voz on-off, aprobaciones pendientes en el chat,
> enlace "ver plan"), **Missions.tsx** (título, lista/detalle, estados de
> misión y de nodo vía mapas de claves, gate del plan y gate de nodo, plan ·
> N pasos, ver más/ver menos), **Automation.tsx** (título, aprobaciones
> pendientes, reglas con toggle, historial, y los 3 mapas de triggers/
> acciones/estados), **Agents.tsx** (las 3 columnas completas: lista, formulario
> CRUD, panel de ejecución con historial) y las secciones de mayor visibilidad
> de **EmailAssistant.tsx** (cabecera, estado de Google, "Procesar inbox con
> IA", bandeja de entrada, dashboard de actividad, propuestas de reunión,
> reglas de auto-respuesta, formulario "Añadir regla", "Probar reglas") — más
> de 140 claves nuevas en los 4 locales (`chat.*`, `missions.*`,
> `automation.*`, `agents.*`, `email.*`, `workspace.shelf.*`). De Workspace se
> migró el shell (`index.tsx`, `Shelf.tsx`); el resto del módulo (`ProjectCard`,
> `TaskBoard`, los 4 popups, `AgentsSection`/`AgentChip`/`AgentWindowCard`,
> `AutomationSection`, `HelpPanel`, `SkillPickerPopup`, `WorkspaceCanvas` —
> ~5500 líneas) NO se tocó: es el módulo más grande y denso del frontend
> (arrastre/resize/drag&drop con mucho texto de UI incrustado), y forzarlo en
> la misma sesión que el resto de I18N-3 habría sido la misma imprudencia que
> motivó separar I18N-2b. **Alcance honesto**: dentro de las páginas migradas,
> los párrafos explicativos largos con textos legales/técnicos muy específicos
> (p.ej. el aviso de Claude Code CLI en Ajustes, ya documentado en I18N-2b, o
> las explicaciones extensas de "Procesar inbox" en Email) se dejaron en
> español a propósito — degradación graceful, nunca roto. Verificado con
> `tsc --noEmit` (EXIT=0, comprobado tras cada archivo) y validación JSON de
> los 4 locales.

| **I18N-3b** ✅ (2026-07-22) | Cierra el hueco de I18N-3: el resto del módulo Workspace. | **Sonnet** | **Alto** |

> **Nota de cierre I18N-3b**: migrados a `t()`/`useT()` los 13 archivos
> pendientes: `Modal.tsx`, `TaskList.tsx`, `HelpPanel.tsx` (+ su función pura
> `windowShortcuts(expanded, t)`, ahora recibe el traductor como parámetro —
> no puede llamar al hook fuera de un componente), `TaskBoard.tsx` (+
> `kanbanShortcuts(t)`, mismo motivo; `KANBAN_SHORTCUTS` deja de ser una
> constante), `ProjectCard.tsx`, `TaskPopup.tsx`, `ProjectPopup.tsx`,
> `MilestonePopup.tsx` (reutiliza `MS_STATUS_KEY` de `shared.ts`, convertido de
> `MS_STATUS_LABEL` con texto literal a claves i18n), `AgentsSection.tsx`,
> `AgentChip.tsx`, `AgentCreatePopup.tsx`, `AutomationSection.tsx`,
> `SkillPickerPopup.tsx` (el catálogo de 254 skills generado desde
> `agency-agents` NO se traduce — dato externo, fuera de alcance; solo el
> chrome de la UI), `WorkspaceCanvas.tsx`. **Patrón de colisión**: en todo
> archivo donde `t` ya se usaba como variable de `Task`/`ToolInfo` en bucles
> `.map((t) => …)`, el hook se importó como `useT` y su resultado se alió
> `tr` (mismo criterio que Settings.tsx en I18N-2) — aplicado en `TaskList`,
> `TaskBoard`, `ProjectCard`, `AgentWindowCard` (arreglado también su llamada
> a `windowShortcuts`, que había quedado con la firma vieja tras el cambio de
> `HelpPanel.tsx` — error de compilación real detectado y corregido con
> `tsc --noEmit` antes de continuar), `AgentCreatePopup`. Reutilización de
> claves ya existentes de I18N-3 donde el texto coincidía literalmente
> (`agents.field.*`, `agents.status.*`, `common.*`, `chat.send`,
> `workspace.taskBoard.col.*`, `workspace.projectCard.dragToMove`) en vez de
> duplicar. 88 claves nuevas añadidas a los 4 locales (419→507). Verificado
> con `tsc --noEmit` (EXIT=0 tras cada archivo, 12 pasadas) y validación JSON
> de los 4 locales. **Bloque I18N completo**: I18N-1 → I18N-2 → I18N-2b →
> I18N-3 → I18N-3b, todo el frontend migrado salvo lo explícitamente diferido
> a I18N-4 (revisión de calidad nativa).

| **I18N-4** ✅ (2026-07-23) | Revisión de calidad de las traducciones (nativa, no literal) + textos de ayuda de conexión (Google OAuth paso a paso, Telegram /start) por idioma. | **Fable 5** | **Alto** |

> **Nota de cierre I18N-4** (dos mitades):
> **(1) Revisión de calidad nativa** — lectura completa de los 4 locales.
> Hallazgos REALES corregidos: **PT** era el peor — la base es portugués
> europeo con tuteo ("A carregar", "Guardar", "Definições", "Precisas") pero
> las ~30 claves de I18N-3b se colaron en portugués brasileño con "você"
> ("salvar", "Carregando", "Adicione", "Status", "prateleira"); unificado TODO
> a pt-PT con tuteo ("guardar", "A carregar", "Adiciona", "Estado", "estante"
> — que además ya era el término del resto del módulo). **FR** mezclaba "tu" y
> "vous" según la pantalla (chat/misiones tuteaban, ajustes/workspace trataban
> de vous); unificado a "tu" (registro del ES original y de la persona
> asistente personal), 39 claves; además: "Toi"→"Moi" (etiqueta de chat),
> columnas Kanban a la convención nativa "À faire / En cours / Terminé"
> (Trello), "Email Assistant"→"Assistant e-mail", comillas « » consistentes,
> "recours"→"modèles de secours". **EN** solo pulido menor: columna
> "Pending"→"To do" (convención kanban) y 3 retoques. **ES** intacto salvo
> "ej. Architect"→"ej. Arquitecto". Los literales de UI de Google ("+ CREATE
> CREDENTIALS", "Desktop app", "OAuth client ID") se dejan en inglés en los 4
> idiomas A PROPÓSITO: es lo que el usuario verá en la pantalla real de Google.
> **(2) Textos de ayuda de conexión** — los dos bloques `<details>` paso a paso
> de Ajustes → Conexiones estaban HARDCODEADOS en español (y sin tildes):
> migrados a `tr()` con 57 claves nuevas × 4 idiomas
> (`connections.googleHelp.*` 41 + `connections.telegramHelp.*` 16):
> `EmailGoogleStatus` completo (estados, botones, guía OAuth de 7 pasos con
> enlaces a console.cloud.google.com, nota sobre API Keys vs OAuth, formulario
> manual/.env, mensajes de éxito/error con `{msg}`) y `TelegramSettings`
> completo (estados del bot, placeholders, guía /start de 3 pasos con enlace a
> @BotFather, nota de seguridad DPAPI, confirms). De paso el ES ganó las
> tildes que faltaban ("Cómo", "aquí", "responderá"). Reutilización de claves
> existentes donde el texto coincidía (`email.connectedAs`, `email.connect`,
> `agents.error.save/delete`, `agents.saving`, `common.save/delete`).
> Total: 507→564 claves por locale, paridad verificada por script (los 4
> conjuntos de claves idénticos). Verificado con `tsc --noEmit` (EXIT=0) y
> JSON válido ×4. **Limitación honesta**: `vite build` no pudo correrse en el
> sandbox (el `node_modules` es la instalación de Windows, falta el binario
> rollup de Linux; no se tocó) — queda para la siguiente pasada en Windows,
> como el resto de verificaciones vivas. **Bloque I18N COMPLETO** (I18N-1 →
> 2 → 2b → 3 → 3b → 4).

> **⚠️ Corrección (2026-07-23)**: "Bloque I18N COMPLETO" era falso. El usuario
> reportó español visible con otro idioma seleccionado **incluso dentro de
> Ajustes**, la sección que I18N-2/2b ya daban por migrada. Auditoría real
> (diff de `pages/`+`components/` contra qué archivos importan
> `useT`/`useI18n`, más grep de frases con mayúscula inicial y lectura en
> contexto de cada acierto para descartar falsos positivos — comentarios de
> código, "Aithera" como marca, nombres de teclas): el hueco real es que
> I18N-1→4 tradujeron las páginas (`pages/*.tsx`) pero **NO varios
> subárboles de `components/` que viven EMBEBIDOS dentro de esas páginas ya
> "completas"** — exactamente donde el usuario dice haber mirado. Detalle
> por archivo (con recuento de coincidencias reales, no estimado):
>
> - **`components/voice/VoicePanel.tsx`** (16), **`CoreSelector.tsx`** (13) y
>   **`CoreDesignPanel.tsx`** (8), **`PersonalityPicker.tsx`** (5),
>   **`MicButton.tsx`** (2) — viven dentro de las pestañas Voz y HUB Visual de
>   Ajustes; ninguno importa `useT`. `Settings.tsx` está migrado, pero estos
>   componentes que renderiza NO lo están.
> - **`components/onboarding/WelcomeOverlay.tsx`** (61) — importa `useI18n`
>   pero SOLO para llamar `.getState().setLang(...)` (fijar el idioma elegido
>   en el selector), nunca `useT()` para traducirse a sí mismo. Irónico: la
>   propia pantalla donde el usuario elige idioma está en español fijo.
> - **`pages/Calendar.tsx`** (22) — página entera sin tocar en ninguna sesión
>   I18N previa (no estaba en la lista de I18N-2/3/3b).
> - **`pages/Settings.tsx`** (70 restantes, verificados línea a línea) —
>   dentro de la página YA migrada quedan: las etiquetas de densidad de
>   partículas del AVCS ("Mínimo/Pocas partículas"…), el array
>   `AUTONOMY_PROFILES` con `label`/`hint` literales de los 3 perfiles
>   (manual/balanced/full — nunca migrado, aunque el resto del panel de
>   Permisos sí lo está), los nombres de las 4 políticas MEL y las 8
>   capacidades ("Economía/Calidad/Personalizado…", "Chat/Clasificar/
>   Resumir…"), botones sueltos repetidos ("Eliminar", "Configurar",
>   "Guardar", "Activo/Activa"), el bloque de notificaciones, y — el hallazgo
>   más irónico — **el propio título y botón de cerrar del modal de
>   Ajustes** ("Configuración" / "Cerrar") nunca se migraron.
> - **`pages/EmailAssistant.tsx`** (59 restantes) — el interior profundo de
>   formularios (constructor de reglas de 4 pasos, formulario de prueba,
>   tarjetas de propuesta/regla, dashboard de actividad) que I18N-3 dejó
>   deliberadamente para después; sigue pendiente.
> - **Módulo Workspace** (16 coincidencias sueltas en 9 archivos: `TaskBoard`,
>   `TaskPopup`, `SkillPickerPopup`, `AutomationSection`, `AgentWindowCard`,
>   `ProjectCard`, `Modal`, `MilestonePopup`, `AgentsSection`) y
>   **`components/layout/Sidebar.tsx`** (1) — oversights puntuales de 1-3
>   strings por archivo (mismo patrón que el `aria-label="Modo conversación"`
>   de `Chat.tsx`, ya corregido en esta misma auditoría), no huecos
>   estructurales.
> - **Confirmado SIN problema real** (falsos positivos descartados leyendo el
>   contexto): `pages/Missions.tsx` (los 3 aciertos son comentarios de
>   código, la UI real ya usa `missions.loadError`/`missions.state.waiting`)
>   y la mayoría de `pages/Chat.tsx` (2 aciertos eran comentarios sobre la
>   arquitectura de `useChatStore`; el único real,
>   `aria-label="Modo conversación"`, y el fallback hardcodeado
>   `"Voz no disponible"` de `pages/Hub.tsx`, se corrigieron ya en esta
>   auditoría — 2 claves nuevas, `hub.voice.unavailable` ×4, paridad 571/locale).
>
> **Hallazgo aparte, backend**: `chat_service.DEFAULT_SYSTEM_PROMPT` dice
> "Responde siempre en el idioma del usuario" — es decir, el modelo infiere
> el idioma del MENSAJE que escribe el usuario, no del idioma de interfaz
> seleccionado. Si la UI está en francés pero el usuario teclea en español
> (o en un mensaje corto/ambiguo), Aithera responde en español. Esto es
> distinto de traducir strings de UI: es una instrucción del prompt del
> sistema, y hoy el idioma de interfaz (`useI18n`) nunca viaja al backend en
> ninguna llamada de chat. Sesión I18N-9 más abajo lo cierra.
>
> **Plan de sesiones para el cierre real** (I18N-5 a I18N-9, tabla debajo).
> El bloque I18N NO estará completo hasta que estas 5 sesiones se ejecuten.

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **I18N-5 ✅** (2026-07-23) | Onboarding + Calendario: migrar `WelcomeOverlay.tsx` (61 strings — el asistente de bienvenida completo, incl. el propio selector de idioma) y `pages/Calendar.tsx` (22 — página entera, nunca tocada). | **Sonnet** | **Medio** |

> **Nota de cierre I18N-5 — corrección importante del alcance**:
> `WelcomeOverlay.tsx` resultó ser un **falso positivo** de la auditoría. Al
> leerlo completo (no solo grepear), tiene su PROPIO diccionario `TXT` con
> las 4 traducciones completas (es/en/fr/pt) ya escritas y correctas —
> documentado en su propia cabecera como decisión deliberada: la pantalla de
> bienvenida necesita mostrar copia en el idioma que el usuario ELIGE en el
> paso 1, antes de que el store global `useI18n` pueda reflejar esa
> elección, así que usa un diccionario local en vez del framework i18n
> global. El grep original solo veía las cadenas del bloque `es:` sin
> reparar en que el mismo objeto tenía `en:`/`fr:`/`pt:` completos justo al
> lado. **No se tocó nada de este archivo** — no hacía falta.
> `pages/Calendar.tsx` sí era un hueco real y se migró entero: cabecera,
> navegación de mes, leyenda de estados, nombres de días/meses, modal de
> detalle de día (estado actual, formulario de bloque con validación al
> guardar/borrar, opciones del desplegable, tooltips de eventos/bloques) y
> el tip del pie. Un detalle de implementación digno de nota: el color del
> mensaje de guardado (`formMsg`) se decidía antes mirando si el texto
> empezaba por "Error" — con el mensaje ya traducido eso deja de ser fiable
> en los otros 3 idiomas, así que se añadió un estado `formIsError` booleano
> aparte en vez de siguir mirando el string. 66 claves nuevas × 4 idiomas
> (namespace `calendar.*`), paridad verificada (631/locale). `tsc --noEmit`
> EXIT=0. **Pendiente en Windows**: vistazo visual del calendario en los 4
> idiomas + confirmar que el mensaje de guardado/borrado de bloques se
> colorea bien.
| **I18N-6 ✅** (2026-07-23) | Componentes embebidos en Ajustes → Voz y HUB Visual: `VoicePanel.tsx` (16), `CoreSelector.tsx` (13), `CoreDesignPanel.tsx` (8), `PersonalityPicker.tsx` (5), `MicButton.tsx` (2 — de paso, wirear el prop `language` al idioma de interfaz seleccionado en vez de `"es"` fijo, para que el STT reconozca en el idioma correcto). Es la sección EXACTA donde el usuario reportó el fallo. | **Sonnet** | **Medio** |

> **Nota de cierre I18N-6**: los 5 archivos migrados a `useT()`. En
> `VoicePanel.tsx` los nombres nativos de idioma de voz ("Español"/"English"/
> "日本語"…) se dejaron TAL CUAL a propósito — describen en qué idioma habla
> la VOZ, no el idioma de la interfaz, así que no cambian aunque la app esté
> en francés (mismo criterio que `WelcomeOverlay.tsx`). En `CoreSelector.tsx`
> los 4 nombres de núcleo 3D ("Semilla de Aithera", "Orbe azul", "Bola de
> caca", "Rasengan") SÍ se tradujeron — son etiquetas de producto, no marca —
> salvo "Rasengan" (referencia a Naruto, nombre propio, igual en los 4
> idiomas). Nuevo export `CORE_MODEL_LABEL_KEYS` en `CoreSelector.tsx` para
> que `CoreDesignPanel.tsx` reuse las mismas claves sin duplicar el
> diccionario (`coreDesign.ts` es un módulo de datos puro, no puede llamar
> `useT()`). El "Design Lab" (panel de ajuste fino, marcado "dev only") se
> tradujo también salvo su propio nombre, que se deja como marca de la
> herramienta. **Fix real encontrado**: `MicButton.tsx` recibía SIEMPRE
> `language="es"` desde `Chat.tsx` sin importar el idioma elegido en
> Ajustes — el STT (Whisper) reconocía peor a un usuario hablando en
> francés/inglés/portugués con la UI en su idioma. Corregido: `Chat.tsx` lee
> `useI18n((s) => s.lang)` y lo pasa como `language` (Whisper acepta los
> mismos 4 códigos ISO 639-1 que ya usa el resto del proyecto, sin cambios
> de backend). 78 claves nuevas × 4 idiomas (namespaces `settings.voz.panel.*`,
> `settings.voz.personality.*`, `hub.core.*`, `hub.designLab.*`,
> `voice.mic.*`), paridad verificada (721/locale). `tsc --noEmit` EXIT=0.
> **Nota fuera de alcance** (no de este frontend, aparte): `p.name`/
> `p.description` de las tarjetas de personalidad vienen del backend
> (`api.getPersonalities()`) y hoy están en español fijo — traducirlas
> exigiría tocar `app/ai/personalities.py`, fuera del alcance frontend de
> I18N-6; anotado por si se quiere una sesión aparte. **Pendiente en
> Windows**: vistazo visual de Ajustes → Voz y → HUB Visual en los 4 idiomas
> + probar el dictado por voz con la UI en inglés/francés/portugués.
| ✅ **I18N-7** | Cierra Ajustes de verdad: `AUTONOMY_PROFILES` (label+hint de los 3 perfiles), nombres de las 4 políticas MEL + 8 capacidades, título/botón-cerrar del propio modal de Ajustes, densidad de partículas AVCS, notificaciones, botones sueltos repetidos. + los 16 oversights puntuales del módulo Workspace y Sidebar (1-3 strings/archivo, quick wins). | **Sonnet** | **Medio** |

> **Cierre I18N-7 (2026-07-23)**: `Settings.tsx` migrado por completo — el
> escáner de hardware (CPU/GPU/RAM/tier AVCS), Búsqueda web
> (SerpAPI/Brave/modo navegador), `AUTONOMY_PROFILES`, `MEL_POLICY_META`/
> `MEL_CAP_LABEL` (renombrados a `*_KEYS`, resueltos con `tr()` en cada
> render — incluida la función pura `primaryBadges()`, que ahora devuelve la
> CLAVE de capacidad y no la etiqueta, porque no tiene acceso al hook), los
> botones de Modelos locales/Descarga, Inteligencia (slots/respaldos/pines de
> proyecto), Permisos, Avisos (`NotifyChannelSetting`), ElevenLabs, el bloque
> informativo de Claude Code CLI, y la cabecera/botón-cerrar del propio modal
> de Ajustes (irónicamente nunca traducidos hasta ahora). **Hallazgo real**:
> la sospecha original de un "Volver a conectar" duplicado (línea ~317,
> arrastrada del audit original) resultó ser una falsa alarma — `EmailGoogleStatus`
> ya estaba migrado en su totalidad desde AUTH-1/I18N-2b, el comentario de
> código simplemente describía la lógica de `needsReconnect`, no una cadena
> suelta. Auditoría del módulo Workspace + `Sidebar.tsx` (los "16 oversights"
> originales): resultaron estar YA migrados en sesiones previas salvo 2
> cadenas reales — `useModeloIAOptions.ts` ("Flexible según necesidad", ahora
> `workspace.modeloIA.generic`, resuelta dentro del propio hook con `useT()`)
> y `Sidebar.tsx` ("Conectado"/"Conectando..."/"fallando" del indicador de
> estado, ahora `common.connected`/`common.connecting`/`common.failing`).
> **205 claves nuevas × 4 idiomas** (201 de Settings.tsx + 4 de Workspace/Sidebar),
> paridad verificada por script (926/locale). `npx tsc --noEmit` EXIT=0 dos
> veces (tras Settings.tsx y tras el cierre final). **Nota fuera de alcance
> confirmada de nuevo**: `p.label`/`p.description`/`group` del catálogo de
> Permisos (`PermissionCatalog`, backend) y `p.description`/`model_labels` de
> los proveedores IA siguen en español fijo — mismo caso que
> `personalities.py` (I18N-6/I18N-8), no se tocan aquí por ser contenido
> servido por el backend, no strings de UI. **Pendiente en Windows**: vistazo
> visual de las 7 pestañas de Ajustes en los 4 idiomas.
| ✅ **I18N-8** | `EmailAssistant.tsx` completo (59 restantes): constructor de reglas de 4 pasos, formulario de prueba de regla, tarjetas de propuesta/regla, dashboard de actividad. El archivo más grande que queda. **+ `app/ai/personalities.py` (backend)**: `p.name`/`p.description` del catálogo de personalidades (`PersonalityPicker.tsx`, I18N-6) traducidos. | **Sonnet** | **Alto** |

> **Cierre I18N-8 (2026-07-24)**: `EmailAssistant.tsx` migrado por completo —
> constantes de módulo (`MATCHING_LABEL_KEYS`, `ACTION_LABEL_KEYS`,
> `ACTIVITY_VISUAL`/`ACTIVITY_FILTERS`/`PROPOSAL_STATUS_COLORS` con
> `labelKey`), fechas con `LOCALE_TAG[lang]` (bug real encontrado: 9
> `toLocaleString("es-ES", …)` hardcodeados sin importar el idioma de
> interfaz — mismo patrón que el bug de STT de I18N-6 — arreglado con un
> nuevo export `LOCALE_TAG: Record<Lang,string>` en `store/useI18n.ts`,
> reutilizable por cualquier archivo futuro con el mismo problema), el
> constructor de reglas de 4 pasos completo, el formulario de prueba,
> tarjetas de propuesta/regla, dashboard de actividad y estadísticas, y los
> mensajes de estado/error de las llamadas a la API (conectar/desconectar
> Google, CRUD de reglas, procesar bandeja, confirmar reuniones). Barrido
> final con grep de literales entre comillas Y de template strings con texto
> — limpio salvo comentarios de código y `console.error()`. 213 claves
> nuevas añadidas a los 4 locales (1139/idioma, paridad verificada).
> `app/ai/personalities.py`: `catalog_payload()` ahora traduce `name`/
> `description` al idioma de `Config.app_language` (mismo patrón que
> `_DEFAULT_VOICE_BY_LANG` en `voice.py`) con fallback a español si falta
> traducción o el idioma es desconocido; el `prompt` (instrucciones de TONO
> para el LLM) se deja en español a propósito — cambiar el idioma en que
> Aithera razona es comportamiento del chat (I18N-9), no de la interfaz, y
> queda fuera de alcance aquí. Verificado con script directo (`_localized()`
> en los 4 idiomas + fallback). `tsc --noEmit` limpio (exit 0),
> `py_compile` limpio en todo `app/`. Ningún test existente referenciaba
> `personalities.py` directamente (nada que romper).
| **CODEX-1** | (petición del usuario, 2026-07-23; ver conversación previa) Investigar en profundidad y, si procede, integrar el login de Codex CLI (OpenAI) por SUSCRIPCIÓN (ChatGPT Plus/Pro/Team/Enterprise) como alternativa a la API key — mismo patrón ya construido para Claude Code CLI (botón "Activar" en Ajustes → Proveedores, test de conexión, persistencia en BD). Investigación EN VIVO (instalar el CLI real, no solo documentación): confirmar que es un canal oficial de OpenAI y no el método "superficial" de scraping de sesión web (ese, el de Hermes/Nous, se descarta por frágil y de riesgo de ToS); si es viable, diseñar el wrapper del MEL/AIManager análogo al de Claude Code. **Restricción activa hasta que el usuario lo autorice explícitamente**: no tocar Codex CLI en terminal — el usuario lo está investigando por su cuenta en paralelo; esta sesión solo arranca cuando él dé la señal de que ya puede tocarse. Va DESPUÉS del bloque de traducciones "normales" (I18N-8) a propósito: primero cerrar lo que ya está en marcha. | **Opus** | **Alto** |
| ✅ **I18N-9** | **Idioma de RESPUESTA del chat** (backend, no strings de UI): hoy `chat_service.DEFAULT_SYSTEM_PROMPT` infiere el idioma del mensaje del usuario, nunca del idioma de interfaz. Enhebrar el idioma seleccionado (`useI18n`) en cada request de chat (`api.ts::sendMessage`/`streamChat`) → `build_system_prompt(..., ui_language=...)` con instrucción explícita ("responde SIEMPRE en {idioma}, sin importar en qué idioma escriba el usuario") que sustituya a la inferencia actual; propagar el mismo idioma al `responder.build()` del TIE (para que el resumen de una misión también salga en el idioma correcto) y revisar si el planner necesita el mismo tratamiento. Toca `chat_service.py`, `tie/pipeline.py`, `tie/responder.py`, `lib/api.ts`, `Chat.tsx`. | **Opus** | **Alto** |

> **Cierre I18N-9 (2026-07-24, Opus)** — **desviación deliberada del plan literal,
> auditada primero**: el plan proponía enhebrar `ui_language` desde cada request
> (`api.ts` → `ChatRequest` → … → `build_system_prompt`). La auditoría del código
> real reveló un camino mucho más limpio: el idioma de interfaz YA se persiste
> server-side en `Config.app_language` (lo escribe `useI18n.setLang` en **cada**
> cambio, tanto desde `LanguageSelector.tsx` como desde el onboarding
> `WelcomeOverlay.tsx`), y ya lo leen `personalities.py` y `voice.py`. Enhebrarlo
> por request obligaría a tocar el schema `ChatRequest`, el **contrato CONGELADO
> `AgentTask`** y ~6 archivos del pipeline del TIE; en cambio, **una lectura
> central cubre TODOS los caminos** porque todos pasan por
> `chat_service.build_system_prompt` (chat no-streaming, streaming del TIE camino
> corto vía `NullRuntime.stream_task`, Gateway/Telegram vía `answer()`, y el
> legacy con `TIE_ENABLED=false`). Aithera es monousuario con un idioma activo a
> la vez (Principio 6), así que un ajuste GLOBAL es correcto y mucho menos
> invasivo. **Implementación**: nuevo `app/core/language.py` (`ui_language()` /
> `ui_language_name()` / `language_directive()`, best-effort, lee
> `Config.app_language`, `None`/idioma no soportado → sin forzar). (1)
> `chat_service`: se quitó la frase "responde en el idioma del usuario" del prompt
> base y se inyecta la directiva tajante cuando hay idioma elegido, o el fallback
> histórico suave cuando no lo hay. (2) `responder._synthesize`: el resumen de
> misión sale en el idioma elegido. (3) `planner`: los `goal` de cada nodo (que se
> ven en la vista de Misiones) se escriben en el idioma elegido, sin traducir
> claves/ids/tool_ids. **Cero cambios de frontend** (el plan mencionaba
> `api.ts`/`Chat.tsx` — innecesarios con este enfoque). Tests: `test_i18n_language.py`
> (11: unidad de `app.core.language` en los 4 idiomas + none + idioma desconocido;
> integración de `build_system_prompt` forzando/degradando). **Verificado en el
> sandbox contra SQLite real** (Config con `app_language` en/es/fr/pt): la
> directiva se inyecta correctamente, el prompt base ya no hardcodea idioma, y
> sin idioma se mantiene el comportamiento histórico. `py_compile` limpio en todo
> `app/`; sin regresiones en `test_memory_context`/`test_tie_planner`/`test_tie_handle`
> /`test_gateway` (44 passed). **Desfase teórico documentado**: cambiar de idioma
> y mandar un mensaje en el mismo instante (antes de que el `setConfig` best-effort
> persista) usaría el idioma anterior ese único turno; se autocorrige al siguiente.
> **Fuera de alcance (deuda menor documentada)**: las plantillas DETERMINISTAS de
> `responder` (fallback cuando el LLM está caído) y los strings de estado/error de
> `tie/pipeline.py` (mensaje del gate del plan, "sin respuesta", cancelaciones)
> siguen en español fijo — son fallbacks/estados poco frecuentes cuyo texto NO lo
> genera el LLM; traducirlos requiere un catálogo de strings en backend (un
> I18N-10 aparte si se quiere). El texto conversacional que el usuario lee de
> verdad (respuestas del chat, resumen de misión, plan) ya sale en su idioma.

| ✅ **I18N-10** | Deuda menor de I18N-9: catálogo backend de las plantillas DETERMINISTAS y strings de estado/error que NO pasan por ningún LLM (`tie/responder.py`, `tie/pipeline.py`) — traducirlos requiere un catálogo propio porque no hay ningún LLM de por medio al que instruir con `language_directive()`. | **Opus** | **Medio** |

> **Cierre I18N-10 (2026-07-24, Opus)**: nuevo `app/core/strings.py` — catálogo
> plano `{idioma: {clave: texto}}` (mismo patrón que `useI18n`/`translate()` del
> frontend) con interpolación `{var}` vía `str.format` y `t(key, **vars)` que lee
> `ui_language()` (I18N-9) con triple fallback (idioma elegido → español →
> la propia clave, nunca lanza). 29 claves en los 4 idiomas, namespaced por
> módulo de origen (`responder.*`, `pipeline.*`, `orchestrator.*`, `status.*`).
> **Alcance real, más amplio que lo documentado en el cierre de I18N-9** — la
> auditoría de esta sesión encontró 2 categorías más del mismo problema que el
> cierre anterior no había nombrado explícitamente: (1) **`orchestrator/
> consolidator.py`** es el equivalente EXACTO de `responder.py` para el caso
> multi-objetivo (plantilla determinista + system prompt de síntesis) — dejarlo
> sin traducir habría producido una experiencia inconsistente según el mensaje
> tuviera 1 o 2+ encargos; recibe el mismo tratamiento (`_SYSTEM_PROMPT` +
> `language_directive()` dinámica, `_plantilla()`/`_detalle()` con el catálogo).
> (2) los estados EN VIVO del streaming ("analizando"/"planificando"/
> "ejecutando", `orchestrator/__init__.py`) se muestran en `Chat.tsx` **en
> crudo** (`` `${tieStatus}…` ``, sin ninguna capa de traducción en el frontend)
> — así que estas 3 palabras SOLO pueden traducirse en el backend; ya están en
> el catálogo y `Chat.tsx` no necesitó ningún cambio. También se tradujeron los
> 2 fallbacks `"(sin respuesta)"` de `gateway.py`/`telegram_adapter.py` (mismo
> catálogo, clave `pipeline.no_response`) por ser el mismo tipo de texto que el
> resto del cierre. **Fuera de alcance, deliberado**: el texto que se le PASA a
> un LLM como parte de su propio prompt de razonamiento interno (el bloque
> `problems` de `responder._synthesize()`, el transcript que arma
> `tie/toolloop.py`) — ese texto es INPUT para un modelo que luego sintetiza su
> propia respuesta ya en el idioma correcto; traducir el lenguaje interno de
> instrucciones no cambia lo que el usuario ve y arriesga romper cómo el modelo
> interpreta su propio estado. También fuera de alcance: los campos `title`/
> `body`/`reason` de la Decision API en `pipeline._record_override_decision()`
> (texto de auditoría interna, sin ninguna superficie de UI traducida que lo
> muestre — mismo criterio ya aplicado al catálogo de Permisos y a las
> descripciones de proveedor). Tests: `test_i18n_strings.py` (21 — unidad de
> `t()` en los 4 idiomas + interpolación + clave desconocida + idioma no
> soportado; `_template_success`/`_template_failure`/`_node_output`/
> `plan_summary` de `responder.py` en inglés/francés/portugués;
> `_plantilla`/`_detalle`/`consolidate` de `orchestrator/consolidator.py` en
> inglés/francés/portugués). **Verificado en el sandbox contra SQLite real**:
> `test_i18n_strings.py` + `test_i18n_language.py` (32 passed) y, sin
> regresión, `test_tie_e2e`/`test_module_boundaries`/`test_tie_contracts`/
> `test_tie_planner`/`test_tie_handle`/`test_gateway`/`test_telegram_adapter`
> (85 passed) + `test_orchestrator`/`test_orchestrator_chat`/
> `test_orchestrator_e2e` (41 passed). `py_compile` limpio en los 8 archivos
> tocados. **No se pudo ejecutar en el sandbox** `test_product_contracts.py`
> (excede el límite de tiempo por llamada del entorno de esta sesión; no toca
> ningún código modificado aquí — ToolManager/ApprovalGate/browser no se
> tocaron en I18N-10) — pendiente de correrlo en la pasada de verificación
> completa en Windows, junto con el resto de la suite.

**Nota de alcance (I18N-9)**: deliberadamente NO incluye el redactado de
respuestas automáticas de email (`ai_reply`/`email_tool`) ni los prompts del
planner del TIE en su totalidad — esos ya tienen su propio prompt de estilo
(instrucción del usuario por regla) y son casos de uso distintos al chat
interactivo que el usuario señaló explícitamente ("que cuando tienes un
idioma seleccionado, ese sea el idioma con el que habla el chat"). Si tras
I18N-9 el usuario quiere el mismo tratamiento para email/planner, es una
sesión aparte (mismo patrón, superficie distinta).

> **Nota del usuario (2026-07-23) — I18N-9 se MANTIENE pendiente, no se ha
> hecho todavía**: el fix de I18N-6 (`MicButton`/`Chat.tsx` pasando
> `useI18n().lang` a Whisper) arregla el idioma de ENTRADA del dictado por
> voz — un problema real pero DISTINTO de I18N-9, que es el idioma de SALIDA
> del texto que genera el LLM en el chat. Son dos "idiomas" en el mismo
> flujo (STT antes de que el usuario hable, prompt de sistema para cuando
> Aithera responde) que conviene no confundir. La sesión I18N-9 (backend:
> `chat_service.DEFAULT_SYSTEM_PROMPT`, `tie/pipeline.py`, `tie/responder.py`)
> sigue intacta y pendiente de ejecutar — el usuario ha pedido revisarla con
> Opus específicamente por su importancia (toca el corazón del chat y del
> TIE) antes de tocar código.

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
| **AUTH-1** ✅ (2026-07-23) | Pulir el OAuth de Google a un botón "Conectar con Google" de un clic (flujo limpio, mensajes claros, manejo de token caducado que el usuario ya sufrió). | **Opus** | **Alto** |
| **AUTH-2 ✅** (2026-07-23) | Flujo guiado de API key por proveedor (enlace directo a su página de keys + instrucción por proveedor), para los que no tienen OAuth. Investigar cuáles ofrecen OAuth de verdad. | **Sonnet** | **Medio** |

> **Nota de cierre AUTH-2**: `frontend/src/data/providerAuthHelp.ts` (NUEVO)
> — catálogo `{provider: {url, instructionKey}}` para los 7 proveedores sin
> OAuth (openai/anthropic/gemini/minimax/deepseek/openrouter/grok); el modal
> "Configurar {provider}" de `Settings.tsx` ahora muestra, antes del campo de
> API key, un enlace directo a la página real donde el proveedor deja crear
> la key + una instrucción de 1 frase (dónde hacer clic exactamente) — 8
> claves × 4 idiomas. **Validación al pegar**: ya no hace falta pulsar
> "Probar conexión" a mano — un `useEffect` con debounce de 700ms dispara la
> prueba sola en cuanto el campo tiene ≥20 caracteres (umbral de sobra para
> cualquier key real de estos proveedores); el botón manual se conserva para
> repetir la prueba a voluntad. `ollama` (local, sin key) y `claude_code`
> (su propio botón "Activar", sin este modal) quedan fuera del catálogo a
> propósito.
> **Investigación OAuth real (vía búsqueda web, 2026-07-23)** — resultado
> honesto, no lo que se esperaba: de los 7 proveedores de este catálogo,
> **NINGUNO ofrece hoy OAuth para su API** (todos siguen siendo API-key-only).
> Hallazgo aparte y relevante: **xAI (Grok) SÍ tiene un OAuth 2.0 PKCE real**
> vía `accounts.x.ai` que permite usar Grok con una suscripción SuperGrok/X
> Premium+ existente, sin key — el mismo patrón que ya tiene Claude Code CLI
> en Aithera. **No implementado aquí** (fuera del alcance "medio" de esta
> sesión — un flujo PKCE + servidor de callback local es trabajo nuevo
> equivalente al que ya se hizo para Google, no un ajuste de UI); queda
> anotado como candidata a una sesión futura **GROK-1** (Opus, alto) si el
> usuario quiere ese ahorro. También se confirmó una restricción importante
> del ecosistema (no específica de Aithera): Anthropic prohibió desde
> 2026-02-20 usar tokens OAuth de suscripción en herramientas de terceros
> (aplicado con enforcement de facturación desde 2026-04-04), y Google
> bloqueó el mismo patrón para Gemini CLI desde 2026-02/03 — **no afecta a la
> integración de Claude Code CLI que ya tiene Aithera**, porque esta invoca
> el binario `claude` real como subproceso (usa el CLI tal cual, no extrae ni
> reutiliza su token para llamar a la API por su cuenta), pero es la razón de
> por qué NO se intentó replicar ese patrón para OpenAI/Anthropic/Gemini
> directamente vía API — habría violado los términos de esos proveedores.
> `tsc --noEmit` EXIT=0, paridad i18n 579/locale. **Pendiente en Windows**:
> vistazo visual del modal con el enlace+instrucción real, probar el
> auto-test al pegar una key real de al menos un proveedor.

> **Nota de cierre AUTH-1** — el problema real: el flujo OAuth ya funcionaba,
> pero un token **revocado** (borrado desde la cuenta de Google, cambio de
> contraseña, o refresh_token invalidado) se veía EXACTAMENTE igual que "nunca
> conectado" — `is_connected()=False` sin pista de que la solución era
> "reconecta", no "configura credenciales". El usuario ya lo había sufrido.
> **Backend** (`google_auth.py`): nuevo `_load_and_refresh()` que centraliza
> carga+refresco UNA vez y clasifica el resultado en 6 estados estables
> (`connected` · `expired` = fallo transitorio sin internet, se reintenta solo
> · `revoked` = hay que reconectar · `no_token` · `no_credentials` ·
> `libs_missing`); `connection_state()` lo expone. `get_credentials()` pasa a
> delegar aquí sin cambiar su contrato (creds válido o None). **Bug latente
> arreglado de paso**: cada refresco hacía `write_text(creds.to_json())`, que
> BORRA el campo cacheado `email` del token json → forzaba una llamada extra a
> Gmail getProfile en el siguiente `/status`; nuevo `_write_token_preserving_email()`
> lo conserva. La clasificación revoked-vs-transitorio distingue `invalid_grant`
> (revocado real) de timeouts/DNS (transitorio) — sin internet nunca se marca
> como "reconecta" por error. **Endpoint** `/api/email/status`: un solo probe
> (antes `is_connected()`+`get_connected_email()` podían disparar dos
> refrescos) + clave aditiva `connection_state` (el contrato de 5 claves
> congelado por `test_email_contracts` sigue intacto; el email solo se pide
> cuando de verdad hay conexión). **Frontend**: `EmailGoogleStatus` (Ajustes) y
> la tarjeta de Email del Hub distinguen ahora sesión caducada/revocada
> ("Vuelve a conectar", un clic) de "sin credenciales", con mensajes propios;
> `api.getEmailStatus` tipado con `connection_state`. **i18n**: 6 claves nuevas
> ×4 idiomas (`connections.googleHelp.sessionExpired/sessionRevoked/reconnect/
> offlineRetry` + `hub.email.sessionExpired/reconnect`), paridad verificada
> (570/locale). **Tests**: `test_google_auth_state.py` (11 casos: los 6 estados
> + preservación del email + delegación de `get_credentials`), verificados con
> script standalone contra el código REAL (el sandbox no tiene fastapi/pytest;
> `google_auth` es stdlib puro, así que se ejercitó aislado — 11/11 PASS).
> `tsc --noEmit` EXIT=0, `py_compile` OK. **Pendiente en Windows**: correr la
> suite completa (que incluye `test_email_contracts`) + vistazo en vivo del
> estado "sesión caducada" con el backend real. **Alcance NO tocado a
> propósito**: el registro de credenciales OAuth en Google Cloud Console sigue
> siendo manual (es requisito de Google, no eliminable); la guía de 7 pasos ya
> quedó traducida en I18N-4.

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
3b. **I18N-5/6/7/8** (cierre del bloque i18n "normal", 2026-07-23) — I18N-6
    primero (es la sección exacta que el usuario reportó rota, hecho), luego
    5 (hecho)/7/8 en cualquier orden.
3c. **CODEX-1** (investigación Codex CLI) — justo después de cerrar I18N-8;
    solo arranca cuando el usuario autorice tocar Codex CLI (está
    investigándolo por su cuenta en paralelo).
3d. **I18N-9** (idioma de respuesta del chat, backend) — pendiente, a
    revisar con Opus antes de implementar por su importancia; no confundir
    con el fix de STT ya hecho en I18N-6 (ver nota en la sección 2).
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
