"""JWIKI Tick B 2026-06-30 18:30 — apply wiki-map.md update only.

task_queue.md was already updated by the first run of apply-tick-B-1830.py.
This script only completes the wiki-map.md update.
"""
import os

BASE = r"C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI"
WM = os.path.join(BASE, "00_INDEX", "wiki-map.md")

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