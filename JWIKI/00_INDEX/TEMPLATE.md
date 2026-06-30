# TEMPLATE — Plantilla obligatoria de documento JWIKI

> Copia este archivo como punto de partida. **Llena TODAS las secciones.** Si una sección
> no aplica, escribe "No aplica (razón)" — no la dejes vacía.

---

```markdown
# <Título del documento>

## Resumen
(2-4 frases. Qué es, para qué sirve, dónde encaja en el ecosistema de asistentes JARVIS.)

## Objetivo
(Qué pretende resolver este documento. Una pregunta a la que responde.)

## Estado
🟢 Verificado / 🟡 En progreso / 🔴 VERIFICACIÓN PENDIENTE / ⚫ Abandonado

## Versiones compatibles
| Proyecto | Versión | Notas |
|---|---|---|
| OpenClaw | ... | ... |
| OpenHuman | ... | ... |
| Aithera | V0.7+ | Documentado en este repo |

## Proyectos compatibles
(Lista de proyectos OSS donde este sistema/patrón está presente)

## Dependencias
(Lista de otros documentos JWIKI o sistemas externos requeridos)

## Arquitectura
(Descripción técnica high-level. Diagrama ASCII o mermaid si aplica.)

## Descripción técnica
(Profundización: cómo funciona, qué hace cada componente, qué algoritmos usa.)

## Flujo interno
(Diagrama de secuencia o lista de pasos numerados.)

## Call Stack / API
(Si es código: funciones que llama y en qué orden. Ejemplo:)

```
ChatRequest → POST /api/chat/stream
  → AIManager.chat_stream()
    → Provider.generate_stream()
      → chunks via SSE
        → onChunk en cliente
```

## Diagramas
(ASCII, mermaid, o links a imágenes en `assets/`.)

## Código relacionado
(Path exacto en repos OSS con commit SHA si posible)

- `https://github.com/openclaw/openclaw/blob/<sha>/path/to/file.ts`
- `https://github.com/tinyhumansai/openhuman/blob/<sha>/path/to/file.rs`
- `https://github.com/open-jarvis/OpenJarvis/blob/<sha>/path/to/file.py`

## Ejemplos
(Código copy-paste ready. Indicar proyecto + versión + requisitos.)

```python
# Ejemplo: añadir un proveedor IA custom a Aithera
# Archivo: backend/app/ai/providers/my_provider.py
from app.ai.providers.openai_compatible import OpenAICompatibleProvider

class MyProvider(OpenAICompatibleProvider):
    default_model_name = "my-model-v1"
    base_url = "https://api.myservice.io/v1"
```

## Buenas prácticas
- ✅ Patrón recomendado
- ✅ Otro patrón recomendado

## Errores comunes
- ❌ No hacer X (porque...)
- ❌ No hacer Y (porque...)

## Breaking Changes
(Lista de cambios incompatibles entre versiones)

| Versión | Cambio | Impacto |
|---|---|---|
| MiniMax API 2024 → 2026 | Endpoint cambió de `api.minimax.chat` a `api.minimax.io` | Requiere actualizar URL |
| React 17 → 18 | Strict mode double-render | Streaming libs necesitan ajuste |

## Cambios entre versiones
(Tabla diff de versiones. Idealmente generada automáticamente desde git log.)

## Impacto sobre otros sistemas
(Qué otros dominios o features se ven afectados por cambios aquí)

## Referencias cruzadas
- [01_LANDSCAPE/projects.md#openclaw](../01_LANDSCAPE/projects.md#openclaw)
- [05_AI_PROVIDERS/openai.md](../05_AI_PROVIDERS/openai.md)
- [06_AGENTS/patterns.md](../06_AGENTS/patterns.md)

## Fuentes
(URL + fecha de acceso + autor)

1. https://github.com/openclaw/openclaw/blob/main/README.md — acceso 2026-06-30
2. https://openclaw.ai/ — acceso 2026-06-30
3. Paper arXiv:2601.02577 "Orchestral AI" — 2026-01-05

## Nivel de confianza
(0-100%. 100 = código revisado + 3+ fuentes independientes. <50 = 🟡.)

## Pendientes
- [ ] Verificar comportamiento en OpenHuman v0.53+
- [ ] Documentar edge case X
- [ ] Confirmar pricing actual del proveedor Y

---

## Changelog

### YYYY-MM-DD — versión
- Autor: <agente que escribió>
- Cambio: <qué se añadió/modificó>
- Validador: <agente que aprobó>
```

---

## Notas de uso

1. **Respetar el orden de secciones.** Facilita la lectura cruzada.
2. **El nivel de confianza es crítico.** El equipo `aithera-wiki-*` debe usarlo para priorizar re-validation.
3. **El changelog es por documento**, no centralizado. Permite ver la historia de cada doc sin tocar git log.
4. **Los emojis de estado** (🟢🟡🔴⚫) son obligatorios y deben ir al inicio del documento.

---

*Plantilla v1.0 — 2026-06-30. Mantenedor: Aithera Escriba (`aithera-wiki-escriba`).*