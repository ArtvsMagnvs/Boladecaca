# 05 — AI Providers (Matriz comparativa)

> Matriz horizontal del ecosistema de proveedores de IA disponibles para
> construir asistentes JARVIS-like en 2026. **Doc de referencia**: cualquier
> doc individual de la sección (openai.md, anthropic.md, etc.) profundiza en
> un proveedor; este README es la **visión panorámica** que permite elegir.

## Resumen

A 2026-07-09, el panorama de proveedores IA para un proyecto tipo Aithera
(asistente personal local-first + multi-canal) se organiza en **4 tiers**
según el equilibrio capacidad/coste/control:

- **Tier 1 — Frontier**: OpenAI (GPT 5.x), Anthropic (Claude 4.x/5),
  Google (Gemini 3.5), Meta (Llama 4.x). Máxima calidad, precio alto,
  cerrados salvo Meta.
- **Tier 2 — Strong open/affordable**: DeepSeek, Mistral, Qwen (Alibaba),
  Cohere. Reasoning fuerte a precio 5-10× menor; DeepSeek destaca como
  default barato de Aithera.
- **Tier 3 — Specialized**: xAI Grok, Perplexity, MiniMax, HuggingFace
  Inference. Modelos nicho (tiempo real, búsqueda, razonamiento chino).
- **Local-first**: Ollama, LM Studio, llama.cpp. Privacidad total, coste
  marginal de electricidad, requiere hardware (GPU/Apple Silicon/RAM).

Aithera **V0.7.3** ya tiene 8 proveedores integrados (`backend/app/ai/providers/`):
Ollama, OpenAI, Anthropic, Gemini, MiniMax, DeepSeek, OpenRouter, Grok (xAI).
Faltan Meta directo, Mistral, Qwen, Cohere, Perplexity, HuggingFace Inference,
LM Studio y llama.cpp (vía Ollama).

## Objetivo

- Servir como **punto de entrada único** al elegir proveedor IA para un
  caso de uso (chat, razonamiento, código, multimodal, self-host).
- Documentar el **estado real** de cada tier a julio 2026 con datos
  sintetizados de los docs verificados JWIKI-020..027 y JWIKI-031.
- Mantener **consistencia con el código Aithera**: nombres de clases,
  endpoints y modelos por defecto deben coincidir con `CLAUDE.md §10`
  y `backend/app/ai/providers/`.

## Estado

🟢 Verified — escrito 2026-07-09 sobre docs ya verificados (JWIKI-020..027,
031). 6/6 criterios CONSTITUTION §8. Nivel de confianza: 85%.

## Modelo del documento

```
Tier 1 (Frontier)        →  OpenAI · Anthropic · Google · Meta
Tier 2 (Strong open)     →  DeepSeek · Mistral · Qwen · Cohere
Tier 3 (Specialized)     →  xAI Grok · Perplexity · MiniMax · HuggingFace
Local-first              →  Ollama · LM Studio · llama.cpp
```

Cada tier: tabla con estrellas, modelo flagship jul-2026, context window,
pricing, function calling format, streaming, MCP, OpenAI-compat y licencia.
Tabla final: **matriz comparativa por criterio**. Sección de **selección
por caso de uso**. Sección de **estado en Aithera V0.7.3**.

---

## Tier 1 — Frontier (los 4 que marcan el techo)

Los proveedores frontier son los que definen el techo de calidad en 2026.
Todos tienen modelos **flagship** en producción con capacidad multimodal
(texto + imagen, algunos audio/video), context window ≥128K, y la mejor
disponibilidad de function calling. Precio: el más alto del mercado.

| Proveedor | Modelo flagship jul-2026 | Context | Pricing input/output ($/1M) | Function calling | Streaming | MCP | OpenAI-compat | Licencia |
|---|---|---|---|---|---|---|---|---|
| **OpenAI** | `gpt-5.5` (frontier) / `gpt-5.4-mini` (coste) | 256K | ~$3.00 / ~$15.00 (gpt-5.5) | Nativo (estándar de facto) | SSE | Sí (Responses API + tool calling) | Es el estándar | Closed (weights), MIT (SDK) |
| **Anthropic** | `claude-opus-4-8` (frontier) / `claude-haiku-4-5` (coste) | 200K | ~$15 / ~$75 (opus-4-8) | Propio (`tool_use`, NO OpenAI-compat) | SSE | Sí (tool_use + prompt caching) | No | Closed (weights), MIT (SDK) |
| **Google** | `gemini-3.5-pro` (frontier) / `gemini-3.5-flash` (coste) | **2M** | ~$1.25 / ~$5.00 (3.5-pro) | Nativo | SSE | Sí | Vía adapter, no nativo | Closed (weights), Apache-2.0 (SDK) |
| **Meta** | `llama-4-405b` (frontier) / `llama-4-70b` (coste) | 128K (varía) | Self-host gratis / API partners ~$2.65/$2.65 | OpenAI-compat vía partners | SSE | Sí (en vLLM/Together) | Vía partners | **Open weights (Llama Community License)** |

**Lectura del Tier 1**:

- **OpenAI** es el **estándar de facto**: su formato de function calling
  es el que casi todos los demás imitan. La familia gpt-5.x cubre desde
  nano (clasificación) hasta 5.5 (frontier). Tiene `gpt-oss` (open weights,
  jul 2026) como guiño al open source. Ver [`openai.md`](./openai.md).
- **Anthropic** gana en **código** (#1 histórico en SWE-bench) y
  **razonamiento** (Computer Use es único). Su prompt caching agresivo
  (5 min ephemeral, 90% descuento en reads) es el killer feature para
  system prompts grandes. Ver [`anthropic.md`](./anthropic.md).
- **Google** gana en **multimodal nativo** (texto/imagen/audio/video en
  la misma API) y **context window** (2M es único en producción).
  Gemini 3.5 Flash es **10× más barato** que Pro con calidad razonable.
  Ver [`gemini.md`](./gemini.md).
- **Meta** es el único Tier 1 con **open weights** (Llama 4.x bajo
  Llama Community License). Se puede self-hostear o consumir vía
  partners (Together, Groq, Fireworks). Reasoning en Llama 4 menor que
  Claude/GPT, pero coste marginal en self-host.

---

## Tier 2 — Strong open/affordable (los que democratizan)

Proveedores que dan **80-95% de la calidad frontier** a **5-10% del
precio**. La mayoría tiene **open weights** y opciones de self-host.
Aithera usa DeepSeek de este tier como **default barato**.

| Proveedor | Modelo flagship jul-2026 | Context | Pricing input/output ($/1M) | Function calling | Streaming | MCP | OpenAI-compat | Licencia |
|---|---|---|---|---|---|---|---|---|
| **DeepSeek** | `deepseek-v4-flash` (coste) / `deepseek-r1` (reasoning) | 64K (chat) / 128K (coder) | ~$0.07 / ~$0.27 (v4-flash) | OpenAI-compat nativo | SSE | Sí (razonable) | **Sí (100% compatible)** | Open weights (MIT-like) |
| **Mistral** | `mistral-large-3` (frontier) / `mistral-small-4` (coste) | 128K | ~$2 / ~$6 (large) | Nativo | SSE | Sí | Sí (vía SDK Mistral) | Open weights (Apache-2.0) |
| **Qwen** | `qwen3-max` (frontier) / `qwen3-32b` (open) | 128K-1M (varía) | ~$0.40 / ~$1.20 (max) | OpenAI-compat | SSE | Sí | **Sí (DashScope OpenAI-compat)** | Open weights (Apache-2.0 / Qwen) |
| **Cohere** | `command-r-plus` (RAG) / `command-r` (coste) | 128K | ~$2.50 / ~$10 (r-plus) | Nativo | SSE | Sí | Sí (vía SDK Cohere) | Closed (weights) |

**Lectura del Tier 2**:

- **DeepSeek** es la **sorpresa china 2024-2026**. Su modelo `deepseek-r1`
  (reasoning chain-of-thought, open weights) es comparable a o1 a
  **$0.27/$1.10 por millón**. Aithera v0.7.3 lo integra como
  `DeepSeekProvider` con `deepseek-v4-flash` como default barato.
  Ver [`deepseek.md`](./deepseek.md). **Crítico para Aithera**: el
  `reasoning_content` de R1 debe filtrarse (v0.8 **B21**
  `app/ai/reasoning_filter.py` ya lo hace).
- **Mistral** es el **proveedor europeo** (Francia) con open weights
  Apache-2.0. `mistral-large-3` está al nivel GPT-4 en razonamiento,
  con buen soporte multilingüe (FR/DE/ES/IT). Integración recomendada
  vía Mistral SDK o OpenAI-compat.
- **Qwen** (Alibaba) destaca en **multilingüe** (excelente en chino,
  japonés, español) y **math/code**. `qwen3-max` compite con Claude
  Opus. Open weights Apache-2.0. Integración vía DashScope API
  (OpenAI-compat) o self-host.
- **Cohere** es el **especialista en RAG** (Retrieval-Augmented
  Generation). `command-r-plus` está optimizado para grounding en
  documentos. Pesos cerrados, pero pricing razonable para enterprise.

---

## Tier 3 — Specialized (los que cubren nichos)

Proveedores que no compiten en "general purpose" sino que **destacan en
un eje concreto**: tiempo real (Grok), búsqueda con citas (Perplexity),
razonamiento chino rápido (MiniMax), agregador (OpenRouter), o
ecosistema de modelos (HuggingFace).

| Proveedor | Modelo flagship jul-2026 | Context | Pricing input/output ($/1M) | Function calling | Streaming | MCP | OpenAI-compat | Licencia |
|---|---|---|---|---|---|---|---|---|
| **xAI Grok** | `grok-4.3` (reasoning + humor) / `grok-4-mini` (coste) | 128K-2M (varía) | ~$3 / ~$15 (4.3) | OpenAI-compat | SSE | Sí | **Sí (vía xAI API)** | Closed (weights) |
| **Perplexity** | `sonar-pro` (search-augmented) / `sonar` (coste) | 127K | ~$3 / ~$15 (pro) | Limitado (search-only) | SSE | Parcial | Sí (vía Sonar API) | Closed (weights) |
| **MiniMax** | `MiniMax-M2.7-highspeed` (default Aithera) | 245K (varía) | ~$0.20 / ~$1.50 (M2.7-highspeed) | OpenAI-compat (parcial, sin function calling completo) | SSE | No (a jul-2026) | **Sí (vía `api.minimax.io`)** | Closed (weights) |
| **HuggingFace** | Agregador (200+ modelos) | Depende del modelo | Depende del provider upstream | Depende del modelo | SSE | Sí | Sí (HF Inference API) | Mixto (cada modelo su licencia) |
| **OpenRouter** | Agregador (100+ modelos) | Depende del modelo | Depende del modelo (markup incluido) | OpenAI-compat | SSE | Sí | **Sí (es 100% OpenAI-compat)** | Mixto (cada modelo su licencia) |

**Lectura del Tier 3**:

- **xAI Grok** (Elon Musk) tiene tono "no-corporate", acceso a X/Twitter
  en tiempo real, y reasoning fuerte. Aithera v0.7.3 lo integra como
  `GrokProvider` con `grok-4.3` como default. Útil para tareas que
  requieren **información fresca** de X.
- **Perplexity** es **search-augmented**: cada respuesta lleva citas
  inline a fuentes web. `sonar-pro` es la opción para research.
  Limitado como LLM general (no para razonamiento puro).
- **MiniMax** es el **proveedor chino de razonamiento rápido** que
  Aithera usa como **default por defecto** (`MINIMAX_DEFAULT_MODEL =
  MiniMax-M2.7-highspeed`). Es **barato** y **rápido** pero con
  restricciones: `max_completion_tokens` máximo **2048** (límite duro
  que el código debe respetar) y sin function calling completo.
  Endpoint cambió de `api.minimax.chat` a
  `api.minimax.io/v1/chat/completions` en 2024. Ver
  [`minimax.md`](./minimax.md).
- **HuggingFace Inference API** es un **agregador**: pasas el nombre
  del modelo (ej. `meta-llama/Llama-4-70b`) y HF rutea al provider
  (Together, AWS, etc.). Ideal para experimentar sin comprometerse
  con un vendor.
- **OpenRouter** (ya integrado en Aithera como `OpenRouterProvider`)
  es **100% OpenAI-compatible** y rutea a cualquier modelo del
  catálogo. Default `""` (libre, usuario elige). Útil para
  **A/B testing** entre modelos con cero código.

---

## Local-first (privacidad total, sin API key)

Para casos donde **los datos no pueden salir del dispositivo** (médico,
legal, finanzas, código propietario) o **no hay conexión**, los modelos
locales son la única opción.

| Herramienta | Backend | Modelos soportados | Hardware mínimo (8B) | Hardware frontera (70B+) | API expuesta | Aithera |
|---|---|---|---|---|---|---|
| **Ollama** | Binario único (Go) | Llama, Qwen, DeepSeek, Mistral, Gemma, Phi, Codellama, LLaVA (100+) | 8GB RAM / 6GB VRAM | 64GB RAM / 48GB VRAM (70B q4) | REST OpenAI-compat en `:11434` | ✅ Integrado (`OllamaProvider`, default `llama3`) |
| **LM Studio** | App GUI (Electron) | Cualquiera en formato GGUF (HuggingFace) | 8GB RAM | 64GB RAM | REST OpenAI-compat en `:1234` | ❌ No integrado |
| **llama.cpp** | CLI / librería C/C++ | Formato GGUF (mayoría open weights) | 4GB RAM (modelos 1-3B) | 96GB RAM (405B q2) | Server mode OpenAI-compat | ❌ No integrado (se accede vía Ollama) |
| **vLLM** | Servidor Python (Linux) | Cualquiera HuggingFace | 16GB VRAM (recomendado) | Multi-GPU (A100/H100) | REST OpenAI-compat | ❌ No integrado (post-V1.0) |

**Lectura del bloque Local-first**:

- **Ollama** es la opción más simple. Descargas un binario, haces
  `ollama pull llama3` y tienes un endpoint en `localhost:11434`
  hablando OpenAI-compat. Aithera ya lo integra vía `OllamaProvider`
  con `llama3` como modelo por defecto declarado. Ver
  [`local-ollama.md`](./local-ollama.md).
- **LM Studio** es la versión GUI (Electron) para usuarios no-técnicos.
  Mismo catálogo GGUF, mismo formato OpenAI-compat, distinto puerto
  (1234). Buena opción para el usuario final de Aithera que quiera
  probar modelos sin tocar terminal.
- **llama.cpp** es el **backend real** que usan Ollama y LM Studio
  por debajo. Para integraciones custom (cuantización extrema,
  inferencia en edge devices, Raspberry Pi) es la opción.
- **vLLM** es el **servidor de producción** para self-host serio:
  continuous batching, PagedAttention, throughput 10-20× mayor que
  llama.cpp naïve. Requiere Linux + GPU NVIDIA. Para Aithera
  post-V1.0.

---

## Matriz comparativa por criterio

Esta tabla cruza los **9 proveedores integrados en Aithera V0.7.3** por
**9 criterios técnicos**. Permite identificar de un vistazo quién cumple
qué.

| Criterio | OpenAI | Anthropic | Gemini | DeepSeek | MiniMax | Grok | OpenRouter | Ollama | Cohere† |
|---|---|---|---|---|---|---|---|---|---|
| **API format** | Nativo | Propio (`messages`) | Nativo | OpenAI-compat | OpenAI-compat (parcial) | OpenAI-compat | OpenAI-compat | OpenAI-compat | Nativo |
| **Function calling** | ✅ Estándar | ✅ `tool_use` propio | ✅ | ✅ OpenAI-compat | ❌ (a jul-2026) | ✅ | ✅ | ✅ (modelos grandes) | ✅ Tool Use |
| **Streaming SSE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MCP server/client** | ✅ (Tools) | ✅ (`tool_use`) | ✅ (Tools) | ⚠️ (no nativo, vía adapters) | ❌ | ⚠️ | ✅ (proxy) | ⚠️ (vía wrapper) | ⚠️ |
| **OpenAI-compat directo** | Es el estándar | ❌ | ❌ | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ |
| **Reasoning explícito** | ⚠️ (o-series separado) | ⚠️ (extended thinking) | ⚠️ (gemini-deep) | ✅ R1 nativo (`reasoning_content`) | ⚠️ (M2.7 razona pero sin tag) | ⚠️ (4.3 con thinking) | Depende del modelo | Depende del modelo | ❌ |
| **Multimodal** | ✅ Texto+imagen+audio | ✅ Texto+imagen+PDF | ✅ Texto+imagen+audio+**video** | ❌ Texto | ❌ Texto | ✅ Texto+imagen | Depende del modelo | ✅ Texto+imagen (LLaVA) | ❌ Texto |
| **Context máximo** | 256K | 200K | **2M** | 64K-128K | 245K | 128K-2M | Depende | 128K (varía) | 128K |
| **Licencia** | Closed + MIT SDK | Closed + MIT SDK | Closed + Apache-2.0 SDK | Open weights (MIT-like) | Closed | Closed | Mixto | MIT (binario) | Closed |

† Cohere **no está integrado en Aithera V0.7.3**; se incluye por ser
   referencia Tier 2.

**Lectura de la matriz**:

- Si necesitas **function calling estándar y SDK maduro** → OpenAI
- Si necesitas **razonamiento explícito chain-of-thought** → DeepSeek R1
- Si necesitas **multimodal nativo (incluido video)** → Gemini
- Si necesitas **2M context** → Gemini
- Si necesitas **prompt caching agresivo** → Anthropic
- Si necesitas **100% OpenAI-compat con coste bajo** → DeepSeek o MiniMax
- Si necesitas **privacidad total** → Ollama
- Si necesitas **A/B test rápido entre modelos** → OpenRouter

---

## Selección por caso de uso

Esta sección traduce la matriz en **recomendaciones concretas** para los
5 casos de uso más comunes en un asistente tipo Aithera.

### Chat general (latencia-bajo, coste-bajo)

- **Recomendado**: DeepSeek v4-flash (Aithera default barato) o
  Gemini 3.5 Flash (10× más barato que Pro).
- **Aithera actual**: MiniMax `M2.7-highspeed` es el default
  declarado; tiene la ventaja de ser muy rápido pero el `max_tokens`
  cap a 2048 puede limitar respuestas largas.
- **Alternativa para máxima calidad**: OpenAI `gpt-5.4-mini` o
  Claude `claude-haiku-4-5`.

### Razonamiento profundo (chain-of-thought, math, lógica)

- **Recomendado**: DeepSeek R1 (open weights, comparable a o1) o
  Gemini 3.5 Deep Thinking.
- **Aithera**: B21 reasoning filter (`app/ai/reasoning_filter.py`)
  ya está preparado para filtrar el `<think>...</think>` de modelos
  razonadores (DeepSeek R, MiniMax M2.7).
- **Alternativa**: Claude Opus 4.8 con extended thinking, OpenAI o-series.

### Código (completar, revisar, refactor)

- **Recomendado**: Claude Opus 4.8 (#1 histórico SWE-bench) o
  OpenAI gpt-5.5.
- **Aithera actual**: Anthropic `claude-sonnet-4-6` es el default
  declarado (a actualizar a opus-4-8 en próxima iteración).
- **Alternativa barata**: DeepSeek Coder V2, Codellama 13B (vía Ollama).

### Multimodal (imagen, audio, video)

- **Recomendado**: Gemini 3.5 Pro (multimodal nativo + 2M context) o
  GPT-5.5 (visión + audio).
- **Aithera actual**: Gemini `gemini-3.1-pro-preview` declarado
  (typo en el código; debe ser `gemini-3.5-pro` o `gemini-2.5-pro`).
- **Self-host**: Ollama con LLaVA (visión local sin API key).

### Self-host / privacidad total

- **Recomendado**: Ollama (la opción más simple).
- **Modelos según hardware**:
  - 8GB RAM → `llama3:8b`, `qwen3:8b`, `mistral:7b`
  - 16GB RAM → `gemma2:9b`, `qwen3:14b`
  - 32GB RAM → `qwen3:32b`, `deepseek-r1:32b`
  - 64GB+ → `llama3:70b` (frontier open)
- **Aithera**: `OllamaProvider` con `llama3` como default.
  El usuario puede cambiar el modelo en Settings.

---

## Estado en Aithera V0.7.3

Lista canónica de los **8 proveedores integrados** en Aithera V0.7.3
(fuente: `CLAUDE.md §10`, código en `backend/app/ai/providers/`):

| # | Proveedor | Clase | Endpoint | Modelo default | Notas |
|---|---|---|---|---|---|
| 1 | Ollama | `OllamaProvider` | `localhost:11434` | `llama3` | Local, sin API key, OpenAI-compat |
| 2 | OpenAI | `OpenAIProvider` | OpenAI API | `gpt-5.1` | SDK nativo, async |
| 3 | Anthropic | `AnthropicProvider` | Anthropic API | `claude-sonnet-4-6` | SDK propio (`anthropic-sdk-python`) |
| 4 | Gemini | `GeminiProvider` | Google AI | `gemini-3.1-pro-preview` | SDK propio (`google-generativeai`), ⚠️ typo en default |
| 5 | MiniMax | `MinimaxProvider` | `api.minimax.io/v1/chat/completions` | `MiniMax-M2.7-highspeed` | `max_completion_tokens` cap 2048 |
| 6 | DeepSeek | `DeepSeekProvider` | DeepSeek API | `deepseek-v4-flash` | OpenAI-compat, ultra-barato |
| 7 | OpenRouter | `OpenRouterProvider` | OpenRouter API | `""` (libre) | OpenAI-compat, agregador |
| 8 | Grok (xAI) | `GrokProvider` | xAI API | `grok-4.3` | OpenAI-compat |

**Base compartida** (`backend/app/ai/providers/openai_compatible.py`):
DeepSeek, OpenRouter, Grok, y parcialmente MiniMax reutilizan esta
base para evitar duplicar el cliente HTTP, el parsing de streaming SSE,
y el formato de respuesta.

**`AIManager`** (singleton en `ai_manager.py`):
- Lee `AIProviderConfig` de la BD en `__init__`
- Bootstrap desde `.env` solo si la DB está vacía
- Proveedor activo: el marcado `is_active=True`
- Health check con caché de 30 segundos
- Fallback no-streaming si `generate_stream` no produce chunks

**Seguridad V0.8**:
- API keys cifradas en reposo con DPAPI (`app/core/secrets.py`)
- Migración Alembic `d4e5f6a7b8c9_v08_encrypt_api_keys` re-cifra
  las existentes (idempotente)
- CORS restringido a orígenes conocidos (no `allow_origins=['*']`)

### Qué falta por integrar (candidatos próximos)

De la matriz Tier 1-2-3-Local, **faltan por integrar** en Aithera:

- **Mistral** (Tier 2) — alta prioridad. Open weights Apache-2.0,
  excelente multilingüe, OpenAI-compat vía SDK. Implementación
  trivial reutilizando `openai_compatible.py`.
- **Qwen** (Tier 2) — media prioridad. Open weights, multilingüe,
  excelente en code/math. OpenAI-compat vía DashScope.
- **Cohere** (Tier 2) — baja prioridad. Especialista en RAG, podría
  ser útil para V0.85 Memory.
- **Meta Llama directo** (Tier 1) — depende de casos de uso. Si se
  quiere exponer Llama 4 sin pasar por Ollama, vía Together/Fireworks.
- **Perplexity** (Tier 3) — nicho. Solo si Aithera necesita
  búsqueda-augmented en respuestas.
- **HuggingFace Inference API** (Tier 3) — baja. Útil para
  experimentación pero OpenRouter ya cubre ese nicho.
- **LM Studio** y **llama.cpp directos** (Local) — baja. Ollama ya
  cubre el 90% de los casos local-first.
- **vLLM** (Local) — post-V1.0. Para self-host serio en producción.

### Pendientes detectados en el código actual

- **OpenAI default stale**: `gpt-5.1` declarado en
  `openai_provider.py`, debe actualizarse a `gpt-5.4-mini` (coste)
  o `gpt-5.5` (frontier).
- **Anthropic default stale**: `claude-sonnet-4-6` declarado, debe
  actualizarse a `claude-opus-4-8` (frontier) o `claude-haiku-4-5` (coste).
- **Gemini default typo**: `gemini-3.1-pro-preview` NO existe en el
  lineup oficial; debe ser `gemini-3.5-pro` o `gemini-2.5-pro`.

---

## Pricing detallado (verificación pendiente)

> ⚠️ **ADVERTENCIA**: cifras estimadas a julio 2026 desde docs
> individuales verificados (JWIKI-020..027). **Verificar siempre en la
> página oficial de pricing antes de decisión financiera** — los
> proveedores ajustan precios trimestralmente.

| Proveedor | Modelo | Input $/1M | Output $/1M | Context | Fuente |
|---|---|---|---|---|---|
| OpenAI | gpt-5.5 | ~$3.00 | ~$15.00 | 256K | [`openai.md`](./openai.md) |
| OpenAI | gpt-5.4 | ~$2.50 | ~$10.00 | 256K | [`openai.md`](./openai.md) |
| OpenAI | gpt-5.4-mini | ~$0.40 | ~$1.60 | 256K | [`openai.md`](./openai.md) |
| OpenAI | gpt-5.4-nano | ~$0.10 | ~$0.40 | 256K | [`openai.md`](./openai.md) |
| OpenAI | gpt-realtime-2 | ~$40 (audio in) | ~$80 (audio out) | 32K audio | [`openai.md`](./openai.md) |
| Anthropic | claude-opus-4-8 | ~$15.00 | ~$75.00 | 200K | [`anthropic.md`](./anthropic.md) |
| Anthropic | claude-haiku-4-5 | ~$0.80 | ~$4.00 | 200K | [`anthropic.md`](./anthropic.md) |
| Google | gemini-3.5-pro | ~$1.25 | ~$5.00 | 2M | [`gemini.md`](./gemini.md) |
| Google | gemini-3.5-flash | ~$0.075 | ~$0.30 | 1M | [`gemini.md`](./gemini.md) |
| DeepSeek | deepseek-v4-flash | ~$0.07 | ~$0.27 | 64K | [`deepseek.md`](./deepseek.md) |
| DeepSeek | deepseek-r1 | ~$0.27 | ~$1.10 | 64K | [`deepseek.md`](./deepseek.md) |
| DeepSeek | deepseek-coder-v2 | ~$0.14 | ~$0.28 | 128K | [`deepseek.md`](./deepseek.md) |
| MiniMax | M2.7-highspeed | ~$0.20 | ~$1.50 | 245K | [`minimax.md`](./minimax.md) |

**Ratio coste aproximado** (referencia: 1.0 = gpt-5.5 output):

| Modelo | Ratio output | Caso de uso |
|---|---|---|
| `gpt-5.4-nano` | 0.027 | Clasificación barata |
| `gemini-3.5-flash` | 0.020 | Flash multimodal |
| `deepseek-v4-flash` | 0.018 | **Default Aithera barato** |
| `minimax-m2.7-highspeed` | 0.10 | Default declarado Aithera |
| `gpt-5.4-mini` | 0.107 | OpenAI barato |
| `deepseek-coder-v2` | 0.019 | Código barato |
| `claude-haiku-4-5` | 0.267 | Anthropic barato |
| `gpt-5.4` | 0.667 | OpenAI medio |
| `gemini-3.5-pro` | 0.333 | Google medio |
| `gpt-5.5` | 1.000 | OpenAI frontier |
| `claude-opus-4-8` | 5.000 | Anthropic frontier |

---

## Rate limits típicos (orden de magnitud)

| Proveedor | Free tier | Tier 1 (~$5-50 spend) | Tier 3-4 (~$100-1000) | Notas |
|---|---|---|---|---|
| OpenAI | 3 RPM, 40K TPM | 60 RPM, 500K TPM | 5K-10K RPM | Tier 5+ custom |
| Anthropic | No free tier (trial limitado) | 50 RPM, 100K TPM | 1K-4K RPM | Prompt caching reduce uso efectivo |
| Google | 15 RPM (Gemini API free) | 360 RPM | 1K+ RPM | Vertex AI tiers separados |
| DeepSeek | No free tier | 60 RPM | Custom | Barato incentiva subir tier |
| MiniMax | No free tier | 60 RPM | Custom | Límite duro 2048 max_tokens |
| Grok (xAI) | No free tier | 60 RPM | 1K+ RPM | Tier X Premium tiene cuota |
| OpenRouter | Pay-per-token (no rate limit fijo) | — | — | Mark-up por modelo |
| Ollama | Sin límite (depende de tu hardware) | — | — | Local, sin API key |

---

## Snippets de código

### Snippet 1: Listar todos los proveedores activos desde Aithera

```python
# backend/app/ai/ai_manager.py
from app.ai.providers import (
    OpenAIProvider, AnthropicProvider, GeminiProvider,
    DeepSeekProvider, MinimaxProvider, GrokProvider,
    OpenRouterProvider, OllamaProvider
)

PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "minimax": MinimaxProvider,
    "grok": GrokProvider,
    "openrouter": OpenRouterProvider,
    "ollama": OllamaProvider,
}
```

### Snippet 2: Cambiar de proveedor activo en runtime

```python
# Llamada típica desde un endpoint FastAPI
from app.ai.ai_manager import ai_manager

# Provider activo actual
active = ai_manager.get_active_provider()
print(active.provider_name, active.default_model_name)

# Cambiar (escribe en AIProviderConfig.is_active)
ai_manager.set_active_provider("deepseek")
```

### Snippet 3: Fallback chain (OpenAI → DeepSeek → Ollama)

```python
# Pseudocódigo para producción robusta
async def chat_with_fallback(messages, tools=None):
    chain = ["openai", "deepseek", "ollama"]
    for provider_name in chain:
        try:
            provider = ai_manager.get_provider(provider_name)
            return await provider.chat(messages, tools=tools)
        except Exception as e:
            log.warning(f"{provider_name} falló: {e}, probando siguiente")
    raise AllProvidersFailedError(...)
```

### Snippet 4: Filtrar reasoning de modelos razonadores (B21)

```python
# backend/app/ai/reasoning_filter.py (V0.8)
from app.ai.reasoning_filter import strip_reasoning, StreamingReasoningFilter

# Modo completo (no streaming)
clean_text = strip_reasoning(raw_response)
# Remueve <think>...</think> de DeepSeek R1, MiniMax M2.7, etc.

# Modo streaming (SSE chunk a chunk, tolera tag partido entre chunks)
async for clean_chunk in StreamingReasoningFilter(raw_stream):
    yield clean_chunk
```

### Snippet 5: Configuración multi-proveedor en `.env`

```bash
# .env — Aithera V0.7.3
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=sk-...
MINIMAX_API_KEY=...
GROK_API_KEY=xai-...
OPENROUTER_API_KEY=sk-or-...
# Ollama no requiere API key
DEFAULT_AI_PROVIDER=minimax  # o "deepseek" para barato
```

---

## Referencias cruzadas

### Docs JWIKI verificados (fuentes principales)

- [`openai.md`](./openai.md) — JWIKI-020 (✓ 2026-07-07)
- [`anthropic.md`](./anthropic.md) — JWIKI-021 (✓ 2026-07-07)
- [`gemini.md`](./gemini.md) — JWIKI-022 (✓ 2026-07-07)
- [`deepseek.md`](./deepseek.md) — JWIKI-024 (✓ 2026-07-07)
- [`minimax.md`](./minimax.md) — JWIKI-027 (✓ 2026-07-07)
- [`local-ollama.md`](./local-ollama.md) — JWIKI-031 (✓ 2026-07-07)

### Docs pendientes en esta sección

- `meta-llama.md` — Tier 1 (open weights)
- `mistral.md` — Tier 2 (europeo, multilingüe)
- `qwen.md` — Tier 2 (Alibaba, code/math)
- `cohere.md` — Tier 2 (RAG specialist)
- `grok.md` — Tier 3 (xAI, real-time)
- `perplexity.md` — Tier 3 (search-augmented)
- `openrouter.md` — Tier 3 (agregador OpenAI-compat)
- `huggingface.md` — Tier 3 (agregador HF)
- `lm-studio.md` — Local-first (GUI)
- `llama-cpp.md` — Local-first (backend C/C++)
- `vllm.md` — Local-first (servidor prod)

### Código Aithera (referencias §10 CLAUDE.md)

- `backend/app/ai/ai_manager.py` — singleton, fallback chain
- `backend/app/ai/providers/` — 8 providers integrados
- `backend/app/ai/providers/openai_compatible.py` — base compartida
- `backend/app/ai/reasoning_filter.py` — B21 V0.8, filtra reasoning
- `backend/app/core/secrets.py` — DPAPI cifrado de API keys
- `backend/alembic/versions/d4e5f6a7b8c9_v08_encrypt_api_keys.py` — migración

---

## Pendientes

1. **Verificar pricing oficial** de OpenAI, Anthropic, Gemini, DeepSeek
   y MiniMax en sus páginas oficiales (rate-limited en tick 2026-07-07).
2. **Actualizar defaults stale** en código:
   - `OpenAIProvider.default_model_name`: `gpt-5.1` → `gpt-5.4-mini`
   - `AnthropicProvider.default_model_name`: `claude-sonnet-4-6` → `claude-haiku-4-5` o `claude-opus-4-8`
   - `GeminiProvider.default_model_name`: `gemini-3.1-pro-preview` → `gemini-3.5-pro` o `gemini-2.5-pro`
3. **Crear docs individuales pendientes** (Mistral, Qwen, Cohere,
   Grok, OpenRouter, Meta, Perplexity, HF, LM Studio, llama.cpp, vLLM).
4. **Evaluar integración Mistral** como siguiente provider Tier 2
   (reutiliza `openai_compatible.py`, esfuerzo mínimo).
5. **Evaluar self-host vLLM** post-V1.0 para producción seria en
   servidor propio (continuos batching, PagedAttention).

---

## Nivel de confianza

**85%** — datos sintetizados de docs verificados JWIKI-020..027,031 con
múltiples checks cruzados contra `CLAUDE.md §10` y el código real de
Aithera V0.7.3. Pricing marcado como [VERIFICAR] en cada doc individual
sigue pendiente de contrastar con páginas oficiales; el resto del doc
es estable (formatos API, modelos flagship, integraciones Aithera).

---

## Changelog

- **2026-07-09** — v1.0. Escritura inicial con matriz 4 tiers × 14
  proveedores, criterios cruzados, selección por caso de uso y estado
  Aithera V0.7.3. ~3500 palabras. 6/6 criterios CONSTITUTION §8.
  Reemplaza el borrador mediocre de 11KB (2026-07-07 02:00) que
  carecía de datos contrastados y referencias cruzadas.

---

*Sección 05 — AI PROVIDERS. Matriz horizontal de referencia. Validador
de dominio: Aithera IA (`aithera-ia`). Docs individuales en los archivos
vecinos de esta carpeta. Para el estado global del wiki ver
`00_INDEX/wiki-map.md`.*