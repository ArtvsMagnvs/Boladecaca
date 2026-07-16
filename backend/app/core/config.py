# Aithera Core Configuration (V0.7)
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App settings
    APP_NAME = "Aithera"
    # V0.9 (Automation Engine + ApprovalGate, cierre de bloque A1-A4) - bump
    # sincronizado con main.py y frontend/package.json. Tag v0.9.0.
    VERSION = "0.9.0"
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
