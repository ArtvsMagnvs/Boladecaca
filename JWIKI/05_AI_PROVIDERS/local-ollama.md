# Ollama — Self-host de LLMs en local

## Resumen

Ollama es la **manera más simple de ejecutar LLMs en local**. Un binario único (`ollama`) descarga y corre modelos de Llama, Qwen, DeepSeek, Mistral, Gemma, Phi, etc. Expone una **API REST OpenAI-compatible** en `localhost:11434`. Aithera v0.7.3 lo integra nativamente en `backend/app/ai/providers/ollama_provider.py` con `llama3` como modelo por defecto. Es la opción **#1 para privacidad total y self-host**.

## Objetivo

Documentar Ollama como proveedor integrado en Aithera: instalación, modelos, API, integración. Responde a "¿cómo uso Ollama en Aithera y qué modelos tengo disponibles?".

## Estado

🟡 En progreso — base escrita 2026-07-07.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Ollama | ≥0.5 (recomendado ≥0.10) | MIT, single binary |
| Ollama API | v1 (OpenAI-compat) | `localhost:11434/v1` |
| Ollama native API | n/a (legacy) | `localhost:11434/api/...` |
| Modelos | 100+ en https://ollama.com/library | Llama, Qwen, DeepSeek, Mistral, Gemma, Phi, etc. |
| Aithera | V0.7+ | `app/ai/providers/ollama_provider.py` |

## Instalación

### Windows

```powershell
# Descarga desde https://ollama.com/download/windows
# O via winget
winget install Ollama.Ollama
```

### macOS

```bash
brew install ollama
# O descarga desde https://ollama.com/download/mac
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Iniciar servicio

```bash
ollama serve  # En otra terminal, o como servicio
```

## Modelos populares

| Modelo | Tamaño | RAM mínima | VRAM (GPU) | Notas |
|---|---|---|---|---|
| **llama3** | 8B (4.7GB) | 8GB | 6GB | Default Aithera |
| llama3:70b | 70B (40GB) | 64GB | 48GB | Frontier open |
| **qwen3:8b** | 8B (4.5GB) | 8GB | 6GB | Excelente multilingüe |
| qwen3:32b | 32B (20GB) | 32GB | 24GB | Frontier open |
| **deepseek-r1:1.5b** | 1.5B (1.1GB) | 4GB | 2GB | Reasoning barato |
| deepseek-r1:7b | 7B (4.7GB) | 8GB | 6GB | Reasoning medio |
| deepseek-r1:32b | 32B (20GB) | 32GB | 24GB | Reasoning fuerte |
| **mistral** | 7B (4.1GB) | 8GB | 6GB | Europeo |
| **gemma2:9b** | 9B (5.4GB) | 8GB | 6GB | Google open |
| **phi3:mini** | 3.8B (2.3GB) | 4GB | 4GB | Microsoft, ultra-ligero |
| codellama:13b | 13B (7.4GB) | 16GB | 12GB | Código |
| **llava** | 7B (4.5GB) | 8GB | 6GB | Multimodal (vision) |

## Comandos básicos

```bash
# Descargar modelo
ollama pull llama3

# Ejecutar interactivo
ollama run llama3

# Listar modelos descargados
ollama list

# Ver info de un modelo
ollama show llama3

# Eliminar modelo
ollama rm llama3

# Ver logs/servicio
ollama logs
```

## API REST (OpenAI-compat)

### Chat completions

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Streaming

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

### Function calling

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "What is the weather in Madrid?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }]
  }'
```

## Integración en Aithera

### `app/ai/providers/ollama_provider.py` (excerpt)

```python
from openai import OpenAI

class OllamaProvider:
    """Proveedor Ollama (self-host, OpenAI-compat)."""
    
    default_model_name = "llama3"
    base_url = "http://localhost:11434/v1"
    
    def __init__(self, **kwargs):
        # Ollama no requiere API key (local)
        self.client = OpenAI(
            api_key="ollama",  # placeholder
            base_url=self.base_url
        )
    
    async def chat(self, messages, model=None, **kwargs):
        model = model or self.default_model_name
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    def list_available_models(self) -> list[str]:
        """Llama al endpoint /api/tags de Ollama."""
        import httpx
        r = httpx.get("http://localhost:11434/api/tags")
        return [m["name"] for m in r.json().get("models", [])]
```

### Configuración en Aithera

```python
# AIProviderConfig
{
    "name": "ollama",
    "display_name": "Ollama (local)",
    "is_active": False,  # Activar manualmente desde Settings
    "base_url": "http://localhost:11434/v1",
    "default_model": "llama3"
}
```

### Verificar que Ollama está corriendo

Aithera **no arranca Ollama automáticamente**. El user debe:
1. Instalar Ollama
2. Ejecutar `ollama serve` (o como servicio)
3. Activar el proveedor en Settings → AI Providers → Ollama

Si Ollama no está corriendo, Aithera degrada gracefully y muestra mensaje: "Ollama no detectado en localhost:11434. Inicia ollama serve o cambia de proveedor."

## Cuándo elegir Ollama sobre cloud

✅ **Elegir Ollama cuando**:
- **Privacidad total** (datos no salen del PC)
- **Costo cero** (eléctrico + hardware, no API fees)
- **Offline** (funciona sin internet)
- **Experimentos** (probar modelos sin gastar dinero)
- **Self-host** de modelos frontier (qwen3:32b, deepseek-r1:32b)
- **Latencia ultra-baja** (sin round-trip a API)

❌ **NO elegir Ollama cuando**:
- **Modelo muy grande** sin hardware (70B+ requiere GPUs caras)
- **Velocidad consistente** (varía con carga del sistema)
- **Multimodal avanzado** (Ollama soporta llava pero es limitado)
- **Realtime** (overhead de self-host)
- **Uptime SLA** (si el PC se apaga, el modelo desaparece)

## Hardware mínimo

| Modelo | RAM | VRAM (GPU NVIDIA) | Notas |
|---|---|---|---|
| 1.5B (deepseek-r1:1.5b) | 4GB | 2GB | Cualquier PC moderno |
| 7-8B (llama3, qwen3:8b) | 8GB | 6GB | PC gaming básico |
| 13B (codellama) | 16GB | 12GB | Workstation |
| 32B (qwen3:32b, deepseek-r1:32b) | 32GB | 24GB | Necesita GPU (RTX 3090+) |
| 70B (llama3:70b) | 64GB | 48GB | Multi-GPU o cuantizado |
| 405B (llama3:405b) | 256GB+ | 200GB+ | Cluster, no viable en local |

**Aithera recomienda**: empezar con `llama3` (8B) en cualquier PC con 8GB RAM, escalar a 32B si se tiene hardware.

## Cuantización

Ollama sirve modelos cuantizados (Q4_0, Q5_K_M, Q8_0). Trade-off calidad/tamaño:
- **Q4_0**: 4 bits por peso, ~50% del tamaño original, ~95% calidad
- **Q5_K_M**: 5 bits, ~60% tamaño, ~97% calidad (sweet spot)
- **Q8_0**: 8 bits, ~100% tamaño, ~99% calidad

Ollama usa Q4_0 por defecto para modelos grandes (70B+) y Q5_K_M para medianos (7-32B).

## Pendientes

- [ ] Verificar Ollama versión actual exacta
- [ ] Documentar GPU support (NVIDIA CUDA, AMD ROCm, Apple Metal)
- [ ] Documentar embeddings endpoint (`/api/embeddings`)
- [ ] Comparativa con LM Studio (alternativa GUI)
- [ ] Comparativa con llama.cpp (más bajo nivel)
- [ ] Benchmarks de performance local vs cloud

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-031 local-ollama.md (este doc)]
- [JWIKI-032 local-lmstudio.md](./local-lmstudio.md) — alternativa GUI
- [JWIKI-033 local-llamacpp.md](./local-llamacpp.md) — bajo nivel
- [JWIKI-024 deepseek.md](./deepseek.md) — modelos DeepSeek self-host
- [JWIKI-022 gemini.md](./gemini.md) — alternativa cloud
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. `https://ollama.com` — acceso 2026-07-07
2. `https://ollama.com/library` — catálogo de modelos
3. `https://github.com/ollama/ollama` — código fuente (175k★)
4. `backend/app/ai/providers/ollama_provider.py` — código Aithera v0.7.3
5. CLAUDE.md §10 — sistema multi-proveedor

## Nivel de confianza

**95%** — Ollama es estable, API bien documentada, integración con Aithera confirmada. Pendiente: versión exacta actual, benchmarks.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado
- Validador: contraste con `ollama_provider.py`
- Estado: 🟡 en progreso
