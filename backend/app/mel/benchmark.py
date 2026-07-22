# app/mel/benchmark.py — banco de pruebas MEDIDO de modelos (2026-07-22)
#
# LA PIEZA QUE FALTABA (petición directa del usuario): el auto-catálogo de E1b
# (research.py) puntúa cada modelo por CONOCIMIENTO (otro modelo lo describe),
# pero nadie MEDÍA nada — ni la latencia real en esta máquina ni si el modelo
# de verdad obedece instrucciones o produce JSON válido. Este módulo lanza
# sondas ESTANDARIZADAS, BARATAS y DETERMINISTAS contra cada modelo conectado
# y guarda dos números por (proveedor, modelo):
#
#   speed_score   0-100 — de la latencia MEDIDA (mediana de las sondas).
#   quality_score 0-100 — % de sondas verificables superadas (JSON exacto,
#                          seguir instrucciones al pie de la letra, un
#                          razonamiento con respuesta única comprobable).
#
# Las sondas se corren SOLAS al conectar/cambiar un modelo (evento
# `provider.model_configured`, igual que research) y al arrancar para los que
# no tengan medición — el usuario nunca tiene que "probar y probar": cuando un
# modelo entra en Aithera, se clasifica sin que se entere (petición del
# usuario, 2026-07-22). Las políticas SPEED y BALANCED compilan CON estos
# números (policies.py); un modelo que no responde (p.ej. un id inválido que
# la API rechaza con 400) queda marcado ok=False y las políticas medidas lo
# excluyen — el caso real MiniMax-M3-highspeed jamás habría llegado a primario.
#
# Coste por modelo: 4 llamadas mínimas (~100 tokens de salida en total). No es
# un benchmark académico: es un chequeo de aptitud operativa.
from __future__ import annotations

import asyncio
import json
import statistics
import time
from typing import Any, Optional

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.mel.contracts import ModelRef

logger = get_system_logger("mel.benchmark")

# Techo duro por sonda: un modelo que tarda más que esto en una respuesta de
# una palabra no es utilizable de forma interactiva — cuenta como timeout.
_PROBE_TIMEOUT_S = 180.0


# ---------------------------------------------------------------------------
# Sondas (prompt, verificador determinista). Verificador → True/False.
# ---------------------------------------------------------------------------
def _check_speed(text: str) -> bool:
    return "ok" in text.strip().lower()


def _check_json(text: str) -> bool:
    """JSON EXACTO, sin decoración — proxy de classify/agentic (lo que rompe el
    toolloop en producción es justo esto). Extracción tolerante PROPIA (mismo
    criterio que tie/intents._extract_json, replicado aquí en miniatura porque
    el MEL no puede importar internos del TIE — frontera modular doc 16)."""
    import re

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return False
    candidate = text[start:end + 1]
    try:
        data = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        # claves desnudas ({tool: ...}) → se les ponen comillas y se reintenta
        repaired = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', candidate)
        try:
            data = json.loads(repaired)
        except (json.JSONDecodeError, ValueError):
            return False
    return data == {"tool": "browser", "action": "open_url"}


def _check_instr(text: str) -> bool:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    return len(lines) == 3 and all(l.lower().startswith("dato:") for l in lines)


def _check_reason(text: str) -> bool:
    # 17 - 5 = 12; compra el doble (24) → 12 + 24 = 36
    import re
    nums = re.findall(r"\d+", text)
    return "36" in nums


# (id, prompt, verificador, cuenta_para_calidad)
_PROBES: list[tuple[str, str, Any, bool]] = [
    ("speed", "Responde únicamente con la palabra OK.", _check_speed, False),
    ("json",
     'Devuelve SOLO este objeto JSON, sin markdown y sin ningún texto alrededor: '
     '{"tool": "browser", "action": "open_url"}',
     _check_json, True),
    ("instr",
     "Escribe exactamente tres líneas y nada más. Cada línea debe empezar por «Dato:».",
     _check_instr, True),
    ("reason",
     "María tiene 17 manzanas. Regala 5. Después compra el doble de las que le "
     "quedan en ese momento. ¿Cuántas manzanas tiene ahora? Responde únicamente con el número.",
     _check_reason, True),
]


def _speed_score(median_ms: Optional[float]) -> int:
    """Mapa latencia→0-100. ≤3s = 100 (fluido); 6s ≈ 50; 15s ≈ 20; 60s ≈ 5.
    Sin medición (nunca respondió) = 0."""
    if not median_ms or median_ms <= 0:
        return 0
    return max(1, min(100, round(100 * 3000.0 / max(median_ms, 3000.0))))


async def run_model_benchmark(ref: ModelRef) -> dict:
    """Corre las 4 sondas contra UN modelo (llamada directa al registry, sin
    políticas ni breakers — se mide el modelo, no el MEL) y persiste el
    resultado. Devuelve el dict persistido. Nunca lanza."""
    from app.mel import registry

    probes_out: dict[str, dict] = {}
    latencies: list[float] = []
    quality_total = quality_pass = 0

    for pid, prompt, check, counts_quality in _PROBES:
        t0 = time.monotonic()
        try:
            raw = await asyncio.wait_for(
                registry.execute(ref, prompt, "Responde en español, breve y literal."),
                timeout=_PROBE_TIMEOUT_S,
            )
            ms = (time.monotonic() - t0) * 1000
            if raw.get("error"):
                probes_out[pid] = {"ok": False, "error": str(raw.get("response", ""))[:200]}
            else:
                text = strip_reasoning(raw.get("response", "") or "") or ""
                passed = bool(check(text))
                probes_out[pid] = {"ok": passed, "latency_ms": int(ms)}
                latencies.append(ms)
                if counts_quality:
                    quality_total += 1
                    quality_pass += 1 if passed else 0
                continue
        except asyncio.TimeoutError:
            probes_out[pid] = {"ok": False, "error": f"timeout tras {int(_PROBE_TIMEOUT_S)}s"}
        except Exception as e:
            probes_out[pid] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
        if counts_quality:
            quality_total += 1

    median_ms = statistics.median(latencies) if latencies else None
    result = {
        "provider": ref.provider,
        "model": ref.model,
        "ok": bool(latencies),                      # ¿respondió a ALGO?
        "latency_ms_median": int(median_ms) if median_ms else None,
        "speed_score": _speed_score(median_ms),
        "quality_score": round(100 * quality_pass / quality_total) if quality_total else 0,
        "probes": probes_out,
    }
    _persist(result)
    logger.info(
        f"[benchmark] {ref.key}: ok={result['ok']} "
        f"mediana={result['latency_ms_median']}ms speed={result['speed_score']} "
        f"quality={result['quality_score']}"
    )
    return result


def _persist(result: dict) -> None:
    """Upsert por (provider, model). Best-effort: un fallo de BD no rompe nada."""
    from datetime import datetime

    try:
        from app.db.database import SessionLocal
        from app.mel.models import MelBenchmark

        db = SessionLocal()
        try:
            row = (db.query(MelBenchmark)
                   .filter(MelBenchmark.provider == result["provider"],
                           MelBenchmark.model == result["model"]).first())
            if row is None:
                row = MelBenchmark(provider=result["provider"], model=result["model"])
                db.add(row)
            row.ok = result["ok"]
            row.latency_ms_median = result["latency_ms_median"]
            row.speed_score = result["speed_score"]
            row.quality_score = result["quality_score"]
            row.probes = result["probes"]
            row.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[benchmark] persistencia falló (no crítico): {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Lectura (lo que consume el compilador de políticas y la UI)
# ---------------------------------------------------------------------------
def measured(ref: ModelRef) -> Optional[dict]:
    """{ok, speed_score, quality_score, latency_ms_median} o None si no hay
    medición para ese modelo. Nunca lanza."""
    try:
        from app.db.database import SessionLocal
        from app.mel.models import MelBenchmark

        db = SessionLocal()
        try:
            row = (db.query(MelBenchmark)
                   .filter(MelBenchmark.provider == ref.provider,
                           MelBenchmark.model == ref.model).first())
            if row is None:
                return None
            return {"ok": bool(row.ok), "speed_score": row.speed_score or 0,
                    "quality_score": row.quality_score or 0,
                    "latency_ms_median": row.latency_ms_median}
        finally:
            db.close()
    except Exception:
        return None


def summary() -> list[dict]:
    """Todas las mediciones (para la UI de Inteligencia / diagnóstico)."""
    try:
        from app.db.database import SessionLocal
        from app.mel.models import MelBenchmark

        db = SessionLocal()
        try:
            rows = db.query(MelBenchmark).order_by(MelBenchmark.provider, MelBenchmark.model).all()
            return [{
                "provider": r.provider, "model": r.model, "ok": bool(r.ok),
                "latency_ms_median": r.latency_ms_median,
                "speed_score": r.speed_score, "quality_score": r.quality_score,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            } for r in rows]
        finally:
            db.close()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Orquestación: todos / los que falten / al conectar un modelo
# ---------------------------------------------------------------------------
async def benchmark_all(force: bool = True) -> int:
    """Sondea todos los modelos disponibles (secuencial a propósito: sondear en
    paralelo contaminaría la medición de latencia de los locales, que comparten
    GPU/CPU). Con force=False salta los que ya tienen medición. Al terminar,
    recompila las políticas automáticas no editadas (SPEED/BALANCED absorben
    los números nuevos sin reinicio)."""
    from app.mel import registry

    n = 0
    for ref in registry.list_available():
        if not force and measured(ref) is not None:
            continue
        await run_model_benchmark(ref)
        n += 1
    if n:
        _recompile_policies()
    return n


def _recompile_policies() -> None:
    """Refresca las políticas pristine con las mediciones nuevas. Best-effort."""
    try:
        from app.mel import registry
        from app.mel.policies import policy_store

        policy_store.recompile_pristine(registry.list_available())
    except Exception as e:
        logger.error(f"[benchmark] recompilación de políticas falló (no crítico): {e!r}")


async def benchmark_missing() -> int:
    """Solo los modelos SIN medición (catch-up de arranque — cubre los que se
    conectaron antes de existir este módulo, sin repetir trabajo)."""
    return await benchmark_all(force=False)


async def _on_model_configured(event) -> None:
    """Al conectar/cambiar un modelo se le mide en background — el usuario no
    tiene que hacer nada (mismo patrón que research._on_model_configured)."""
    payload = getattr(event, "payload", None) or {}
    provider, model = payload.get("provider"), payload.get("model")
    if not provider or not model:
        return
    from app.mel import registry

    medido = False
    for ref in registry.list_available():
        if ref.provider == provider and (ref.model == model or model is None):
            try:
                await run_model_benchmark(ref)
                medido = True
            except Exception as e:
                logger.error(f"[benchmark] fallo midiendo {ref.key} (no crítico): {e!r}")
    if medido:
        _recompile_policies()


def register() -> None:
    """Suscribe el auto-benchmark a `provider.model_configured`. Idempotente.
    Lo llama `mel.register_handlers()` (mismo punto que research)."""
    from app.core.events import subscribe, unsubscribe

    unsubscribe("provider.model_configured", _on_model_configured)
    subscribe("provider.model_configured", _on_model_configured)
