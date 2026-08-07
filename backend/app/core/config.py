# Aithera Core Configuration (V0.7)
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App settings
    APP_NAME = "Aithera"
    # V1.1 CERRADO (2026-08-06): Learner operativo (LSL + Mission Learning +
    # atribucion de fallos + LLL/analisis nocturno + panel "Aithera aprende").
    # Bump sincronizado con main.py y frontend/package.json. Tag v1.1.0.
    VERSION = "1.1.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # API settings
    API_URL = "http://localhost:8000"
    API_PREFIX = "/api"

    # V0.85 (MOS M2): cadencia de los jobs de ingesta proactiva (doc 07 §6).
    MEMORY_INGEST_INTERVAL_MIN = int(os.getenv("MEMORY_INGEST_INTERVAL_MIN", "20"))
    MEMORY_INGEST_CALENDAR_INTERVAL_MIN = int(os.getenv("MEMORY_INGEST_CALENDAR_INTERVAL_MIN", "60"))

    # V0.9 (Automation A2a): lifecycle del MOS (compactacion, doc 08 RFC-007).
    # MEMORY_BUDGET_MB: presupuesto global de la memoria vectorial; si se supera,
    # el lifecycle aprieta las ventanas de retencion. MEMORY_LIFECYCLE_HOUR: hora
    # LOCAL del job nocturno (tras el summarizer de las 03:30, doc 07 §7).
    MEMORY_BUDGET_MB = int(os.getenv("MEMORY_BUDGET_MB", "512"))
    MEMORY_LIFECYCLE_HOUR = int(os.getenv("MEMORY_LIFECYCLE_HOUR", "4"))
    # V0.9: kill-switch global del Automation Engine (jobs + motor de reglas).
    AUTOMATION_ENABLED = os.getenv("AUTOMATION_ENABLED", "true").lower() == "true"
    # V0.9 (A2a, doc 12 A8): ventana (segundos) del guard anti-flood del Gateway
    # por (canal, user_ref). 0 = desactivado. 1s no molesta al chat humano y
    # corta un loop de mensajes (un canal que reenvia en bucle).
    GATEWAY_COOLDOWN_S = float(os.getenv("GATEWAY_COOLDOWN_S", "1.0"))

    # V1.0 (TIE v1): kill-switch del Task Intelligence Engine. Con False, el
    # Gateway sigue usando el chat_message_handler legacy (el switch a tie.handle
    # es T4). En T1 el TIE existe pero no está enganchado todavía.
    TIE_ENABLED = os.getenv("TIE_ENABLED", "true").lower() == "true"
    # V1.0 (T4): si un plan toca algo sensible, se aprueba EL PLAN entero antes de
    # ejecutar nada (transparencia estilo plan-mode). Con False, cada nodo sensible
    # pide su propio permiso durante la ejecución (el gate de nodo de T3 sigue ahí).
    TIE_PLAN_APPROVAL = os.getenv("TIE_PLAN_APPROVAL", "true").lower() == "true"
    # [Fix bug real 2026-07-17] limpieza automática de misiones TERMINADAS
    # (done/failed/cancelled) más viejas que esto — nunca toca una misión viva.
    # 0 desactiva la limpieza automática (el botón "×" manual sigue funcionando).
    TIE_MISSION_RETENTION_DAYS = int(os.getenv("TIE_MISSION_RETENTION_DAYS", "30"))
    # [V1.1 L2] Plazo DURO de la reflexión post-misión del Learner (segundos).
    # Corre en background y ya respondimos al usuario, así que puede permitirse
    # más que el camino caliente — pero no puede quedarse colgada: si el modelo
    # no contesta a tiempo, la misión se queda con sus contadores (que son
    # deterministas y ya están guardados) y no se aprende de ella. Reflexionar
    # nunca puede costar más que trabajar (doc 15 §10, "coste silencioso").
    LEARNER_REFLECTION_BUDGET_S = float(os.getenv("LEARNER_REFLECTION_BUDGET_S", "20"))
    # [V1.1 LC1, doc 41 §3.4] EL JUEZ. Retardo antes de juzgar una misión: hace
    # falta que EXISTA "el después" (qué dijo el usuario tras la respuesta), que
    # es la señal más informativa de si sirvió. Juzgar al instante sería juzgar
    # a ciegas justo en lo que más importa. Se adelanta solo si llega el
    # siguiente mensaje del usuario, y la cola drena en background.
    LEARNER_JUDGE_DELAY_MIN = float(os.getenv("LEARNER_JUDGE_DELAY_MIN", "10"))
    # Plazo duro de la llamada al juez. Más generoso que la reflexión de L2
    # porque el modelo típico es un razonador LOCAL (deepseek-r1 y compañía):
    # lento, gratis y sin prisa — todo esto corre de madrugada o en segundo
    # plano, nunca en el camino del usuario.
    LEARNER_JUDGE_BUDGET_S = float(os.getenv("LEARNER_JUDGE_BUDGET_S", "180"))
    # Cuántas misiones REALES sin juzgar recupera la pasada nocturna (catch-up +
    # backfill del histórico). Techo, no objetivo: con la app encendida la cola
    # ya las va juzgando y aquí no queda casi nada.
    LEARNER_JUDGE_BACKFILL = int(os.getenv("LEARNER_JUDGE_BACKFILL", "100"))
    # Turnos de charla por llamada agrupada del lote nocturno. Todo recibe
    # veredicto; el coste se controla AGRUPANDO, no omitiendo (doc 41 §3.4).
    LEARNER_CHAT_BATCH = int(os.getenv("LEARNER_CHAT_BATCH", "25"))
    # V1.0 (TIE v1, T2): Model Router mínimo. Hints de modelo barato/potente. Si
    # vacíos, el router cae al modelo del proveedor activo del AIManager. Cuando
    # exista el MEL (E1, plan aparte), estos settings los gestionan sus políticas
    # y `router.py` pasa a delegar en `mel.complete(capability=...)`.
    # [R7] TIE_FAST_MODEL/TIE_SMART_MODEL retirados: eran los hints de T2, previos
    # al MEL. Desde E2 quien elige modelo es el MEL (política activa + override de
    # tarea + pin de proyecto, configurable en Ajustes → Inteligencia). Dejarlos
    # habría sido un segundo mando que ya no movía nada.
    # Presupuesto de latencia DURO del contexto del MOS (ms). Si el enricher lo
    # excede, contexto vacío — el TIE nunca espera (mismo patrón que chat_service M4).
    TIE_CONTEXT_BUDGET_MS = int(os.getenv("TIE_CONTEXT_BUDGET_MS", "300"))
    # [A·VOZ-7, doc 32] TTL del contexto del MOS cacheado POR SESIÓN en la charla.
    # Dentro de una conversación el contexto de memoria a largo plazo es estable,
    # así que se resuelve una vez por (sesión, tema) y se reutiliza — menos
    # consultas al MOS y un prefijo de system prompt estable (no invalida el caché
    # de prompt del proveedor turno a turno). Se refresca al expirar, al cambiar de
    # tema, o cuando se escribe en memoria (para no dejar memoria fresca invisible).
    TIE_SESSION_CTX_TTL_S = int(os.getenv("TIE_SESSION_CTX_TTL_S", "600"))
    # Concurrencia de olas del executor (T3/V1.2). En V1.0 la ola es de tamaño 1
    # (secuencial); el semáforo entra en V1.2 con las olas paralelas.
    TIE_MAX_PARALLEL = int(os.getenv("TIE_MAX_PARALLEL", "3"))
    # [Sesión A, 2026-08-04] EL PRESUPUESTO DEL BUCLE PASA DE FIJO A BASADO EN
    # PROGRESO. El techo fijo (5/12 vueltas, TIE_TOOL_MAX_ITERS[_WRITE] — hoy
    # retirados) trataba igual a una misión que AVANZA (leyó el documento,
    # buscó, va a escribir — el caso real de Cordyceps necesitaba ~30 pasos
    # legítimos) que a una que gira en vacío. Subir el número habría sido un
    # parche: la tarea grande de mañana necesitaría 60. El criterio correcto es
    # el de Claude Code: el límite es "¿sigo progresando?", no "¿cuántos pasos
    # llevo?". Dos números lo gobiernan:
    #
    # TECHO DURO de seguridad por nodo: la única función legítima del número
    # total es cortar un bucle desbocado, no acotar el trabajo legítimo. Un
    # nodo que da 60 vueltas CON progreso real es una tarea grande, no un bug.
    TIE_TOOL_HARD_CEILING = int(os.getenv("TIE_TOOL_HARD_CEILING", "60"))
    # LÍMITE DE ATASCO: vueltas CONSECUTIVAS sin ninguna herramienta ejecutada
    # con éxito (JSON inválido, answer rechazado, tool denegada/fallida, permiso
    # no concedido…) tras las que el bucle se rinde con la causa real. Es EL
    # corte efectivo — y corta ANTES que el techo viejo cuando algo va mal (4
    # vueltas estériles, no 12). El detector de fallo IDÉNTICO de S9c sigue
    # cortando incluso antes (3 repeticiones exactas).
    TIE_TOOL_STALL_LIMIT = int(os.getenv("TIE_TOOL_STALL_LIMIT", "4"))
    # Timeout por llamada a herramienta dentro del bucle (segundos). El
    # ToolManager lo acota además a su propio máximo duro.
    TIE_TOOL_TIMEOUT_S = int(os.getenv("TIE_TOOL_TIMEOUT_S", "60"))
    # [Opt latencia 2026-07-21] Política del bucle de tool-use. El bucle se
    # ejecuta UNA VEZ POR ACCIÓN, así que su modelo domina la latencia de una
    # misión. Con la política de calidad del usuario (p.ej. custom→claude/opus)
    # cada paso tardaba 13-18s (medido en los logs del usuario). La elección
    # de herramienta es una decisión estructurada, no necesita el modelo más
    # potente. [2026-07-22] Default "speed": la política MEDIDA (mel/benchmark)
    # elige el modelo más rápido de ESTA máquina con un suelo mínimo de calidad
    # estructurada — antes "economy" (barato ≠ rápido: el local barato tardaba
    # 100s+ por paso en el equipo del usuario, medido). Si hiciera falta, pon
    # aquí otra política o fija un modelo con TIE_TOOL_MODEL.
    TIE_TOOL_POLICY = os.getenv("TIE_TOOL_POLICY", "speed")
    # Fija un modelo EXACTO para el bucle (ej. "claude_code:haiku"). Vacío = usar
    # TIE_TOOL_POLICY. Máxima prioridad si se define.
    TIE_TOOL_MODEL = os.getenv("TIE_TOOL_MODEL", "").strip()
    # [A·VOZ-8] La RESPUESTA de la conversación por VOZ se enruta por esta política,
    # no por la política de calidad activa del usuario. Motivo: en voz la fluidez
    # manda sobre la máxima calidad, y si el usuario tiene el chat en una política
    # pesada (custom→claude/opus) o en un local lento, cada respuesta hablada
    # tardaba segundos. "speed" = el modelo más RÁPIDO medido de ESTA máquina con
    # un suelo de calidad (mismo criterio que TIE_TOOL_POLICY; "economy" NO, porque
    # barato ≠ rápido — el local barato del usuario tarda 100s+). El chat de TEXTO
    # sigue usando la política elegida por el usuario. Vacío = sin override (usa la
    # política activa, como antes).
    VOICE_CHAT_POLICY = os.getenv("VOICE_CHAT_POLICY", "speed").strip()
    # [PU3, doc 35, 2026-07-30] `TIE_TOOL_APPROVAL_WAIT_S` existía para acotar
    # cuánto espera el bucle una respuesta de permiso (120s por defecto, luego
    # caducaba). Retirado por decisión explícita del usuario: ningún gate
    # caduca — se espera indefinidamente a que el usuario responda (con el
    # permiso pre-autorizado, A3b, la espera sigue siendo instantánea). Ver
    # `tie/toolloop.py::_wait_gate`.
    # [S4, doc 34 §10] Ventana deslizante del transcript del bucle de tool-use.
    # El transcript CRECE con cada iteracion y se reenviaba ENTERO en cada
    # llamada (observaciones de 4000 chars x 12 vueltas = ~50k chars al final):
    # el prompt de las ultimas vueltas era mayoritariamente historia vieja e
    # irrelevante, y cada token de mas es latencia. El PROMPT se acota a los
    # bloques de cabecera (objetivo + contexto + catalogo, SIEMPRE) + las
    # ultimas N interacciones; el transcript completo se conserva en memoria
    # para telemetria/debug. 0 = sin ventana (comportamiento anterior).
    TIE_TOOL_TRANSCRIPT_WINDOW = int(os.getenv("TIE_TOOL_TRANSCRIPT_WINDOW", "8"))
    # [S4·P5] Modelo/politica FIJOS para el clasificador de intents. Mismo patron
    # y mismo motivo que TIE_TOOL_MODEL/TIE_TOOL_POLICY del bucle: `classify`
    # corre en el camino caliente de CADA mensaje no trivial y domina el
    # "analizando". Con la politica de calidad del usuario (custom -> opus) eso
    # son decenas de segundos para una tarea que es puro parseo estructurado.
    # Vacio = sin modelo fijo, manda TIE_CLASSIFY_POLICY ("speed": el modelo
    # mas RAPIDO medido de esta maquina con suelo de calidad estructurada).
    TIE_CLASSIFY_MODEL = os.getenv("TIE_CLASSIFY_MODEL", "").strip()
    TIE_CLASSIFY_POLICY = os.getenv("TIE_CLASSIFY_POLICY", "speed").strip()

    # [S4 · NEW-2, doc 34 §10] DEADLINES del camino caliente. Antes NO habia ni
    # un `timeout` ni un `wait_for` en mel/executor.py, tie/intents.py ni
    # tie/router.py: el unico limite eran los 180 s del provider de Ollama, y
    # con cadena de fallback eran 180 s POR SALTO. Sin plazo, el chat podia
    # pasar minutos en "analizando" sin escribir una linea — lo que la campaña
    # 00 leyo como "cuelgue" (no lo era: el event loop seguia vivo; era falta
    # de plazo). 0 desactiva el deadline correspondiente.
    #   · REQUEST: una llamada completa a un proveedor. Vencer = fallo
    #     "timeout" -> breaker + salto al siguiente candidato de la cadena.
    #   · STREAM_FIRST_CHUNK: solo el PRIMER chunk (los siguientes ya fluyen).
    #   · CLASSIFY: el clasificador entero; vencer degrada por el MISMO camino
    #     que ya existe para su error (accion determinista o charla).
    MEL_REQUEST_DEADLINE_S = int(os.getenv("MEL_REQUEST_DEADLINE_S", "120"))
    MEL_STREAM_FIRST_CHUNK_S = int(os.getenv("MEL_STREAM_FIRST_CHUNK_S", "60"))
    TIE_CLASSIFY_DEADLINE_S = int(os.getenv("TIE_CLASSIFY_DEADLINE_S", "60"))
    # Latido del stream: cada cuantos segundos se emite un `status` mientras se
    # espera al clasificador/planner/accion. Objetivo medible de S4: NINGUN
    # turno de chat por encima de este plazo sin respuesta NI evento. 0 = off.
    TIE_HEARTBEAT_S = int(os.getenv("TIE_HEARTBEAT_S", "15"))

    # [S5 · NEW-1, doc 34 §10] TUBERIA ENTRE PASOS. Cuantos caracteres del
    # resultado de CADA nodo del que depende un paso se le pasan a ese paso.
    # EL HUECO QUE CIERRA: `_execute_node` construia el contexto del nodo SOLO
    # con memoria del MOS; el resultado de sus dependencias no llegaba por
    # ningun camino, asi que "lee X y haz Y con ello" solo funcionaba si ambas
    # cosas caian en el MISMO nodo. En cuanto el planner las separaba, el
    # segundo paso trabajaba a ciegas y lo decia con una disculpa educada
    # ("el contenido completo no llego a cargarse en la sesion" — era LITERAL).
    TIE_NODE_HANDOFF_CHARS = int(os.getenv("TIE_NODE_HANDOFF_CHARS", "12000"))
    # Presupuesto de la observacion de una tool que DEVUELVE CONTENIDO
    # (document.read_*, filesystem.read_file, browser.get_text/get_html). El
    # tope general de 4000 es correcto para un `list_dir`, pero descabezaba un
    # GDD de 20 paginas — y ademas recortaba el JSON YA SERIALIZADO, asi que
    # cuanto contenido real sobrevivia dependia del ruido de estructura.
    TIE_OBSERVATION_CHARS_CONTENT = int(os.getenv("TIE_OBSERVATION_CHARS_CONTENT", "24000"))

    # [S3, doc 34 §10] Presupuesto de llamadas LLM por CAMINO — medido, no solo
    # "va lento". `telemetry.record("path", name=...)` etiqueta cada turno con
    # el camino que tomó (chat/direct/planned/multi, ver tie/pipeline.py y
    # orchestrator/__init__.py); `mission_timeline()` compara el conteo real de
    # eventos "llm_call" contra el presupuesto de ese camino. BUDGET_LLM_CHAT=0
    # es un techo teórico: el camino corto NUNCA crea mission_id (A·VOZ-3), así
    # que hoy no hay traza a la que se le pueda aplicar. BUDGET_LLM_DIRECT cubre
    # un bucle de tool-use de acción mecánica (un solo encargo, sin planner).
    # BUDGET_LLM_PLANNED cubre planificar + ejecutar un grafo de 2-3 nodos.
    # BUDGET_LLM_MULTI_PER_OBJECTIVE es el mismo techo que planned, aplicado a
    # cada objetivo independiente de una orquestación multi-encargo (R2).
    BUDGET_LLM_CHAT = int(os.getenv("BUDGET_LLM_CHAT", "0"))
    BUDGET_LLM_DIRECT = int(os.getenv("BUDGET_LLM_DIRECT", "6"))
    BUDGET_LLM_PLANNED = int(os.getenv("BUDGET_LLM_PLANNED", "12"))
    BUDGET_LLM_MULTI_PER_OBJECTIVE = int(os.getenv("BUDGET_LLM_MULTI_PER_OBJECTIVE", "8"))

    # [2026-07-19] El navegador de Aithera se ve. Si navega por ti, tienes que
    # poder mirarlo y tomar el control. Solo se pone a True para automatismos de
    # fondo donde una ventana emergente molestaria.
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").strip().lower() in ("1", "true", "yes")
    # [2026-07-23, petición del usuario] CHROME REAL, no el Chromium "de test":
    # canal del navegador ("chrome" = el Google Chrome instalado; "chromium" =
    # el bundled de Playwright como respaldo si Chrome no está).
    BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "chrome").strip().lower()
    # Perfil PERSISTENTE de Aithera: cookies, sesiones (Google incluida) y
    # consentimientos aceptados SOBREVIVEN entre misiones y reinicios. El
    # usuario inicia sesión en Google UNA vez en este perfil y queda iniciada.
    # NOTA técnica: no puede usarse el perfil de uso diario del usuario —
    # Chrome ≥136 bloquea la automatización sobre el user-data-dir por defecto
    # (protección anti-infostealers) y además su Chrome abierto lo tiene
    # bloqueado. Perfil propio persistente = mismo efecto práctico, sin pelea.
    BROWSER_PROFILE_DIR = os.getenv(
        "BROWSER_PROFILE_DIR",
        os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Aithera", "chrome-profile"),
    )

    # --- V1.0 (R2, Orquestador — doc 23) ---
    # Kill-switch: con False, el Gateway sigue enganchado a `tie.handle` y todo
    # se comporta exactamente como antes de este bloque.
    ORCH_ENABLED = os.getenv("ORCH_ENABLED", "true").lower() in ("1", "true", "yes")
    # Misiones simultáneas como máximo. Protege al MEL y sobre todo a los modelos
    # LOCALES: lanzar 6 misiones a la vez contra un Ollama con un modelo cargado
    # las pone a competir por la misma GPU y todas van más lentas.
    ORCH_MAX_CONCURRENT = int(os.getenv("ORCH_MAX_CONCURRENT", "3"))
    # Profundidad máxima de anidamiento (objetivo → sub-objetivos). 2 permite el
    # caso real ("15 canales" → un trabajo por canal) sin abrir la puerta a una
    # recursión que se dispare sola.
    ORCH_MAX_DEPTH = int(os.getenv("ORCH_MAX_DEPTH", "2"))

    # V1.0 (MEL E1b, doc 19 §5.4/doc 22 §3·E1b): cada cuántos días se re-investigan
    # las capacidades de los modelos configurados (el número que pidió el usuario).
    MEL_RESEARCH_REFRESH_DAYS = int(os.getenv("MEL_RESEARCH_REFRESH_DAYS", "14"))
    # [P4, doc 34, 2026-07] Cuántos modelos investiga como máximo el job NOCTURNO
    # del auto-catálogo en cada pasada. Antes se disparaba a los 900s del arranque
    # (podía coincidir con el usuario ya trabajando) e investigaba TODOS los
    # configurados de golpe (hasta 16 en la campaña de test en vivo) — 45 minutos
    # compitiendo por el proveedor activo. Con esto: nocturno (job cron junto a los
    # del MOS) y como mucho 1 modelo por noche, repartido en varias noches.
    MEL_RESEARCH_MAX_PER_NIGHT = int(os.getenv("MEL_RESEARCH_MAX_PER_NIGHT", "1"))

    # V0.8 (hardening): CORS restringido. Además de localhost (cubierto por
    # regex) y file:// de Electron (origen 'null'), se pueden declarar orígenes
    # extra por env como CSV — p.ej. la IP de la red local al exponer la web:
    # CORS_ALLOWED_ORIGINS="http://192.168.1.50:8000,http://192.168.1.50:5173"
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "")

    # AI Settings
    DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3")

    # Ollama settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")

    # Anthropic settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # MiniMax settings (FIX V0.3 P5, mantenido en V0.4)
    MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7-highspeed")

    # Database (FIX V0.4): leemos DATABASE_URL del entorno. Si no existe,
    # caemos al SQLite en %APPDATA%/Aithera/aithera.db para mantener
    # compatibilidad con instalaciones existentes que aun no han migrado.
    @property
    def DATABASE_URL(self) -> str:
        url = os.getenv("DATABASE_URL")
        if url:
            return url
        # Fallback SQLite para no romper el arranque si no hay PostgreSQL.
        sqlite_path = os.path.join(
            os.environ.get("APPDATA") or ".", "Aithera", "aithera.db"
        )
        return f"sqlite:///{sqlite_path}"


settings = Settings()


# Compatibilidad V0.4 (Fase 1b): exponer DATABASE_URL como constante a nivel
# de modulo, tal y como espera el codigo de database.py tras la migracion.
# Si el .env no define DATABASE_URL, mantenemos SQLite como fallback para no
# romper instalaciones que aun no han hecho el upgrade.
DATABASE_URL = settings.DATABASE_URL
