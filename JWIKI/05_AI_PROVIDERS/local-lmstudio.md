# LM Studio — GUI amigable para LLMs local

## Resumen

**LM Studio** es la alternativa **GUI** a Ollama. Aplicación desktop (Electron + React) que permite descargar, ejecutar y chatear con LLMs locales. Soporta cualquier modelo GGUF. Tiene un servidor OpenAI-compatible embebido. NO integrado en Aithera V0.7.3 directamente (accesible vía Ollama o instalando LM Studio por separado).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **LM Studio** | ≥0.3 (recomendado ≥0.4) | Closed source, free para uso personal |
| LM Studio Server | OpenAI-compat | Embedded en la app |
| Modelos GGUF | Cualquiera | Llama, Qwen, Mistral, etc. |

## Características

- **GUI amigable** para descargar y chatear con LLMs.
- **Server OpenAI-compatible embebido** (activable).
- **Búsqueda de modelos** desde HuggingFace.
- **Chat UI** con markdown rendering.
- **Soporte GPU** (NVIDIA, AMD, Apple Silicon).
- **Configuración avanzada** (temperature, top-p, top-k, repeat penalty).
- **Multi-modelo** (cambiar entre modelos sin reiniciar).

## Instalación

```powershell
# Windows
winget install LMStudio.LMStudio
```

```bash
# macOS
brew install lm-studio
```

```bash
# Linux (AppImage)
wget https://lmstudio.ai/releases/latest/linux-x64/LM_Studio-*.AppImage
chmod +x LM_Studio-*.AppImage
```

## Server OpenAI-compatible

LM Studio puede correr un servidor local que expone API OpenAI-compatible en `localhost:1234`:

1. Abrir LM Studio → Developer tab.
2. Cargar un modelo.
3. Start Server → port 1234.

```python
from openai import OpenAI

client = OpenAI(
    api_key="lm-studio",  # no necesario realmente
    base_url="http://localhost:1234/v1"
)

response = client.chat.completions.create(
    model="loaded-model",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Cuándo elegir LM Studio vs Ollama

- **LM Studio**: si prefieres GUI, no te gusta la CLI.
- **Ollama**: si quieres automation, scripts, server headless.
- Ambos son compatibles con los mismos modelos GGUF.

## Para Aithera V0.85

LM Studio puede ser un **proveedor alternativo** a Ollama en Aithera:
- Configurar base_url `http://localhost:1234/v1` en `ai_providers` DB.
- Reusar `OpenAICompatibleProvider` (ya implementado).

## Referencias cruzadas

- [JWIKI-031 local-ollama.md](./local-ollama.md) — Ollama
- [JWIKI-033 local-llamacpp.md](./local-llamacpp.md) — llama.cpp

## Fuentes

1. https://lmstudio.ai/ — acceso 2026-07-09
2. https://lmstudio.ai/docs — docs

## Nivel de confianza

**85%** — Confirmado, ampliamente usado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified