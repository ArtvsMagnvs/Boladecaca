# backend/app/core/corpus.py — DE DÓNDE VIENE cada misión (V1.1 LC1, doc 41 §6)
#
# El Learner solo puede aprender de trabajo REAL. El desastre que abrió el
# rediseño (doc 41 §0) tenía dos mitades: juzgar mal lo que pasó, y aprender de
# misiones que ni siquiera eran del usuario — campañas de test, baterías de
# `mission_lab`, misiones de un E2E. Esto cierra la segunda mitad.
#
# Vive en `app/core/` y no en `app/learner/` por el mismo motivo que
# `failures.py` (L2b): quien marca el origen es el TIE al crear la misión, y el
# TIE no puede importar del Learner — el Learner OBSERVA al TIE, no al revés
# (doc 16 + doc 15 regla constitucional).
#
# Es MECÁNICO a propósito (doc 41 §1: lo mecánico extrae y protege; la IA
# entiende y propone). Saber si un proceso es una prueba no es un juicio: o
# lleva la marca o no la lleva.
from __future__ import annotations

import os
import re
import time
from typing import Optional

# Los orígenes posibles. `user` es el ÚNICO del que se aprende; el resto se
# registra igual (auditable) pero no alimenta propuestas.
USER = "user"
TEST = "test"
CAMPAIGN = "campaign"
E2E = "e2e"
AUTOMATION = "automation"
ORIGINS = (USER, TEST, CAMPAIGN, E2E, AUTOMATION)

# La marca de prueba, por dos vías porque hay dos formas de lanzar pruebas:
#  - variable de entorno: para lo que corre DENTRO del proceso del backend
#    (pytest, el E2E del Learner).
#  - clave de Config: para lo que lo dirige DESDE FUERA por HTTP
#    (`scripts/mission_lab.py`, las campañas) — ahí el entorno del script no
#    llega al backend, así que la marca tiene que viajar por la base de datos.
ENV_FLAG = "AITHERA_TEST_CORPUS"
CONFIG_FLAG = "learner.test_corpus"

# El valor de la marca puede ser un origen concreto ("campaign", "e2e") o
# simplemente "1"/"true" — que significa "test" a secas.
_VERDADEROS = {"1", "true", "yes", "on", "si", "sí"}

# Caché corta de la clave de Config: se consulta al crear CADA misión (camino
# caliente) y es una bandera que cambia una vez cada mucho.
_TTL_S = 30.0
_cache: tuple[float, Optional[str]] = (0.0, None)


def _normaliza(valor: Optional[str]) -> Optional[str]:
    """Traduce el valor de la marca a un origen del catálogo, o None si no
    marca nada. Desconocido pero no vacío ⇒ `test`: la dirección segura es
    tratar lo dudoso como prueba (aprender de una prueba contamina; no aprender
    de una misión real solo cuesta una oportunidad)."""
    if valor is None:
        return None
    v = str(valor).strip().lower()
    if not v or v in {"0", "false", "no", "off"}:
        return None
    if v in ORIGINS:
        return v
    return TEST if v in _VERDADEROS else TEST


def _desde_config() -> Optional[str]:
    global _cache
    ahora = time.monotonic()
    if ahora - _cache[0] < _TTL_S:
        return _cache[1]
    valor = None
    try:
        from app.db.database import Config, SessionLocal

        db = SessionLocal()
        try:
            fila = db.query(Config).filter(Config.key == CONFIG_FLAG).first()
            valor = fila.value if fila else None
        finally:
            db.close()
    except Exception:
        valor = None                 # sin BD todavía: no es una prueba, es el arranque
    _cache = (ahora, _normaliza(valor))
    return _cache[1]


def reset_cache() -> None:
    """Olvida la caché de la marca. La usan los tests y quien cambia la bandera
    y quiere que surta efecto en el acto."""
    global _cache
    _cache = (0.0, None)


def test_marker() -> Optional[str]:
    """El origen que impone la marca de prueba activa, o None si no hay marca.
    El entorno manda sobre la Config: es lo más cercano al proceso."""
    return _normaliza(os.environ.get(ENV_FLAG)) or _desde_config()


def current_origin(source: str = USER) -> str:
    """El origen de una misión que se está creando AHORA.

    `source` es el `Mission.source` de siempre (user/automation/learner/
    workspace). La marca de prueba tiene prioridad: una misión de automatización
    lanzada dentro de una campaña es corpus de prueba, no automatización real."""
    marca = test_marker()
    if marca:
        return marca
    s = (source or USER).strip().lower()
    if s and s != USER:
        # `learner` y `workspace` también son trabajo de la casa, no del
        # usuario pidiendo algo: se agrupan bajo automation para el juez.
        return AUTOMATION
    return USER


# ---------------------------------------------------------------------------
# Lo HISTÓRICO: heurística, y solo para lo que ya está escrito sin marca
# ---------------------------------------------------------------------------
# Las misiones anteriores a LC1 no llevan `origin`. No hay forma de recuperar
# el dato, así que para ELLAS se reconoce lo que las pruebas del proyecto dejan
# escrito en el propio goal. Es una red de seguridad para el backfill, NUNCA el
# mecanismo principal: lo que se cree a partir de ahora llega ya etiquetado.
_HUELLAS = (
    re.compile(r"test[\s\-_]*campan[yñ]a", re.I),
    re.compile(r"\bcampan[yñ]a[\s\-_]*\d", re.I),
    re.compile(r"example\.(com|org|net)", re.I),
    re.compile(r"\[contexto interno:", re.I),
    re.compile(r"\btest[\s\-_]*lab\b", re.I),
    re.compile(r"\bmission[\s\-_]*lab\b", re.I),
    re.compile(r"\bpytest\b", re.I),
    re.compile(r"^\s*(test|prueba)[\s:\-]", re.I),
)


def looks_like_test(goal: str) -> bool:
    """¿El texto de una misión HISTÓRICA delata que era una prueba? Conservador
    a propósito: solo huellas que las pruebas de este proyecto dejan de verdad.
    No intenta adivinar intención — de eso ya se encarga el juez, que ve el goal
    y puede señalarlo por su cuenta."""
    if not goal:
        return False
    return any(p.search(goal) for p in _HUELLAS)


def origin_of(stored: Optional[str], goal: str = "", source: str = USER) -> str:
    """El origen de una misión YA GUARDADA. Si trae `origin` escrito, manda ese
    (es el dato real). Si no lo trae — histórica —, se aplica la heurística."""
    s = (stored or "").strip().lower()
    if s in ORIGINS:
        return s
    if looks_like_test(goal):
        return TEST
    src = (source or USER).strip().lower()
    return USER if src in ("", USER) else AUTOMATION


def is_real(origin: str) -> bool:
    """¿Se puede aprender de esto? Solo el trabajo real del usuario."""
    return (origin or "").strip().lower() == USER
