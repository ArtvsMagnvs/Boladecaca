# Aithera Backend - Main Application
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from app.db.database import engine, Base
from app.core.config import settings
from app.api.endpoints import config, projects, tasks, calendar, ai, chat, agents, voice, tools, memory
# V0.8 (Fase 5 Clientes): router de configuracion del canal Telegram.
from app.api.endpoints import telegram as telegram_endpoints
# V0.7.2 (Sprint 2, PLAN_MAESTRO_2026 B4): god-endpoint de email dividido en
# 7 routers de dominio + app/services/email_service.py. Todos comparten
# prefix='/email'; la superficie publica /api/email es identica (contratos).
from app.api.endpoints import (
    email_auth,
    email_inbox,
    email_compose,
    email_auto_reply,
    email_processing,
    email_meetings,
    email_activity,
)
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5: importar el paquete
# `app.tools` dispara el auto-registro del ToolManager (filesystem/shell/git).
# Sin este import, `GET /api/tools/` devolveria [] y el AgentManager no podria
# ejecutar nada. Importar como efecto secundario es el patron estandar
# para inicializacion en Python.
import app.tools  # noqa: F401  (registra tool_manager al importar)
# V0.6 (Fase 3 Memory System): importamos el memory_manager para que se
# inicialice al arrancar. Si ChromaDB/sentence-transformers fallan,
# el constructor degrada gracefully (no rompe el backend).
from app.memory.memory_manager import memory_manager
from app.core.logging_config import get_system_logger, log_error, log_info

# Configurar logger
logger = get_system_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    log_info("startup", "Iniciando Aithera Backend...")
    try:
        Base.metadata.create_all(bind=engine)
        log_info("startup", "Base de datos inicializada correctamente")
    except Exception as e:
        log_error("startup", e, "Error al inicializar base de datos")
        raise

    # V0.6 (Fase 3): arrancamos el sistema de memoria semantica. La primera
    # vez descarga el modelo de embeddings (sentence-transformers, ~80MB),
    # por eso este mensaje puede tardar 1-2 min en aparecer.
    if memory_manager.is_healthy():
        stats = memory_manager.get_stats()
        log_info(
            "startup",
            f"Memory system listo — {stats['conversations']} conv, "
            f"{stats['user_context']} ctx, {stats['documents']} docs",
        )
    else:
        log_error(
            "startup",
            Exception(memory_manager.get_init_error() or "unknown"),
            "Memory system no disponible (chat seguira funcionando sin memoria)",
        )

    # V0.8 (Fase 5 Clientes): arranque de canales sobre el Gateway. El adapter
    # de Telegram se registra SOLO si hay token en Config; si falta la lib
    # python-telegram-bot o el token, se omite y el backend sigue (principio 1:
    # no romper lo que funciona). Los adapters son piezas finas: la logica de
    # negocio vive detras del Gateway. Ver 06_GATEWAY_V08_DISENO.md.
    try:
        from app.gateway.gateway import gateway
        from app.db.database import SessionLocal
        from app.db.models import Config

        _db = SessionLocal()
        try:
            _tok = _db.query(Config).filter(Config.key == "telegram_bot_token").first()
            _ids = _db.query(Config).filter(Config.key == "telegram_chat_id").first()
        finally:
            _db.close()

        # El token se guarda cifrado (DPAPI); lo desciframos para el adapter.
        from app.core import secrets
        token = secrets.decrypt((_tok.value if _tok else "") or "").strip()
        if token:
            from app.gateway.adapters.telegram_adapter import TelegramAdapter
            allowed = {
                c.strip()
                for c in ((_ids.value if _ids else "") or "").split(",")
                if c.strip()
            }
            gateway.register(TelegramAdapter(token, allowed))
            await gateway.start_all()
            log_info(
                "startup",
                f"Canal Telegram iniciado ({len(allowed)} chat_id autorizados)",
            )
        else:
            log_info("startup", "Telegram no configurado (sin token) — canal omitido")
    except Exception as e:
        log_error(
            "startup", e,
            "No se pudo iniciar el canal Telegram (backend sigue sin ese canal)",
        )

    yield

    # Shutdown: parada limpia de los canales del Gateway (polling de Telegram).
    log_info("shutdown", "Cerrando Aithera Backend...")
    try:
        from app.gateway.gateway import gateway
        await gateway.stop_all()
    except Exception as e:
        log_error("shutdown", e, "Error deteniendo los canales del Gateway")

    # FIX (audit sistema de audio): el httpx.AsyncClient de ElevenLabs
    # (creado una vez al importar app.voice.elevenlabs_voice) nunca se
    # cerraba en shutdown. En un solo proceso de desarrollo no se nota, pero
    # es la limpieza correcta de un cliente HTTP con conexiones persistentes.
    try:
        from app.voice.elevenlabs_voice import voice_client as _el_client
        await _el_client.close()
    except Exception as e:
        log_error("shutdown", e, "Error cerrando el cliente HTTP de ElevenLabs")


# Create FastAPI app
app = FastAPI(
    title="Aithera API",
    description="Sistema Operativo de IA - Backend API",
    # V0.7.3 (Sprint 4 cierre fase Email Assistant - bump sincronizado
    # con root(), core/config.py y frontend/package.json).
    version="0.8.0",
    lifespan=lifespan
)

# CORS middleware — V0.8 (hardening): ya NO wildcard. Se permiten:
#  - localhost / 127.0.0.1 en cualquier puerto (regex) → Vite dev + build local
#  - "null" → Electron carga la UI con file:// y envía Origin: null
#  - orígenes extra declarados en Settings.CORS_ALLOWED_ORIGINS (IPs de LAN)
# Bloqueante antes de exponer a la red: una web maliciosa en el navegador ya no
# puede llamar al backend (su origen no está en la lista). El PIN/token de red
# es una capa aparte, pendiente para cuando se sirva la web (post-V1.0).
_default_cors_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",  # Vite dev server
    "http://localhost:8000", "http://127.0.0.1:8000",  # build servido por FastAPI
    "null",                                             # Electron (file://)
]
_extra_cors_origins = [
    o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_cors_origins + _extra_cors_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(email_auth.router, prefix="/api")
app.include_router(email_inbox.router, prefix="/api")
app.include_router(email_compose.router, prefix="/api")
app.include_router(email_auto_reply.router, prefix="/api")
app.include_router(email_processing.router, prefix="/api")
app.include_router(email_meetings.router, prefix="/api")
app.include_router(email_activity.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
# V0.5 (Fase 2 AgentManager + ExecutionEngine): herramientas del engine.
app.include_router(tools.router, prefix="/api")
# V0.6 (Fase 3 Memory System): endpoints de memoria semantica.
app.include_router(memory.router, prefix="/api")
# V0.8 (Fase 5 Clientes): configuracion del canal Telegram (status/configure).
app.include_router(telegram_endpoints.router, prefix="/api")


@app.get("/")
def root():
    """V0.7.3 (Sprint 4 cierre fase Email Assistant - bump sincronizado con FastAPI
    app.version y core/config.py (VERSION = 0.7.1))."""
    return {
        "name": "Aithera",
        "version": "0.8.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    log_info("health", "Health check solicitado")
    return {"status": "healthy"}


# Exception handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura y loguea todas las excepciones no manejadas."""
    error_trace = traceback.format_exc()
    log_error(
        "exception_handler", 
        exc, 
        f"Path: {request.url.path} | Method: {request.method}"
    )
    logger.error(f"Traceback completo:\n{error_trace}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc),
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
