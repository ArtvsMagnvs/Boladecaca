# Convenciones — Naming

## Resumen

**Naming conventions** unificadas. Ver CLAUDE.md §14.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Python (CLAUDE.md §14)

| Element | Convention | Example |
|---|---|---|
| Variables | snake_case | `user_email` |
| Functions | snake_case | `def send_email():` |
| Classes | PascalCase | `class EmailTool:` |
| Constants | UPPERCASE | `MAX_EXECUTION_TIME` |
| Modules | snake_case | `email_tool.py` |
| Private | _prefix | `_validate_args` |

## TypeScript/React

| Element | Convention | Example |
|---|---|---|
| Variables | camelCase | `const userEmail = ""` |
| Functions | camelCase | `const sendEmail = () => {}` |
| Components | PascalCase | `function EmailCard()` |
| Constants | UPPERCASE | `const MAX_RETRIES = 3` |
| Files (comp) | PascalCase | `EmailCard.tsx` |
| Files (util) | camelCase | `api.ts` |
| Types/Interfaces | PascalCase | `interface UserData {}` |
| Hooks | use* prefix | `useEmail` |

## Database

| Element | Convention | Example |
|---|---|---|
| Tables | snake_case plural | `users`, `chat_messages` |
| Columns | snake_case | `user_id`, `created_at` |
| Primary key | id | `id` |
| Foreign key | {table}_id | `user_id` |
| Timestamps | _at suffix | `created_at`, `updated_at` |
| Booleans | is_/has_ prefix | `is_active`, `has_children` |

## URLs (API)

| Element | Convention | Example |
|---|---|---|
| Endpoints | kebab-case | `/api/auto-reply/rules` |
| Prefijos | `/api/{resource}` | `/api/email`, `/api/agents` |
| Actions | verbs | `POST /api/email/send` |
| IDs | path param | `/api/agents/{id}` |
| Queries | snake_case | `?max_results=20` |

## LLM / AI

| Element | Convention | Example |
|---|---|---|
| Provider names | lowercase | `"openai"`, `"anthropic"` |
| Model names | respetar mayúsculas | `"MiniMax-M2.7-highspeed"` |

## Git

- **Branches**: `feature/...`, `fix/...`, `v0.7.3` (versión).
- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`).

## Para Aithera

- ✅ V0.7.3: convenciones aplicadas (CLAUDE.md §14).

## Fuentes

1. CLAUDE.md §14

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified