# Gateway multi-canal + MessageEnvelope — diseño V0.8 (esqueleto)

> Fecha: 2026-07-03. Estado: **esqueleto implementado y testeado** (`app/gateway/`,
> `backend/tests/test_gateway.py`). Los adapters (Telegram, Web) son trabajo
> mecánico posterior que sigue el patrón descrito aquí. Patrón de referencia:
> OpenClaw (ver `01_BENCHMARK_JARVIS_OSS.md`). Cumple los principios 1, 3 y 4 del AOS.

---

## 1. Por qué esto primero (y por qué importa el diseño)

V0.8 añade clientes nuevos: bot de Telegram, cliente web, PWA. La tentación es
escribir el bot de Telegram directamente contra `/api/chat`. Eso duplicaría la
lógica de sesión, memoria y autorización en cada canal, y cada canal nuevo
volvería a copiarla.

En su lugar, se construye **una sola pieza de diseño** — el `MessageEnvelope` y el
`Gateway` — y todos los canales pasan a ser **adapters finos**. Un adapter solo
traduce el formato nativo de su canal (un `Update` de Telegram, un POST del web)
al envelope, y traduce la respuesta de vuelta. Cero lógica de negocio dentro.

**Regla de oro (principio 3 del AOS — un backend, múltiples clientes):** la lógica
de negocio NUNCA sabe de qué canal vino un mensaje. Añadir un canal = escribir un
adapter, cero cambios en el resto del backend.

Si el envelope queda bien diseñado, Telegram, Web y cualquier canal futuro
(Discord, WhatsApp) son trabajo mecánico. Si queda mal diseñado, se arrastra
siempre. Por eso el esqueleto se diseña con cuidado y los adapters se dejan como
implementación guiada.

---

## 2. Piezas del esqueleto (`app/gateway/`)

| Archivo | Rol |
|---|---|
| `envelope.py` | Los contratos de datos: `MessageEnvelope` (entrante), `OutboundMessage` (saliente), `Attachment`. Pydantic v2. |
| `base.py` | `ChannelAdapter` (ABC): la interfaz que TODO canal implementa. |
| `gateway.py` | `Gateway` (registro + despacho) + `chat_message_handler` (handler por defecto) + singleton `gateway`. |
| `__init__.py` | Re-exporta la API pública del paquete. |

### 2.1 MessageEnvelope — mensaje ENTRANTE normalizado

```python
class MessageEnvelope(BaseModel):
    envelope_id: str      # uuid autogenerado, correlaciona entrada↔salida
    channel: str          # "electron" | "web" | "telegram" | ...
    user_ref: str         # identidad EN ESE canal (chat_id, session_id...)
    text: str
    attachments: list[Attachment]
    reply_to: str | None  # id nativo del mensaje al que se responde
    metadata: dict        # espacio libre por canal (no contamina el núcleo)
    created_at: datetime
```

Decisiones clave:
- `user_ref` es la identidad **dentro del canal**, no un usuario global. Aithera es
  monousuario (principio 6), así que no hay tabla de usuarios; el `user_ref` sirve
  para que el adapter sepa a quién responder y para la whitelist de autorización.
- `metadata` es el escape hatch: cualquier dato específico de un canal
  (por ejemplo el `message_id` de Telegram para editar mensajes) vive aquí sin
  ensuciar el contrato común.
- `attachments` normaliza adjuntos: cada canal rellena lo que soporte; el núcleo
  no necesita saber cómo Telegram resuelve un `file_id`.

### 2.2 OutboundMessage — respuesta SALIENTE normalizada

```python
class OutboundMessage(BaseModel):
    text: str
    envelope_id: str      # correlación con el envelope de entrada
    attachments: list[Attachment]
    error: bool           # True si es un mensaje de error/ rechazo
    metadata: dict
```

El handler puede devolver **un `str`** (se envuelve en `OutboundMessage`
automáticamente) o **un `OutboundMessage` completo** si necesita adjuntos o
metadata. Es lo que permite que en V1.0 el Orchestrator devuelva respuestas ricas
sin tocar ni un adapter.

### 2.3 ChannelAdapter — la interfaz de un canal

```python
class ChannelAdapter(ABC):
    name: str                                    # "telegram", "web", ...

    async def to_envelope(self, raw) -> MessageEnvelope   # obligatorio
    async def deliver(self, msg, envelope) -> None        # obligatorio
    async def authorize(self, envelope) -> bool           # default True
    async def start(self) -> None                         # default nada
    async def stop(self) -> None                          # default nada
```

- `to_envelope` / `deliver` son los únicos métodos **obligatorios**: traducir en
  ambos sentidos.
- `authorize` es el **hook de seguridad por canal** (hardening V0.8). Telegram lo
  sobreescribe con la whitelist de `chat_id`; Web con el PIN/token. Default `True`
  para canales locales de confianza (Electron en localhost).
- `start` / `stop` para canales que necesitan ciclo de vida (el polling de
  Telegram arranca en `start`). Default no-op.

---

## 3. Flujo de un mensaje

```
canal nativo
   │  raw (Update de Telegram, POST web, ...)
   ▼
adapter.to_envelope(raw)  ──►  MessageEnvelope
   ▼
gateway.dispatch(envelope)
   ├─ ¿canal registrado?      no ─► GatewayError (bug de wiring, debe explotar)
   ├─ adapter.authorize(env)  no ─► OutboundMessage(error, "No autorizado") ─► deliver ─► FIN
   ├─ handler(envelope)             (chat_message_handler por defecto; Orchestrator en V1.0)
   │     └─ excepción ─► fail-soft: OutboundMessage(error, "Ha habido un error...")
   ▼
adapter.deliver(outbound, envelope)  ──►  canal nativo
```

Garantías de `dispatch` (verificadas en `test_gateway.py`):
1. **Canal desconocido → `GatewayError`.** Es un bug de wiring, debe explotar fuerte.
2. **`authorize()` False → el handler NI se llama.** El rechazo se entrega al usuario.
3. **Excepción del handler → fail-soft.** El usuario recibe un mensaje amable por su
   canal; el detalle (tipo de excepción) queda en el log. Nunca se filtra un stack
   trace a un canal.

---

## 4. El handler por defecto

`chat_message_handler` es el equivalente **channel-agnostic** de `POST /api/chat`
(no streaming: Telegram y similares no lo necesitan):

1. Construye el system prompt (`_build_system_prompt`, reutilizado de `chat.py`).
2. Guarda el mensaje del usuario en memoria (`metadata={"channel": ...}`).
3. Llama al proveedor IA activo (`ai_manager.chat`).
4. Aplica **B21** (`strip_reasoning`): sin cadena de pensamiento del modelo.
5. Guarda la respuesta y la devuelve.

**Punto de cambio único para V1.0:** `gateway.set_handler(orchestrator_handler)`.
El Orchestrator sustituye al chat directo sin que ningún adapter se entere. Esa es
toda la gracia del envelope (principio 4 del AOS — la IA razona, Aithera decide).

---

## 5. Guía paso a paso para escribir un adapter

Ejemplo: `TelegramAdapter` (python-telegram-bot v21, polling). Trabajo mecánico.

1. **Crear** `app/gateway/adapters/telegram_adapter.py` con una clase que herede de
   `ChannelAdapter` y declare `name = "telegram"`.
2. **`to_envelope(update)`**: de un `telegram.Update` extraer `chat_id` → `user_ref`,
   `message.text` → `text`, `message.message_id` → `metadata["message_id"]`.
   Adjuntos: resolver `file_id` a URL o dejar el `file_id` en `Attachment.url`.
3. **`deliver(msg, envelope)`**: `bot.send_message(chat_id=envelope.user_ref,
   text=msg.text)`. Si `msg.attachments`, mandar los adjuntos correspondientes.
4. **`authorize(envelope)`**: comprobar `envelope.user_ref` contra la whitelist de
   `chat_id` (config en BD). Devolver `False` si no está → el usuario no autorizado
   recibe "No autorizado" y el handler no se ejecuta.
5. **`start()`**: arrancar el polling (`application.run_polling` en una tarea async);
   en cada update recibido: `env = await self.to_envelope(update)` →
   `await gateway.dispatch(env)`. **`stop()`**: parar el polling limpiamente.
6. **Registrar** en el `lifespan` de `main.py`:
   `gateway.register(TelegramAdapter(...))` y `await gateway.start_all()` al
   arrancar, `await gateway.stop_all()` al apagar.

El adapter Web es aún más simple: `to_envelope` desde el body del POST, `deliver`
devolviendo el `OutboundMessage` en la response HTTP (o por WebSocket si se quiere
push), `authorize` con el PIN/token de sesión.

Regla al escribir adapters: **son piezas finas**. Si te ves metiendo lógica de
negocio (decidir qué responder, tocar la BD de dominio, llamar tools), va en el
handler, no en el adapter.

---

## 6. Qué está hecho y qué queda (V0.8)

Hecho (este esqueleto, 2026-07-03):
- `MessageEnvelope`, `OutboundMessage`, `Attachment`, `ChannelAdapter`, `Gateway`,
  `chat_message_handler`, singleton `gateway`.
- Tests de contrato del núcleo: registro, dispatch, authorize, fail-soft, ciclo de
  vida, correlación de `envelope_id` (`backend/tests/test_gateway.py`).

Queda (adapters + wiring, trabajo mecánico guiado por §5):
- `TelegramAdapter` + whitelist de `chat_id`.
- `WebAdapter` + PIN/token; React build servido por FastAPI en `/app`; PWA.
- Registro de adapters y `start_all`/`stop_all` en el `lifespan` de `main.py`.
- Security hardening (CORS restringido, cifrado de API keys) — ver
  `03_ROADMAP_ACTUALIZADO.md` §V0.8.

---

*Diseño construido sobre el patrón OpenClaw. Consistente con los principios 1
(no romper lo que funciona), 3 (un backend, múltiples clientes) y 4 (la IA razona,
Aithera decide) del AOS.*
