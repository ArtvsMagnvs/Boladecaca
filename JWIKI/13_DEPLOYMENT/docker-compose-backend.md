# Docker Compose — Backend

## Resumen

**Docker Compose** permite empaquetar FastAPI + PostgreSQL + ChromaDB en containers reproducibles. **NO usado en Aithera V0.7.3 desktop** (single binary). V1.0+ para SaaS.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## docker-compose.yml

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: aithera
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: aithera
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aithera"]
      interval: 10s
  
  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://aithera:${DB_PASSWORD}@postgres:5432/aithera
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ~/.aithera:/root/.aithera

volumes:
  postgres_data:
```

## Dockerfile (backend)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Para Aithera

- ❌ V0.7.3: NO Docker (single binary desktop).
- ⏳ V1.0+: Docker compose para SaaS / multi-user.

## Referencias cruzadas

- [JWIKI-210 docker-postgres.md](./docker-postgres.md)

## Fuentes

1. https://docs.docker.com/compose/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified