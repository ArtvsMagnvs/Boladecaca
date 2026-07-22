# Aithera Core Configuration (V0.7)
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App settings
    APP_NAME = "Aithera"
    # V1.0 R7 (cierre del bloque ORQUESTRATOR, doc 23) - bump sincronizado con
    # main.py y frontend/package.json. Tag v0.9.5. El cierre de V1.0 COMPLETO
    # (tras el MVP-beta) sera v1.0.0.
    VERSION = "0.9.5"
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
    # Concurrencia de olas del executor (T3/V1.2). En V1.0 la ola es de tamaño 1
    # (secuencial); el semáforo entra en V1.2 con las olas paralelas.
    TIE_MAX_PARALLEL = int(os.getenv("TIE_MAX_PARALLEL", "3"))
    # V1.0 (R1, doc 23): vueltas máximas del bucle de tool-use por nodo
    # (elegir→ejecutar→observar). 5 basta para encadenar varias herramientas sin
    # que un modelo que se atasca queme tokens indefinidamente.
    TIE_TOOL_MAX_ITERS = int(os.getenv("TIE_TOOL_MAX_ITERS", "5"))
    # [S2, B-1] Presupuesto AMPLIADO para nodos con herramientas de ESCRITURA
    # (filesystem/shell/git/…): crear un proyecto con varios archivos no cabe en
    # 5 vueltas — era parte del techo estructural del fallo B. La selección la
    # hace el runtime según las tools del nodo (ver runtime.py::_iters_for).
    TIE_TOOL_MAX_ITERS_WRITE = int(os.getenv("TIE_TOOL_MAX_ITERS_WRITE", "12"))
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
    # Cuánto espera el bucle a que el usuario conteste una petición de permiso
    # para una acción sensible. Si no contesta a tiempo, el paso sigue SIN esa
    # acción y lo dice — la aprobación NO se cancela: queda pendiente en la UI.
    # Con el permiso pre-autorizado (A3b) la espera es instantánea.
    TIE_TOOL_APPROVAL_WAIT_S = int(os.getenv("TIE_TOOL_APPROVAL_WAIT_S", "120"))

    # [2026-07-19] El navegador de Aithera se ve. Si navega por ti, tienes que
    # poder mirarlo y tomar el control. Solo se pone a True para automatismos de
    # fondo donde una ventana emergente molestaria.
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").strip().lower() in ("1", "true", "yes")

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
