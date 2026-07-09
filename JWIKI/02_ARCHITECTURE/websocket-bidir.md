# WebSocket Bidireccional — Cuándo usar vs SSE

## Resumen

**WebSocket** es conexión bidireccional full-duplex sobre TCP. Aithera V0.7.3 **NO usa WebSocket** (usa SSE). Para V1.0+ podría considerar.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## WebSocket vs SSE

| Aspecto | WebSocket | SSE |
|---|---|---|
| **Dirección** | Bidireccional | Server → Client |
| **Protocolo** | Upgrade HTTP → ws | HTTP |
| **Estado** | Stateful (connection) | Stateless (HTTP) |
| **Reconexión** | Manual | Auto |
| **Costo servidor** | Alto (mantener conexión) | Bajo (stateless) |
| **Costo cliente** | Igual | Igual |
| **Caso de uso** | Chat real-time, multiplayer, bi-di | AI streaming, notifications |

## Cuando usar WebSocket

- ✅ **Bidireccional real-time**: chat con typing indicators, multiplayer.
- ✅ **Baja latencia requerida**: < 50ms.
- ✅ **Server push frecuente**: > 1 update/segundo.
- ✅ **Estado compartido**: conexión persistente.

## Cuando NO usar WebSocket

- ❌ **Solo server push**: usar SSE (más simple).
- ❌ **Request/response ocasional**: usar HTTP.
- ❌ **Mobile (battery)**: SSE es más friendly.
- ❌ **Detrás de proxies raros**: SSE friendly.

## Aithera V0.7.3 — NO usa WebSocket

Aithera solo usa SSE (chat streaming). No hay necesidad de WebSocket en V0.7.3.

## Aithera V1.0+ — posibles casos

| Caso | Solución |
|---|---|
| Chat typing indicators | WebSocket (futuro) |
| Multi-user collaboration | WebSocket (futuro) |
| Real-time notifications | SSE suficiente |
| AI streaming | SSE (ya) |

## Implementación WebSocket en FastAPI

```python
from fastapi import WebSocket

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    while True:
        # recibe del cliente
        msg = await websocket.receive_json()
        # envía al cliente (response)
        response = await ai_provider.chat(msg)
        await websocket.send_json(response)
```

## Desventajas de WebSocket

- ❌ Stateful (dificulta load balancing).
- ❌ Complejo retry logic.
- ❌ No HTTP-cacheable.
- ❌ Algunos proxies/firewalls bloquean.
- ❌ Mayor consumo memoria server.

## Para Aithera V1.0

**Mantener SSE como default**. WebSocket solo si hay caso real de bidireccionalidad (typing, presence).

## Referencias cruzadas

- [JWIKI-050 sse-streaming.md](./sse-streaming.md)
- [JWIKI-047 multi-client.md](./multi-client.md)

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
2. https://fastapi.tiangolo.com/advanced/websockets/

## Nivel de confianza

**90%** — WebSocket bien documentado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified