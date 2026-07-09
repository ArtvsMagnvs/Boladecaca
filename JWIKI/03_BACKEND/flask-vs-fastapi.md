# Flask vs FastAPI — Comparativa

## Resumen

**Flask** es el framework Python clásico minimalista. **FastAPI** es el moderno async-first. Aithera V0.7.3 eligió FastAPI por async + OpenAPI + Pydantic.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

| Aspecto | Flask | FastAPI |
|---|---|---|
| Async | ❌ sync | ✅ nativo |
| Validación | Manual (Marshmallow) | ✅ Pydantic auto |
| OpenAPI | ❌ manual | ✅ auto |
| Performance | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Ecosystem | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Curva aprendizaje | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Streaming | ❌ difícil | ✅ SSE nativo |
| WebSockets | ❌ (extensiones) | ✅ nativo |

## Cuando elegir Flask

- ✅ Proyecto simple, no necesita async.
- ✅ Ecosystem masivo (Flask-SQLAlchemy, Flask-Login, etc.).
- ✅ Equipo Python sin experiencia async.

## Cuando elegir FastAPI

- ✅ Async nativo.
- ✅ Validación automática.
- ✅ OpenAPI out-of-the-box.
- ✅ Performance.

## Para Aithera

**FastAPI** es la elección correcta. Flask habría sido limitante para SSE streaming.

## Hello World

Flask:
```python
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    return jsonify({"response": "hello"})

app.run(port=8000)
```

FastAPI:
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {"response": "hello"}
```

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-062 django-vs-fastapi.md](./django-vs-fastapi.md)

## Fuentes

1. https://flask.palletsprojects.com/
2. https://fastapi.tiangolo.com/

## Nivel de confianza

**95%** — Comparativa bien conocida.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified