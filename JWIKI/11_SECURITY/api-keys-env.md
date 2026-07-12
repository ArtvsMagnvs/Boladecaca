# API Keys — Env vars

## Resumen

Aithera V0.7.3 usa **.env file** para API keys (OpenAI, Anthropic, etc.). Patrón clásico 12-factor app.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
# backend/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
MINIMAX_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

## Lectura con Pydantic Settings

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    gemini_api_key: str | None = None
    telegram_bot_token: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
```

## .env.example (versionado)

```bash
# backend/.env.example
OPENAI_API_KEY=sk-REPLACE_ME
ANTHROPIC_API_KEY=sk-ant-REPLACE_ME
```

## Precedence

Pydantic lee en este orden:
1. Environment vars (highest).
2. `.env` file.
3. Defaults en código.

## Aithera bootstrap

Aithera V0.2-V0.7.3 lee .env al arrancar. Si DB vacía, **bootstrap desde .env** crea AIProviderConfig entries.

⚠️ **Problema**: si user edita .env pero ya hay AIProviderConfig en BD, BD tiene precedencia.

## Aithera V0.8+ migration

CLAUDE.md §1: Aithera V0.8+ migra de **.env + BD plaintext** → **DPAPI-cifrado en BD**. .env sigue siendo bootstrap, pero se cifra al persistir.

## Pitfalls

- ❌ **No commitear .env** al git.
- ❌ **No loguear API keys** (incluso parcialmente).
- ❌ **No compartir .env** entre developers.

## Referencias cruzadas

- [JWIKI-181 api-keys-encrypted-db.md](./api-keys-encrypted-db.md)
- [JWIKI-182 api-keys-keyring.md](./api-keys-keyring.md)
- [JWIKI-190 secrets-managers.md](./secrets-managers.md)

## Fuentes

1. https://12factor.net/config
2. CLAUDE.md §1

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified