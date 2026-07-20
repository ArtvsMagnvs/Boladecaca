# app/automation/permissions.py — Permisos & Autonomía (V0.9 A3b, doc 20 §A3b)
#
# La capa de POLÍTICA sobre el ApprovalGate (A1). El gate es el mecanismo HITL
# en tiempo de ejecución; este módulo decide, para cada capacidad sensible, si
# el usuario ya la pre-autorizó (pasa directa) o si debe seguir abriendo el
# gate (pregunta siempre). Petición explícita del usuario (2026-07-16).
#
# Catálogo DECLARATIVO (no una tabla — pocos permisos, cambian con el código,
# no con datos de usuario; mismo criterio que `rules_builtin.py`). El ESTADO
# (on/off por permiso + perfil activo) sí es dato de usuario → tabla `Config`
# key-value existente (mismo patrón que `telegram.py`), sin migración nueva.
#
# Regla de oro (nunca romperla): pre-autorizado NUNCA significa "en silencio".
# `ApprovalGate.request_approval` (ver approval.py) sigue dejando una fila en
# `approvals` con `resolution_note="auto (permiso pre-autorizado)"` — hay
# rastro de auditoría incluso en modo autónomo.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

_PREFIX = "permission."
_PROFILE_KEY = "autonomy_profile"
DEFAULT_PROFILE = "manual"


@dataclass(frozen=True)
class PermissionDef:
    """Una capacidad sensible gobernable. `id` en notación con puntos — mismo
    criterio que los nombres de evento (doc 17 §3.1), para que sea legible y
    grepable. `available=False` = la tool/capacidad aún no existe en Aithera
    (browser/computer use); aparece en el catálogo YA para que la UI la
    muestre como "próximamente" y no haga falta tocar el frontend cuando
    llegue — solo cambiar este flag."""
    id: str
    label: str          # humano, sin tecnicismos — lo que ve el usuario
    description: str
    group: str           # agrupación en la UI
    risk: str             # "low" | "medium" | "high" — para los perfiles
    available: bool = True


# El catálogo completo hasta donde el proyecto puede ver hoy (V0.9) + V1.x.
CATALOG: list[PermissionDef] = [
    PermissionDef(
        id="email.send", label="Enviar correos",
        description="Enviar o responder emails en tu nombre sin que lo confirmes antes.",
        group="Comunicación", risk="medium",
    ),
    PermissionDef(
        id="telegram.send", label="Enviar mensajes de Telegram",
        description="Mandarte avisos y resúmenes por Telegram sin preguntar cada vez.",
        group="Comunicación", risk="low",
    ),
    PermissionDef(
        id="workspace.write", label="Crear y modificar tareas",
        description="Crear, cerrar o mover tareas y milestones del Workspace.",
        group="Workspace", risk="low",
    ),
    PermissionDef(
        id="agent.execute", label="Ejecutar agentes",
        description="Lanzar tareas sobre tus agentes sin pedir permiso cada vez.",
        group="Agentes", risk="medium",
    ),
    PermissionDef(
        id="shell.run", label="Ejecutar comandos del sistema",
        description="Correr comandos de terminal en tu ordenador.",
        group="Sistema", risk="high",
    ),
    PermissionDef(
        id="filesystem.write", label="Modificar archivos",
        description="Crear, editar o borrar archivos en tu ordenador.",
        group="Sistema", risk="high",
    ),
    PermissionDef(
        id="git.write", label="Hacer cambios en git",
        description="Hacer commits o modificar el repositorio de tus proyectos.",
        group="Sistema", risk="high",
    ),
    # [Δ 2026-07-18] activadas: Browser Tool y Desktop Tool ya existen
    # (app/tools/browser_tool.py, app/tools/desktop_tool.py) — se cambia
    # SOLO el flag `available`, tal como el comentario de PermissionDef ya
    # anticipaba. Grupo real, ya no "Próximamente".
    PermissionDef(
        id="browser.use", label="Usar el navegador web",
        description="Navegar por internet en tu nombre (buscar, rellenar formularios).",
        group="Sistema", risk="medium", available=True,
    ),
    PermissionDef(
        id="computer.use", label="Controlar el ordenador",
        description="Manejar tu ordenador directamente (clics, teclado).",
        group="Sistema", risk="high", available=True,
    ),
    # [Auditoría v0.9.5, D-1] Los gates del TIE eran "kinds fantasma": tie.plan,
    # tie.node y tie.checkpoint no existían en este catálogo, así que el perfil
    # "Autónomo" con TODO activado seguía preguntando por cada plan y cada
    # entregable (los 5-6 permisos del fallo D). Entran al catálogo como
    # capacidades de MISIÓN gobernables — la regla de oro de A3b se mantiene:
    # pre-autorizado nunca es silencioso, el gate se auto-resuelve CON rastro.
    PermissionDef(
        id="tie.plan_approval", label="Ejecutar planes sin confirmación",
        description="Ejecutar los planes de una misión (incluidos sus pasos sensibles) "
                    "sin pedirte el visto bueno previo. Cada acción sigue gobernada "
                    "por su propio permiso de esta lista.",
        group="Misiones", risk="high",
    ),
    PermissionDef(
        id="tie.checkpoint", label="Continuar tras cada entregable",
        description="Seguir con la misión después de cada entregable sin preguntarte "
                    "«¿sigo con el resto?». Los entregables quedan igualmente visibles "
                    "en la vista de Misiones.",
        group="Misiones", risk="low",
    ),
]

_BY_ID: dict[str, PermissionDef] = {p.id: p for p in CATALOG}

# Perfiles rápidos (el equivalente a "omitir permisos" de Claude). `manual` es
# el default seguro — todo apagado, Aithera pregunta siempre. `full` NO
# incluye los `available=False` (no hay nada que autorizar de una tool que no
# existe todavía) — hoy [Δ 2026-07-18] el catálogo no tiene ninguna entrada
# `available=False` (browser.use/computer.use ya se activaron), pero la regla
# se deja intacta para el próximo permiso que se reserve así.
PROFILES: dict[str, frozenset[str]] = {
    "manual": frozenset(),
    "balanced": frozenset(p.id for p in CATALOG if p.available and p.risk == "low"),
    "full": frozenset(p.id for p in CATALOG if p.available),
}


@dataclass
class PermissionState:
    id: str
    label: str
    description: str
    group: str
    risk: str
    available: bool
    enabled: bool


@dataclass
class PermissionCatalog:
    permissions: list[PermissionState] = field(default_factory=list)
    profile: str = DEFAULT_PROFILE


# ---------------------------------------------------------------------------
# Persistencia — tabla Config existente, mismo patrón que telegram.py
# ---------------------------------------------------------------------------
def _config_get(db, key: str) -> Optional[str]:
    from app.db.models import Config

    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else None


def _config_set(db, key: str, value: str) -> None:
    from app.db.models import Config

    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


# ---------------------------------------------------------------------------
# Acciones de tool → permiso del catálogo (Fix 2026-07-19)
# ---------------------------------------------------------------------------
# EL BUG QUE CIERRA: el bucle de tool-use (R1) pide permiso con
# `kind="tool.<tool_id>.<action>"` (p.ej. `tool.email.send_email`), pero el
# catálogo usa ids de CAPACIDAD (`email.send`). Nunca casaban, y como
# `is_pre_authorized` es fail-closed, el resultado era que el modo "Autónomo"
# —con los 9 permisos activados— NO tenía ningún efecto sobre las acciones que
# pedía el bucle: preguntaba SIEMPRE, hasta para enviar un email que el propio
# usuario acababa de pedir por el chat.
#
# Este mapa es la traducción que faltaba. Se declara por TOOL (todas sus
# acciones sensibles caen bajo el mismo permiso) y, cuando hace falta afinar,
# por (tool, acción) concreta.
_TOOL_PERMISSION: dict[str, str] = {
    "email": "email.send",
    "browser": "browser.use",
    "desktop": "computer.use",
    "shell": "shell.run",
    "powershell": "shell.run",
    "filesystem": "filesystem.write",
    "git": "git.write",
    "aithera": "workspace.write",
    "telegram": "telegram.send",
}

# Excepciones por acción concreta, cuando una tool cubre dos capacidades
# distintas. `aithera.run_agent_task` lanza un agente: eso es `agent.execute`,
# no `workspace.write` — permitir crear tareas no debería implicar poder
# ejecutar agentes.
_ACTION_PERMISSION: dict[str, str] = {
    "aithera.run_agent_task": "agent.execute",
}


def permission_for_tool_action(tool_id: str, action: str) -> Optional[str]:
    """El permiso del catálogo que gobierna una acción de tool, o None si esa
    acción no está cubierta por ninguno (→ se pregunta siempre, fail-closed)."""
    if not tool_id:
        return None
    return _ACTION_PERMISSION.get(f"{tool_id}.{action}") or _TOOL_PERMISSION.get(tool_id)


# ---------------------------------------------------------------------------
# Kinds de gate → permiso del catálogo (Auditoría v0.9.5, D-1)
# ---------------------------------------------------------------------------
# La segunda mitad del fix del 2026-07-19: aquel mapa tradujo las ACCIONES DE
# TOOL (`tool.<id>.<action>`), pero los gates del propio TIE quedaron fuera.
# Este mapa los cubre. `tie.node` cae bajo el paraguas de `tie.plan_approval`
# a propósito: un gate de nodo ES un paso de un plan — quien autoriza ejecutar
# planes autoriza sus pasos (misma decisión de diseño que T4a: aprobar el plan
# autoriza sus nodos sensibles).
_GATE_KIND_PERMISSION: dict[str, str] = {
    "tie.plan": "tie.plan_approval",
    "tie.node": "tie.plan_approval",
    "tie.checkpoint": "tie.checkpoint",
}


def is_kind_pre_authorized(kind: str) -> bool:
    """La consulta ÚNICA que hace `ApprovalGate.request_approval` (approval.py).
    Resuelve en orden: (1) el kind ES un permiso del catálogo (p. ej.
    `email.send`, el caso de A3b); (2) el kind es un gate del TIE con
    traducción declarada. Fail-closed en todo lo demás — un kind nuevo sin
    entrada aquí pregunta SIEMPRE, que es el default seguro."""
    if is_pre_authorized(kind):
        return True
    traducido = _GATE_KIND_PERMISSION.get(kind)
    return bool(traducido) and is_pre_authorized(traducido)


def is_tool_action_pre_authorized(tool_id: str, action: str) -> bool:
    """¿El usuario ya autorizó de antemano esta acción de tool? Traduce al id
    del catálogo y consulta el estado real. Fail-closed: sin traducción, no."""
    permiso = permission_for_tool_action(tool_id, action)
    return bool(permiso) and is_pre_authorized(permiso)


# ---------------------------------------------------------------------------
# API pública del módulo (namespace-módulo, patrón workspace_service/decision_service)
# ---------------------------------------------------------------------------
def is_pre_authorized(permission_id: str) -> bool:
    """Fail-CLOSED: un id que no existe en el catálogo, o sin fila en Config
    todavía, NUNCA se trata como pre-autorizado — el gate pregunta, que es el
    comportamiento seguro por defecto. Es la función que consulta
    `ApprovalGate.request_approval` (approval.py, sin import a nivel de
    módulo — evita el ciclo approval<->permissions)."""
    perm = _BY_ID.get(permission_id)
    if perm is None or not perm.available:
        return False
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        return _config_get(db, _PREFIX + permission_id) == "on"
    finally:
        db.close()


def set_permission(permission_id: str, enabled: bool) -> None:
    """Activa/desactiva UN permiso. Lanza ValueError si el id no existe o si
    la tool todavía no está disponible (nada que autorizar de verdad)."""
    perm = _BY_ID.get(permission_id)
    if perm is None:
        raise ValueError(f"permiso desconocido: {permission_id!r}")
    if not perm.available:
        raise ValueError(f"permiso {permission_id!r} no disponible todavía (próximamente)")
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        _config_set(db, _PREFIX + permission_id, "on" if enabled else "off")
        db.commit()
    finally:
        db.close()


def apply_profile(profile: str) -> None:
    """Aplica un perfil rápido: setea TODOS los permisos disponibles según el
    perfil (los no disponibles se quedan tal cual, no hay nada que tocar) y
    recuerda el perfil activo. Lanza ValueError si el perfil no existe."""
    if profile not in PROFILES:
        raise ValueError(f"perfil desconocido: {profile!r} (usa: {', '.join(PROFILES)})")
    from app.db.database import SessionLocal

    enabled_ids = PROFILES[profile]
    db = SessionLocal()
    try:
        for perm in CATALOG:
            if not perm.available:
                continue
            _config_set(db, _PREFIX + perm.id, "on" if perm.id in enabled_ids else "off")
        _config_set(db, _PROFILE_KEY, profile)
        db.commit()
    finally:
        db.close()


def get_catalog() -> PermissionCatalog:
    """El catálogo completo + el estado actual de cada permiso + el perfil
    activo — lo que consume la UI de Ajustes → Permisos de una sola llamada."""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        states = [
            PermissionState(
                id=p.id, label=p.label, description=p.description,
                group=p.group, risk=p.risk, available=p.available,
                enabled=(_config_get(db, _PREFIX + p.id) == "on") if p.available else False,
            )
            for p in CATALOG
        ]
        profile = _config_get(db, _PROFILE_KEY) or DEFAULT_PROFILE
    finally:
        db.close()
    return PermissionCatalog(permissions=states, profile=profile)
