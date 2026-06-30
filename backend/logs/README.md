# Directorio de Logs - Aithera

Este directorio contiene los archivos de log del sistema Aithera.

## Archivos de Log

### system.log
**Propósito**: Registro general de eventos del sistema
**Nivel**: INFO, WARNING, DEBUG
**Contenido**: Eventos normales, advertencias, información de debug
**Rotación**: 5MB máximo por archivo, 3 backups conservados

### errors.log
**Propósito**: Registro exclusivo de errores
**Nivel**: ERROR, CRITICAL
**Contenido**: Todos los errores y excepciones del sistema
**Rotación**: 5MB máximo por archivo, 3 backups conservados

## Formato de Logs

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] Message
```

Ejemplo:
```
[2024-01-15 14:30:45] [INFO] [startup] Base de datos inicializada correctamente
[2024-01-15 14:31:20] [ERROR] [api.projects] Error al crear proyecto: ValidationError
[2024-01-15 14:32:10] [WARNING] [ai.manager] Proveedor Ollama no responde
```

## Módulos Registrados

- **main**: Aplicación principal FastAPI
- **startup**: Eventos de inicio
- **shutdown**: Eventos de apagado
- **health**: Health checks
- **api.***: Endpoints de API (projects, tasks, calendar, etc.)
- **ai.***: Sistema de IA
- **agents.***: Agentes de IA
- **exception_handler**: Manejador global de excepciones

## Cómo Ver Logs

### Ver últimos errores (PowerShell)
```powershell
Get-Content -Tail 20 .\backend\logs\errors.log
```

### Ver últimos eventos del sistema (PowerShell)
```powershell
Get-Content -Tail 30 .\backend\logs\system.log
```

### Buscar errores específicos (PowerShell)
```powershell
Select-String -Path .\backend\logs\errors.log -Pattern "ConnectionError"
```

### Ver logs en tiempo real (PowerShell)
```powershell
Get-Content -Wait .\backend\logs\system.log
```

## Configuración

El sistema de logs se configura en `backend/app/core/logging_config.py`.

Parámetros configurables:
- **Directorio de logs**: `backend/logs/`
- **Tamaño máximo**: 5MB por archivo
- **Backups**: 3 archivos de backup
- **Encoding**: UTF-8

## Buenas Prácticas

1. **Revisar logs regularmente** - Especialmente antes de hacer cambios
2. **Limpiar logs antiguos** - Los backups rotates se mantienen automáticamente
3. **No commitear logs** - Agregar `.gitignore` si no existe
4. **Niveles apropiados** - Usar log_info para info general, log_error solo para errores

## Ejemplo de Uso en Código

```python
from app.core.logging_config import log_info, log_error, log_warning

# Registrar información
log_info("mi_modulo", "Operación completada")

# Registrar advertencia
log_warning("mi_modulo", "Recurso bajo")

# Registrar error
try:
    # código que puede fallar
    pass
except Exception as e:
    log_error("mi_modulo", e, "Contexto adicional")
```

---

*Nota: Este directorio es creado automáticamente por el sistema de logging.*
