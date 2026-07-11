# User Context — Preferencias y datos del usuario

## Resumen

User context es la **memoria persistente sobre el usuario** (preferencias, datos, hábitos). Aithera V0.7.3 lo soporta vía ChromaDB collection `user_context`. V0.85+ lo formaliza.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Estructura

```python
# UserContext schema
class UserContext:
    user_id: str
    preferences: dict  # {key: value}
    habits: list[Habit]  # cosas que el user hace frecuentemente
    projects: list[Project]
    personal_info: dict  # nombre, timezone, idioma, etc.
    last_updated: datetime
```

## Aithera V0.7.3

```python
# backend/app/memory/memory_manager.py
self.user_context = self.client.get_or_create_collection("user_context")

async def set_preference(self, key: str, value: str):
    await self.user_context.add(
        documents=[f"{key} = {value}"],
        metadatas=[{"type": "preference", "key": key, "value": value}],
        ids=[f"pref-{key}"]
    )

async def get_preferences(self) -> dict:
    results = await self.user_context.get(where={"type": "preference"})
    return {r.metadata["key"]: r.metadata["value"] for r in results}
```

## API endpoints

```python
# GET /api/memory/preferences
# POST /api/memory/preferences
# {"key": "language", "value": "es"}
```

## Examples

- `language = es` (preferencia)
- `timezone = Europe/Madrid` (config)
- `preferred_provider = deepseek` (AI config)
- `default_calendar_id = primary` (Calendar)
- `email_signature = "..."` (Email)

## Para V0.85 MOS

User context es el **núcleo de la personalización**:
- Briefing diario personalizado.
- Respuestas adaptadas al estilo del user.
- Sugerencias proactivas basadas en hábitos.

## Privacy

User context contiene **datos personales**. Aithera V0.8+ debería:
- ✅ Cifrar en BD.
- ✅ Permitir al user ver/borrar todo.
- ✅ Opt-out para items sensibles.

## References

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-131 conversation-memory.md](./conversation-memory.md)
- `PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md`

## Fuentes

1. CLAUDE.md §1 (Memory ChromaDB en Aithera V0.6+)
2. https://www.trychroma.com/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified