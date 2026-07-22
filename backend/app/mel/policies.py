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
from app.mel.catalog import cost_of, unfit_for
# [E1b, doc 19 §5.4.3] el compilador usa el score EFECTIVO (catálogo curado
# desplazado por el auto-catálogo investigado), no el catálogo puro — research.py
# hace de wrapper de catalog.score_of() y no importa policies.py (sin ciclo).
from app.mel.research import effective_score as score_of
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


# ---------------------------------------------------------------------------
# [2026-07-22, petición del usuario] Políticas MEDIDAS: SPEED y BALANCED usan
# los números reales de mel/benchmark.py (latencia medida en ESTA máquina +
# calidad verificable por sondas), no solo el conocimiento del catálogo.
# ---------------------------------------------------------------------------
# Suelo de calidad medida para SPEED: por debajo, un modelo rápido pero que no
# obedece instrucciones/JSON hace perder MÁS tiempo del que ahorra (reintentos
# del toolloop). Se aplica solo si hay medición; sin medición se confía en el
# score del catálogo (mismo umbral que Economy).
_SPEED_MIN_QUALITY = 34   # ≥1 de las 3 sondas verificables superadas


def _bench(r: ModelRef) -> Optional[dict]:
    """Medición de benchmark del modelo, o None. Import diferido para no crear
    ciclo (benchmark importa registry, no policies)."""
    from app.mel import benchmark
    return benchmark.measured(r)


def _order_speed(available: list[ModelRef], cap: Capability) -> list[ModelRef]:
    """El más RÁPIDO medido primero. Un modelo medido como muerto (ok=False —
    p.ej. un id que la API rechaza con 400) queda EXCLUIDO del pool principal;
    los rápidos-pero-torpes (calidad medida < suelo) van detrás de los dignos.
    Sin medición → después de los medidos, ordenados por coste (heurística)."""
    dead, slow_pool, fast_pool, unmeasured = [], [], [], []
    for r in available:
        b = _bench(r)
        if b is None:
            unmeasured.append(r)
        elif not b["ok"]:
            dead.append(r)
        elif b["quality_score"] < _SPEED_MIN_QUALITY:
            slow_pool.append((b["latency_ms_median"] or 10 ** 9, r))
        else:
            fast_pool.append((b["latency_ms_median"] or 10 ** 9, r))
    ordered = [r for _, r in sorted(fast_pool, key=lambda t: (t[0], t[1].key))]
    ordered += [r for _, r in sorted(slow_pool, key=lambda t: (t[0], t[1].key))]
    ordered += sorted(unmeasured, key=lambda r: (cost_of(r), r.key))
    ordered += sorted(dead, key=lambda r: r.key)   # último recurso, jamás primario
    return ordered


def _order_balanced(available: list[ModelRef], cap: Capability) -> list[ModelRef]:
    """Calidad buena a velocidad decente: maximiza una mezcla del score de la
    capacidad (catálogo+investigado, 60%) y la velocidad MEDIDA (40%). Sin
    medición, la velocidad cuenta neutra (50) — el catálogo decide. Los
    medidos-muertos, al final."""
    def combo(r: ModelRef) -> float:
        b = _bench(r)
        speed = float(b["speed_score"]) if (b and b["ok"]) else 50.0
        return 0.6 * float(score_of(r, cap)) + 0.4 * speed

    alive = [r for r in available if not (_bench(r) and not _bench(r)["ok"])]
    dead = [r for r in available if r not in alive]
    return sorted(alive, key=lambda r: (-combo(r), cost_of(r), r.key)) + sorted(dead, key=lambda r: r.key)


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
        # [2026-07-21] Fuera los NO APTOS para esta capacidad (p.ej. Claude CLI
        # jamás compila en chat/classify/agentic — fallo real de producción).
        pool = [r for r in pool if cap not in unfit_for(r.provider)]

        if not pool:
            compiled[cap.value] = []   # Offline sin local → degradada en esta capacidad
            continue

        if name == PolicyName.ECONOMY:
            ordered = _order_economy(pool, cap)
        elif name == PolicyName.SPEED:
            ordered = _order_speed(pool, cap)
        elif name == PolicyName.BALANCED:
            ordered = _order_balanced(pool, cap)
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
    """Compila las políticas automáticas (todas menos Custom, que es el lienzo
    del usuario). [2026-07-22] +SPEED y +BALANCED (medidas por benchmark)."""
    return {
        PolicyName.ECONOMY.value: _compile_policy(PolicyName.ECONOMY, available),
        PolicyName.QUALITY.value: _compile_policy(PolicyName.QUALITY, available),
        PolicyName.OFFLINE.value: _compile_policy(PolicyName.OFFLINE, available),
        PolicyName.SPEED.value: _compile_policy(PolicyName.SPEED, available),
        PolicyName.BALANCED.value: _compile_policy(PolicyName.BALANCED, available),
    }


def _compile_custom(available: list[ModelRef]) -> dict[str, list[str]]:
    """El punto de partida de la política Personalizada = las mejores elecciones
    por capacidad (calidad). El usuario la edita desde ahí; "Restaurar" vuelve
    aquí. No es una política automática (no la recompila el catálogo sola) — es
    el lienzo editable del usuario (petición directa del usuario, 2026-07-18)."""
    return _compile_policy(PolicyName.QUALITY, available)


def _order_for(name: str, available: list[ModelRef], cap: Capability) -> list[ModelRef]:
    """El orden de candidatos que usa una política concreta para una capacidad —
    lo comparte la compilación automática y la edición manual (para que los
    respaldos de un modelo elegido a mano sigan el mismo criterio de esa política).
    [2026-07-21] Excluye los NO APTOS para la capacidad (unfit_for)."""
    available = [r for r in available if cap not in unfit_for(r.provider)]
    if name == PolicyName.OFFLINE.value:
        return _order_quality([r for r in available if r.is_local], cap)
    if name == PolicyName.ECONOMY.value:
        return _order_economy(available, cap)
    if name == PolicyName.SPEED.value:
        return _order_speed(available, cap)
    if name == PolicyName.BALANCED.value:
        return _order_balanced(available, cap)
    return _order_quality(available, cap)   # quality, custom


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
            existing = {r.name for r in db.query(MelPolicy.name).all()}
            active = default_active(available)
            now = datetime.utcnow()
            # Las 3 automáticas + la Personalizada (lienzo del usuario, = quality
            # de partida). Idempotente por nombre: si ya existe una, no la pisa
            # (respeta ediciones del usuario). Añade solo las que falten — así un
            # backend que arrancó antes de existir 'custom' la crea al reiniciar.
            seed = dict(compile_all(available))
            seed[PolicyName.CUSTOM.value] = _compile_custom(available)
            added = []
            for name, chains in seed.items():
                if name in existing:
                    continue
                db.add(MelPolicy(
                    name=name, version=1, compiled=chains, pristine=True,
                    is_active=(name == active and not existing), created_at=now, updated_at=now,
                ))
                added.append(name)
            if added:
                db.commit()
                logger.info(f"[policies] sembradas {added}; activa por defecto: {active}")
        except Exception as e:
            logger.error(f"[policies] ensure_compiled falló (no crítico): {type(e).__name__}: {e}")
            db.rollback()
        finally:
            db.close()

    def recompile_pristine(self, available: list[ModelRef]) -> list[str]:
        """[2026-07-22] Recompila las políticas AUTOMÁTICAS que el usuario no ha
        editado (`pristine=True`) con los datos actuales (catálogo + investigado
        + benchmark medido). Las editadas JAMÁS se tocan (doc 19 §5.3). Lo llama
        el benchmark al terminar una tanda de mediciones — así SPEED/BALANCED
        reflejan los números nuevos sin esperar a un reinicio."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        fresh = compile_all(available)
        updated: list[str] = []
        db = SessionLocal()
        try:
            for row in db.query(MelPolicy).filter(MelPolicy.pristine.is_(True)).all():
                if row.name in fresh and row.compiled != fresh[row.name]:
                    row.compiled = fresh[row.name]
                    row.version = (row.version or 1) + 1
                    row.updated_at = datetime.utcnow()
                    updated.append(row.name)
            if updated:
                db.commit()
                logger.info(f"[policies] recompiladas (pristine) con datos nuevos: {updated}")
            return updated
        except Exception as e:
            logger.error(f"[policies] recompile_pristine falló (no crítico): {type(e).__name__}: {e}")
            db.rollback()
            return []
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

    def chain_for_named(self, name: str, capability: Capability,
                        available: list[ModelRef]) -> list[ModelRef]:
        """La cadena de una política CONCRETA por nombre (la usa `policy_override`).
        Lee la persistida —así respeta las ediciones del usuario, igual que
        `active_chain`—; si no está persistida, la compila en memoria. Nunca
        recompila una política editada desde el catálogo (bug corregido: antes
        `policy_override` ignoraba las ediciones)."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        by_key = {r.key: r for r in available}
        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.name == name).first()
            if row and row.compiled:
                keys = row.compiled.get(capability.value, [])
                # [2026-07-21] Filtro RETROACTIVO de no-aptos: una política
                # editada ANTES de existir la regla (p.ej. Claude CLI en chat)
                # se sanea aquí, en ejecución, sin tocar lo persistido.
                chain = [by_key[k] for k in keys
                         if k in by_key and capability not in unfit_for(by_key[k].provider)]
                if chain:
                    return chain
        except Exception as e:
            logger.error(f"[policies] chain_for_named({name}) falló, compilo en memoria: {e!r}")
        finally:
            db.close()

        # No persistida (o vacía tras filtrar) → compila en memoria.
        try:
            if name == PolicyName.CUSTOM.value:
                chains = _compile_custom(available)
            else:
                chains = _compile_policy(PolicyName(name), available)
        except ValueError:
            return []
        return [by_key[k] for k in chains.get(capability.value, []) if k in by_key]

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
                # [2026-07-21] Mismo filtro retroactivo de no-aptos que en
                # chain_for_named — la EJECUCIÓN jamás usa un modelo no apto
                # para la capacidad, sin importar qué diga la política guardada.
                chain = [by_key[k] for k in keys
                         if k in by_key and capability not in unfit_for(by_key[k].provider)]
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

    # -----------------------------------------------------------------------
    # Edición manual del usuario (petición directa, 2026-07-18) — el usuario
    # puede escoger el modelo PRIMARIO por capacidad en Economy/Quality/Custom, y
    # "Restaurar" vuelve a los valores por defecto. Al editar, la política deja
    # de ser `pristine` (marca de "tocada por el usuario"; el compilador ya no la
    # actualizará sola — doc 19 §5.3).
    # -----------------------------------------------------------------------
    def set_primary(self, name: str, capability_value: str,
                    model_key: Optional[str], available: list[ModelRef]) -> bool:
        """Fija el modelo PRIMARIO de UNA capacidad en una política. `model_key`
        None = "Automático" (recompila esa capacidad desde el catálogo). Con un
        model_key concreto, la cadena queda [elegido, …respaldos] donde los
        respaldos siguen el orden propio de esa política (nunca deja al usuario
        sin red de seguridad ante un fallo transitorio). Devuelve False si la
        política o el modelo no existen."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        by_key = {r.key: r for r in available}
        if model_key is not None and model_key not in by_key:
            return False
        try:
            cap = Capability(capability_value)
        except ValueError:
            return False
        # [2026-07-21] Un modelo NO APTO para la capacidad no puede elegirse.
        if model_key is not None and cap in unfit_for(by_key[model_key].provider):
            return False

        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.name == name).first()
            if row is None:
                return False
            compiled = dict(row.compiled or {})
            if model_key is None:
                # Automático: recompila SOLO esta capacidad desde el catálogo.
                if name == PolicyName.CUSTOM.value:
                    single = _compile_custom(available)
                else:
                    single = _compile_policy(PolicyName(name), available)
                compiled[capability_value] = single.get(capability_value, [])
            else:
                fallbacks = [r for r in _order_for(name, available, cap) if r.key != model_key]
                chain = [by_key[model_key]] + fallbacks
                compiled[capability_value] = [r.key for r in chain[:_MAX_CHAIN]]
            row.compiled = compiled          # dict nuevo → SQLAlchemy detecta el cambio
            row.pristine = False
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"[policies] set_primary falló: {type(e).__name__}: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def set_slot(self, name: str, capability_value: str, position: int,
                 model_key: str, available: list[ModelRef]) -> bool:
        """[2026-07-21, petición del usuario] Edita UNA posición concreta de la
        cadena (0=primario, 1-2=respaldos, 3=último recurso). REGLA DEL ÚLTIMO
        ESLABÓN: la posición final (_MAX_CHAIN-1) solo admite modelos LOCALES —
        es la red de seguridad cuando todo lo demás (o la conexión) falla.
        Tras colocar el modelo: se deduplica (si ya estaba en otra posición se
        quita de allí), se rellena hasta _MAX_CHAIN con el orden propio de la
        política, y se garantiza que la cadena termina en un local si existe
        alguno (mismo criterio que el compilador). Marca la política editada."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        by_key = {r.key: r for r in available}
        if model_key not in by_key:
            return False
        try:
            cap = Capability(capability_value)
        except ValueError:
            return False
        if not (0 <= position < _MAX_CHAIN):
            return False
        if position == _MAX_CHAIN - 1 and not by_key[model_key].is_local:
            return False   # el último eslabón es SIEMPRE local
        # [2026-07-21] Ni siquiera como respaldo: no-apto es no-apto.
        if cap in unfit_for(by_key[model_key].provider):
            return False

        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.name == name).first()
            if row is None:
                return False
            compiled = dict(row.compiled or {})
            chain = [k for k in compiled.get(capability_value, []) if k in by_key]
            # Coloca (reemplaza la posición; si la cadena es más corta, al final).
            if position < len(chain):
                chain[position] = model_key
                edited_at = position
            else:
                chain.append(model_key)
                edited_at = len(chain) - 1
            # Dedupe conservando LA POSICIÓN EDITADA como la válida.
            out: list[str] = []
            for i, k in enumerate(chain):
                if k == model_key and i != edited_at:
                    continue
                if k in out:
                    continue
                out.append(k)
            # Relleno con el orden propio de la política.
            fill = [r.key for r in _order_for(name, available, cap) if r.key not in out]
            while len(out) < _MAX_CHAIN and fill:
                out.append(fill.pop(0))
            # Red de seguridad: terminar en local si existe alguno y no hay ya.
            best_local = next((r for r in _order_quality(available, cap) if r.is_local), None)
            if best_local and not any(by_key[k].is_local for k in out):
                if len(out) >= _MAX_CHAIN:
                    out[-1] = best_local.key
                else:
                    out.append(best_local.key)
            compiled[capability_value] = out[:_MAX_CHAIN]
            row.compiled = compiled
            row.pristine = False
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"[policies] set_slot falló: {type(e).__name__}: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def restore(self, name: str, available: list[ModelRef]) -> bool:
        """Devuelve una política a sus valores por defecto: recompila las
        automáticas desde el catálogo; la Personalizada vuelve a su lienzo base
        (= Quality). La marca `pristine` de nuevo. No cambia cuál está activa."""
        from app.db.database import SessionLocal
        from app.mel.models import MelPolicy

        db = SessionLocal()
        try:
            row = db.query(MelPolicy).filter(MelPolicy.name == name).first()
            if row is None:
                return False
            if name == PolicyName.CUSTOM.value:
                chains = _compile_custom(available)
            else:
                chains = _compile_policy(PolicyName(name), available)
            row.compiled = chains
            row.pristine = True
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"[policies] restore falló: {type(e).__name__}: {e}")
            db.rollback()
            return False
        finally:
            db.close()


policy_store = PolicyStore()
