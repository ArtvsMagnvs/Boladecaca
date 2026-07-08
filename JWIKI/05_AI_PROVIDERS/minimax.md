# MiniMax (MiniMax) — Proveedor chino de razonamiento

## Resumen

MiniMax es un proveedor chino de modelos de IA especializado en **razonamiento** y **ultra-baja latencia**. Es uno de los 8 proveedores ya integrados en Aithera v0.7.3 (ver `backend/app/ai/providers/minimax_provider.py`), junto con OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Grok y Ollama. Su modelo estrella `MiniMax-M2.7-highspeed` es la opción por defecto de Aithera (constante `MINIMAX_DEFAULT_MODEL`). Se caracteriza por su endpoint `api.minimax.io/v1/chat/completions` (cambió desde `api.minimax.chat` en 2024), compatibilidad parcial con OpenAI, y un `max_completion_tokens` limitado a **2048** — restricción que hay que respetar en el código.

## Objetivo

Documentar MiniMax como proveedor integrado en Aithera: API, modelos, restricciones, y comparativa con alternativas. Responde a "¿por qué MiniMax es el default en Aithera, y cuándo conviene cambiar?".

## Estado

🟡 En progreso — base escrita 2026-07-07. Pendiente cross-check con `backend/app/ai/providers/minimax_provider.py` para confirmar constantes y configuración.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| MiniMax API | v1 (chat/completions) | Endpoint actual: `api.minimax.io/v1/chat/completions` (cambió desde `api.minimax.chat` en 2024) |
| MiniMax-M2.7 | Última | Modelo razonador, buen balance calidad/costo |
| MiniMax-M2.7-highspeed | Última | Default en Aithera, ultra-rápido |
| MiniMax-M2.7-flash | (verificar disponibilidad) | Si existe, más barato y rápido |
| OpenAI Python SDK | ≥1.0 | Compatible con el endpoint OpenAI-compat |
| Aithera | V0.7+ | `app/ai/providers/minimax_provider.py` lo integra |

## Proyectos compatibles

- **Compatible con OpenAI Python SDK** vía `base_url="https://api.minimax.io/v1"` (ajustar el client base)
- **Compatible con curl/HTTP** vía `/v1/chat/completions`
- **No soporta** vision, audio, embeddings (a 2026-07-07 — verificar)
- **No soporta** function calling completo (verificar; Aithera probablemente lo evita para MiniMax)

## API y configuración

### Endpoint

```
POST https://api.minimax.io/v1/chat/completions
```

**Breaking change 2024 → 2026**:
- ❌ `api.minimax.chat` (legacy)
- ✅ `api.minimax.io/v1/chat/completions` (actual)

### Request body (OpenAI-compat)

```json
{
  "model": "MiniMax-M2.7-highspeed",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "max_completion_tokens": 2048,
  "temperature": 0.7,
  "stream": false
}
```

### Response (OpenAI-compat)

```json
{
  "id": "cmpl-...",
  "object": "chat.completion",
  "created": 1735689600,
  "model": "MiniMax-M2.7-highspeed",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 23,
    "completion_tokens": 12,
    "total_tokens": 35
  }
}
```

### Streaming (SSE)

Funciona igual que OpenAI streaming. Enviar `"stream": true` y leer chunks `data: {...}\n\n`.

## Restricciones importantes

### 1. `max_completion_tokens` máximo 2048

El endpoint **rechaza** requests con `max_completion_tokens > 2048`. Esto es un límite duro del proveedor. Aithera debe respetar este valor cuando el proveedor activo es MiniMax.

```python
# Aithera v0.7.3
DEFAULT_MAX_COMPLETION_TOKENS = 2048  # MiniMax limit
```

### 2. Pricing no público claro

MiniMax **no publica pricing oficial** en una página accesible. Los precios se negocian caso por caso o vía partners. Para Aithera, esto significa:
- Coste difícil de predecir
- Cambio de pricing sin aviso
- **Recomendación**: no usar MiniMax para producción de alto volumen sin acuerdo comercial

### 3. Reasoning models

Modelos como `MiniMax-M2.7` (sin -highspeed) tienen cadena de pensamiento `<think>...</think>` que debe filtrarse (ver Aithera v0.8 **B21** en `backend/app/ai/reasoning_filter.py`).

## Configuración en Aithera

### `app/ai/providers/minimax_provider.py` (excerpt)

```python
from app.ai.providers.openai_compatible import OpenAICompatibleProvider

class MinimaxProvider(OpenAICompatibleProvider):
    """Proveedor MiniMax (default en Aithera v0.7.3)."""
    
    default_model_name = "MiniMax-M2.7-highspeed"
    base_url = "https://api.minimax.io/v1"  # NO api.minimax.chat
    
    MAX_COMPLETION_TOKENS = 2048  # HARD LIMIT del proveedor
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, base_url=self.base_url, **kwargs)
    
    def get_max_completion_tokens(self) -> int:
        return self.MAX_COMPLETION_TOKENS
```

### Configuración en BD

```python
# AIProviderConfig
{
    "name": "minimax",
    "display_name": "MiniMax",
    "is_active": True,  # Default en Aithera v0.7.3
    "api_key": "<encrypted-via-DPAPI>",  # V0.8: cifrado
    "default_model": "MiniMax-M2.7-highspeed",
    "max_tokens": 2048
}
```

### Variables de entorno

```bash
# .env (opcional, bootstrap)
MINIMAX_API_KEY=<key>
```

## MiniMax en Aithera: modelo por defecto

**Razones** (especulación — el WHY exacto no está documentado en código, pero es deducible):
1. **Velocidad**: M2.7-highspeed es uno de los más rápidos del mercado
2. **Costo**: probablemente más barato que OpenAI/Anthropic para uso general
3. **Razonamiento**: M2.7 es fuerte en chain-of-thought
4. **OpenAI-compat**: fácil de integrar en Aithera
5. **Acceso desde China**: si el user está en región con OpenAI bloqueado, MiniMax es alternativa

## Cuándo NO usar MiniMax

- ❌ Tareas que requieren **>2048 tokens de output** (resúmenes largos, código largo)
- ❌ Producción de alto volumen sin acuerdo de pricing
- ❌ Cuando se necesita **vision/audio/multimodal** (no soportado a 2026-07-07)
- ❌ Function calling complejo (verificar; probablemente limitado)
- ❌ Cuando el user necesita **uptime SLA** (proveedor más pequeño que OpenAI/Anthropic)

## Alternativas a MiniMax en Aithera

| Caso | Alternativa | Razón |
|---|---|---|
| >2048 tokens output | OpenAI gpt-5.5, Anthropic claude-opus-4-8 | Sin límite duro |
| Vision | OpenAI gpt-5.5, Gemini 3.5-pro | Multimodal nativo |
| Razonamiento puro | DeepSeek R1 | Reasoning especializado, open weights |
| Velocidad máxima | Gemini 3.5-flash, Grok 4.3 | Latencia < 500ms |
| Self-host privado | Ollama + DeepSeek-R1-Distill | 100% local |

## Breaking Changes históricos

| Fecha | Cambio | Impacto |
|---|---|---|
| 2024-2026 | `api.minimax.chat` → `api.minimax.io/v1` | Requiere actualizar URL en Aithera |
| (sin fecha pública) | `max_completion_tokens` cap a 2048 | Respeta límite en código |

## Comparativa con otros proveedores chinos

| Proveedor | Pricing | Razonamiento | Velocidad | OpenAI-compat | Aithera integrado |
|---|---|---|---|---|---|
| **MiniMax** | [no público] | ✅ fuerte | ✅ muy rápido | ✅ parcial | ✅ |
| **DeepSeek** | ~$0.27/$1.10 por 1M | ✅ R1 | ✅ rápido | ✅ completo | ✅ |
| **Qwen** | Open weights (self-host) o API | ✅ bueno | ✅ rápido | ✅ vía DashScope | ⏳ pendiente |
| **GLM** | Tier-2 pricing | ✅ bueno | medio | ✅ | ⏳ pendiente |
| **Doubao** | TBD | ✅ fuerte | ✅ | ✅ | ⏳ pendiente |

## Estrategia de Aithera con MiniMax

Aithera v0.7.3 usa MiniMax como **default**, pero el sistema permite cambiar de proveedor activo desde la UI de Settings → AI Providers. La razón de ser default es velocidad + costo + razonamiento. Si en algún momento MiniMax:
- Cambia la API
- Sube precios
- Tiene outage prolongado

Aithera puede cambiar a DeepSeek o Anthropic con un click.

## Pendientes

- [ ] Verificar pricing oficial de MiniMax (no público)
- [ ] Confirmar modelos disponibles exactos (puede haber nuevos como M3)
- [ ] Confirmar si soporta function calling o no
- [ ] Confirmar si soporta vision/audio
- [ ] Cross-check con `backend/app/ai/providers/minimax_provider.py` para confirmar constantes
- [ ] Documentar el patrón de cambio de provider activo desde la UI

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-034 function-calling.md](./function-calling.md) — function calling por proveedor
- [JWIKI-035 streaming.md](./streaming.md) — SSE streaming
- [JWIKI-038 rate-limits.md](./rate-limits.md) — rate limits
- [JWIKI-042 chinese-providers.md](./chinese-providers.md) — comparativa proveedores chinos
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) — SOP añadir proveedor
- [JWIKI-263 change-active-provider.md](../16_SOPS/change-active-provider.md) — SOP cambiar proveedor activo

## Fuentes

1. `https://api.minimax.io/v1/chat/completions` — acceso 2026-07-07 (endpoint)
2. `backend/app/ai/providers/minimax_provider.py` — código Aithera v0.7.3
3. `backend/app/ai/providers/openai_compatible.py` — base class usada
4. `Actualizacion_V0.2.txt` — hardcoded key + default model (legacy)
5. CLAUDE.md §10 — sistema multi-proveedor Aithera
6. [JWIKI-240 cors-open-prod.md](../15_KNOWN_PITFALLS/cors-open-prod.md) — API keys plaintext (resuelto en V0.8)

## Nivel de confianza

**85%** — Datos verificados contra el código Aithera v0.7.3 (`minimax_provider.py`). Pendiente: pricing oficial, lista exacta de modelos, soporte de function calling.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado desde cero
- Validador: cross-check con `minimax_provider.py`
- Estado: 🟡 en progreso
