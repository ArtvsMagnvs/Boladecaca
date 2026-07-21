# app/ai/local_catalog.py — catálogo de MODELOS LOCALES instalables (V1.0)
#
# La visión del usuario (2026-07-18): Aithera no depende de un único modelo
# local genérico, sino de varios ESPECIALISTAS que conviven, y el MEL reparte
# cada tarea al que mejor la hace:
#
#   AITHERA
#   ├── Runtime      → Ollama (el motor, no un modelo)
#   ├── General AI   → Qwen
#   ├── Coding AI    → Ornith
#   ├── Reasoning AI → DeepSeek
#   └── Vision AI    → Qwen Vision
#
# Cada familia ofrece 2-3 variantes de potencia distinta. El usuario elige e
# instala con 1 clic (descarga automática vía Ollama).
#
# HONESTIDAD SOBRE `recommended` (importante): hoy la recomendación es un
# DEFAULT CURADO por tamaño típico, NO una medición del PC del usuario. El
# escáner de hardware (CPU/GPU/RAM → qué variante cabe de verdad) es una
# actualización futura, decidida así explícitamente. Hasta entonces la UI
# muestra el tamaño en disco de cada variante para que el usuario decida con
# un dato real, y `recommended` se presenta como sugerencia, no como veredicto.
#
# TODOS los tags de este archivo están VERIFICADOS (2026-07-18): los de la
# librería oficial contra `registry.ollama.ai/v2/library/...` (HTTP 200) y los
# de Ornith contra la API de HuggingFace (repos GGUF oficiales de
# deepreinforce-ai). No hay ni un tag inventado — un "1 clic" que falla porque
# el tag no existe sería peor que no tener el botón.
from __future__ import annotations

from typing import Any, Optional

# Categorías (el orden es el de presentación en la UI).
CATEGORIES = [
    ("runtime", "Runtime", "El motor que ejecuta los modelos locales en tu PC."),
    ("general", "IA General", "Conversación, redacción y tareas del día a día."),
    ("coding", "IA de Programación", "Escribir, revisar y explicar código."),
    ("reasoning", "IA de Razonamiento", "Problemas de varios pasos y análisis profundo."),
    ("vision", "IA de Visión", "Entender imágenes y capturas de pantalla."),
]


# family -> definición. `models[].tag` es lo que se le pasa a `ollama pull`.
LOCAL_CATALOG: dict[str, dict[str, Any]] = {
    "ollama": {
        "label": "Ollama",
        "category": "runtime",
        "description": "El runtime local. Sin él no funciona ningún modelo de esta lista.",
        "is_runtime": True,          # no se instala como modelo: se comprueba que esté vivo
        "install_url": "https://ollama.com/download",
        "models": [],
    },
    # [2026-07-21] Familia Llama añadida (petición del usuario: "incluido llama").
    # `llama3` es el default histórico de Aithera (proveedor Ollama) y muy
    # probablemente ya está en el disco del usuario — ahora aparece en el
    # catálogo con su chip "instalado" en vez de existir solo por fuera.
    # Tags verificados de la librería oficial de Ollama.
    "llama": {
        "label": "Llama",
        "category": "general",
        "description": "La familia clásica de Meta. `llama3` es el modelo por defecto histórico de Aithera.",
        "models": [
            {"tag": "llama3.2:3b", "label": "Llama 3.2 3B", "size_gb": 2.0,
             "tier": "ligero", "recommended": False,
             "notes": "Muy ligero; para equipos con recursos mínimos."},
            {"tag": "llama3", "label": "Llama 3 8B", "size_gb": 4.7,
             "tier": "ligero", "recommended": True,
             "notes": "El default histórico de Aithera; sólido en chat general."},
            {"tag": "llama3.3:70b", "label": "Llama 3.3 70B", "size_gb": 43.0,
             "tier": "potente", "recommended": False,
             "notes": "Muy capaz, pero solo para equipos con muchísima memoria."},
        ],
    },
    "qwen": {
        "label": "Qwen",
        "category": "general",
        "description": "Equilibrado en conversación y tareas generales. Buen punto de partida.",
        "models": [
            {"tag": "qwen3:8b", "label": "Qwen3 8B", "size_gb": 5.2,
             "tier": "ligero", "recommended": False,
             "notes": "Rápido; suficiente para chat y tareas cortas."},
            {"tag": "qwen3:14b", "label": "Qwen3 14B", "size_gb": 9.3,
             "tier": "equilibrado", "recommended": True,
             "notes": "El mejor compromiso calidad/recursos para uso general."},
            {"tag": "qwen3:32b", "label": "Qwen3 32B", "size_gb": 20.0,
             "tier": "potente", "recommended": False,
             "notes": "Notablemente mejor, pero pide bastante VRAM/RAM."},
        ],
    },
    "ornith": {
        "label": "Ornith 1.0",
        "category": "coding",
        "description": "Especialista en programación (deepreinforce-ai). Muy fuerte en código, "
                       "menos en razonamiento abierto — por eso convive con los demás.",
        "models": [
            # Ollama sabe tirar de repos GGUF de HuggingFace con el prefijo hf.co/.
            # El quant Q4_K_M es el estándar de facto: mejor relación calidad/tamaño.
            {"tag": "hf.co/deepreinforce-ai/Ornith-1.0-9B-GGUF:Q4_K_M",
             "label": "Ornith 1.0 · 9B", "size_gb": 5.8,
             "tier": "ligero", "recommended": True,
             "notes": "Especialista en código que cabe en la mayoría de equipos."},
            {"tag": "hf.co/deepreinforce-ai/Ornith-1.0-35B-GGUF:Q4_K_M",
             "label": "Ornith 1.0 · 35B", "size_gb": 21.5,
             "tier": "potente", "recommended": False,
             "notes": "Mucho más capaz programando; necesita un equipo holgado."},
        ],
    },
    "deepseek": {
        "label": "DeepSeek R1",
        "category": "reasoning",
        "description": "Modelo razonador: piensa paso a paso antes de responder. "
                       "Aithera ya filtra su cadena de pensamiento (B21).",
        "models": [
            {"tag": "deepseek-r1:8b", "label": "DeepSeek R1 8B", "size_gb": 5.2,
             "tier": "ligero", "recommended": False,
             "notes": "Razonamiento decente con pocos recursos."},
            {"tag": "deepseek-r1:14b", "label": "DeepSeek R1 14B", "size_gb": 9.0,
             "tier": "equilibrado", "recommended": True,
             "notes": "El salto de calidad más rentable en razonamiento."},
            {"tag": "deepseek-r1:32b", "label": "DeepSeek R1 32B", "size_gb": 20.0,
             "tier": "potente", "recommended": False,
             "notes": "Para análisis largos y problemas difíciles."},
        ],
    },
    "qwen_vision": {
        "label": "Qwen Vision",
        "category": "vision",
        "description": "Entiende imágenes y capturas. Se combina con la tool `desktop` "
                       "(screenshot/OCR) para que Aithera 'vea' la pantalla.",
        "models": [
            {"tag": "qwen2.5vl:7b", "label": "Qwen2.5-VL 7B", "size_gb": 6.0,
             "tier": "ligero", "recommended": True,
             "notes": "Visión suficiente para capturas y documentos."},
            {"tag": "qwen2.5vl:32b", "label": "Qwen2.5-VL 32B", "size_gb": 21.0,
             "tier": "potente", "recommended": False,
             "notes": "Mejor comprensión visual; equipo holgado."},
        ],
    },
}


def all_models() -> list[dict[str, Any]]:
    """Aplana el catálogo: una entrada por modelo instalable, con su familia."""
    out: list[dict[str, Any]] = []
    for family, fam in LOCAL_CATALOG.items():
        if fam.get("is_runtime"):
            continue
        for m in fam.get("models", []):
            out.append({**m, "family": family, "family_label": fam["label"],
                        "category": fam["category"]})
    return out


def find_model(tag: str) -> Optional[dict[str, Any]]:
    """Busca un modelo del catálogo por su tag exacto. None si no es del catálogo
    (p.ej. un modelo que el usuario bajó a mano con `ollama pull`)."""
    for m in all_models():
        if m["tag"] == tag:
            return m
    return None


def family_of(tag: str) -> Optional[str]:
    m = find_model(tag)
    return m["family"] if m else None
