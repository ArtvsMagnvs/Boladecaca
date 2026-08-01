# app/core/hardware.py — Escáner de hardware + recomendación de modelo/AVCS (2026-07-21)
#
# Lee las capacidades reales del PC del usuario (CPU, RAM, GPU/VRAM) y las traduce
# en dos recomendaciones AUTOMÁTICAS que el usuario puede aceptar o cambiar:
#   1. Qué modelo(s) de Ollama instalar — óptimo para ESTE PC, + uno inferior
#      seguro y (SOLO si el equipo lo aguanta de sobra) uno superior.
#   2. Qué nivel de partículas del AVCS soporta sin sobrecargar.
#
# Fail-soft total: si no se puede leer algo (sin GPU NVIDIA, nvidia-smi ausente,
# psutil no instalado), degrada a lo que sí sabe y nunca rompe.
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 1) ESCANEO
# ---------------------------------------------------------------------------
def _read_ram_gb() -> Optional[float]:
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception:
        return None


def _read_cpu() -> dict:
    out: dict[str, Any] = {"name": None, "cores": None, "threads": None}
    try:
        import psutil

        out["cores"] = psutil.cpu_count(logical=False)
        out["threads"] = psutil.cpu_count(logical=True)
    except Exception:
        pass
    # Nombre comercial del CPU (para el panel informativo de Ajustes → Sistema).
    # Windows: registro (fiable y sin subprocesos); fallback platform.processor().
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            out["name"] = str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
    except Exception:
        try:
            import platform

            out["name"] = platform.processor() or None
        except Exception:
            pass
    return out


def _read_gpu() -> dict:
    """GPU NVIDIA vía nvidia-smi (fail-soft). Devuelve {present, name, vram_gb}."""
    gpu: dict[str, Any] = {"present": False, "name": None, "vram_gb": None, "vendor": None}
    exe = shutil.which("nvidia-smi")
    if not exe:
        return gpu
    try:
        r = subprocess.run(
            [exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode == 0 and r.stdout.strip():
            first = r.stdout.strip().splitlines()[0]
            name, mem_mib = [p.strip() for p in first.split(",")[:2]]
            gpu.update(present=True, name=name, vendor="nvidia",
                       vram_gb=round(float(mem_mib) / 1024, 1))
    except Exception:
        pass
    return gpu


def scan() -> dict:
    """Radiografía del equipo. Nunca lanza."""
    ram = _read_ram_gb()
    cpu = _read_cpu()
    gpu = _read_gpu()
    # "Memoria útil para modelos": la VRAM si hay GPU dedicada (inferencia en
    # GPU, mucho más rápida); si no, la RAM (inferencia en CPU). Es el número
    # que gobierna qué modelo cabe con holgura.
    usable_gb = gpu["vram_gb"] if gpu["present"] and gpu["vram_gb"] else ram
    return {
        "ram_gb": ram,
        "cpu": cpu,
        "gpu": gpu,
        "usable_model_gb": usable_gb,
    }


# ---------------------------------------------------------------------------
# 2) RECOMENDACIÓN DE MODELO OLLAMA
# ---------------------------------------------------------------------------
# Reglas (un modelo que no cabe da mala experiencia). La holgura necesaria
# DEPENDE de dónde corra:
#   - GPU dedicada (VRAM): es memoria exclusiva → un modelo puede ocupar hasta
#     ~80% (queda sitio para el contexto). Superior solo si ≤65% (holgura real).
#   - RAM (sin GPU): la comparte el SO y otras apps → conservador: ≤55% para el
#     óptimo, ≤40% para el superior.
# ÓPTIMO = el general más grande que quepa con holgura. INFERIOR = uno más
# pequeño (siempre seguro). SUPERIOR = uno más grande SOLO si cabe con MUCHA
# holgura (regla del usuario: solo si el equipo lo maneja bien de verdad).
_FIT_GPU = 0.80
_FIT_GPU_SUP = 0.65
_FIT_RAM = 0.55
_FIT_RAM_SUP = 0.40


def recommend_ollama(hw: Optional[dict] = None) -> dict:
    """Recomienda modelos GENERALES de Ollama para este equipo (óptimo + inferior
    + superior-solo-si-seguro). Usa el catálogo real (local_catalog)."""
    from app.ai.local_catalog import LOCAL_CATALOG

    hw = hw or scan()
    usable = hw.get("usable_model_gb")
    on_gpu = bool(hw.get("gpu", {}).get("present"))
    fit_comfort = _FIT_GPU if on_gpu else _FIT_RAM
    fit_superior = _FIT_GPU_SUP if on_gpu else _FIT_RAM_SUP

    # Candidatos generales, ordenados por tamaño (los que gobiernan chat/uso diario).
    general = sorted(LOCAL_CATALOG["qwen"]["models"], key=lambda m: m["size_gb"])

    if not usable:
        # Sin dato de memoria: recomendar el más ligero (lo más seguro) y avisar.
        light = general[0]
        return {
            "known_hardware": False,
            "optimal": _rec(light, "El más ligero — no pude leer tu memoria, voy a lo seguro."),
            "lower": None,
            "higher": None,
            "note": "No se pudo detectar RAM/GPU; recomiendo el modelo más ligero por seguridad.",
        }

    fit = [m for m in general if m["size_gb"] <= fit_comfort * usable]
    optimal = fit[-1] if fit else general[0]     # el mayor que cabe con holgura; si ninguno, el más ligero

    idx = general.index(optimal)
    lower = general[idx - 1] if idx > 0 else None
    higher = None
    if idx + 1 < len(general):
        cand = general[idx + 1]
        if cand["size_gb"] <= fit_superior * usable:   # SOLO si cabe con MUCHA holgura
            higher = cand

    reason = (f"Tu equipo tiene ~{usable:.0f} GB de memoria útil"
              f"{' de GPU' if hw['gpu']['present'] else ' de RAM (sin GPU dedicada)'}: "
              f"'{optimal['label']}' es el mejor equilibrio calidad/velocidad para él.")
    return {
        "known_hardware": True,
        "optimal": _rec(optimal, reason),
        "lower": _rec(lower, "Más ligero y rápido, por si quieres máxima fluidez.") if lower else None,
        "higher": _rec(higher, "Tu equipo lo aguanta de sobra: más calidad si la quieres.") if higher else None,
        "note": None,
    }


def _rec(model: Optional[dict], why: str) -> Optional[dict]:
    if not model:
        return None
    return {"tag": model["tag"], "label": model["label"], "size_gb": model["size_gb"],
            "tier": model.get("tier"), "why": why}


# ---------------------------------------------------------------------------
# 3) RECOMENDACIÓN DE PARTÍCULAS DEL AVCS
# ---------------------------------------------------------------------------
# Q2 (mínimo) … Q4 (máximo). El AVCS es 3D (three.js): lo mueve sobre todo la
# GPU. Con GPU dedicada potente → Q4; integrada/CPU → Q2 (mínimo).
# [doc 35 PU5, 2026-07-30] Q1 eliminado: no llegaba al mínimo estético y
# cualquier equipo actual mueve Q2.
_AVCS_TIERS = {
    "Q2": {"label": "Mínimo", "particles": "moderadas", "hint": "Ligero; va bien en cualquier equipo actual"},
    "Q3": {"label": "Alto", "particles": "muchas", "hint": "Fluido con GPU dedicada"},
    "Q4": {"label": "Máximo", "particles": "el máximo", "hint": "Solo con GPU dedicada potente"},
}


def recommend_avcs(hw: Optional[dict] = None) -> dict:
    hw = hw or scan()
    gpu = hw["gpu"]
    vram = gpu.get("vram_gb") or 0
    ram = hw.get("ram_gb") or 0

    if gpu["present"] and vram >= 8:
        tier = "Q4"
    elif gpu["present"] and vram >= 4:
        tier = "Q3"
    else:
        tier = "Q2"          # mínimo: sin GPU dedicada o RAM justa

    return {
        "recommended_tier": tier,
        "tiers": _AVCS_TIERS,
        "why": (f"{'GPU ' + gpu['name'] + f' ({vram:.0f} GB)' if gpu['present'] else 'sin GPU dedicada'}"
                f"{f', {ram:.0f} GB RAM' if ram else ''}: "
                f"'{_AVCS_TIERS[tier]['label']}' va fluido sin sobrecargar."),
        # Aviso para la UI: qué niveles podrían ir justos en este equipo.
        "warn_above": None if tier == "Q4" else ("Q4" if tier == "Q3" else "Q3"),
    }


def full_recommendation() -> dict:
    """Todo de una: escaneo + recomendación de modelo + de AVCS. Lo consume la
    configuración inicial (auto) y el panel de Ajustes."""
    hw = scan()
    return {
        "hardware": hw,
        "ollama": recommend_ollama(hw),
        "avcs": recommend_avcs(hw),
    }
