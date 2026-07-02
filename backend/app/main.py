# Aithera Backend - Main Application
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from app.db.database import engine, Base
from app.api.endpoints import config, projects, tasks, calendar, ai, chat, agents, voice, tools, memory
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

    yield

    # Shutdown: cleanup if needed
    log_info("shutdown", "Cerrando Aithera Backend...")


# Create FastAPI app
app = FastAPI(
    title="Aithera API",
    description="Sistema Operativo de IA - Backend API",
    # V0.7.3 (Sprint 4 cierre fase Email Assistant - bump sincronizado
    # con root(), core/config.py y frontend/package.json).
    version="0.7.3",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/")
def root():
    """V0.7.3 (Sprint 4 cierre fase Email Assistant - bump sincronizado con FastAPI
    app.version y core/config.py (VERSION = 0.7.1))."""
    return {
        "name": "Aithera",
        "version": "0.7.3",
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
