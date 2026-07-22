# scripts/model_task_bench.py — banco de TAREAS reales por modelo (2026-07-22)
#
# La segunda mitad del benchmark (petición del usuario): las sondas de
# mel/benchmark.py miden UNA llamada (latencia + disciplina de formato); esto
# mide la CAPACIDAD AGENTIC real — cada modelo ejecutando el bucle de tools de
# verdad (app/tie/toolloop.py, el mismo que usan las misiones) contra el
# filesystem, el navegador (Chromium real), la búsqueda (SerpAPI/Brave reales)
# y la memoria, con VERIFICACIÓN DETERMINISTA del resultado en disco/BD.
#
# Por (modelo × escenario) se mide: éxito (verificado, no declarado), duración,
# iteraciones del bucle y nº de tools ejecutadas/denegadas. Se persiste en
# mel_benchmarks.tasks (JSON) — la materia prima para que el MEL reparta por
# TIPO de tarea, no solo por velocidad.
#
# Uso:  python scripts/model_task_bench.py [--models clave1,clave2] [--tags files,web]
# Todo el trabajo de archivos queda confinado a test-lab/ (gitignored).
# Coste: ~3-5 llamadas LLM por escenario; 1 búsqueda SerpAPI por modelo (web_info).
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LAB = Path(__file__).resolve().parents[2] / "test-lab" / "task-bench"

_SCENARIO_TIMEOUT_S = 300      # techo duro por (modelo, escenario)
_MAX_ITERS = 6                 # vueltas del bucle por escenario


# ---------------------------------------------------------------------------
# Escenarios: (id, tag, tools, instrucción(dir), setup(dir), verify(dir)->bool)
# Verificadores DETERMINISTAS: miran el disco/la BD, jamás el texto del modelo.
# ---------------------------------------------------------------------------
def _esc_files_create(d: Path):
    target = d / "notas.txt"
    return (
        f"Crea la carpeta {d.as_posix()} si no existe y dentro un archivo notas.txt "
        f"cuyo contenido sea exactamente: benchmark aithera",
        lambda: None,
        lambda: target.exists() and "benchmark aithera" in target.read_text(encoding="utf-8", errors="ignore"),
    )


def _esc_files_edit(d: Path):
    target = d / "lista.txt"

    def setup():
        d.mkdir(parents=True, exist_ok=True)
        target.write_text("uno\ndos\ntres\n", encoding="utf-8")

    def verify():
        if not target.exists():
            return False
        txt = target.read_text(encoding="utf-8", errors="ignore")
        return "cuatro" in txt and "uno" in txt and "tres" in txt   # añadió SIN destruir

    return (
        f"El archivo {target.as_posix()} tiene tres líneas. Añádele al final una cuarta "
        f"línea con la palabra: cuatro. No borres las líneas existentes.",
        setup, verify,
    )


def _esc_code_write(d: Path):
    target = d / "pares.py"

    def verify():
        if not target.exists():
            return False
        src = target.read_text(encoding="utf-8", errors="ignore")
        # se EJECUTA de verdad: la vara de medir es que el código funcione
        import subprocess
        try:
            out = subprocess.run([sys.executable, str(target)], capture_output=True,
                                 timeout=15, text=True)
            return out.returncode == 0 and "8" in out.stdout and "7" not in out.stdout
        except Exception:
            return False

    return (
        f"Crea el archivo {target.as_posix()}: un script Python que imprima los números "
        f"pares del 2 al 10, uno por línea. Después léelo para verificar que quedó bien.",
        lambda: d.mkdir(parents=True, exist_ok=True), verify,
    )


def _esc_doc_csv(d: Path):
    target = d / "gastos.csv"

    def verify():
        if not target.exists():
            return False
        lines = [l for l in target.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
        if len(lines) < 4:
            return False
        head = lines[0].lower().replace(" ", "")
        return "concepto" in head and "importe" in head and all("," in l for l in lines[:4])

    return (
        f"Crea el documento {target.as_posix()}: un CSV con cabecera 'concepto,importe' "
        f"y exactamente 3 filas de gastos de ejemplo (inventa conceptos e importes).",
        lambda: d.mkdir(parents=True, exist_ok=True), verify,
    )


def _esc_web_read(d: Path):
    target = d / "web.txt"

    def verify():
        return target.exists() and "example domain" in target.read_text(
            encoding="utf-8", errors="ignore").lower()

    return (
        f"Abre en el navegador https://example.com, lee el titular principal de la página, "
        f"y guárdalo en el archivo {target.as_posix()}.",
        lambda: d.mkdir(parents=True, exist_ok=True), verify,
    )


def _esc_web_info(d: Path):
    target = d / "capital.txt"

    def verify():
        return target.exists() and "canberra" in target.read_text(
            encoding="utf-8", errors="ignore").lower()

    return (
        f"Busca en internet cuál es la capital de Australia y guarda SOLO el nombre de la "
        f"ciudad en el archivo {target.as_posix()}.",
        lambda: d.mkdir(parents=True, exist_ok=True), verify,
    )


def _esc_memory(code: str):
    async def verify():
        """[fix del propio banco] Verificador ASÍNCRONO y con REINTARDO: la
        indexación de ChromaDB tras `store()` no es instantánea — verificar en
        el mismo milisegundo daba falsos negativos (medido: los modelos
        ejecutaban las 2 tools bien y aun así 'fallaban'). Se reintenta hasta
        3 veces con 2.5s entre intentos. Se busca en TODOS los tipos activos
        (los modelos eligen personal/project/conversational indistintamente —
        eso es gusto, no incapacidad)."""
        from app.memory import memory_router

        for intento in range(3):
            if intento:
                await asyncio.sleep(2.5)
            items = await memory_router.search(
                f"código del laboratorio de pruebas {code}", top_k=25)
            if any(code.lower() in (getattr(i, "content", "") or "").lower()
                   for i in items):
                return True
        return False

    return (
        f"Guarda en tu memoria este dato: el código del laboratorio de pruebas es {code}. "
        f"Después búscalo en tu memoria para confirmar que quedó guardado.",
        lambda: None, verify,
    )


def build_scenarios(model_slug: str, run_tag: str = "") -> list[dict]:
    base = LAB / model_slug
    # Código ÚNICO por modelo Y POR TANDA: por modelo para que uno no valide lo
    # guardado por otro (pasó con slug[:6] → "AZUL-claude" compartido); por
    # tanda para que los restos de tandas anteriores en la memoria jamás
    # produzcan un falso positivo ni compitan en el ranking semántico.
    import hashlib
    code = f"AZUL-{hashlib.sha1((model_slug + run_tag).encode()).hexdigest()[:8].upper()}"
    files_create = _esc_files_create(base / "s1")
    files_edit = _esc_files_edit(base / "s2")
    code_write = _esc_code_write(base / "s3")
    doc_csv = _esc_doc_csv(base / "s4")
    web_read = _esc_web_read(base / "s5")
    web_info = _esc_web_info(base / "s6")
    memory = _esc_memory(code)
    return [
        {"id": "files_create", "tag": "files", "tools": ["filesystem"], "spec": files_create, "dir": base / "s1"},
        {"id": "files_edit", "tag": "files", "tools": ["filesystem"], "spec": files_edit, "dir": base / "s2"},
        {"id": "code_write", "tag": "code", "tools": ["filesystem"], "spec": code_write, "dir": base / "s3"},
        {"id": "doc_csv", "tag": "docs", "tools": ["filesystem"], "spec": doc_csv, "dir": base / "s4"},
        {"id": "web_read", "tag": "web", "tools": ["browser", "filesystem"], "spec": web_read, "dir": base / "s5"},
        {"id": "web_info", "tag": "web", "tools": ["search", "filesystem"], "spec": web_info, "dir": base / "s6"},
        {"id": "memory_save", "tag": "memory", "tools": ["memory"], "spec": memory, "dir": None},
    ]


# ---------------------------------------------------------------------------
# Clasificación de fallos (v2 — petición del usuario: el banco debe decir POR
# QUÉ, sin excepciones). Un fallo de INFRAESTRUCTURA jamás cuenta como
# incapacidad del modelo:
#   quota        límite de uso del proveedor (429) → reintentable
#   connection   caída de red/Ollama → reintentable
#   timeout      el escenario agotó su techo duro
#   no_tools     el modelo respondió pero no logró ejecutar NINGUNA tool
#                (formato/decisión — esto SÍ es del modelo)
#   wrong_result ejecutó tools pero el resultado verificado es incorrecto
#                (esto SÍ es del modelo)
#   bench_error  excepción del propio banco (culpa nuestra, no del modelo)
# ---------------------------------------------------------------------------
_RETRYABLE = ("quota", "connection")
_MAX_RETRIES = 2          # reintentos extra ante fallos de infraestructura
_RETRY_BACKOFF_S = 30.0


def _classify(err: str, executed: int, verified: bool, timed_out: bool,
              bench_exc: bool) -> str | None:
    if verified:
        return None
    if bench_exc:
        return "bench_error"
    low = (err or "").lower()
    if "429" in (err or "") or "hit your" in low or "rate limit" in low or "quota" in low:
        return "quota"
    if "error connecting" in low or "connection" in low or "getaddrinfo" in low:
        return "connection"
    if timed_out:
        return "timeout"
    return "wrong_result" if executed > 0 else "no_tools"


async def _run_scenario_once(model_key: str, esc: dict) -> dict:
    from app.tie import toolloop
    from app.tools.tool_manager import tool_manager

    instruction, setup, verify = esc["spec"]
    # [v2] LIMPIEZA PREVIA: sin esto, el verificador encontraba archivos de la
    # tanda ANTERIOR y daba éxitos falsos (medido: "creó" un archivo en 1.1s
    # con 0 tools). El directorio del escenario nace vacío en cada medición.
    if esc.get("dir"):
        import shutil
        shutil.rmtree(esc["dir"], ignore_errors=True)
    setup()
    t0 = time.monotonic()
    timed_out = bench_exc = False
    res = None
    try:
        res = await asyncio.wait_for(
            toolloop.run(
                instruction=instruction, context="", allowed_tools=esc["tools"],
                tool_manager=tool_manager, max_iters=_MAX_ITERS,
                model_override=model_key,
                # Benchmark lanzado por el operador a propósito: sin gates (las
                # escrituras están confinadas a test-lab por la instrucción y
                # las tools por la whitelist del escenario).
                pre_approved=True,
                session_key=f"bench-{model_key}-{esc['id']}",
                timeout_s=60,
                # El banco MIDE: salta el filtro de aptitud (si no, un modelo
                # excluido no podría re-evaluarse jamás). Producción no lo usa.
                fitness_exempt=True,
            ),
            timeout=_SCENARIO_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        timed_out = True
    except Exception as e:
        bench_exc = True
        bench_err = f"{type(e).__name__}: {e}"[:200]
    finally:
        try:
            from app.tools import browser_tool
            await browser_tool.close_session(f"bench-{model_key}-{esc['id']}")
        except Exception:
            pass

    executed = sum(1 for c in (res.tool_calls if res else []) if c.get("ok"))
    denied = sum(1 for c in (res.tool_calls if res else []) if c.get("denied"))
    try:
        out = verify()
        verified = bool(await out if asyncio.iscoroutine(out) else out)
    except Exception as e:
        verified, bench_exc = False, True
        bench_err = f"verificador roto: {type(e).__name__}: {e}"[:200]

    if bench_exc:
        err = bench_err
    elif timed_out:
        err = f"timeout tras {_SCENARIO_TIMEOUT_S}s"
    else:
        err = res.error or ""
    kind = _classify(err, executed, verified, timed_out, bench_exc)
    return {
        "ok": verified,                        # la VERIFICACIÓN manda, no res.ok
        "failure_kind": kind,                  # None si ok
        "unavailable": kind in _RETRYABLE,     # compat con la lectura previa
        "loop_ok": bool(res.ok) if res else False,
        "duration_ms": int((time.monotonic() - t0) * 1000),
        "iterations": res.iterations if res else _MAX_ITERS,
        "tools_executed": executed,
        "tools_denied": denied,
        # Rastro compacto de QUÉ hizo (diagnóstico sin releer logs):
        "tool_calls": [
            {"t": f"{c.get('tool_id')}.{c.get('action')}",
             "ok": bool(c.get("ok")), "denied": bool(c.get("denied"))}
            for c in (res.tool_calls if res else [])
        ][:12],
        "error": err[:250] if not verified else None,
    }


async def run_scenario(model_key: str, esc: dict) -> dict:
    """Corre el escenario con REINTENTOS ante fallos de infraestructura
    (cuota/conexión): hasta _MAX_RETRIES extra con backoff. El resultado final
    lleva `attempts`; si tras los reintentos sigue siendo infraestructura,
    queda `unavailable` (no medible) — jamás como incapacidad del modelo."""
    result = None
    for attempt in range(1, _MAX_RETRIES + 2):
        result = await _run_scenario_once(model_key, esc)
        result["attempts"] = attempt
        if result["ok"] or result["failure_kind"] not in _RETRYABLE:
            return result
        if attempt <= _MAX_RETRIES:
            print(f"     · {esc['id']}: {result['failure_kind']} — reintento "
                  f"{attempt}/{_MAX_RETRIES} en {int(_RETRY_BACKOFF_S)}s", flush=True)
            await asyncio.sleep(_RETRY_BACKOFF_S)
    return result


def persist(provider: str, model: str, tasks: dict) -> None:
    """MERGE, no reemplazo: una pasada parcial (--tags memory) actualiza SOLO
    esos escenarios y conserva los demás. Reemplazar borraría medidas buenas de
    una tanda anterior — un run parcial no puede destruir datos."""
    from datetime import datetime

    from app.db.database import SessionLocal
    from app.mel.models import MelBenchmark

    db = SessionLocal()
    try:
        row = (db.query(MelBenchmark)
               .filter(MelBenchmark.provider == provider, MelBenchmark.model == model).first())
        if row is None:
            row = MelBenchmark(provider=provider, model=model, ok=True)
            db.add(row)
        merged = dict(row.tasks or {})
        merged.update(tasks)
        row.tasks = merged          # dict NUEVO → SQLAlchemy detecta el cambio
        row.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


async def main(only_models: set[str] | None, only_tags: set[str] | None) -> None:
    from app.mel import registry
    from app.mel import benchmark as micro

    # La memoria hace falta para el escenario memory_save (init bloqueante).
    from app.memory.memory_manager import memory_manager
    print("Inicializando memoria (ChromaDB)…", flush=True)
    memory_manager.initialize_sync()

    refs = registry.list_available()
    # Los medidos como MUERTOS por el micro-benchmark se saltan (no responden).
    alive = []
    for r in refs:
        m = micro.measured(r)
        if m is not None and not m["ok"]:
            print(f"  · {r.key}: SALTADO (medido como muerto)", flush=True)
            continue
        if only_models and r.key not in only_models:
            continue
        alive.append(r)
    # Rápidos primero (resultados parciales útiles cuanto antes).
    alive.sort(key=lambda r: (micro.measured(r) or {}).get("latency_ms_median") or 10 ** 9)

    # Etiqueta de tanda: hace únicos los códigos de memoria entre tandas (los
    # restos de una tanda anterior no pueden dar falsos positivos ni competir
    # en el ranking). Se pasa por CLI en el resume; default = hoy.
    import datetime as _dt
    run_tag = _dt.date.today().isoformat()

    print(f"═══ Task-bench v2: {len(alive)} modelos × escenarios (tanda {run_tag}) ═══", flush=True)
    resumen: dict[str, dict] = {}
    for ref in alive:
        slug = ref.key.replace(":", "_").replace("/", "_").replace(".", "_")[:40]
        escenarios = [e for e in build_scenarios(slug, run_tag)
                      if only_tags is None or e["tag"] in only_tags]
        tasks: dict[str, dict] = {}
        print(f"\n▶ {ref.key}", flush=True)
        for esc in escenarios:
            r = await run_scenario(ref.key, esc)
            tasks[esc["id"]] = r
            mark = "✓" if r["ok"] else ("·" if r.get("unavailable") else "✗")
            kind = f" [{r['failure_kind']}]" if r.get("failure_kind") else ""
            print(f"   {mark} {esc['id']:14s} {r['duration_ms']/1000:6.1f}s "
                  f"iters={r['iterations']} tools={r['tools_executed']}{kind}"
                  + (f" — {r['error'][:120]}" if r.get("error") else ""), flush=True)
        persist(ref.provider, ref.model, tasks)
        oks = sum(1 for t in tasks.values() if t["ok"])
        na = sum(1 for t in tasks.values() if t.get("unavailable"))
        resumen[ref.key] = {"ok": oks, "total": len(tasks), "na": na,
                            "avg_s": round(sum(t["duration_ms"] for t in tasks.values())
                                           / max(len(tasks), 1) / 1000, 1)}
        print(f"   → {oks}/{len(tasks) - na} tareas medidas"
              + (f" ({na} no medibles: cuota/conexión)" if na else "")
              + f", media {resumen[ref.key]['avg_s']}s", flush=True)

    print("\n═══ Matriz final (éxito / total, media por tarea) ═══", flush=True)
    for key, s in sorted(resumen.items(), key=lambda kv: (-kv[1]["ok"], kv[1]["avg_s"])):
        medibles = s["total"] - s["na"]
        pct = round(100 * s["ok"] / medibles) if medibles else 0
        print(f"  {key:45s} {s['ok']}/{medibles} ({pct}%)  media {s['avg_s']}s"
              + (f"  [{s['na']} no medibles]" if s["na"] else ""), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="claves provider:model separadas por coma")
    ap.add_argument("--tags", help="files,code,docs,web,memory")
    args = ap.parse_args()
    asyncio.run(main(
        set(args.models.split(",")) if args.models else None,
        set(args.tags.split(",")) if args.tags else None,
    ))
