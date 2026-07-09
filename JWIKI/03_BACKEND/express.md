# Express.js — Alternativa Node.js

## Resumen

**Express.js** es el framework backend Node.js más popular. Aithera V0.7.3 NO usa Express (usa FastAPI Python). Este doc es referencia comparativa.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Características

- ✅ Minimalista y flexible.
- ✅ Ecosystem masivo de middleware.
- ✅ JavaScript everywhere (frontend + backend).
- ❌ Callback hell (aunque async/await lo arregla).
- ❌ Menos type-safety que TypeScript puro.

## Versión

| Componente | Versión |
|---|---|
| Node.js | ≥18 (LTS) |
| Express | 4.x |
| TypeScript | opcional pero recomendado |

## Hello World

```javascript
const express = require('express');
const app = express();
const port = 3000;

app.get('/api/hello', (req, res) => {
    res.json({ message: 'Hello from Express!' });
});

app.listen(port, () => {
    console.log(`Express listening on port ${port}`);
});
```

## Para Aithera — NO aplica

Aithera está casada con Python (FastAPI). Express no es opción.

**Pero** podría usarse para:
- Microservicio ligero (e.g., webhooks de Gmail).
- Bridge a un servicio Node.js existente.

## Comparativa con FastAPI

| Aspecto | Express | FastAPI |
|---|---|---|
| Lenguaje | JavaScript | Python |
| Async | ✅ (promises) | ✅ (async/await) |
| Type safety | Opcional (TS) | Built-in (Pydantic) |
| OpenAPI | ❌ manual | ✅ auto |
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Ecosystem | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| AI/ML libraries | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**Aithera eligió Python (FastAPI) por AI/ML ecosystem**.

## Referencias cruzadas

- [JWIKI-057 README.md](./README.md)
- [JWIKI-058 fastapi.md](./fastapi.md)

## Fuentes

1. https://expressjs.com/

## Nivel de confianza

**90%** — Express bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified