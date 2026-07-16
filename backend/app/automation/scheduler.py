# app/automation/scheduler.py — el planificador único del backend (V0.9 A2a)
#
# APScheduler entra AQUÍ (no antes, doc 11 §A.5): absorbe los jobs asyncio de
# V0.85 (ingesta, resumen nocturno) + el nuevo lifecycle del MOS. Misma función
# de trabajo, mejor gestión (un scheduler que registra/lista/quita jobs, en vez
# de N `asyncio.create_task(_loop())` sueltos).
#
# Envoltorio FINO sobre AsyncIOScheduler: singleton, arrancado/parado en el
# `lifespan` de main.py, con helpers para intervalos y cron. Cada job corre
# aislado — un fallo de una pasada NO mata el scheduler ni a otros jobs (misma
# garantía que los `_loop` con try/except que sustituye). El wiring concreto
# (qué funciones se registran) vive en el composition root (main.py), no aquí:
# así el scheduler no depende de app.memory (evita el acoplamiento inverso).
from __future__ import annotations

from typing import Any, Callable, Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("scheduler")


class SchedulerService:
    """AsyncIOScheduler singleton. Construcción barata (no toca hilos ni el loop
    hasta `start()`, que debe llamarse DENTRO del event loop del lifespan)."""

    def __init__(self) -> None:
        self._scheduler: Any = None  # apscheduler.schedulers.asyncio.AsyncIOScheduler

    @property
    def running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    def start(self) -> None:
        """Crea y arranca el scheduler sobre el event loop actual. Idempotente."""
        if self._scheduler is not None:
            return
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        # coalesce=True: si el backend estuvo dormido y se acumularon disparos,
        # se ejecuta UNA sola vez al despertar (no N veces).
        # max_instances=1: un job nunca se solapa consigo mismo.
        # misfire_grace_time: margen amplio para jobs que se retrasan (arranque).
        self._scheduler = AsyncIOScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}
        )
        self._scheduler.start()
        logger.info("[scheduler] APScheduler iniciado")

    def shutdown(self) -> None:
        """Parada limpia (llamar en el shutdown del lifespan). `wait=False` para
        no bloquear el cierre esperando jobs en curso."""
        if self._scheduler is None:
            return
        try:
            self._scheduler.shutdown(wait=False)
        except Exception as e:
            logger.error(f"[scheduler] error al parar: {e!r}")
        finally:
            self._scheduler = None
            logger.info("[scheduler] APScheduler detenido")

    def add_interval_job(
        self,
        func: Callable,
        *,
        minutes: int,
        id: str,
        jitter: Optional[int] = None,
        first_run_delay_s: Optional[int] = None,
    ) -> None:
        """Registra un job periódico (cada `minutes`). `jitter` reparte el disparo
        para no competir con otros jobs; `first_run_delay_s` retrasa la primera
        pasada (equivale al jitter inicial de los `_loop` de V0.85 — no competir
        con el arranque). `replace_existing` para re-registrar sin duplicar."""
        from datetime import datetime, timedelta

        from apscheduler.triggers.interval import IntervalTrigger

        kwargs: dict[str, Any] = {"minutes": minutes}
        if jitter:
            kwargs["jitter"] = jitter
        trigger = IntervalTrigger(**kwargs)
        run_kwargs: dict[str, Any] = {}
        if first_run_delay_s:
            # next_run_time en el futuro = la primera pasada espera ese retardo
            # (equivalente al jitter inicial de los _loop de V0.85).
            run_kwargs["next_run_time"] = datetime.now() + timedelta(seconds=first_run_delay_s)
        self._scheduler.add_job(func, trigger=trigger, id=id, replace_existing=True, **run_kwargs)
        logger.info(f"[scheduler] job de intervalo '{id}' cada {minutes} min")

    def add_cron_job(self, func: Callable, *, hour: int, minute: int, id: str) -> None:
        """Registra un job diario a una hora LOCAL (cron). Para el resumen
        nocturno (03:30) y el lifecycle (04:00) — horas pensadas para el usuario
        dormido, en reloj local (doc 07 §7)."""
        from apscheduler.triggers.cron import CronTrigger

        self._scheduler.add_job(
            func, trigger=CronTrigger(hour=hour, minute=minute), id=id, replace_existing=True
        )
        logger.info(f"[scheduler] job cron '{id}' diario a las {hour:02d}:{minute:02d} local")

    def jobs(self) -> list[str]:
        """Ids de los jobs registrados (para diagnóstico / endpoint de estado)."""
        if self._scheduler is None:
            return []
        return [j.id for j in self._scheduler.get_jobs()]


# Singleton — mismo patrón que gateway / approval_gate / memory_router.
scheduler_service = SchedulerService()
