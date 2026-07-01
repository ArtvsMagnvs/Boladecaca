"""JWIKI Tick B 2026-06-30 18:30 — apply changes to task_queue.md and wiki-map.md.

Marks JWIKI-005 as in_progress (re-dispatch post-daemon-crash recovery).
Updates metrics block.
"""
import os
import sys

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
- **Updated**: 2026-06-30 18:26 (DAEMON CRASH RECOVERY -- turno B tick 3 spawn perdio agente `mvs_c3565c1cffec4d9781e4199d924b7b8e`; reset a pending para re-despacho en proximo tick B :30)
- **Material crudo**: `JWIKI/material/JWIKI-005-raw.md` (NO entregado -- daemon crash)"""

new_block_005 = """### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Stanford, local-first, 5 primitivos (model, reasoning, agent, tools/memory, routing). Routing dinámico basado en complejidad. Energía como métrica.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 18:30 (turno B tick 5 -- post-crash re-despach; investigador arrancado via `ticks/spawn_agent.py` slot 005b)
- **Material crudo**: `JWIKI/material/JWIKI-005-raw.md` (en curso, re-despach post-crash)"""

assert old_block_005 in tq, "Block 005 not found in task_queue.md"
tq = tq.replace(old_block_005, new_block_005, 1)

# Update metrics block
old_metrics = """- **In progress (Turno B)**: 0"""
new_metrics = """- **In progress (Turno B)**: 1 (JWIKI-005 re-despach post-crash 18:30)"""
assert old_metrics in tq, "Metrics block not found"
tq = tq.replace(old_metrics, new_metrics, 1)

# Update Pending count
old_pending = """- **Pending**: 262 (incl. JWIKI-005, JWIKI-006, JWIKI-007, JWIKI-008 reset tras daemon crash)"""
new_pending = """- **Pending**: 261 (JWIKI-007, 009, 011... despues de re-despach 005; JWIKI-006 re-despachado turno A 18:30)"""
assert old_pending in tq, "Pending block not found"
tq = tq.replace(old_pending, new_pending, 1)

with open(TQ, "w", encoding="utf-8") as f:
    f.write(tq)
print("task_queue.md updated")

# ---- wiki-map.md ----
with open(WM, "r", encoding="utf-8") as f:
    wm = f.read()

old_row_005 = "| JWIKI-005 | 01_LANDSCAPE/openjarvis.md | OpenJarvis Stanford local-first | B | 🔴 pending | (post-crash)"
new_row_005 = "| JWIKI-005 | 01_LANDSCAPE/openjarvis.md | OpenJarvis Stanford local-first | B | 🟡 in_progress | (post-crash, re-despach 18:30)"
assert old_row_005 in wm, "Row 005 not found in wiki-map.md"
wm = wm.replace(old_row_005, new_row_005, 1)

with open(WM, "w", encoding="utf-8") as f:
    f.write(wm)
print("wiki-map.md updated")
print("DONE")