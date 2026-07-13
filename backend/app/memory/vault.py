# app/memory/vault.py — Vault: espejo Markdown de resumenes diarios y decisiones
# (V0.85, doc 07 §9). Interno del MOS — accesible SOLO via el barrel app.memory
# (doc 16 §4.1); vigilado por tests/test_module_boundaries.py.
#
# Solo escritura en V0.85 (bidireccional = V1.x, fuera de alcance ahora). Escribe
# en %APPDATA%/Aithera/vault/YYYY/MM/ — AITHERA_VAULT_PATH la reubica (mismo
# patron que AITHERA_CHROMA_PATH en memory_manager.py, para aislar en tests).
#
# Best-effort: un fallo de disco nunca rompe al caller (summarizer.py /
# decision_service.py) — mismo principio fail-soft que el resto del MOS. El
# vault es un espejo de lectura humana, no la fuente de verdad (esa sigue
# siendo ChromaDB/SQL); perder una escritura del espejo no pierde datos.
from __future__ import annotations

import os
from datetime import date as date_cls, datetime
from pathlib import Path
from typing import Any, Optional

VAULT_PATH = Path(os.environ.get("AITHERA_VAULT_PATH") or os.path.join(
    os.environ.get("APPDATA") or ".", "Aithera", "vault"
))


def _month_dir(target: date_cls) -> Path:
    d = VAULT_PATH / f"{target.year:04d}" / f"{target.month:02d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_daily_summary(target: date_cls, content: str) -> Optional[Path]:
    """Espejo de mem_personal kind=daily_summary. Mismo dia -> sobreescribe
    (igual que el dedup_key=day:{date} del store). None si falla (best-effort)."""
    try:
        path = _month_dir(target) / f"{target.isoformat()}-resumen.md"
        text = f"# Resumen del {target.isoformat()}\n\n{(content or '').strip()}\n"
        path.write_text(text, encoding="utf-8")
        return path
    except Exception as e:
        print(f"[vault] no se pudo escribir el resumen diario (no critico): {e}")
        return None


def write_decision(decision: Any) -> Optional[Path]:
    """Espejo de una Decision (app.db.models.Decision). Mismo decision.id ->
    mismo archivo, se sobreescribe (soporta el re-espejo de link_outcome).
    None si falla (best-effort)."""
    try:
        created = decision.created_at or datetime.utcnow()
        target = created.date() if isinstance(created, datetime) else created

        lines = [f"# {decision.title}", ""]
        if decision.body:
            lines += [decision.body.strip(), ""]
        if decision.reason:
            lines += [f"**Motivo**: {decision.reason}", ""]
        if decision.project:
            lines += [f"**Proyecto**: {decision.project}", ""]
        lines += [
            f"**Impacto**: {decision.impact}  ",
            f"**Estado**: {decision.status}  ",
        ]
        if decision.outcome:
            lines += [f"**Resultado**: {decision.outcome}  "]
        if decision.mission_id:
            lines += [f"**Mision**: {decision.mission_id}  "]

        path = _month_dir(target) / f"{decision.id}-decision.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[vault] no se pudo escribir la decision (no critico): {e}")
        return None
