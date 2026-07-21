# INSTRUCCIONES PARA CLAUDE CODE — tareas de ejecución local (2026-07-21)

> **Contexto**: estas tareas las preparó la sesión de Cowork (que no puede
> ejecutar git ni el backend en esta máquina). Lee primero `CLAUDE.md` §25
> (bloque UX + MEL-UI + OBSERVABILIDAD) para entender qué cambió. Ejecuta los
> pasos EN ORDEN y reporta el resultado de cada uno. Si algo falla, para y
> repórtalo — no lo silencies ni improvises arreglos grandes sin avisar.

---

## PASO 1 — Aplicar la migración 26.ª (telemetría)

La tabla `mission_events` (migración `a7c8d9e0f1a2_v10_mission_telemetry`)
está escrita pero NO aplicada al Postgres real.

```bat
cd backend
venv\Scripts\activate
alembic upgrade head
alembic current
```

**Criterio de éxito**: `alembic current` muestra `a7c8d9e0f1a2`. La migración
es aditiva e idempotente (patrón del proyecto) — no toca datos existentes.
Si `DATABASE_URL` no está en el entorno, la carga el propio `alembic/env.py`
del `.env` del backend, como siempre.

## PASO 2 — Suite completa de tests

```bat
cd backend
venv\Scripts\activate
python -m pytest tests/ -q
```

**Esperado**: verde (la última referencia conocida era 751 passed, pre-S1; hay
tests nuevos desde entonces). Flakes CONOCIDOS que no bloquean:
`test_import_app_main_no_bloquea_en_memoria` (presupuesto de import, sensible a
carga de la máquina) y algún flake frío de ChromaDB. Cualquier OTRO fallo:
repórtalo con el traceback antes de seguir.

## PASO 3 — Batería del Mission Lab (backend corriendo)

Necesita el backend levantado. Si no está corriendo:

```bat
cd backend
iniciar_backend.bat
```

(o `python -m uvicorn app.main:app --port 8000` con el venv activo). Espera a
"Application startup complete". Después, en OTRA terminal:

```bat
cd backend
venv\Scripts\activate
python scripts\mission_lab.py
```

- La batería lanza ~7 misiones de prueba por el endpoint real de chat. TODO lo
  que escriben queda confinado a `test-lab/` (gitignored). Tarda varios
  minutos (misiones de navegador incluidas).
- Al terminar, genera el reporte agregado y GUÁRDALO como baseline:

```bat
mkdir test-lab\reports 2>NUL
python scripts\mission_report.py --aggregate 1 > test-lab\reports\baseline-2026-07-21.txt
type test-lab\reports\baseline-2026-07-21.txt
```

**Reporta**: cuántos escenarios ✓/✗, tiempos por escenario, y el contenido del
reporte agregado (latencia por capacidad|modelo, éxito por tool). Si algún
escenario falla, incluye su timeline:
`python scripts\mission_report.py <mission_id>`.

## PASO 4 — Limpieza git de lo reubicado

La sesión de Cowork reorganizó el repo (ver CLAUDE.md §25 "Orden del repo"):
`Fase_*` → `archive/fases/`, guías → `docs/`, restos CrewAI →
`archive/crewai-ajeno/`, scratch → `scratch/` y `backend/scratch/`. El
`.gitignore` ya ignora lo que no debe ir al repo. Falta des-trackear lo que YA
estuviera versionado:

```bat
git rm -r --cached --ignore-unmatch scratch backend/scratch archive/crewai-ajeno TripoSR otsaas graphify-out backend/graphify-out backend/Aithera test-lab
git status
```

Revisa `git status`: los moves deben aparecer como renames/deletes+adds, y NO
debe quedar nada de `TripoSR/`, `otsaas/`, `scratch/` ni logs por añadir.
NUNCA comitees `.env`, tokens, ni `backend/data/`.

## PASO 5 — Commit de todo

Un solo commit está bien (o divide si lo ves más limpio):

```bat
git add -A
git commit -m "feat(2026-07-21): UX (tema claro gris + AVCS identidad + escenario oscuro Hub), Settings reorganizado (HUB Visual, voz unificada, Kokoro install real), modelos locales (self-heal enable, familia Llama, Eliminar real), proveedores jul-2026 (grupos, Claude CLI Activar, catalogo verificado, fix schema model_labels), MEL-UI vinculado (chatPrimary efectivo, fallos visibles, 4 slots, banner solo-local), gating UNFIT claude_code, telemetria de misiones (mission_events + hooks + API + lab), orden del repo, docs 30-31, CLAUDE.md §25"
```

## PASO 6 — Reporte final

Devuelve al usuario: (1) `alembic current`, (2) resultado de la suite,
(3) resumen de la batería + ruta del baseline, (4) hash del commit.

### Notas de seguridad
- Si el backend del usuario YA está corriendo con trabajo en curso, no lo
  reinicies sin avisar (el lab funciona contra el backend que esté vivo, pero
  necesita el CÓDIGO NUEVO cargado — si el proceso es de antes de estos
  cambios, los endpoints `/api/telemetry/*` no existirán: reinícialo con
  permiso del usuario).
- Las misiones de escritorio (ratón/teclado) NO están en la batería: no las
  añadas.
- `archive/crewai-ajeno/` es basura de CrewAI conservada por precaución — el
  usuario puede borrarla cuando quiera; tú no la borres sin que te lo pida.
