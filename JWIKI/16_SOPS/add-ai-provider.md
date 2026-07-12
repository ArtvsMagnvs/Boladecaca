# SOP — Añadir proveedor IA

## Cuándo
Necesitas integrar un nuevo LLM provider (e.g., Mistral local, Cohere nuevo modelo).

## Pasos

1. **Crear provider class** en `backend/app/ai/providers/`:
```python
from app.ai.providers.base_provider import BaseProvider

class NewProvider(BaseProvider):
    name = "newprovider"
    default_model = "..."
    
    async def chat(self, messages, **kwargs):
        # API call
        ...
    
    async def stream_chat(self, messages, **kwargs):
        async for chunk in ...:
            yield chunk
```

2. **Registrar en `ai_manager.py`**:
```python
self.providers["newprovider"] = NewProvider(...)
```

3. **Añadir entry a `AIProviderConfig` table** (idempotent via bootstrap).

4. **Añadir a Settings UI** (`frontend/src/pages/Settings.tsx`).

5. **Actualizar `CLAUDE.md §10`** con el provider.

## Verificación

- [ ] `POST /api/chat` con `provider="newprovider"` retorna 200.
- [ ] Streaming funciona.
- [ ] UI permite configurar API key.

## Rollback

- Remove provider class.
- Remove from ai_manager registry.
- Drop DB entries: `DELETE FROM ai_provider_configs WHERE provider='newprovider'`.

## Para Aithera

- ✅ Patrón aplicado para 8 providers (CLAUDE.md §10).

## Referencias cruzadas

- [JWIKI-058 fastapi.md](../03_BACKEND/fastapi.md)

## Fuentes

1. CLAUDE.md §10

---

*Estado: 🟢 verified*