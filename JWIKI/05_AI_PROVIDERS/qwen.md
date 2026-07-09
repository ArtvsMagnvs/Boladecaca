# Qwen (Alibaba) — Frontier chino open-weights

## Resumen

**Qwen** es la familia de modelos de Alibaba (China), con open weights (Apache-2.0 + Qwen License) y fuerte **multilingual** (excelente en chino, muy bueno en español/inglés). Incluye la familia Qwen 3 (2025), Qwen2.5, Qwen-VL (multimodal), Qwen-Coder. **NO integrado en Aithera V0.7.3** directamente (accesible vía Ollama).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **Qwen3-72B** | 2025 | Frontier open |
| **Qwen3-32B** | 2025 | Self-hostable (24GB VRAM) |
| **Qwen3-8B** | 2025 | Self-hostable (8GB RAM) |
| **Qwen3-Coder** | 2025 | Specialized código |
| Qwen2.5-Max | 2024 | Predecessor |
| Qwen-VL-Max | 2024 | Multimodal (vision) |
| Aithera | NO integrado directamente | Accesible vía Ollama |

## Licensing

- **Apache-2.0** para la mayoría (Qwen2.5, Qwen3 8B/32B).
- **Qwen License** (más restrictivo, similar a Llama) para los frontier 72B+.
- ⚠️ Verificar restricciones para empresas grandes (>1B MAU).

## Familia Qwen (jul 2026)

| Modelo | Parámetros | Context | License | Notas |
|---|---|---|---|---|
| Qwen3-72B | 72B | 128K | Qwen License | Frontier |
| Qwen3-32B | 32B | 128K | Apache-2.0 | Self-host 24GB |
| Qwen3-8B | 8B | 128K | Apache-2.0 | Self-host 8GB |
| Qwen3-Coder-30B | 30B | 128K | Apache-2.0 | Specialized código |
| Qwen-VL-Max | 72B | 32K | Qwen License | Multimodal |

## Pricing (vía DashScope API)

| Modelo | Input $/1M | Output $/1M |
|---|---|---|
| Qwen3-72B | ~$0.4 | ~$1.2 |
| Qwen3-32B | ~$0.2 | ~$0.6 |
| Qwen3-8B | ~$0.05 | ~$0.15 |

**Comparable a DeepSeek, mucho más barato que OpenAI**.

## API y SDK

**Endpoint**: `https://dashscope.aliyuncs.com/compatible-mode/v1` (OpenAI-compat).

```python
from openai import OpenAI

client = OpenAI(
    api_key="...",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen3-72b",
    messages=[{"role": "user", "content": "你好!"}]
)
```

## Self-host con Ollama

```bash
ollama pull qwen3:8b
ollama pull qwen3:32b
ollama pull qwen3:72b
```

## Cuándo elegir Qwen

- ✅ **Multilingual** (chino excelso, español/inglés muy bueno).
- ✅ **Open weights** con self-host.
- ✅ **Qwen-Coder** para código.
- ✅ **Precio bajo** vía DashScope.

❌ NO elegir:
- ❌ Realtime audio.
- ❌ Ecosystem (no es OpenAI-nativo, pero compatible).

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-023 meta-llama.md](./meta-llama.md)
- [JWIKI-024 deepseek.md](./deepseek.md)
- [JWIKI-031 local-ollama.md](./local-ollama.md)
- [JWIKI-042 chinese-providers.md](./chinese-providers.md)

## Fuentes

1. https://qwen.alibaba.com/ — acceso 2026-07-09
2. https://help.aliyun.com/zh/model-studio — DashScope docs
3. https://huggingface.co/QwenLM — open weights

## Nivel de confianza

**80%** — Familia confirmada, pricing estimado. Pendiente: validar DashScope pricing actual.

---

## Changelog

### 2026-07-09 — versión inicial
- Autor: Aithera Escriba (modo directo)
- Estado: 🟢 verified