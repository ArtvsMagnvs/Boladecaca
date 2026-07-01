# JWIKI Tick — 2026-06-30 19:15 — CAMBIO DE PARADIGMA: 1 equipo secuencial, ritmo 30 min

> **Decisión del usuario**: eliminar el paralelismo agresivo de 2 turnos cada 15 min. Pasar a **1 solo equipo** (investigador / escriba / auditor principales), ritmo natural del pipeline (~30 min entre docs).
> Tick A 19:00 fue el último con el modelo viejo. A partir de aquí el cron `jwiki-tick-a` corre cada 30 min con prompt unificado.

## Por qué el cambio

El usuario pidió:
- **Ritmo 30-35 min** entre tiks, no 15 min.
- **Eliminar los "agentes dobles"** (`aithera-wiki-inv2`, `aithera-wiki-scr2`, `aithera-wiki-aud2` — turno B) — no se usan para nuevos tiks.
- **Mantener el resto igual** — los agentes principales (`aithera-wiki-investigador`, `aithera-wiki-escriba`, `aithera-wiki-auditor`) siguen.
- **Con calma** — no romper lo que funciona; los spawns en curso terminan su trabajo.

## Cambios ejecutados

### 1. Cron `jwiki-tick-b` → DESACTIVADO
```
mavis cron disable mavis jwiki-tick-b
→ Cron task 'jwiki-tick-b' disabled.
```
Ya no se generan nuevos tiks de turno B cada 15 min. Los spawns ya entregados (sesiones vivas) terminan su trabajo.

### 2. Cron `jwiki-tick-a` → RECONFIGURADO
**Antes**:
- Schedule: `*/15 * * * *` (cada 15 min)
- Prompt: tick turno A, IDs pares, agente `aithera-wiki-investigador`
- Alerta si turno A no cerró en 30 min

**Ahora**:
- Schedule: `*/30 * * * *` (cada 30 min)
- Prompt: tick único, siguiente ID pending (cualquier paridad), mismo agente `aithera-wiki-investigador`
- Alerta si tick anterior no cerró en 35 min (margen +5 min por el ritmo más relajado)

Comando ejecutado:
```
mavis cron update mavis jwiki-tick-a --schedule "*/30 * * * *" --prompt "..."
→ Cron task 'jwiki-tick-a' updated.
```

### 3. Agentes dobles → NO TOCADOS en disco
`aithera-wiki-inv2`, `aithera-wiki-scr2`, `aithera-wiki-aud2` siguen registrados. Razones:
- Sus systemPrompts ya están cargados en sesiones activas (sesiones cron tick B 18:30/18:45/19:00 que spawnean hijos con estos nombres).
- Matar los agentes rompería las sesiones en curso (005 raw entregado + escriba en marcha, 007 investigación en vuelo, 009 investigación recién despachada).
- Si los necesitamos en el futuro, están ahí. Si no, los borramos cuando no haya spawns activos que los referencien.

## Estado al momento del cambio (19:11)

**Verificados (4)**: JWIKI-001 (history.md), 002 (projects.md), 003 (openclaw.md), 004 (openhuman.md).

**In progress Turno A (3)**:
| ID | Tema | Estado | Notas |
|---|---|---|---|
| JWIKI-006 | JarvisAgent Tauri+Vue | sin raw | dispatch 18:30, 41 min elapsed. ⚠️ Alerta marginal pero sin intervenir todavía |
| JWIKI-008 | Clawdbot (MCP-based) | **raw entregado 19:10** ✅ | 28KB, listo para escriba |
| JWIKI-010 | Comparativa frameworks agentes | sin raw | dispatch 19:00, 11 min — dentro del ETA |

**In progress Turno B (3)** [sesiones activas, ya no se generan más]:
| ID | Tema | Estado | Notas |
|---|---|---|---|
| JWIKI-005 | OpenJarvis Stanford | raw entregado 18:52 | escriba turno B (`aithera-wiki-scr2`) trabajando en `01_LANDSCAPE/openjarvis.md` |
| JWIKI-007 | Hermes Agent Nous | sin raw | dispatch 18:45 (slot 007b re-despach 19:01), 26 min — en el límite |
| JWIKI-009 | Superpowers Skill framework | sin raw | dispatch 19:00, 11 min — dentro del ETA. Agente `aithera-wiki-inv2` |

**Pending (2)**: JWIKI-011 (LangGraph), JWIKI-012 (CrewAI).

**Total raws en disco**: 6 (001, 002, 003, 004 verificados + 005, 008 recientes).

## Decisiones operativas

### JWIKI-006 con 41 min sin raw → esperar
El usuario dijo "con calma". A las 19:30 (próximo cron tick A) hará 60 min. Si a 19:30 sigue sin raw, intervención manual (kill sesión `mvs_54554922829c4407beba061e482b21ce` + re-spawn).

### JWIKI-008 raw entregado → escribir cuando el flujo lo permita
El sistema serial-write pipeline aún tiene 005 en curso. El orden lógico es: 005 → 008 → siguientes. Pero como ahora NO hay dos turnos paralelos, el orden natural es FIFO por tiempo de entrega del raw.

### Próximo tick automático
**Cron `jwiki-tick-a` a las 19:30** (con nuevo schedule 30 min):
- Prompt dirá "siguiente ID pending (más bajo)" → JWIKI-011 (LangGraph overview).
- Investigador principal `aithera-wiki-investigador` será despachado.
- Pero antes: el tick 19:00 fue hace 30 min → margen exacto. Si el cron evalúa "tick anterior cerró?" y ve 6 in_progress sin cerrar, podría alertar. Hay que ver cómo se comporta en la práctica.

### Sesiones activas que NO hay que matar
- `mvs_87ab0ebdcbd84d5bb6cb44b250e61c1e` (cron tick B 18:45) — su spawn 007b está en vuelo.
- `mvs_87ab0ebdcbd84d5bb6cb44b250e61c1e` (cron tick B 19:00) — su spawn 009 está en vuelo.
- `mvs_f515116aae994889b4af9bd26daf433c` (cron tick A 19:00) — su spawn 010 está en vuelo.
- `mvs_a40edbe302bf4515a9e583f99d1fb886` (cron tick A 18:45) — su spawn 008 está entregando.
- Las sesiones spawn-eadas (`mvs_5455...21ce` para 006, etc.) — dejarlas vivas.

## Plan para los próximos 30-60 min

| Tiempo | Acción esperada |
|---|---|
| 19:15-19:25 | JWIKI-007 raw debería llegar (turno B slot 007b 19:01 + 26 min). |
| 19:15-19:25 | JWIKI-009 raw debería llegar (turno B 19:00 + 11 min). |
| 19:15-19:25 | JWIKI-010 raw debería llegar (turno A 19:00 + 11 min). |
| 19:25-19:30 | Escriba principal debería tomar el siguiente raw listo (¿008?). |
| **19:30** | **Próximo cron tick A** (schedule nuevo). Despacha JWIKI-011 (LangGraph) con `aithera-wiki-investigador`. |
| 19:30-19:45 | Si JWIKI-006 sigue sin raw a 60 min → intervention manual. |
| 19:45+ | Escriba cierra 005 (OpenJarvis doc) o 008 (Clawdbot doc), según orden de entrega. |

## Documentación a actualizar (próximo tick)

- `task_queue.md` header: cambiar "Turno A cada 15 min IDs pares + Turno B cada 15 min IDs impares" a "Tick único cada 30 min (cron `jwiki-tick-a`), cualquier ID pending".
- `wiki-map.md` header: idem si tiene notas sobre turnos.
- `CHANGELOG.md`: entrada con el cambio de paradigma.

---

*Mantenido por Mavis (orquestador). Cambio de paradigma ejecutado en respuesta al feedback del usuario a las 19:03 Europe/Paris. Sistema en transición: 6 in_progress activos con los spawns previos, próximo tick automático a 19:30 con el nuevo schedule.*