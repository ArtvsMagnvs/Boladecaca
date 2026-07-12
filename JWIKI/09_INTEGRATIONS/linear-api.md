# Linear API — Issue tracking

## Resumen

**Linear** es plataforma moderna de issue tracking (alternativa a Jira). API GraphQL oficial. **NO integrado en Aithera V0.7.3**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```python
import requests

LINEAR_API_KEY = "lin_api_..."

headers = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

# GraphQL query
query = """
query {
    viewer { id name email }
    teams { nodes { id name key } }
}
"""

response = requests.post(
    "https://api.linear.app/graphql",
    json={"query": query},
    headers=headers
).json()

print(response["data"]["viewer"])
```

## Crear issue

```python
mutation = """
mutation IssueCreate($title: String!, $teamId: String!) {
    issueCreate(input: {title: $title, teamId: $teamId}) {
        success
        issue { id title url }
    }
}
"""

variables = {"title": "Implementar nueva feature", "teamId": "..."}

response = requests.post(
    "https://api.linear.app/graphql",
    json={"query": mutation, "variables": variables},
    headers=headers
).json()
```

## Aithera V1.0+ skills

V1.0 Orchestrator podría tener skills:
- `linear_list_issues` — listar issues.
- `linear_create_issue` — crear.
- `linear_update_status` — mover en workflow.
- `linear_search` — buscar.

## Casos de uso

- ✅ **Auto-create issues** desde emails con tareas accionables.
- ✅ **Sync bidireccional** Aithera tasks ↔ Linear issues.
- ✅ **Status reports** diarios.

## Para Aithera

- ❌ V0.7.3: NO integrado.
- ⏳ V1.0+: Linear skill (Orchestrator).

## Referencias cruzadas

- [JWIKI-160 notion-api.md](./notion-api.md)
- [JWIKI-162 github-api.md](./github-api.md)

## Fuentes

1. https://developers.linear.app/docs/graphql/working-with-the-graphql-api
2. https://linear.app/docs/api

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified