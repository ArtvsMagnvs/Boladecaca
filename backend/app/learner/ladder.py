# app/learner/ladder.py — la ESCALERA DE CONFIANZA (V1.1 L1, doc 15 §3)
#
# Funciones PURAS (sin BD, sin LLM, sin I/O): dado el estado de una propuesta y
# su evidencia, ¿puede subir un peldaño? ¿por qué ruta? Ser puro es lo que las
# hace testeables al milímetro — y lo que garantiza que la política de
# validación vive en UN sitio y no repartida por los llamadores.
#
# LA REGLA CONSTITUCIONAL (doc 15, cabecera): el Learner observa, analiza y
# PROPONE. Nada llega a `consolidated` sin evidencia suficiente o aprobación
# humana — este módulo es el único juez de "suficiente", y es deliberadamente
# DESCONFIADO (fail-closed): ante una evidencia malformada, un kind
# desconocido o una transición ilegal, la respuesta es NO.
#
# CÓMO SE MAPEA LA ESCALERA A LAS SKILLS (decisión de diseño de L1): las skills
# NO usan `learner_proposals` — su propio `SkillStatus` ES su escalera, con
# esta correspondencia (doc 09 §1.2 ↔ doc 15 §3.1):
#
#     escalera general      skill
#     ----------------      -----------------------------------------
#     observed/candidate    (todavía no existe como skill: vive en el
#                            análisis del LLL hasta juntar MIN_REP)
#     proposed              DRAFT       (existe, visible, en cuarentena)
#     validated             VALIDATED   (3 ejecuciones OK o el usuario)
#     consolidated          LOCAL       (reposo normal, sobrevive a la
#                                        compactación)
#     (+ deprecated)        DEPRECATED  (nunca se borra; superseded_by)
#
# Dos maquinarias para el mismo camino habría sido frameworkitis (doc 16);
# library.py aplica ESTAS MISMAS constantes al validar una skill.
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constantes de política (doc 15 §3.2/§3.3 — números del diseño, no inventados)
# ---------------------------------------------------------------------------
MIN_REP = 3            # evidencias en contextos DISTINTOS para ser candidate
LOW_RISK_AUTO_N = 5    # riesgo bajo: auto-validación con N consistentes y 0 contradicciones
MEDIUM_OK_EXECUTIONS = 3  # riesgo medio: ejecuciones OK reales (o aprobación explícita)

RISKS = ("low", "medium", "high")

# Estados de la escalera (doc 15 §3.1) + terminales de registro.
STATES = ("observed", "candidate", "proposed", "validated", "consolidated",
          "rejected", "reverted")

# Transiciones LEGALES. Todo lo que no esté aquí se rechaza — la escalera se
# sube peldaño a peldaño, nunca en ascensor. `rejected` es alcanzable desde
# cualquier estado vivo (el usuario siempre puede decir no); `reverted` SOLO
# desde consolidated (deshacer lo no aplicado no significa nada).
_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "observed":     ("candidate", "rejected"),
    "candidate":    ("proposed", "rejected"),
    "proposed":     ("validated", "rejected"),
    "validated":    ("consolidated", "rejected"),
    "consolidated": ("reverted",),
    "rejected":     (),
    "reverted":     (),
}

# ---------------------------------------------------------------------------
# Evidencia — SOLO señal externa (doc 15 §3.3, anti-contaminación)
# ---------------------------------------------------------------------------
# "El LLM dijo que salió bien" NO es evidencia: es un bucle de
# retroalimentación que refuerza sus propios errores. Cuenta únicamente lo
# verificable desde fuera del modelo:
EXTERNAL_SIGNAL_KINDS = frozenset({
    "validation_ok",      # la validación determinista del executor (T3) dio OK
    # [V1.1 LC2, doc 41 §4.3] LA EVIDENCIA QUE DE VERDAD DICE "SIRVIÓ": un
    # veredicto `served` de un juez INDEPENDIENTE (capacidad LEARN, no el
    # modelo que ejecutó) que citó señales duras, sobre trabajo REAL del
    # usuario. Su payload lleva `verdict_id`, así que es verificable: se puede
    # abrir la fila de `mission_verdicts` y leer en qué se apoyó.
    "judged_success",
    "judged_failure",     # el contrario, y también es información (ver abajo)
    "execution_fail",     # una tool/skill corrió y falló (señal negativa real)
    "user_feedback",      # ✓/✎/✗ explícito del usuario (patrón email V0.7.3)
    "user_approval",      # aprobación explícita (ApprovalGate / panel)
    "decision_outcome",   # link_outcome de la Decision API (doc 08 RFC-002)
    "contradiction",      # evidencia EN CONTRA (resetea rachas, doc 15 §7.2)
    # --- legado, admitido pero SIN VALOR (ver `POSITIVE_KINDS`) ---
    # `execution_ok` significaba "la máquina terminó sin colgarse", y eso NO es
    # que al usuario le sirviera: es exactamente el criterio con el que el
    # Learner acabó proponiendo ocho intentos fallidos como procedimiento fijo
    # (doc 41 §0). Se mantiene en el conjunto para que las evidencias YA
    # guardadas sigan siendo legibles y auditables, pero no cuenta para subir
    # ningún peldaño hasta que el re-juicio las convierta en `judged_success`.
    "execution_ok",
    "legacy_unjudged",    # marca de migración: era `execution_ok`, sin juzgar
})

# Las que SUMAN para subir peldaños. Todo lo demás se guarda pero no empuja —
# la asimetría es deliberada: una evidencia dudosa no debe poder promover nada,
# y en cambio una negativa sí debe poder frenar.
POSITIVE_KINDS = frozenset({
    "judged_success", "validation_ok", "user_feedback",
    "user_approval", "decision_outcome",
})

# Las que RESTAN o frenan.
NEGATIVE_KINDS = frozenset({"contradiction", "execution_fail", "judged_failure"})

# Las que ya no valen para nada salvo para poder mirarlas.
INERT_KINDS = frozenset({"execution_ok", "legacy_unjudged"})


def is_valid_evidence(ev: Any) -> bool:
    """¿Es una evidencia admisible? Exige dict con `kind` externo y
    `context_key` no vacío (misión/día — para poder distinguir contextos).
    Fail-closed: cualquier forma rara es un no."""
    if not isinstance(ev, dict):
        return False
    if ev.get("kind") not in EXTERNAL_SIGNAL_KINDS:
        return False
    return bool(str(ev.get("context_key") or "").strip())


def counts_for_promotion(ev: Any) -> bool:
    """¿Esta evidencia EMPUJA hacia arriba? (LC2, doc 41 §4.3)

    Separar "admisible" de "cuenta" es lo que permitió cambiar el criterio sin
    borrar el historial: las evidencias `execution_ok` de antes del juez siguen
    ahí, se pueden leer y auditar, pero dejaron de valer para subir peldaños."""
    return is_valid_evidence(ev) and ev.get("kind") in POSITIVE_KINDS


def distinct_contexts(evidence: List[dict]) -> int:
    """Nº de contextos DISTINTOS con evidencia POSITIVA. Una racha de suerte no
    es un patrón (doc 15 §3.3): tres éxitos en la MISMA misión cuentan como
    UNO. Lo negativo no suma (resta por otra vía) y lo INERTE tampoco — un
    `execution_ok` es la máquina diciendo que terminó, no el usuario diciendo
    que le sirvió."""
    positivos = {
        str(ev["context_key"]).strip()
        for ev in evidence
        if counts_for_promotion(ev)
    }
    return len(positivos)


def unjudged_in(evidence: List[dict]) -> int:
    """Cuántas evidencias hay esperando un veredicto. No es un error: es el
    estado normal de lo que se acumuló antes de que existiera el juez, y el
    panel puede explicarlo con ese número en la mano ('3 misiones sin juzgar
    todavía') en vez de dejar la propuesta parada sin decir por qué."""
    return sum(1 for ev in evidence
               if is_valid_evidence(ev) and ev.get("kind") in INERT_KINDS)


def count_kind(evidence: List[dict], kind: str) -> int:
    return sum(1 for ev in evidence if is_valid_evidence(ev) and ev["kind"] == kind)


def has_user_approval(evidence: List[dict]) -> bool:
    return count_kind(evidence, "user_approval") > 0


def contradictions_in(evidence: List[dict]) -> int:
    """Evidencia EN CONTRA. [LC2] Un veredicto `failed` de un juez independiente
    cuenta como contradicción: si el trabajo se hizo y NO sirvió, eso no es
    neutral respecto a convertirlo en procedimiento — es un argumento en
    contra. Es la mitad de "se aprende igual del error que del acierto" que
    vive en la escalera; la otra (extraer la lección) vive en el juez y en la
    consolidación."""
    return count_kind(evidence, "contradiction") + count_kind(evidence, "judged_failure")


# ---------------------------------------------------------------------------
# El juicio: ¿puede esta propuesta subir al siguiente peldaño?
# ---------------------------------------------------------------------------
def can_transition(state: str, to: str) -> bool:
    """¿Es LEGAL el salto (con independencia de la evidencia)?"""
    return to in _TRANSITIONS.get(state, ())


def can_validate(risk: str, evidence: List[dict],
                 contradictions: int = 0) -> Tuple[bool, str]:
    """¿Hay base para proposed → validated? Devuelve (sí/no, motivo legible).

    Las TRES rutas de doc 15 §3.2, literales:
      · low    — auto con ≥LOW_RISK_AUTO_N evidencias consistentes en contextos
                 distintos Y 0 contradicciones. Una sola contradicción para la
                 auto-ruta en seco (mejor preguntar que asumir, §7.2).
      · medium — MEDIUM_OK_EXECUTIONS ejecuciones OK reales O aprobación
                 explícita del usuario, lo que llegue antes.
      · high   — SIEMPRE HITL: solo la aprobación del usuario vale. Ninguna
                 cantidad de evidencia automática la sustituye.
    """
    contradicciones = contradictions + contradictions_in(evidence)

    if risk == "high":
        if has_user_approval(evidence):
            return True, "aprobación explícita del usuario (riesgo alto: siempre HITL)"
        return False, "riesgo alto: exige aprobación explícita del usuario, sin excepciones"

    if risk == "medium":
        if has_user_approval(evidence):
            return True, "aprobación explícita del usuario"
        # [LC2] Antes se contaba `execution_ok` — "la máquina terminó". Ahora
        # cuenta el veredicto de un juez independiente sobre si SIRVIÓ, más la
        # validación determinista del executor, que es una comprobación real y
        # no una opinión del propio modelo.
        oks = (count_kind(evidence, "judged_success")
               + count_kind(evidence, "validation_ok"))
        if oks >= MEDIUM_OK_EXECUTIONS:
            return True, (f"{oks} misiones juzgadas útiles de verdad "
                          f"(umbral {MEDIUM_OK_EXECUTIONS})")
        sin_juzgar = unjudged_in(evidence)
        pista = (f"; hay {sin_juzgar} sin juzgar todavía" if sin_juzgar else "")
        return False, (f"riesgo medio: hacen falta {MEDIUM_OK_EXECUTIONS} misiones "
                       f"juzgadas útiles (hay {oks}{pista}) o la aprobación del usuario")

    if risk == "low":
        if contradicciones > 0:
            return False, (f"riesgo bajo con {contradicciones} contradicción(es): "
                           f"la auto-validación se detiene — se pregunta, no se asume")
        n = distinct_contexts(evidence)
        if n >= LOW_RISK_AUTO_N:
            return True, f"{n} evidencias consistentes en contextos distintos, 0 contradicciones"
        if has_user_approval(evidence):
            return True, "aprobación explícita del usuario"
        return False, (f"riesgo bajo: hacen falta {LOW_RISK_AUTO_N} evidencias en contextos "
                       f"distintos (hay {n}) o la aprobación del usuario")

    # Riesgo desconocido = fail-closed. Un typo en el llamador no puede
    # convertirse en una ruta de validación permisiva.
    return False, f"clase de riesgo desconocida: {risk!r} (fail-closed)"


def can_be_candidate(evidence: List[dict]) -> Tuple[bool, str]:
    """observed → candidate exige MIN_REP contextos distintos (doc 15 §3.3):
    'una racha de suerte no es evidencia'."""
    n = distinct_contexts(evidence)
    if n >= MIN_REP:
        return True, f"patrón con {n} contextos distintos (umbral {MIN_REP})"
    sin_juzgar = unjudged_in(evidence)
    if sin_juzgar:
        # Se dice el porqué exacto: no es que no haya pasado nada, es que lo
        # que pasó todavía no consta como útil. Sin esto, una propuesta llena
        # de evidencias legado se quedaría quieta sin explicación.
        return False, (f"señal insuficiente: {n} contexto(s) juzgado(s) útil(es) de "
                       f"{MIN_REP} necesarios ({sin_juzgar} sin juzgar todavía)")
    return False, f"señal insuficiente: {n} contexto(s) distinto(s) de {MIN_REP} necesarios"


# ---------------------------------------------------------------------------
# El mismo juicio, aplicado a una SKILL (mapeo de la cabecera)
# ---------------------------------------------------------------------------
def skill_can_validate(evidence_count: int, actor: str) -> Tuple[bool, str]:
    """DRAFT → VALIDATED de una skill. Las skills son clase de riesgo MEDIO
    (doc 15 §3.2): MEDIUM_OK_EXECUTIONS ejecuciones OK — que en la skill vive
    ya agregado en `evidence_count` — o el usuario en persona."""
    if actor == "user":
        return True, "validada a mano por el usuario"
    if evidence_count >= MEDIUM_OK_EXECUTIONS:
        return True, f"{evidence_count} ejecuciones con éxito (umbral {MEDIUM_OK_EXECUTIONS})"
    return False, (f"hacen falta {MEDIUM_OK_EXECUTIONS} ejecuciones con éxito "
                   f"(hay {evidence_count}) o la validación del usuario")


# Transiciones legales del ciclo de vida de una skill (doc 09 §1.2). PROPOSED
# es "propuesta a la GSN" (V2.0+): sale de LOCAL, no del camino de cuarentena.
SKILL_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "draft":      ("validated", "deprecated"),
    "validated":  ("local", "deprecated"),
    "local":      ("proposed", "deprecated"),
    "proposed":   ("local", "deprecated"),
    "deprecated": (),        # terminal: nunca se borra, nunca resucita en silencio
}


def skill_can_transition(status: str, to: str) -> bool:
    return to in SKILL_TRANSITIONS.get(status, ())
