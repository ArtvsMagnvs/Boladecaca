# Django vs FastAPI — Comparativa

## Resumen

**Django** es el framework Python full-stack más maduro. **FastAPI** es el moderno async-first. Aithera eligió FastAPI por simplicidad + async + AI/ML ecosystem.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

| Aspecto | Django | FastAPI |
|---|---|---|
| Tipo | Full-stack | API framework |
| ORM | Built-in (Django ORM) | ❌ externo (SQLAlchemy) |
| Admin | ✅ built-in | ❌ externo (sqladmin) |
| Auth | ✅ built-in | ❌ externo (FastAPI-Users) |
| Async | ✅ (Django 4.1+) | ✅ nativo |
| OpenAPI | ❌ manual (DRF) | ✅ auto |
| AI/ML | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Lines of code (hello) | 50+ | 10 |

## Cuando elegir Django

- ✅ Web app full-stack (con templates HTML).
- ✅ Admin panel out-of-the-box.
- ✅ ORM maduro.
- ✅ Apps que necesitan auth built-in.

## Cuando elegir FastAPI

- ✅ Solo API (SPA frontend separado).
- ✅ Async nativo.
- ✅ AI/ML ecosystem.
- ✅ Performance crítico.

## Para Aithera

Aithera es **API + Electron frontend**. Django sería overkill (admin no se necesita, templates no se necesitan). FastAPI es la elección correcta.

## Hello World

Django (con DRF):
```python
# models.py
class ChatMessage(models.Model):
    content = models.TextField()

# views.py
class ChatView(APIView):
    def post(self, request):
        return Response({"response": "hello"})

# urls.py + settings.py + manage.py...
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
- [JWIKI-061 flask-vs-fastapi.md](./flask-vs-fastapi.md)

## Fuentes

1. https://www.djangoproject.com/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified