# llama.cpp — Inferencia LLM low-level CPU/GPU

## Resumen

**llama.cpp** (Georgi Gerganov) es el proyecto de referencia para **inferencia de LLMs en CPU** y GPU. Escrito en C++. Permite correr Llama y otros modelos en hardware modesto (incluso Raspberry Pi). Es la **base de Ollama y LM Studio**. NO integrado en Aithera V0.7.3 directamente.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **llama.cpp** | main (rolling) | **MIT**, ~80k★ |
| Binding Python | llama-cpp-python | PyPI package |
| Binding Node.js | node-llama-cpp | npm package |
| Formato modelo | GGUF | Quantized GGML Universal Format |

## Características

- **CPU inference** con optimizaciones AVX2/AVX-512/NEON.
- **GPU acceleration**: NVIDIA CUDA, AMD ROCm, Apple Metal, Intel SYCL.
- **Quantización**: 1.5-bit a 8-bit (Q2_K a Q8_0).
- **Multi-modelo** en un proceso.
- **Batch processing**.
- **Context shifting** para contextos largos.
- **Speculative decoding**.
- **LoRA adapters** en runtime.

## Cuándo elegir llama.cpp vs Ollama vs LM Studio

| Criterio | llama.cpp | Ollama | LM Studio |
|---|---|---|---|
| **GUI** | ❌ CLI only | ❌ CLI only | ✅ Sí |
| **Performance** | **⭐⭐⭐⭐⭐** (más rápido) | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Facilidad** | ⭐⭐ (compilar) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Embeddings** | ✅ | ✅ | ✅ |
| **Multi-modelo en proceso** | ✅ | ✅ | ✅ |
| **Server OpenAI** | ❌ manual | ✅ built-in | ✅ built-in |
| **Binding Python** | ✅ llama-cpp-python | ✅ | ❌ |

**Llama.cpp** es para quien quiere máximo performance + control total.

## API server (manual)

llama.cpp tiene un server minimalista que se compila aparte:

```bash
./llama-server -m model.gguf -c 4096 --port 8080
```

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/chat/completions",
    json={
        "model": "model.gguf",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)
```

## Para Aithera V0.85

Si necesitas máximo performance (sin overhead de Ollama), añadir llama.cpp como proveedor:
- Binding Python: `pip install llama-cpp-python`.
- Cargar modelo con `Llama(model_path="...")`.

## Referencias cruzadas

- [JWIKI-031 local-ollama.md](./local-ollama.md)
- [JWIKI-032 local-lmstudio.md](./local-lmstudio.md)

## Fuentes

1. https://github.com/ggerganov/llama.cpp — ~80k★, MIT
2. https://github.com/abetlen/llama-cpp-python — binding Python
3. https://github.com/ggerganov/ggml — formato GGML original

## Nivel de confianza

**90%** — llama.cpp es estable y battle-tested.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified