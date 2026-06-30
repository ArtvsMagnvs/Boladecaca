# Logging Configuration - Aithera System Logger
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Crear directorio de logs si no existe
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Archivos de log
SYSTEM_LOG = LOGS_DIR / "system.log"
DESKTOP_LOG = LOGS_DIR / "desktop.log"
ERROR_LOG = LOGS_DIR / "errors.log"


def setup_logger(name: str, log_file: Path, level=logging.INFO) -> logging.Logger:
    """
    Configura y retorna un logger con salida a archivo y consola.
    
    Args:
        name: Nombre del logger (típicamente __name__ del módulo)
        log_file: Ruta al archivo de log
        level: Nivel de logging (default: INFO)
    
    Returns:
        Logger configurado
    """
    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicar handlers si el logger ya existe
    if logger.handlers:
        return logger
    
    # Formato del log
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo con rotación (max 5MB por archivo, máximo 3 archivos)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_system_logger(name: str = "aithera") -> logging.Logger:
    """Obtiene el logger del sistema."""
    return setup_logger(name, SYSTEM_LOG)


def get_error_logger() -> logging.Logger:
    """Obtiene el logger de errores (solo ERROR y superiores)."""
    return setup_logger("aithera.error", ERROR_LOG, level=logging.ERROR)


def log_error(module: str, error: Exception, context: str = ""):
    """
    Registra un error con contexto adicional.
    
    Args:
        module: Nombre del módulo donde ocurrió el error
        error: Excepción capturada
        context: Información adicional de contexto
    """
    logger = get_error_logger()
    error_msg = f"[{module}] {type(error).__name__}: {str(error)}"
    if context:
        error_msg += f" | Context: {context}"
    logger.error(error_msg)


def log_info(module: str, message: str):
    """Registra un mensaje de información."""
    logger = get_system_logger()
    logger.info(f"[{module}] {message}")


def log_warning(module: str, message: str):
    """Registra un mensaje de advertencia."""
    logger = get_system_logger()
    logger.warning(f"[{module}] {message}")


def log_debug(module: str, message: str):
    """Registra un mensaje de debug."""
    logger = get_system_logger()
    logger.debug(f"[{module}] {message}")


def log_critical(module: str, message: str):
    """Registra un mensaje crítico."""
    logger = get_system_logger()
    logger.critical(f"[{module}] {message}")


# Decorador para logging automático de funciones
def log_function_call(logger_name: str = "aithera"):
    """
    Decorador para logging automático de llamadas a funciones.
    
    Uso:
        @log_function_call("mi_modulo")
        def mi_funcion():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_system_logger(logger_name)
            func_name = func.__name__
            logger.debug(f"Llamando {func_name} con args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} completado exitosamente")
                return result
            except Exception as e:
                log_error(logger_name, e, f"Error en {func_name}")
                raise
        return wrapper
    return decorator


# Ejemplo de uso integrado en FastAPI (ver main.py para implementación)
if __name__ == "__main__":
    # Prueba del sistema de logging
    logger = get_system_logger("test")
    logger.info("Sistema de logging iniciado")
    logger.warning("Este es un mensaje de prueba")
    logger.error("Este es un error de prueba")
