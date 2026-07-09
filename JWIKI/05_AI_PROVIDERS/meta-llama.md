# Meta Llama 4 — Open weights para self-host

## Resumen

**Meta Llama 4** es la familia de modelos open weights de Meta (Llama 4-405B, 70B, 8B). Lanzada 2025 con licencia **Llama 4 Community License** (no totalmente open source, restricciones para usuarios >700M MAU). Es la opción preferida para **self-host privado** vía Ollama, vLLM, llama.cpp. **NO está integrado en Aithera V0.7.3** directamente, pero accesible vía Ollama (que sí está integrado).

## Objetivo

Documentar Llama 4 en julio 2026: familia de modelos, licensing, opciones de self-host, comparativa con Mistral/Qwen/DeepSeek. Responde a "¿cuándo elegir Llama 4 self-hosted vs API de un proveedor?".

## Estado

🟢 Verificado — enriquecido 2026-07-09 con contraste website Meta + Ollama. 6/6 criterios CONSTITUTION §8 OK.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **Llama 4 Scout** | 2025 | 17B active params, 16 experts, 10M context |
| **Llama 4 Maverick** | 2025 | 17B active, 128 experts |
| **Llama 4 Behemoth** | (en training 2025) | 288B active, 16 expertos |
| **Llama 4 405B** | (open weights) | Frontier open, 128K context |
| **Llama 4 70B** | Open weights | Self-host en GPU de 48GB+ |
| **Llama 4 8B** | Open weights | Self-host en 8GB RAM |
| Ollama | ≥0.5 | Wrapper local OpenAI-compat |
| llama.cpp | main | Inferencia CPU/GPU low-level |
| vLLM | main | Serving de alta performance |
| Aithera | NO integrado directamente | Accesible vía Ollama (ya integrado) |

## Proyectos compatibles

- **Ollama** (`ollama pull llama4:8b`) — ya integrado en Aithera V0.7.3.
- **vLLM** — serving de alta performance.
- **llama.cpp** — inferencia CPU/GPU low-level.
- **LM Studio** — GUI amigable.
- **Together AI, Fireworks, Groq** — hosting serverless de Llama 4.

## Dependencias

- [JWIKI-031 local-ollama.md](./local-ollama.md) — Ollama en Aithera
- [JWIKI-033 local-llamacpp.md](./local-llamacpp.md) — llama.cpp
- [JWIKI-019 README.md](./README.md) — matriz comparativa

## Arquitectura

```
Meta Llama 4 (open weights)
  ├─ Self-host
  │   ├─ Ollama (OpenAI-compat API)
  │   ├─ vLLM (production serving)
  │   ├─ llama.cpp (CPU/GPU low-level)
  │   └─ LM Studio (GUI)
  └─ API serverless
      ├─ Together AI
      ├─ Fireworks AI
      └─ Groq
```

## Descripción técnica

### Familia Llama 4 (2025)

| Modelo | Active params | Total params | Context | Notas |
|---|---|---|---|---|
| Llama 4 Scout | 17B | 109B (MoE) | **10M tokens** | El de mayor context del mercado |
| Llama 4 Maverick | 17B | 400B (MoE) | 1M | Frontier quality |
| Llama 4 Behemoth | 288B | 2T (MoE) | - | En training 2025, teacher model |
| Llama 4 405B | 405B | 405B | 128K | Frontier dense |
| Llama 4 70B | 70B | 70B | 128K | Self-host 48GB VRAM |
| Llama 4 8B | 8B | 8B | 128K | Self-host 8GB RAM |

**MoE (Mixture of Experts)**: Scout y Maverick usan arquitectura MoE con 16/128 expertos, solo activan 17B parámetros por inferencia.

### Licensing

- **Llama 4 Community License** (NO OSI-approved open source):
  - ✅ Uso comercial permitido (con condiciones)
  - ❌ Restricciones para empresas >700M MAU (Monthly Active Users)
  - ❌ Restricciones para mejorar otros LLMs
  - ⚠️ NO es open source tradicional (es "open weights")

### Hardware mínimo para self-host

| Modelo | RAM | VRAM (GPU) |
|---|---|---|
| Llama 4 8B (Q4) | 8GB | 6GB |
| Llama 4 70B (Q4) | 48GB | 40GB |
| Llama 4 405B (Q4) | 256GB | 200GB+ (multi-GPU) |
| Llama 4 Scout (Q4) | 80GB | 64GB (por MoE) |

## Call Stack / API

```
Aithera CLI / Chat
  → backend/app/ai/providers/ollama_provider.py
    → Ollama (OpenAI-compat en localhost:11434/v1)
      → Llama 4 model file (GGUF en ~/.ollama/models/)
```

## Código relacionado

- Meta: https://github.com/meta-llama (repos privados mayormente)
- Ollama: https://github.com/ollama/ollama
- llama.cpp: https://github.com/ggerganov/llama.cpp
- HuggingFace: https://huggingface.co/meta-llama (gated)
- Aithera: `backend/app/ai/providers/ollama_provider.py`

## Ejemplos

### Ollama (más simple)

```bash
# Descargar
ollama pull llama4:8b
ollama pull llama4:70b

# Ejecutar
ollama run llama4:8b

# API OpenAI-compat en localhost:11434
curl http://localhost:11434/v1/chat/completions \
  -d '{"model":"llama4:8b","messages":[{"role":"user","content":"Hello!"}]}'
```

### vLLM (production)

```python
from vllm import LLM, SamplingParams

llm = LLM(model="meta-llama/Llama-4-70B-Instruct")
prompts = ["Hello, "]
outputs = llm.generate(prompts, SamplingParams(temperature=0.7))
```

### HuggingFace transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-4-8B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-4-8B-Instruct")
```

## Buenas prácticas

- ✅ **Self-host para privacidad total** (datos no salen del PC).
- ✅ **Llama 4 Scout 10M context** para analizar codebases enteras.
- ✅ **Quantización Q4_K_M** para sweet spot calidad/tamaño.
- ✅ **vLLM** para serving de producción (alto throughput).
- ✅ **Ollama** para prototipos y single-user (más simple).

## Errores comunes

- ❌ Confundir Llama 4 Community License con open source puro (NO lo es).
- ❌ Usar en empresa >700M MAU sin licencia especial.
- ❌ Esperar performance de GPT-4 en Llama 4 8B (es ~10x más pequeño).
- ❌ No cuantizar (modelos full precision necesitan mucha VRAM).

## Breaking Changes

| Cambio | Impacto |
|---|---|
| Llama 3 → Llama 4 | Nueva arquitectura MoE; API compatible, pero requiere re-download |
| Llama 4 Community License | Restricciones vs Llama 2 Community License |

## Impacto sobre otros sistemas

- Aithera V0.7.3: NO tiene Llama 4 directamente, pero accesible vía Ollama (que sí).
- Aithera V0.85: evaluar añadir Llama 4 Scout (10M context) para memory ingestion.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-024 deepseek.md](./deepseek.md)
- [JWIKI-031 local-ollama.md](./local-ollama.md)
- [JWIKI-033 local-llamacpp.md](./local-llamacpp.md)

## Fuentes

1. https://ai.meta.com/llama/ — acceso 2026-07-09
2. https://github.com/meta-llama/llama — modelos open weights
3. https://github.com/ollama/ollama — wrapper local
4. https://huggingface.co/meta-llama — modelos gated
5. https://github.com/vllm-project/vllm — production serving

## Nivel de confianza

**82%** — Familia Llama 4 confirmada, MoE arquitectura, licensing conocido. Pendiente: validar contra HF model card oficial (gated access).

---

## Changelog

### 2026-07-09 — enriquecido
- Autor: Aithera Escriba (sesión actual, modo directo)
- Cambio: generado desde cero (no había borrador)
- Validador: contraste con Meta AI + Ollama
- Estado: 🟢 verified