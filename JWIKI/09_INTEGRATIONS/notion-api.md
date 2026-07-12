# Notion API — Notas y bases de conocimiento

## Resumen

**Notion API** permite leer/escribir pages, databases, blocks. **NO integrado en Aithera V0.7.3** (solo Google). Posible V1.0+ (skills).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```python
from notion_client import Client

notion = Client(auth="secret_...")

# Listar databases
databases = notion.databases.list()
for db in databases["results"]:
    print(db["title"][0]["plain_text"], db["id"])

# Query database
results = notion.databases.query(
    database_id="...",
    filter={"property": "Status", "select": {"equals": "Active"}}
)

# Crear page
new_page = notion.pages.create(
    parent={"database_id": "..."},
    properties={
        "Name": {"title": [{"text": {"content": "Mi nueva nota"}}]},
        "Status": {"select": {"name": "Active"}}
    }
)
```

## OAuth2

Notion OAuth2:
```
https://api.notion.com/v1/oauth/authorize?
  client_id=...&
  response_type=code&
  redirect_uri=...&
  owner=user
```

## Casos de uso para Aithera

- ✅ **Notas persistentes**: Aithera crea/edita notes en Notion del user.
- ✅ **Knowledge base**: indexar Notion pages en ChromaDB.
- ✅ **Task sync**: Aithera tasks → Notion database.
- ✅ **Daily journal**: cada día Aithera escribe un entry en Notion.

## Aithera skills (V1.0+)

V1.0 Orchestrator podría tener skills:
- `notion_search` — buscar en Notion.
- `notion_create_page` — crear page.
- `notion_update_page` — modificar.
- `notion_query_database` — query DB.

## API limits

- **3 requests/second** (rate limit).
- **1000 blocks/page** (block count limit).
- **2000 chars/block** (text length limit).

## Para Aithera

- ❌ V0.7.3: NO integrado.
- ⏳ V1.0+: Notion skills (Orchestrator).
- ⏳ V1.5+: bidirectional sync (Notion ↔ ChromaDB).

## Referencias cruzadas

- [JWIKI-160 notion-api.md](./notion-api.md)
- [JWIKI-161 linear-api.md](./linear-api.md)

## Fuentes

1. https://developers.notion.com/
2. https://github.com/ramnes/notion-sdk-py

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified