# FASE 1 — V0.3: Estabilización + Hub Completo
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.3.0
**Prerrequisito**: Aithera V0.2.0 funcionando
**Sesiones**: 2

---

## SESIÓN 1: Fixes de bugs conocidos

**Tiempo estimado**: 2-3 horas
**Empieza con**: `git status` limpio en V0.2.0. Leer `CLAUDE.md` sección 19 para contexto de cada bug.

### Fix P1 — AgentResponse incompleto

**Archivo**: `backend/app/db/schemas.py`

```python
class AgentResponse(BaseModel):
    id: int
    name: str
    agent_type: Optional[str] = None        # AÑADIR
    description: Optional[str] = None       # AÑADIR
    system_prompt: Optional[str] = None
    is_active: bool = True                  # AÑADIR
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
```

### Fix P2 — Voice status anidado vs plano

**Archivo**: `backend/app/api/endpoints/voice.py`

El endpoint `GET /status` debe devolver directamente (sin clave `voice` anidada):
```python
return {
    "configured": bool(api_key),
    "voices_count": len(voices),
    "message": "ElevenLabs configurado" if api_key else "Sin API key"
}
```

### Fix P3 — .gitignore

**Archivo**: `.gitignore` en la raíz del proyecto. Añadir estas líneas si no están:
```
backend/.env
backend/*.db
*.db
```

### Fix P4 — backend/aithera.db en git

```bash
git rm --cached backend/aithera.db
git commit -m "chore: eliminar aithera.db huérfano del repositorio"
```

### Fix P5 — Modelo MiniMax por defecto

Cambiar en tres sitios:

`backend/app/ai/providers/minimax_provider.py`:
```python
default_model_name = "MiniMax-M2.7-highspeed"  # era "MiniMax-M2.7"
```

`backend/app/ai/catalog.py`:
```python
"default_model": "MiniMax-M2.7-highspeed"  # era "MiniMax-M2.7"
```

`backend/app/ai/ai_manager.py` — en `_bootstrap_from_env`:
```python
seeds.append(("minimax", os.getenv("MINIMAX_MODEL", "MiniMax-M2.7-highspeed"), minimax_key, None))
# era "MiniMax-M2.7"
```

### Fix P6 — Versión inconsistente en root()

`backend/app/main.py`:
```python
@app.get("/")
def root():
    return {"name": "Aithera", "version": "0.3.0", "status": "running"}
```

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] El backend arranca sin warnings de SQLAlchemy
- [ ] `GET /api/voice/status` devuelve estructura plana `{ configured, voices_count, message }`
- [ ] `GET /api/agents/` devuelve `agent_type`, `description`, `is_active` en cada agente
- [ ] `GET /` devuelve `"version": "0.3.0"`
- [ ] MiniMax responde con modelo `MiniMax-M2.7-highspeed` al probar desde Settings
- [ ] `.gitignore` incluye `backend/.env` y `backend/*.db`
- [ ] `backend/aithera.db` ya no aparece en `git status`

### 🛑 Para aquí

Todos los checks pasan. Commit: `fix: V0.2 bugs — AgentResponse, voice status, gitignore, MiniMax model`.
La Sesión 2 implementa el Hub.

---

## SESIÓN 2: Hub Layout completo

**Tiempo estimado**: 3-4 horas
**Empieza con**: el backend de Sesión 1 funcionando. NO modificar `AICore.tsx` en ningún momento.

### Layout del Hub

```
┌─────────────────────────────────────────────────────────────────┐
│  PANEL IZQUIERDO    │    AI CORE (centro)    │  PANEL DERECHO   │
│  ─────────────────  │  ───────────────────   │  ─────────────── │
│  Proyectos activos  │                        │  Próximos eventos│
│  Tareas pendientes  │   [Esfera 3D animada]  │  Chat reciente   │
│  Agentes activos    │                        │  (Email: V0.7)   │
├─────────────────────┴────────────────────────┴──────────────────┤
│  BARRA DE ESTADO: Backend ● | IA: MiniMax/M2.7-hs ✓ | Voz: OFF  │
└─────────────────────────────────────────────────────────────────┘
```

### Estructura CSS Grid en `frontend/src/pages/Hub.tsx`

```css
grid-template-columns: 280px 1fr 280px;
grid-template-rows: 1fr auto;
height: 100vh;
```

### Panel Izquierdo — endpoints

```
GET /api/projects/?limit=5&status=active   → top 5 proyectos activos
GET /api/tasks/?limit=5&status=pending     → top 5 tareas pendientes
GET /api/agents/                           → filtrar is_active=true en frontend
```

Mostrar prioridad con puntos de color: rojo (high), amarillo (medium), verde (low).

### Panel Derecho — endpoints

```
GET /api/calendar/events?limit=5           → próximos 5 eventos ordenados por start_date ASC
GET /api/chat/history?limit=3              → últimas 3 conversaciones
```

Email: mostrar `<p className="text-ink/40">Email disponible en V0.7</p>`

### Barra de estado inferior

Usar `useAppStore` (ya existe):
- `backendConnected` → punto `●` verde/rojo + texto
- `aiStatus.provider` + `aiStatus.model` → "IA: MiniMax / M2.7-highspeed"
- `aiStatus.healthy` → ✓ o ✗
- Voz: llamar `GET /api/voice/status` al montar → "Voz: ON / OFF"

### Polling de datos (cada 30 segundos)

```typescript
useEffect(() => {
  loadHubData();
  const interval = setInterval(loadHubData, 30000);
  return () => clearInterval(interval);
}, []);
```

### Interactividad

- Clic en proyecto → `navigate('/projects')`
- Clic en tarea → `navigate('/tasks')`
- Clic en AI Core (esfera) → `navigate('/chat')`

### Bump de versión

- `backend/app/main.py`: `version="0.3.0"`
- `backend/app/core/config.py`: `VERSION = "0.3.0"`
- `frontend/package.json`: `"version": "0.3.0"`

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] El Hub muestra proyectos activos con datos reales de la API
- [ ] El Hub muestra tareas pendientes con datos reales
- [ ] El Hub muestra próximos eventos de calendario
- [ ] La barra de estado inferior muestra el estado real del backend y la IA
- [ ] El polling cada 30s funciona (verificar en Network tab de DevTools)
- [ ] Clic en un proyecto navega a `/projects`
- [ ] El AI Core sigue animándose (no se rompe por el nuevo layout)
- [ ] `GET /` devuelve `"version": "0.3.0"`

### 🛑 Para aquí

Aithera V0.3.0 completada. Commit: `feat: V0.3.0 — Hub layout completo con datos reales`.

**Siguiente fase**: `Fase_1b_PostgreSQL_Migration_V04.md`

---

## ARCHIVOS MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/db/schemas.py`, `backend/app/api/endpoints/voice.py`, `backend/app/ai/providers/minimax_provider.py`, `backend/app/ai/catalog.py`, `backend/app/ai/ai_manager.py`, `backend/app/main.py`, `backend/app/core/config.py`, `.gitignore`

**Sesión 2**: `frontend/src/pages/Hub.tsx`, `frontend/package.json`
