import os
BASE = r"C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI"
TQ = os.path.join(BASE, "00_INDEX", "task_queue.md")
WM = os.path.join(BASE, "00_INDEX", "wiki-map.md")

with open(TQ, "r", encoding="utf-8") as f:
    tq = f.read()

old_block_002 = """### JWIKI-002 — Comparativa proyectos OSS principales
- **Path destino**: `01_LANDSCAPE/projects.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: JWIKI-001 (en curso, turno B)
- **Prioridad**: alta (Fase 1)
- **Notas**: tabla comparativa OpenClaw/OpenHuman/OpenJarvis/JarvisAgent/Hermes/Clawdbot/Superpowers. Stars, licencia, stack, features, último commit.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:15 (turno A tick 1 — material crudo en curso)
- **Material crudo**: `JWIKI/material/JWIKI-002-raw.md` (79 hechos verificados, listo para escriba)"""

new_block_002 = """### JWIKI-002 — Comparativa proyectos OSS principales
- **Path destino**: `01_LANDSCAPE/projects.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: JWIKI-001 (en curso, turno B)
- **Prioridad**: alta (Fase 1)
- **Notas**: tabla comparativa OpenClaw/OpenHuman/OpenJarvis/JarvisAgent/Hermes/Clawdbot/Superpowers. Stars, licencia, stack, features, último commit.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:45 (turno A tick 2 -- investigador 13:15 cerro con 79 hechos; proximo tick A: escriba toma 002)
- **Material crudo**: `JWIKI/material/JWIKI-002-raw.md` ok (222 lineas, 79 hechos verificados, listo para escriba)"""

assert old_block_002 in tq, "Block 002 not found"
tq = tq.replace(old_block_002, new_block_002, 1)

old_block_004 = """### JWIKI-004 — OpenHuman desktop-first Rust+TS
- **Path destino**: `01_LANDSCAPE/openhuman.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: 7.8k stars, Rust+TS, v0.53.43 (mayo 2026). Personal context layer, conexiones Gmail/Notion/GitHub/Slack/Calendar/Drive/Linear/Jira."""

new_block_004 = """### JWIKI-004 — OpenHuman desktop-first Rust+TS
- **Path destino**: `01_LANDSCAPE/openhuman.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: 7.8k stars, Rust+TS, v0.53.43 (mayo 2026). Personal context layer, conexiones Gmail/Notion/GitHub/Slack/Calendar/Drive/Linear/Jira. **Resolver conflicto v0.53.43 vs v0.54.7 detectado en JWIKI-002.**
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:45 (turno A tick 2 -- investigador spawn)
- **Material crudo**: `JWIKI/material/JWIKI-004-raw.md` (en curso)"""

assert old_block_004 in tq, "Block 004 not found"
tq = tq.replace(old_block_004, new_block_004, 1)

with open(TQ, "w", encoding="utf-8") as f:
    f.write(tq)
print("task_queue.md updated")

with open(WM, "r", encoding="utf-8") as f:
    wm = f.read()
old_row = "| JWIKI-004 | 01_LANDSCAPE/openhuman.md | OpenHuman desktop-first Rust+TS | A | plain pending |"
new_row = "| JWIKI-004 | 01_LANDSCAPE/openhuman.md | OpenHuman desktop-first Rust+TS | A | yellow in_progress |"
assert old_row in wm, "Row 004 not found"
wm = wm.replace(old_row, new_row, 1)
with open(WM, "w", encoding="utf-8") as f:
    f.write(wm)
print("wiki-map.md updated")
print("DONE")
