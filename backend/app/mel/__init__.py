# backend/app/mel/__init__.py — API PÚBLICA del MEL (Model Execution Layer)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.mel` — nunca de los internos
# (contracts/registry/decision/policies/fallback/executor/catalog/capabilities/
# models). La frontera la vigila tests/test_module_boundaries.py. En particular,
# NADIE fuera de `app.mel` importa `ai_manager` ni providers: solo `registry.py`
# lo hace (doc 19 §1.2).
#
# V1.0 E1: contratos congelados + registry (envuelve ai_manager) + Rule Engine +
# fallback/breakers + compilador de políticas. El resto del sistema NO llama
# todavía al MEL (el switch de `tie/router.py` y los ~9 call-sites es E2).
# V1.0 E1b: capacidad RESEARCH activada — Catálogo Auto-Investigado (doc 19 §5.4).
from __future__ import annotations

from typing import Optional

# --- Contratos congelados (E1) ---
from app.mel.contracts import (
    Capability,
    PolicyName,
    ModelRef,
    Constraints,
    ExecutionRequest,
    ExecutionResult,
    ServedBy,
    Usage,
    DecisionTrace,
)

# --- Internos (para exponer funciones públicas; no se re-exportan los módulos) ---
from app.mel import executor as _executor
from app.mel import decision as _decision
from app.mel import registry as _registry
from app.mel import research as _research
from app.mel import overrides as _overrides
from app.mel.policies import policy_store as _policy_store


# ---------------------------------------------------------------------------
# API pública (doc 19 §1.2 / §2)
# ---------------------------------------------------------------------------
async def complete(req: ExecutionRequest) -> ExecutionResult:
    """Ejecuta una petición de capacidad y devuelve el resultado. El caller pide
    QUÉ (capability), el MEL decide CON QUÉ MODELO. Nunca lanza."""
    return await _executor.complete(req)


def stream(req: ExecutionRequest):
    """Igual que complete pero streaming (AsyncIterator[str] de texto ya filtrado)."""
    return _executor.stream(req)


def vision_available() -> bool:
    """[B·WEB-2, doc 32] ¿Hay AHORA MISMO algún modelo capaz de mirar una imagen?

    Existe para que una tool pueda decirlo ANTES de intentarlo (su `preflight()`,
    patrón de la Sesión A del doc 40) en vez de gastar una llamada al LLM para
    descubrirlo. Consulta el mismo punto único de aptitud que usan las políticas
    (`is_capable` → `supports_vision`), así que no puede desalinearse con lo que
    de verdad ejecutaría el MEL.

    Fail-closed: si algo falla al consultarlo, False. Decir "no puedo ver" de más
    solo cuesta una funcionalidad; decirlo de menos acaba en coordenadas
    inventadas."""
    try:
        from app.mel.policies import is_capable

        return any(is_capable(ref, Capability.VISION) for ref in _registry.list_available())
    except Exception:
        return False


def decision_trace(decision_id: str) -> Optional[DecisionTrace]:
    """La traza de una decisión reciente (por qué se eligió ese modelo)."""
    return _decision.get_trace(decision_id)


def recent_decisions(limit: int = 50) -> list[DecisionTrace]:
    """Las decisiones más recientes (observabilidad — pantalla Actividad, v2)."""
    return _decision.recent_traces(limit)


def policies() -> list[dict]:
    """Las políticas compiladas (Economy/Quality/Offline) con su estado."""
    return _policy_store.list_policies()


def active_policy_name() -> Optional[str]:
    """Nombre de la política activa (o None si no hay ninguna fijada todavía).
    Lo usa `aithera_tool` para saber sobre qué política editar el modelo del chat
    sin importar internos del MEL (disciplina modular, doc 16)."""
    return _policy_store.active_name()


def set_active_policy(name: str) -> bool:
    """Cambia la política activa (Settings → Inteligencia). True si existía."""
    return _policy_store.set_active(name)


def is_cli_agent_model(model_key: Optional[str]) -> bool:
    """[2026-08-04] ¿Ese `provider:model` es un AGENTE CLI autosuficiente
    (Claude Code, Codex)?

    Lo consulta `agent_manager` para decidir el camino de ejecución: a un agente
    CLI se le delega la tarea ENTERA en la carpeta del proyecto (trae sus
    propias herramientas), en vez de meterlo en el bucle de tools de Aithera —
    que es un agente dentro de otro agente y era la causa real de que "no
    sirvieran". Vive aquí (API pública) para que `app.agents` no tenga que
    importar internos del MEL (doc 16)."""
    from app.mel.catalog import is_cli_agent

    if not model_key:
        return False
    return is_cli_agent(model_key.split(":", 1)[0])


def list_models() -> list[dict]:
    """Los (proveedor, modelo) realmente configurados, para que la UI pueble los
    selectores de la personalización. `key` es el `provider:model` que usan las
    cadenas de política (petición del usuario, 2026-07-18)."""
    from app.ai.catalog import get_provider_info
    from app.mel.catalog import (
        supports_learn as _supports_learn,
        supports_vision as _supports_vision,
        unfit_for,
    )
    from app.mel import benchmark as _benchmark
    out = []
    for ref in _registry.list_available():
        info = get_provider_info(ref.provider)
        label = info.get("label", ref.provider)
        # [2026-08-02, petición del usuario] Nombre COMPLETO del modelo, no
        # abreviado — el catálogo curado ya lo tiene ("MiniMax M2.7 highspeed
        # (rápido)", "Fable 5 (el más capaz)"...). Para modelos sin entrada en
        # el catálogo (típicamente los locales de Ollama: "llama3",
        # "qwen3:8b"...) se usa el propio nombre tal cual — ya es "completo",
        # solo no tiene un alias comercial que traducir.
        model_label = info.get("model_labels", {}).get(ref.model, ref.model)
        # [2026-07-21] capacidades para las que NO es apto (la UI lo excluye/
        # marca; p.ej. Claude CLI en chat/classify). [2026-07-22] Se suma la
        # no-aptitud MEDIDA por el task-bench: un modelo con fallo real medido
        # no es asignable a esa tarea NI SIQUIERA en Personalizado.
        # [2026-08-04] Las dos fuentes se exponen POR SEPARADO además de la
        # unión. Motivo real: la UI borraba en silencio todo lo no-apto y el
        # usuario preguntó tres veces "¿por qué solo salen los de MiniMax?".
        # Sin saber si la exclusión viene del CATÁLOGO (decisión de diseño,
        # p.ej. los CLI de Claude/Codex) o de una MEDICIÓN (el task-bench vio
        # fallar ese modelo de verdad), la UI solo puede decir "no está" — que
        # es justo lo que no sirve. `unfit` (la unión) se conserva intacto
        # porque Ajustes → Inteligencia ya lo consume.
        catalog_unfit = {c.value for c in unfit_for(ref.provider)}
        # [B·WEB-2, 2026-08-05] La VISIÓN no se decide por proveedor sino por
        # (proveedor, modelo) —`gemini` ve, `ollama` solo con un modelo VL—, así
        # que `unfit_for()` no puede saberlo y hay que sumarla aquí.
        #
        # EL FALLO QUE CIERRA: sin esto, el selector de Inteligencia OFRECÍA
        # modelos ciegos para la capacidad de visión y, al elegir uno,
        # `set_primary` lo rechazaba por dentro (usa `is_capable`) — el usuario
        # veía que su elección "no se guardaba" sin ninguna explicación. La UI y
        # la ejecución tienen que compartir el MISMO criterio de aptitud.
        if not _supports_vision(ref.provider, ref.model):
            catalog_unfit.add(Capability.VISION.value)
        # [LC1, 2026-08-07] Y el APRENDIZAJE, por el mismo motivo y con el mismo
        # riesgo: se decide por (proveedor, modelo) —un llama3 pequeño no sirve
        # de juez, un deepseek-r1 sí—, así que `unfit_for()` tampoco puede
        # saberlo. Sin esta línea, Inteligencia ofrecería modelos que
        # `set_primary` rechazaría por dentro: la UI y la ejecución tienen que
        # compartir el MISMO criterio de aptitud (el invariante que lo vigila
        # vive en tests/test_lc1_juez.py).
        if not _supports_learn(ref.provider, ref.model):
            catalog_unfit.add(Capability.LEARN.value)
        measured_unfit = set(_benchmark.measured_unfit(ref))
        out.append({"key": ref.key, "provider": ref.provider, "model": ref.model,
                    "is_local": ref.is_local, "label": label, "model_label": model_label,
                    "unfit": sorted(catalog_unfit | measured_unfit),
                    "unfit_catalog": sorted(catalog_unfit),
                    "unfit_measured": sorted(measured_unfit)})
    return out


def set_policy_primary(name: str, capability: str, model_key: Optional[str]) -> bool:
    """Fija el modelo primario de una capacidad en una política (None = auto).
    Marca la política como editada. La usa Settings → Inteligencia."""
    return _policy_store.set_primary(name, capability, model_key, _registry.list_available())


def set_policy_slot(name: str, capability: str, position: int, model_key: str) -> bool:
    """[2026-07-21] Edita UNA posición de la cadena (0-3). La última posición
    solo admite modelos locales (red de seguridad offline). Settings→Inteligencia."""
    return _policy_store.set_slot(name, capability, position, model_key, _registry.list_available())


def health_summary() -> dict:
    """[2026-07-21] ¿Está Aithera trabajando EXCLUSIVAMENTE con modelos locales
    porque la nube configurada está caída? Alimenta el banner naranja del
    frontend. `local_only` = hay ≥1 proveedor de nube configurado, TODOS tienen
    su circuit breaker abierto (fallos reales recientes), y hay local con el que
    seguir trabajando. Elegir una política todo-local a propósito NO activa el
    aviso (eso es una decisión, no una avería)."""
    from app.mel.fallback import breakers

    refs = _registry.list_available()
    cloud = sorted({r.provider for r in refs if not r.is_local})
    has_local = any(r.is_local for r in refs)
    down = sorted([p for p in cloud if not breakers.is_closed(p)])
    local_only = bool(cloud) and len(down) == len(cloud) and has_local
    # [2026-07-21] Motivo por proveedor caído (para el panel de fallos de
    # Inteligencia: "MiniMax fallando: red/timeout").
    down_detail = {p: (breakers.open_reason(p) or "unknown") for p in down}
    return {
        "local_only": local_only,
        "cloud_providers": cloud,
        "providers_down": down,
        "down_detail": down_detail,
        "has_local": has_local,
    }


def restore_policy(name: str) -> bool:
    """Devuelve una política a sus valores por defecto (botón Restaurar)."""
    return _policy_store.restore(name, _registry.list_available())


# --- Override explícito por proyecto (E2b, doc 19 §7b) ---
def set_project_override(project_id: int, model_id: str, capability: Optional[str] = None) -> bool:
    """Pina un modelo para TODO un proyecto ("a partir de ahora todo con Claude").
    `capability=None` = todas. Lo llama el TIE al confirmar alcance "proyecto"."""
    return _overrides.set_project_override(project_id, model_id, capability)


def overrides_for(project_id: int) -> list[dict]:
    """Los pines de modelo de un proyecto (para la UI / consulta)."""
    return _overrides.overrides_for(project_id)


def list_overrides() -> list[dict]:
    """Todos los pines activos (panel global de Inteligencia, borrables)."""
    return _overrides.list_all()


def clear_override(override_id: int) -> bool:
    """Borra un pin por id (botón borrar). True si existía."""
    return _overrides.clear_override(override_id)


def resolve_model_name(text: str) -> Optional[ModelRef]:
    """Resuelve un nombre coloquial de modelo al (provider, model) configurado, o
    None. La usa el TIE (E2b) para el override explícito del usuario (doc 19 §7b.2)."""
    return _registry.resolve_model_name(text)


def ensure_ready() -> None:
    """Compila las políticas si no existen (idempotente). Lo llama el wizard (O5)
    o, de forma defensiva, cualquier `complete()`. Seguro llamarlo en el lifespan."""
    _policy_store.ensure_compiled(_registry.list_available())


def register_handlers() -> None:
    """[E1b] Cablea el MEL con el bus de eventos: suscribe la investigación
    automática a `provider.model_configured` (doc 19 §5.4.1). Idempotente. Lo
    llama el lifespan, mismo patrón que `tie.register_handlers()`.
    [2026-07-22] También el auto-BENCHMARK: al conectar un modelo se le mide
    (latencia real + calidad verificable) sin que el usuario haga nada."""
    _research.register()
    from app.mel import benchmark as _benchmark
    _benchmark.register()


def benchmark_summary() -> list[dict]:
    """[2026-07-22] Las mediciones reales por modelo (velocidad/calidad) — para
    la UI de Inteligencia y diagnóstico."""
    from app.mel import benchmark as _benchmark
    return _benchmark.summary()


async def benchmark_missing() -> int:
    """[2026-07-22] Mide los modelos SIN medición (catch-up de arranque; lo
    programa el lifespan). Los nuevos se miden solos vía register_handlers."""
    from app.mel import benchmark as _benchmark
    return await _benchmark.benchmark_missing()


def capability_report() -> list[dict]:
    """El informe auto-investigado por modelo conectado (doc 19 §5.4.3) — el
    "documento interno" consultable. `GET /api/mel/capability-report` lo expone."""
    return _research.report_summary()


async def refresh_capability_reports() -> int:
    """[E1b + P4 doc 34] El job NOCTURNO del auto-catálogo — como mucho
    `MEL_RESEARCH_MAX_PER_NIGHT` modelos por pasada, nunca proveedores por CLI,
    solo si de verdad tocaba (`MEL_RESEARCH_REFRESH_DAYS`). Lo programa el
    lifespan vía `scheduler_service.add_cron_job`, junto a los jobs nocturnos
    del MOS — antes era un `add_interval_job` disparado a los 900s del
    arranque, que podía coincidir con el usuario ya trabajando (doc 34 §4)."""
    return await _research.nightly_refresh()


async def refresh_capability_reports_full() -> int:
    """[P4 doc 34] Variante COMPLETA (todos los modelos, de golpe, `force=True`)
    para un disparo manual puntual — no la usa el scheduler. Ver
    `research.refresh_all()`."""
    return await _research.refresh_all()


__all__ = [
    # contratos
    "Capability", "PolicyName", "ModelRef", "Constraints",
    "ExecutionRequest", "ExecutionResult", "ServedBy", "Usage", "DecisionTrace",
    # API pública
    "complete", "stream", "decision_trace", "recent_decisions",
    "policies", "set_active_policy", "active_policy_name", "resolve_model_name", "ensure_ready",
    "register_handlers", "capability_report", "refresh_capability_reports",
    "refresh_capability_reports_full",
    "list_models", "set_policy_primary", "restore_policy",
    "set_project_override", "overrides_for", "list_overrides", "clear_override",
    "set_policy_slot", "health_summary",
    "benchmark_summary", "benchmark_missing",
    "vision_available",
]
