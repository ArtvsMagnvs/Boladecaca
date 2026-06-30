# Aithera Backend - Main Application
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from app.db.database import engine, Base
from app.api.endpoints import config, projects, tasks, calendar, ai, chat, agents, email_assistant
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
    
    yield
    
    # Shutdown: cleanup if needed
    log_info("shutdown", "Cerrando Aithera Backend...")


# Create FastAPI app
app = FastAPI(
    title="Aithera API",
    description="Sistema Operativo de IA - Backend API",
    version="0.1.0",
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
app.include_router(email_assistant.router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "Aithera",
        "version": "0.1.0",
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
