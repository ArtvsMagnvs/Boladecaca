# app/mel/policies.py — políticas + compilador (doc 19 §4-6, E1)
#
# Una política = {capacidad → cadena ordenada [primario, respaldo₁…ₙ]}. El
# compilador las genera desde los modelos disponibles + el catálogo de scores; se
# persisten como JSON versionado en `mel_policies`. El Rule Engine (decision.py)
# consume la cadena ya compilada — la compilación es OFFLINE, la decisión es O(1).
#
# Dos capas separadas (testabilidad):
#   - `_compile_*` — funciones PURAS (lista de ModelRef + catálogo → cadenas).
#   - `PolicyStore` — la persistencia (DB) + la política activa.
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.logging_config import get_system_logger
from app.mel.capabilities import is_smart
from app.mel.catalog import cost_of, score_of
from app.mel.contracts import Capability, ModelRef, PolicyName

logger = get_system_logger("mel.policies")

# Umbral mínimo de calidad para que Economy considere un modelo "aceptable"
# (doc 19 §4). Por debajo, no entra en la cadena de Economy salvo como último
# recurso local.
_ECONOMY_MIN_SCORE = 55
# Longitud máxima de cadena (primario + respaldos) — doc 19 §5.2 "longitud 2-4".
_MAX_CHAIN = 4


def _order_quality(available: list[ModelRef], cap: Capability) -> list[ModelRef]:
    """Orden puro por score de la capacidad; el coste solo desempata (más barato
    primero a igualdad). Termina en el mejor local (respaldo offline)."""
    return sorted(available, key=lambda r: (-score_of(r, cap), cost_of(r), r.key))


def _order_economy(available: list[ModelRef], cap: Capability) -> list[ModelRef]:
    """Más barato cuyo score ≥ umbral; locales primero a igualdad de coste. Los
    que no llegan al umbral van al final (nunca se quedan sin cadena)."""
    aceptables = [r for r in available if score_of(r, cap) >= _ECONOMY_MIN_SCORE]
    resto = [r for r in available if score_of(r, cap) < _ECONOMY_MIN_SCORE]
    key = lambda r: (cost_of(r), 0 if r.is_local else 1, -score_of(r, cap), r.key)
    return sorted(aceptables, key=key) + sorted(resto, key=key)


def _compile_policy(name: PolicyName, available: list[ModelRef]) -> dict[str, list[str]]:
    """Compila UNA política → {capability_value: [model_key, ...]}. Nunca produce
    cadenas vacías si hay ≥1 modelo (con 1 solo proveedor, cadenas de 1 — válido
    y explícito, doc 19 §5.2)."""
    compiled: dict[str, list[str]] = {}
    for cap in Capability:
        if name == PolicyName.OFFLINE:
            pool = [r for r in available if r.is_local]
        else:
            pool = list(available)

        if not pool:
            compiled[cap.value] = []   # Offline sin local → degradada en esta capacidad
            continue

        if name == PolicyName.ECONOMY:
            ordered = _order_economy(pool, cap)
        else:  # QUALITY y OFFLINE ordenan por calidad
            ordered = _order_quality(pool, cap)

        # Economy/Quality terminan SIEMPRE en el mejor local disponible como red
        # de seguridad (doc 19 §4), si no está ya en los primeros puestos.
        if name != PolicyName.OFFLINE:
            best_local = next((r for r in _order_quality(available, cap) if r.is_local), None)
            chain = ordered[:_MAX_CHAIN]
            if best_local and best_local.key not in [r.key for r in chain]:
                chain = chain[:_MAX_CHAIN - 1] + [best_local]
        else:
            chain = ordered[:_MAX_CHAIN]

        compiled[cap.value] = [r.key for r in chain]
    return compiled


def compile_all(available: list[ModelRef]) -> dict[str, dict[str, list[str]]]:
    """Compila las 3 políticas automáticas. Pura (no toca la DB)."""
    return {
        PolicyName.ECONOMY.value: _compile_policy(PolicyName.ECONOMY, available),
        PolicyName.QUALITY.value: _compile_policy(PolicyName.QUALITY, available),
        PolicyName.OFFLINE.value: _compile_policy(PolicyName.OFFLINE, available),
    }


def default_active(available: list[ModelRef]) -> str:
    """Economy si hay ≥1 local sano, si no Quality (doc 19 §5.2)."""
    return PolicyName.ECONOMY.value if any(r.is_local for r in available) else PolicyName.QUALITY.value


# ---------------------------------------------------------------------------
# Persistencia + política activa
# ---------------------------------------------------------------------------
class PolicyStore:
    """Lee/escribe `mel_policies`. `ensure_compiled()` compila+persiste si no hay
    nada (primer arranque / wizard); `active_chain(capability)` devuelve la cadena
    de la política activa como lista de model_key. Best-effort en lectura: si la
    DB falla, cae a compilar en memoria (el MEL nunca se queda sin política)."""

    def ensure_compiled(self, available: list[ModelRef]) -> None:
        """Idempotente: si ya hay políticas persistidas, no hace nada. Si no,
        compila las 3 y marca la activa por defecto. Lo llama el wizard (O5) y,
        de forma defensiva, el executor la primera vez."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        db = SessionLocal()
        try:
            if db.query(MelPolicy).count() > 0:
                return
            compiled = compile_all(available)
            active = default_active(available)
            now = datetime.utcnow()
            for name, chains in compiled.items():
                db.add(MelPolicy(
                    name=name, version=1, compiled=chains, pristine=True,
                    is_active=(name == active), created_at=now, updated_at=now,
                ))
            db.commit()
            logger.info(f"[policies] compiladas 3 políticas; activa por defecto: {active}")
        except Exception as e:
            logger.error(f"[policies] ensure_compiled falló (no crítico): {type(e).__name__}: {e}")
            db.rollback()
        finally:
            db.close()

    def active_name(self) -> Optional[str]:
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.is_active.is_(True)).first()
            return row.name if row else None
        except Exception:
            return None
        finally:
            db.close()

    def active_chain(self, capability: Capability, available: list[ModelRef]) -> list[ModelRef]:
        """La cadena (lista de ModelRef reales y disponibles) de la política activa
        para una capacidad. Si no hay política persistida o la DB falla, compila la
        política por defecto EN MEMORIA — el MEL nunca se queda sin decidir."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        by_key = {r.key: r for r in available}
        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.is_active.is_(True)).first()
            if row and row.compiled:
                keys = row.compiled.get(capability.value, [])
                chain = [by_key[k] for k in keys if k in by_key]
                if chain:
                    return chain
        except Exception as e:
            logger.error(f"[policies] active_chain falló, compilo en memoria: {type(e).__name__}: {e}")
        finally:
            db.close()

        # Fallback: compila la política por defecto en memoria.
        name = default_active(available)
        chains = _compile_policy(PolicyName(name), available)
        return [by_key[k] for k in chains.get(capability.value, []) if k in by_key]

    def set_active(self, name: str) -> bool:
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        db = SessionLocal()
        try:
            if db.query(MelPolicy).filter(MelPolicy.name == name).count() == 0:
                return False
            db.query(MelPolicy).update({MelPolicy.is_active: False})
            db.query(MelPolicy).filter(MelPolicy.name == name).update({MelPolicy.is_active: True})
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    def list_policies(self) -> list[dict]:
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        db = SessionLocal()
        try:
            rows = db.query(MelPolicy).all()
            return [{"name": r.name, "version": r.version, "compiled": r.compiled,
                     "pristine": r.pristine, "is_active": r.is_active} for r in rows]
        except Exception:
            return []
        finally:
            db.close()


policy_store = PolicyStore()
