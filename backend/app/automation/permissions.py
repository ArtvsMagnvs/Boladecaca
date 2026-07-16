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
    # --- Futuros: la tool todavía no existe, el permiso ya sí (doc 20 A3b) ---
    PermissionDef(
        id="browser.use", label="Usar el navegador web",
        description="Navegar por internet en tu nombre (buscar, rellenar formularios).",
        group="Próximamente", risk="medium", available=False,
    ),
    PermissionDef(
        id="computer.use", label="Controlar el ordenador",
        description="Manejar tu ordenador directamente (clics, teclado).",
        group="Próximamente", risk="high", available=False,
    ),
]

_BY_ID: dict[str, PermissionDef] = {p.id: p for p in CATALOG}

# Perfiles rápidos (el equivalente a "omitir permisos" de Claude). `manual` es
# el default seguro — todo apagado, Aithera pregunta siempre. `full` NO
# incluye los `available=False` (no hay nada que autorizar de una tool que
# no existe todavía).
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
