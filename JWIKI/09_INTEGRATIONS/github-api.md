# GitHub API — Para código

## Resumen

**GitHub API** permite interactuar con repos, issues, PRs, Actions. **NO integrado en Aithera V0.7.3** (excepto git tool para status/log). Posible V1.0+ skills.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## GitHub CLI vs API

| Approach | Use case |
|---|---|
| **GitHub CLI** (`gh`) | local, shell, Aithera V0.7.3 ✅ |
| **GitHub REST API** | full programmatic |
| **GitHub GraphQL API** | efficient queries |

## Aithera git_tool (V0.7.3)

`backend/app/tools/git_tool.py` usa `git` CLI:
- `git status`
- `git log`
- `git diff`
- `git commit`

## GitHub REST API (V1.0+)

```python
import requests

headers = {
    "Authorization": "Bearer ghp_...",
    "Accept": "application/vnd.github+json"
}

# Listar repos
repos = requests.get(
    "https://api.github.com/user/repos",
    headers=headers
).json()

# Crear issue
new_issue = requests.post(
    "https://api.github.com/repos/owner/repo/issues",
    headers=headers,
    json={"title": "Bug found", "body": "Description"}
).json()

# Crear PR
new_pr = requests.post(
    "https://api.github.com/repos/owner/repo/pulls",
    headers=headers,
    json={"title": "Fix bug", "head": "fix-branch", "base": "main"}
).json()
```

## GitHub GraphQL

```python
query = """
query {
    user(login: "octocat") {
        repositories(first: 10) {
            nodes {
                name
                stargazerCount
                issues(states: OPEN) { totalCount }
            }
        }
    }
}
"""
```

## Casos de uso Aithera V1.0+

- ✅ **Auto-create issues** desde emails o chat.
- ✅ **Triage**: Aithera clasifica issues (bug/feature/question).
- ✅ **PR reviews**: Aithera revisa código automáticamente.
- ✅ **Code search**: Aithera busca en codebase del user.

## Rate limits

- **REST**: 5000 requests/hour (authenticated).
- **GraphQL**: same, but per query complexity.

## Para Aithera

- ✅ V0.7.3: git_tool (local git CLI).
- ⏳ V1.0+: GitHub API skills (Orchestrator).
- ⏳ V1.5+: PR auto-review con Claude Code Agent.

## Referencias cruzadas

- [JWIKI-160 notion-api.md](./notion-api.md)
- [JWIKI-161 linear-api.md](./linear-api.md)

## Fuentes

1. https://docs.github.com/en/rest
2. https://docs.github.com/en/graphql

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified