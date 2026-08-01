# backend/app/agents/skills_catalog.py — el catálogo de skills, del lado del
# backend (PU2, doc 35).
#
# EL PROBLEMA QUE RESUELVE: `Agent.skills` (columna JSON, V0.87 W2c) siempre
# aceptó strings libres — nada en el backend comprobaba que existieran en el
# catálogo real. El frontend SÍ tiene un selector con catálogo
# (`SkillPickerPopup.tsx`, 254 entradas de `msitarzewski/agency-agents`), pero
# eso solo protege al usuario que crea un agente A MANO; un agente creado por
# chat/`aithera_tool.create_agent` podía llevar skills inventadas por el LLM
# ("growth-hacking-expert" cuando el catálogo real dice "Growth Hacker") sin
# que nadie lo notara.
#
# DÓNDE VIVE EL ARCHIVO (decisión deliberada, no la del diseño original de doc
# 35 §PU2 punto 1): NO se creó un endpoint `GET /api/agents/skills-catalog`
# para que el frontend deje de tener su copia. `SkillPickerPopup.tsx` evita a
# propósito cualquier fetch en caliente ("Autosuficiencia local", doc 09) —
# picar una skill no debe depender de que el backend esté despierto. En vez de
# romper esa propiedad, este módulo lleva su PROPIA copia del mismo JSON
# (`skills_catalog.json`, generado por el mismo script
# `frontend/scripts/generate_skills_catalog.py`). Es duplicación de datos, no
# de lógica — el riesgo real (que diverjan) es bajo: el catálogo es un
# artefacto generado que casi nunca cambia, y regenerarlo implica correr el
# script con las DOS rutas de salida. Documentado aquí con toda intención para
# que quien lo regenere sepa que hay dos copias que mantener iguales.
from __future__ import annotations

import difflib
import json
import unicodedata
from pathlib import Path
from typing import Optional

_CATALOG_PATH = Path(__file__).parent / "skills_catalog.json"

_catalog: Optional[dict] = None
_by_lower_name: Optional[dict[str, dict]] = None


def _load() -> dict:
    """Carga perezosa, una vez por proceso. Si el archivo falta o está roto,
    degrada a un catálogo vacío (fail-open en LECTURA — un catálogo vacío hace
    que `validate_skills` rechace TODO, que es fail-closed donde importa: no
    se cuela ninguna skill inventada solo porque el archivo no cargó)."""
    global _catalog, _by_lower_name
    if _catalog is not None:
        return _catalog
    try:
        _catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        _catalog = {"source": "", "categories": [], "skills": []}
    _by_lower_name = {
        str(s.get("name", "")).strip().lower(): s
        for s in _catalog.get("skills", [])
        if s.get("name")
    }
    return _catalog


def list_categories() -> list[dict]:
    return list(_load().get("categories", []))


def list_skills() -> list[dict]:
    return list(_load().get("skills", []))


def skill_by_name(name: str) -> Optional[dict]:
    """Búsqueda case-insensitive por NOMBRE — es lo que `Agent.skills` guarda
    (no el `slug`), heredado de como ya funcionaba `SkillPickerPopup.tsx`. Los
    254 nombres del catálogo son únicos (verificado al construir este módulo),
    así que el nombre es un identificador seguro sin necesidad de migrar el
    formato de almacenamiento existente."""
    _load()
    return _by_lower_name.get(name.strip().lower()) if _by_lower_name else None


def suggest(name: str, limit: int = 3) -> list[str]:
    """Sugerencias para un nombre que NO existe: primero substring (rápido y
    predecible — "growth" -> "Growth Hacker"), luego difflib como respaldo
    (typos: "Antropologist" -> "Anthropologist`)."""
    _load()
    names = [s["name"] for s in _catalog.get("skills", [])]
    q = name.strip().lower()
    if not q:
        return []
    substr = [n for n in names if q in n.lower()]
    if substr:
        return substr[:limit]
    return difflib.get_close_matches(name, names, n=limit, cutoff=0.6)


def _normalize(s: str) -> str:
    """Minúsculas + sin acentos, para que "márketing"/"Marketing" comparen
    igual (el usuario pide en español, el catálogo está en inglés/nombres
    propios que a veces sí llevan acento en la traducción del chat)."""
    s = unicodedata.normalize("NFKD", s or "")
    return s.encode("ascii", "ignore").decode("ascii").strip().lower()


def _match_category(term: str) -> Optional[dict]:
    """[PU2-ext] ¿El término es una CATEGORÍA del catálogo ("marketing",
    "research"...) y no el nombre de una skill? Match acento-insensible
    contra las 17 categorías reales — exacto primero (clave o etiqueta),
    luego substring en cualquier dirección ("market" -> "Marketing")."""
    q = _normalize(term)
    if not q:
        return None
    cats = list_categories()
    for c in cats:
        if _normalize(c.get("key", "")) == q or _normalize(c.get("label", "")) == q:
            return c
    for c in cats:
        key, label = _normalize(c.get("key", "")), _normalize(c.get("label", ""))
        if (key and (q in key or key in q)) or (label and (q in label or label in q)):
            return c
    return None


def skills_in_category(category: dict, limit: int = 8) -> list[dict]:
    """Skills reales de una categoría, en orden alfabético — determinista, sin
    inventar un ranking de "relevancia" que el catálogo no ofrece. Acotado a
    `limit` para no volcar las 36 de marketing al prompt del modelo: basta con
    un puñado de candidatos reales para que elija 2-3."""
    key = category.get("key")
    out = sorted(
        (s for s in list_skills() if s.get("category") == key),
        key=lambda s: s.get("name", ""),
    )
    return out[:limit]


def _keyword_candidates(term: str, limit: int = 8) -> list[dict]:
    """[PU2-ext] Búsqueda de un término suelto que NO es ninguna categoría
    (p. ej. "research": no es una de las 17 categorías, pero SÍ aparece en el
    nombre de 3 skills de categorías distintas — UX Researcher, Investment
    Researcher, Trend Researcher). Substring acento-insensible sobre nombre Y
    descripción; prioriza coincidencias de NOMBRE (más relevante) sobre las
    de solo-descripción."""
    q = _normalize(term)
    if len(q) < 3:
        return []
    name_hits, desc_hits = [], []
    for s in list_skills():
        name = _normalize(s.get("name", ""))
        if q in name:
            name_hits.append(s)
            continue
        if q in _normalize(s.get("description", "")):
            desc_hits.append(s)
    return (name_hits + desc_hits)[:limit]


def validate_skills(names: list[str]) -> list[str]:
    """Valida una lista de nombres de skill contra el catálogo real.

    Devuelve la lista CANONICALIZADA (respeta las mayúsculas reales del
    catálogo, aunque el llamador mande otra combinación) si todo existe.
    Lanza `ValueError` con el motivo Y sugerencias si alguna no existe — mismo
    patrón que la validación de `allowed_tools` ya existente en
    `AgentManager.create_agent`/`update_agent`, para que el error vuelva
    accionable hasta el toolloop (el modelo puede corregirse solo en la
    siguiente vuelta, mismo criterio que el resto del proyecto).

    [PU2-ext, doc 35] Un usuario real no se sabe los 254 nombres de memoria —
    pide cosas como "skills de research y márketing". Antes de esta extensión
    esos términos sueltos caían en el mismo "no existe" que un typo, con una
    sugerencia por difflib casi siempre inútil (comparar "research" contra 254
    nombres por distancia de edición no encuentra nada bueno). Ahora, en
    orden de especificidad: (1) nombre exacto → válido tal cual; (2) el
    término ES una categoría real del catálogo ("marketing") → el error lista
    skills REALES de esa categoría para que el modelo elija 2-3 concretas en
    la siguiente vuelta; (3) el término aparece en el nombre o la descripción
    de alguna skill ("research") → el error lista esas coincidencias; (4)
    respaldo original: sugerencia por substring/difflib (typos de un nombre
    casi correcto). NINGÚN nivel selecciona nada por su cuenta — nunca se
    adivina en silencio (mismo principio que el resto del proyecto, doc
    23 §22): siempre hace falta que el modelo confirme con un nombre real en
    el siguiente intento, y ese intento es invisible para el usuario (ocurre
    dentro del propio bucle de tool-use, R1)."""
    canon: list[str] = []
    problems: list[str] = []
    for raw in names:
        n = str(raw).strip()
        if not n:
            continue
        hit = skill_by_name(n)
        if hit:
            canon.append(hit["name"])
            continue

        cat = _match_category(n)
        if cat:
            candidatos = ", ".join(s["name"] for s in skills_in_category(cat))
            problems.append(
                f"'{n}' es una categoría del catálogo ('{cat.get('label', cat.get('key'))}'), "
                f"no el nombre de una skill concreta. Elige nombres reales de esa "
                f"categoría, por ejemplo: {candidatos}."
            )
            continue

        kw = _keyword_candidates(n)
        if kw:
            candidatos = ", ".join(s["name"] for s in kw)
            problems.append(
                f"'{n}' no es el nombre de ninguna skill, pero hay relacionadas "
                f"en el catálogo: {candidatos}."
            )
            continue

        sug = suggest(n)
        hint = f" ¿Querías: {', '.join(sug)}?" if sug else ""
        problems.append(f"'{n}' no existe en el catálogo de skills.{hint}")
    if problems:
        raise ValueError("Skills inválidas: " + " | ".join(problems))
    return canon


def descriptions_for(names: list[str]) -> list[dict]:
    """Las entradas completas (name+description+category) de una lista de
    nombres YA validados — para componer el bloque de contexto que ve el
    modelo al ejecutar (PU2 parte 3). Nombres que no resuelven se omiten en
    silencio (defensivo: si algo quedó en BD desde antes de esta validación,
    no debe romper la ejecución del agente, solo perder ese matiz)."""
    out = []
    for n in names:
        hit = skill_by_name(n)
        if hit:
            out.append(hit)
    return out
