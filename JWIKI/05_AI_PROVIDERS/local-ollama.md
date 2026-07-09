# Ollama — Self-host de LLMs en local

## Resumen

**Ollama** es la manera más simple de ejecutar LLMs en local. Un binario único (`ollama`) descarga y corre modelos de Llama, Qwen, DeepSeek, Mistral, Gemma, Phi, etc. Expone una **API REST OpenAI-compatible** en `localhost:11434`. Aithera V0.7.3 lo integra nativamente en `backend/app/ai/providers/ollama_provider.py` con `llama3` como modelo por defecto. Es la opción **#1 para privacidad total y self-host**.

## Estado

🟢 Verificado — generado 2026-07-07, contrastado con GitHub API 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **Ollama** | ≥0.5 (recomendado ≥0.10) | **MIT**, 175.608★, último push 2026-07-06 |
| Ollama API | OpenAI-compat | `localhost:11434/v1` |
| Modelos | 100+ en https://ollama.com/library | Llama, Qwen, DeepSeek, Mistral, Gemma, Phi |

## Instalación

```powershell
# Windows
winget install Ollama.Ollama
```

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh
```

```bash
ollama serve  # iniciar servicio
```

## Modelos populares

| Modelo | Tamaño | RAM | VRAM |
|---|---|---|---|
| llama3 | 8B | 8GB | 6GB |
| llama3:70b | 70B | 64GB | 48GB |
| qwen3:8b | 8B | 8GB | 6GB |
| qwen3:32b | 32B | 32GB | 24GB |
| deepseek-r1:1.5b | 1.5B | 4GB | 2GB |
| deepseek-r1:32b | 32B | 32GB | 24GB |
| mistral | 7B | 8GB | 6GB |
| gemma2:9b | 9B | 8GB | 6GB |
| phi3:mini | 3.8B | 4GB | 4GB |
| llava | 7B | 8GB | 6GB (vision) |
| codellama:13b | 13B | 16GB | 12GB (code) |

## Comandos básicos

```bash
ollama pull llama3
ollama run llama3
ollama list
ollama show llama3
ollama rm llama3
```

## API REST (OpenAI-compat)

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3","messages":[{"role":"user","content":"Hello!"}]}'
```

```bash
# Streaming
curl http://localhost:11434/v1/chat/completions \
  -d '{"model":"llama3","messages":[{"role":"user","content":"Tell me a story"}],"stream":true}'
```

```bash
# Function calling (compatible OpenAI tools format)
curl http://localhost:11434/v1/chat/completions \
  -d '{"model":"llama3","messages":[{"role":"user","content":"What is the weather in Madrid?"}],"tools":[...]}'
```

## Integración en Aithera

```python
from openai import OpenAI

class OllamaProvider:
    default_model_name = "llama3"
    base_url = "http://localhost:11434/v1"
    
    def __init__(self, **kwargs):
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
```

## Cuándo elegir Ollama

- ✅ **Privacidad total** (datos no salen del PC).
- ✅ **Costo cero** (eléctrico + hardware).
- ✅ **Offline** (sin internet).
- ✅ **Self-host** de modelos frontier (qwen3:32b, deepseek-r1:32b).
- ✅ **Latencia ultra-baja**.

❌ NO elegir:
- ❌ Modelos muy grandes sin hardware.
- ❌ Velocidad consistente.
- ❌ Realtime avanzado.
- ❌ Uptime SLA.

## Hardware mínimo

| Modelo | RAM | VRAM |
|---|---|---|
| 1.5B | 4GB | 2GB |
| 7-8B | 8GB | 6GB |
| 13B | 16GB | 12GB |
| 32B | 32GB | 24GB (RTX 3090+) |
| 70B | 64GB | 48GB (multi-GPU) |

## Cuantización

- **Q4_0**: 50% tamaño, ~95% calidad
- **Q5_K_M**: 60% tamaño, ~97% calidad (sweet spot)
- **Q8_0**: 100% tamaño, ~99% calidad

Ollama usa Q4_0 por default para 70B+, Q5_K_M para medianos.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-023 meta-llama.md](./meta-llama.md)
- [JWIKI-024 deepseek.md](./deepseek.md)
- [JWIKI-032 local-lmstudio.md](./local-lmstudio.md)
- [JWIKI-033 local-llamacpp.md](./local-llamacpp.md)

## Fuentes

1. https://ollama.com — acceso 2026-07-09
2. https://github.com/ollama/ollama — 175.608★, MIT
3. https://ollama.com/library — catálogo

## Nivel de confianza

**95%** — Ollama estable, API bien documentada.

---

## Changelog

### 2026-07-07 — versión inicial
### 2026-07-09 — contrastado GitHub API (175.608★, último push 2026-07-06)
- Estado: 🟢 verified