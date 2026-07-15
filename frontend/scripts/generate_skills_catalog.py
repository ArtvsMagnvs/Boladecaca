"""Genera frontend/src/data/skillsCatalog.json a partir del repo
msitarzewski/agency-agents (254 personas de agente en 17 divisiones).

V0.87 (WPMS W2c, doc 18): se reinterpretan los "name"+"description" de cada
persona como TAGS de skill que se pueden asignar a un agente de Aithera (no
se instancian las personas completas — eso queda para "configurar mas
adelante", explicitamente diferido por el usuario). category = la carpeta
division (marketing/engineering/...), ya normalizada en divisions.json del
propio repo con su label/icon/color.

Uso (re-sincronizar cuando el repo fuente cambie):
    git clone --depth 1 https://github.com/msitarzewski/agency-agents.git /tmp/agency-agents
    python generate_skills_catalog.py /tmp/agency-agents ../src/data/skillsCatalog.json

Datos estaticos (no hay endpoint ni fetch en caliente) — coherente con
"Autosuficiencia local" (doc 09): el catalogo funciona sin red una vez
generado. 254 skills / 17 categorias a fecha 2026-07-15, ~116KB.
"""
import json
import re
import sys
from pathlib import Path

import yaml

NON_DIVISION_DIRS = {"integrations", "strategy", "examples", "scripts"}


def parse_frontmatter(text: str) -> dict | None:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def main():
    repo_root = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    divisions_raw = json.loads((repo_root / "divisions.json").read_text(encoding="utf-8"))
    divisions = divisions_raw["divisions"]

    skills = []
    seen_slugs = set()
    for div_key, div_meta in divisions.items():
        if div_key in NON_DIVISION_DIRS:
            continue
        div_dir = repo_root / div_key
        if not div_dir.is_dir():
            continue
        for md_file in sorted(div_dir.rglob("*.md")):
            fm = parse_frontmatter(md_file.read_text(encoding="utf-8", errors="ignore"))
            if not fm or "name" not in fm:
                continue
            name = str(fm["name"]).strip()
            slug = f"{div_key}:{md_file.stem}"
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            skills.append({
                "slug": slug,
                "name": name,
                "description": str(fm.get("description", "")).strip(),
                "emoji": fm.get("emoji") or "🏷️",
                "category": div_key,
                "categoryLabel": div_meta["label"],
            })

    skills.sort(key=lambda s: (s["category"], s["name"]))
    categories = [
        {"key": k, "label": v["label"]}
        for k, v in divisions.items() if k not in NON_DIVISION_DIRS
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"source": "msitarzewski/agency-agents", "categories": categories, "skills": skills}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(skills)} skills en {len(categories)} categorias -> {out_path}")


if __name__ == "__main__":
    main()
