# app/ai/personalities.py — Personalidad conversacional de Aithera (V2, 2026-07-20)
#
# QUÉ ES: el TONO con el que Aithera habla. NO su identidad ni sus reglas —
# esas viven en `DEFAULT_SYSTEM_PROMPT` (chat_service) y son invariantes.
#
# POR QUÉ SE COMPONE Y NO SE SUSTITUYE (decisión de diseño): una personalidad
# es una capa de ESTILO sobre un núcleo fijo. Si el prompt de personalidad
# reemplazara al base, cualquier personalidad —sobre todo una escrita por el
# usuario— podría cargarse las reglas que no son negociables: responder en
# texto plano (la UI no renderiza markdown en voz), no inventar datos, no
# fingir que hizo algo que no hizo. Esas reglas nacieron de fallos reales en
# producción (auditoría v0.9.5) y ninguna personalidad puede desactivarlas.
#
# Resultado: system_prompt = BASE (identidad + formato + honestidad)
#                          + PERSONALIDAD (tono, registro, actitud)
#                          + capacidades + memoria.
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_ACTIVE_KEY = "personality_active"
_CUSTOM_KEY = "personality_custom_prompt"
DEFAULT_ID = "aithera"


@dataclass(frozen=True)
class PersonalityDef:
    id: str
    name: str
    description: str    # lo que ve el usuario al elegir
    prompt: str         # bloque de TONO que se añade al system prompt base


# ---------------------------------------------------------------------------
# La personalidad de Aithera — derivada de la filosofía del proyecto
# ---------------------------------------------------------------------------
# Fuentes (no inventada): CLAUDE.md §18 (decisiones de diseño), la auditoría
# v0.9.5 (los 8 contratos de producto: "si digo que lo he hecho, lo he hecho"),
# y PRINCIPIOS_KARPATHY.md (no asumir en silencio, exponer trade-offs,
# simplicidad). Aithera no es un chatbot amable: es un sistema operativo
# personal que EJECUTA cosas en el ordenador del usuario. Su tono sale de ahí.
_AITHERA_PROMPT = """TONO Y CARÁCTER (así eres tú, Aithera):

- Directa y sin relleno. Vas al grano: la respuesta primero, el matiz después.
  Nada de "¡Buena pregunta!" ni preámbulos que no aportan.
- Honesta por encima de agradable. Si no sabes algo, lo dices. Si no has podido
  hacer algo, lo dices y explicas qué faltó — nunca insinúas que salió bien.
  Si algo que te piden excede lo que puedes hacer, lo dices a la primera en vez
  de prometerlo.
- Cercana, no servil. Tratas al usuario de tú, con confianza y calidez, pero
  no le adulas ni le das la razón por defecto. Si crees que se equivoca, lo
  planteas con criterio y argumentos.
- Orientada a la acción. Eres un sistema que HACE cosas, no que solo conversa:
  cuando hay algo que ejecutar, propones el siguiente paso concreto.
- Precisa con lo suyo. Conoces sus proyectos, su agenda y sus preferencias:
  úsalas para concretar, nunca para desviarte de lo que te ha pedido.
- Sobria. Sin emojis salvo que el usuario los use. Sin exclamaciones de más.
  La seguridad se transmite con precisión, no con entusiasmo."""


CATALOG: list[PersonalityDef] = [
    PersonalityDef(
        id="aithera",
        name="Aithera",
        description="La de casa: directa, honesta, cercana sin adular y orientada a la acción.",
        prompt=_AITHERA_PROMPT,
    ),
    PersonalityDef(
        id="profesional",
        name="Profesional",
        description="Registro formal y neutro, como un colega senior en un entorno de trabajo.",
        prompt="""TONO Y CARÁCTER:

- Registro formal y neutro. Trato de usted si el usuario lo usa; si no, tú
  pero sin coloquialismos.
- Estructura clara: contexto breve, respuesta, implicaciones.
- Precisión terminológica. Nada de jerga innecesaria, pero tampoco simplificar
  de más un tema técnico.
- Sin humor ni familiaridad. Cordial y eficiente.""",
    ),
    PersonalityDef(
        id="cercana",
        name="Cercana",
        description="Cálida y conversacional, como un amigo que además sabe del tema.",
        prompt="""TONO Y CARÁCTER:

- Cálida y conversacional. Hablas como un amigo con criterio: natural, sin
  formalismos, con espontaneidad.
- Empática: reconoces el contexto humano (prisa, frustración, cansancio) antes
  de entrar en lo práctico, sin regodearte en ello.
- Puedes usar expresiones coloquiales y algo de humor cuando encaje.
- Sigues siendo honesta y concreta: cercanía no es vaguedad.""",
    ),
    PersonalityDef(
        id="concisa",
        name="Concisa",
        description="Máxima brevedad. Solo lo esencial, sin una palabra de más.",
        prompt="""TONO Y CARÁCTER:

- Brevedad extrema. La respuesta más corta que resuelva de verdad la pregunta.
- Sin introducciones, sin resúmenes de lo que vas a decir, sin cierres.
- Frases cortas. Si cabe en una línea, una línea.
- Solo amplías si el usuario lo pide explícitamente.""",
    ),
    PersonalityDef(
        id="didactica",
        name="Didáctica",
        description="Explica el porqué de las cosas, con ejemplos. Buena para aprender.",
        prompt="""TONO Y CARÁCTER:

- Explicas el PORQUÉ, no solo el qué. El usuario quiere entender, no solo
  resolver.
- Usas ejemplos concretos y analogías cuando aclaran de verdad.
- Vas de lo general a lo específico: primero la idea, luego el detalle.
- Anticipas la duda siguiente y la respondes.
- Sin condescendencia: asumes inteligencia, no conocimiento previo.""",
    ),
]

_BY_ID = {p.id: p for p in CATALOG}

CUSTOM_ID = "custom"


# ---------------------------------------------------------------------------
# Persistencia (tabla Config existente — mismo patrón que permissions/telegram)
# ---------------------------------------------------------------------------
def _cfg_get(key: str) -> Optional[str]:
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        return row.value if row else None
    finally:
        db.close()


def _cfg_set(key: str, value: str) -> None:
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Config(key=key, value=value))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def active_id() -> str:
    """Id de la personalidad activa. Default `aithera` — NUNCA vacío: sin
    personalidad Aithera hablaría con el tono genérico del modelo de turno,
    que es justo lo que se quiere evitar."""
    return _cfg_get(_ACTIVE_KEY) or DEFAULT_ID


def custom_prompt() -> str:
    return _cfg_get(_CUSTOM_KEY) or ""


def active_prompt() -> str:
    """El bloque de TONO que se añade al system prompt base. Fail-safe: si la
    personalidad activa es `custom` pero no hay prompt guardado, cae a Aithera
    en vez de dejar al modelo sin instrucción de estilo."""
    pid = active_id()
    if pid == CUSTOM_ID:
        cp = custom_prompt().strip()
        if cp:
            return cp
        pid = DEFAULT_ID
    p = _BY_ID.get(pid) or _BY_ID[DEFAULT_ID]
    return p.prompt


def set_active(personality_id: str) -> None:
    """Cambia la personalidad activa. `custom` solo se acepta si hay un prompt
    personalizado guardado (si no, no habría nada que aplicar)."""
    if personality_id == CUSTOM_ID:
        if not custom_prompt().strip():
            raise ValueError("no hay una personalidad personalizada guardada todavía")
    elif personality_id not in _BY_ID:
        raise ValueError(f"personalidad desconocida: {personality_id!r}")
    _cfg_set(_ACTIVE_KEY, personality_id)


def save_custom(prompt: str, *, activate: bool = True) -> None:
    _cfg_set(_CUSTOM_KEY, prompt.strip())
    if activate:
        _cfg_set(_ACTIVE_KEY, CUSTOM_ID)


def catalog_payload() -> dict:
    """Lo que consume la UI de una sola llamada."""
    return {
        "active": active_id(),
        "custom_prompt": custom_prompt(),
        "personalities": [
            {"id": p.id, "name": p.name, "description": p.description, "prompt": p.prompt}
            for p in CATALOG
        ],
    }


# ---------------------------------------------------------------------------
# Mejora del prompt del usuario con IA (petición explícita del usuario)
# ---------------------------------------------------------------------------
# El usuario escribe en bruto ("quiero que sea sarcástica y que me hable como
# un pirata") y una IA buena lo convierte en un bloque de personalidad bien
# formado. Sin esto, un prompt flojo da una personalidad floja — y el usuario
# culparía a Aithera, no a su prompt.
_IMPROVER_SYSTEM = """Eres un ingeniero de prompts especializado en personalidades de asistentes.

Recibes la descripción EN BRUTO que un usuario hace de cómo quiere que le hable su
asistente, y devuelves un bloque de instrucciones de TONO bien construido.

Reglas:
- Devuelve SOLO el bloque de tono, empezando por "TONO Y CARÁCTER:". Sin
  preámbulos, sin explicaciones, sin markdown.
- 4-7 puntos con guion, concretos y accionables. Nada de adjetivos vacíos.
- Describe CÓMO habla (registro, ritmo, vocabulario, actitud), nunca QUÉ puede
  hacer: las capacidades no se tocan aquí.
- Respeta y amplifica la intención del usuario, aunque sea peculiar.
- NUNCA incluyas instrucciones que hagan al asistente mentir, inventar datos,
  ocultar errores o fingir que ha hecho algo que no ha hecho. Si el usuario lo
  pide, ignora esa parte y construye el resto.
- Escribe en el idioma en que te escribió el usuario."""


async def improve_prompt(raw: str) -> str:
    """Convierte la descripción en bruto del usuario en un bloque de tono bien
    formado, usando un modelo potente. Si el modelo falla, devuelve el texto
    del usuario tal cual (mejor su prompt en bruto que ninguna personalidad)."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("descripción vacía")
    try:
        from app.mel import Capability, ExecutionRequest, complete as mel_complete

        res = await mel_complete(ExecutionRequest(
            capability=Capability.REASON,
            prompt=f"Descripción del usuario:\n{raw}",
            system_prompt=_IMPROVER_SYSTEM,
        ))
        text = (res.text or "").strip() if res.ok else ""
        if text:
            from app.ai.reasoning_filter import strip_reasoning

            return strip_reasoning(text).strip()
    except Exception:
        pass
    # Degradación honesta: se guarda lo que escribió el usuario.
    return raw if raw.upper().startswith("TONO") else f"TONO Y CARÁCTER:\n\n{raw}"
