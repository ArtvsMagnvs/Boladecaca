"""JWIKI Tick B 2026-06-30 18:30 (post-delivery) — update task_queue + wiki-map
to mark JWIKI-005 raw as delivered.

The state stays 'in_progress' (the escriba aithera-wiki-scr2 still needs to write
the doc final at 01_LANDSCAPE/openjarvis.md). Only the Material crudo line and
Updated timestamp get updated to reflect the delivery + cross-workspace recovery.
"""
import os

BASE = r"C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI"
TQ = os.path.join(BASE, "00_INDEX", "task_queue.md")
WM = os.path.join(BASE, "00_INDEX", "wiki-map.md")

# ---- task_queue.md ----
with open(TQ, "r", encoding="utf-8") as f:
    tq = f.read()

old_block_005 = """### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Stanford, local-first, 5 primitivos (model, reasoning, agent, tools/memory, routing). Routing dinámico basado en complejidad. Energía como métrica.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 18:30 (turno B tick 5 -- post-crash re-despach; investigador arrancado via `ticks/spawn_agent.py` slot 005b)
- **Material crudo**: `JWIKI/material/JWIKI-005-raw.md` (en curso, re-despach post-crash)"""

new_block_005 = """### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: in_progress (raw entregado, pendiente escriba)
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Stanford, local-first, 5 primitivos (model, reasoning, agent, tools/memory, routing). Routing dinámico basado en complejidad. Energía como métrica. **Repo real: `open-jarvis/OpenJarvis`** (NO stanford-oval como decia el briefing). Paper arXiv:2605.17172, labs Hazy Research + Scaling Intelligence Lab (Stanford).
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 18:52 (turno B tick 5 -- raw entregado, 141 hechos verificados, 50031 bytes. Pendiente escriba `aithera-wiki-scr2` para doc final)
- **Material crudo**: `JWIKI/material/JWIKI-005-raw.md` OK (50031 bytes, 141 hechos verificados, 503 lineas)"""

assert old_block_005 in tq, "Block 005 not found"
tq = tq.replace(old_block_005, new_block_005, 1)

# Update metrics
old_metrics = """- **In progress (Turno B)**: 1 (JWIKI-005 re-despach post-crash 18:30)"""
new_metrics = """- **In progress (Turno B)**: 1 (JWIKI-005 raw entregado, pendiente escriba)"""
assert old_metrics in tq, "Metrics not found"
tq = tq.replace(old_metrics, new_metrics, 1)

with open(TQ, "w", encoding="utf-8") as f:
    f.write(tq)
print("task_queue.md updated")

# ---- wiki-map.md ----
with open(WM, "r", encoding="utf-8") as f:
    wm = f.read()

old_row_005 = "| JWIKI-005 | 01_LANDSCAPE/openjarvis.md | OpenJarvis Stanford local-first | B | 🟡 in_progress | (post-crash, re-despach 18:30)"
new_row_005 = "| JWIKI-005 | 01_LANDSCAPE/openjarvis.md | OpenJarvis Stanford local-first | B | 🟡 in_progress | (raw entregado 18:52, pendiente escriba)"
assert old_row_005 in wm, "Row 005 not found"
wm = wm.replace(old_row_005, new_row_005, 1)

with open(WM, "w", encoding="utf-8") as f:
    f.write(wm)
print("wiki-map.md updated")
print("DONE")