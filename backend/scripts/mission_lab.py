# scripts/mission_lab.py — batería de misiones de prueba en entorno SEGURO
# (doc 31, 2026-07-21)
#
# Lanza misiones variadas contra el BACKEND REAL (HTTP, como un usuario) y al
# terminar imprime el reporte de telemetría de cada una. TODA escritura de
# archivos queda confinada a la carpeta `test-lab/` del repo (gitignored) —
# regla dura: jamás una misión de prueba apunta a archivos reales del usuario.
#
# Uso (backend corriendo):
#   python scripts/mission_lab.py                   # batería completa
#   python scripts/mission_lab.py --only files,web  # subconjunto por etiqueta
#   python scripts/mission_lab.py --list            # ver escenarios
#   python scripts/mission_lab.py --baseline test-lab/baseline.json
#                                                     # compara y actualiza baseline
#
# [S3, doc 34 §10] Tras cada misión se consulta su presupuesto de llamadas LLM
# (telemetry.mission_timeline, vía import directo — mismo patrón que
# mission_report.py: este script y el backend comparten BD/entorno) y se
# imprime PASS/FAIL. El proceso termina con código 1 si algún escenario se
# pasó de presupuesto — así una campaña se puede enganchar a CI/CD sin leer
# la salida a ojo. `--baseline <archivo.json>` compara además contra la pasada
# anterior (llamadas y duración por escenario) y deja actualizado el archivo
# para la siguiente comparación — "va lento" se vuelve un número.
#
# Las misiones de escritorio (desktop tool) NO están en la batería automática:
# mueven el ratón/teclado reales — solo con el usuario delante.
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

BASE = "http://127.0.0.1:8000/api"
LAB = (Path(__file__).resolve().parents[2] / "test-lab").as_posix()

# Escenarios: (etiqueta, nombre, prompt). Cada prompt ANCLA el trabajo al lab.
SCENARIOS: list[tuple[str, str, str]] = [
    ("files", "crear_nota",
     f"Crea un archivo de texto en la carpeta {LAB} llamado nota_lab.txt con una frase "
     f"sobre el estado del proyecto. Solo puedes escribir dentro de {LAB}."),
    ("files", "mini_web",
     f"Crea en la carpeta {LAB}/mini-web una página web sencilla (index.html con CSS "
     f"embebido) que diga 'Aithera Lab' con estilo oscuro. Solo escribe dentro de {LAB}."),
    ("code", "script_python",
     f"Crea en {LAB}/scripts un script Python fizzbuzz.py que imprima FizzBuzz del 1 al 30, "
     f"y verifica que existe leyéndolo. Solo escribe dentro de {LAB}."),
    ("web", "buscar_web",
     "Busca en internet cuál es la última versión estable de Python y dime el número de versión."),
    ("web", "browser_wikipedia",
     "Abre en el navegador la página de Wikipedia sobre Alan Turing y dime en qué año nació, "
     "leyéndolo de la propia página."),
    ("memory", "guardar_recordar",
     "Guarda en tu memoria que el color del laboratorio de pruebas es verde esmeralda, "
     "y confírmame qué has guardado."),
    ("multi", "doble_objetivo",
     f"Haz dos cosas: (1) crea {LAB}/doble.txt con el texto 'objetivo uno', y (2) dime "
     f"cuántos días tiene julio. Solo escribe dentro de {LAB}."),
]


async def run_mission(client: httpx.AsyncClient, name: str, prompt: str) -> dict:
    """Envía el prompt por el endpoint de chat real (el mismo camino del usuario)
    y espera la respuesta completa. Devuelve {name, elapsed_s, mission_id?, answer}."""
    t0 = time.monotonic()
    mission_id = None
    answer_parts: list[str] = []
    try:
        async with client.stream(
            "POST", f"{BASE}/chat/stream",
            json={"message": prompt},
            timeout=httpx.Timeout(600.0, connect=10.0),
        ) as resp:
            event = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    if event == "mission":
                        try:
                            mission_id = json.loads(data).get("mission_id") or data
                        except Exception:
                            mission_id = data
                    elif event in (None, "", "text", "message"):
                        answer_parts.append(data)
                    elif event == "status":
                        pass
                if not line.strip():
                    event = None
    except Exception as e:
        return {"name": name, "elapsed_s": round(time.monotonic() - t0, 1),
                "mission_id": mission_id, "error": f"{type(e).__name__}: {e}"}
    return {"name": name, "elapsed_s": round(time.monotonic() - t0, 1),
            "mission_id": mission_id, "answer": ("".join(answer_parts))[:300]}


def _budget_check(mission_id: str | None) -> dict | None:
    """[S3] Consulta la telemetría de la misión y resume su presupuesto. None
    si no hubo misión que consultar (camino corto sin traza, doc 34 §10 —
    ninguno de los escenarios de hoy toma ese camino) o si algo falló al leer."""
    if not mission_id:
        return None
    try:
        import app.telemetry as telemetry
        data = telemetry.mission_timeline(mission_id)
    except Exception:
        return None
    s = data.get("summary") or {}
    if "within_budget" not in s:
        return None
    return {
        "llm_calls": s.get("llm_calls", 0),
        "path": s.get("path", "desconocido"),
        "budget": s.get("budget"),
        "within_budget": bool(s.get("within_budget", True)),
        "total_ms": s.get("total_ms", 0),
    }


def _compare_and_save_baseline(path: str, results: list[dict]) -> None:
    """[S3] Compara cada escenario con la pasada anterior guardada en `path`
    (llamadas LLM y duración), imprime la variación, y deja el archivo
    actualizado con la pasada ACTUAL — así la siguiente campaña compara contra
    esta. Si el archivo no existe todavía, simplemente lo crea (primera
    baseline, nada que comparar aún)."""
    p = Path(path)
    anterior: dict = {}
    if p.exists():
        try:
            anterior = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  (no se pudo leer la baseline anterior: {e!r} — se ignora)")

    print("\n═══ Comparación con baseline ═══" if anterior else "\n═══ Baseline (primera pasada) ═══")
    actual: dict = {}
    for r in results:
        b = r.get("budget")
        calls = b["llm_calls"] if b else None
        ms = b["total_ms"] if (b and b.get("total_ms")) else int(r["elapsed_s"] * 1000)
        actual[r["name"]] = {"llm_calls": calls, "total_ms": ms}

        prev = anterior.get(r["name"])
        if not prev:
            continue
        linea = f"  {r['name']}:"
        prev_ms = prev.get("total_ms")
        if prev_ms is not None:
            d_ms = ms - prev_ms
            linea += f" {'+' if d_ms >= 0 else ''}{d_ms}ms ({prev_ms}→{ms})"
        prev_calls = prev.get("llm_calls")
        if calls is not None and prev_calls is not None:
            d_calls = calls - prev_calls
            linea += f", llamadas {'+' if d_calls >= 0 else ''}{d_calls} ({prev_calls}→{calls})"
        print(linea)

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(actual, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  (baseline actualizada en {p})")


async def main(only: set[str] | None, baseline: str | None = None) -> None:
    Path(LAB).mkdir(parents=True, exist_ok=True)
    scenarios = [s for s in SCENARIOS if only is None or s[0] in only]
    print(f"═══ Aithera Mission Lab — {len(scenarios)} escenarios → {LAB} ═══")
    results = []
    async with httpx.AsyncClient() as client:
        # Salud primero: sin backend no hay lab.
        try:
            r = await client.get("http://127.0.0.1:8000/health", timeout=5.0)
            r.raise_for_status()
        except Exception:
            print("✗ El backend no responde en :8000 — arráncalo y reintenta.")
            return
        for tag, name, prompt in scenarios:
            print(f"\n▶ [{tag}] {name} …")
            res = await run_mission(client, name, prompt)
            res["budget"] = _budget_check(res.get("mission_id"))
            results.append(res)
            status = "✗ " + res["error"] if res.get("error") else "✓"
            print(f"  {status} en {res['elapsed_s']}s"
                  + (f" — misión {res['mission_id']}" if res.get("mission_id") else " (camino corto)"))
            if res.get("answer"):
                print(f"  ↳ {res['answer'][:160]}")
            b = res["budget"]
            if b:
                marca = "PASS" if b["within_budget"] else "FAIL"
                print(f"  {marca} presupuesto: {b['llm_calls']} llamadas de {b['budget']} (camino {b['path']})")

    print("\n═══ Resumen ═══")
    for r in results:
        print(f"  {'✗' if r.get('error') else '✓'} {r['name']}: {r['elapsed_s']}s"
              + (f" (misión {r['mission_id']})" if r.get("mission_id") else ""))
    print("\nTimeline de cada misión: python scripts/mission_report.py <mission_id>")
    print("Reporte agregado:        python scripts/mission_report.py --aggregate 1")

    fuera_de_presupuesto = [r for r in results if r.get("budget") and not r["budget"]["within_budget"]]
    if fuera_de_presupuesto:
        print(f"\n✗ {len(fuera_de_presupuesto)} escenario(s) por encima de presupuesto:")
        for r in fuera_de_presupuesto:
            b = r["budget"]
            print(f"   - {r['name']}: {b['llm_calls']}/{b['budget']} llamadas (camino {b['path']})")

    if baseline:
        _compare_and_save_baseline(baseline, results)

    if fuera_de_presupuesto:
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="etiquetas separadas por coma (files,code,web,memory,multi)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--baseline", help="archivo JSON: compara y actualiza contra la pasada anterior")
    args = ap.parse_args()
    if args.list:
        for tag, name, prompt in SCENARIOS:
            print(f"[{tag}] {name}: {prompt[:90]}…")
        sys.exit(0)
    asyncio.run(main(set(args.only.split(",")) if args.only else None, baseline=args.baseline))
