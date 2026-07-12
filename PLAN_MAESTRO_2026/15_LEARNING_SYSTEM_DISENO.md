# 15 — Aithera Learning System (ALS) — aprendizaje continuo con cuarentena

> **Origen**: briefing del usuario 2026-07-12 (pilar "Sistema de Aprendizaje").
> **Gobernado por**: doc 16 (principios). **Extiende** el doc 09 (LSL/LLL): los 5
> análisis del LLL siguen siendo el núcleo analítico; este doc construye alrededor
> el sistema completo (fuentes, validación, Mission Learning, reflexión multi-escala,
> Skill Evolution, Knowledge Evolution). **Módulo**: `backend/app/learner/`.
>
> **Regla constitucional del Learner** (Principio 8): observa, analiza y PROPONE.
> Nunca planifica (TIE), nunca ejecuta (AE/runtimes), nunca aplica un cambio al
> conocimiento permanente sin pasar la cuarentena de §3. El MOS almacena lo
> aprendido; el Learner es quien aprende.

---

## 1. El pipeline (la forma de todo el sistema)

```
COLLECT ──▶ ANALYZE ──▶ PROPOSE ──▶ VALIDATE ──▶ CONSOLIDATE ──▶ MEASURE ──▶ EVOLVE
pasivo,      jobs        candidatos   cuarentena    escribe en     métricas     merge/split/
coste 0 en   batch       con          (evidencia    el MOS por     de uso y     deprecate;
critical     (Ollama-    confianza    o HITL)       APIs públicas  calidad      olvido
path         first)                                                             controlado
```

Dos propiedades no negociables:
1. **Collect es gratis**: el Learner NO instrumenta nada nuevo — lee lo que el
   sistema ya escribe por diseño (traces del TIE, `decisions`, `mem_error`,
   resultados del AE, feedback ✓/✎/✗). Si aprender exigiera frenar el producto,
   estaría mal diseñado (doc 16 §2.1).
2. **Nada entra al conocimiento permanente sin validación** (§3). El aprendizaje
   sin cuarentena es contaminación con extra de pasos.

## 2. Fuentes de aprendizaje (las 19 del briefing, mapeadas a capturas existentes)

| Fuente (briefing) | Dónde se captura YA | Desde |
|---|---|---|
| Tareas / éxitos / errores / soluciones | traces del TIE (nodos con result/validation/error) + `mem_error` | V1.0 |
| Conversaciones | `mem_conversational` (MOS) | V0.85 |
| Proyectos | `mem_project` + `decisions.project` | V0.85 stub → V1.2 |
| Correcciones y feedback del usuario | patrón ✓/✎/✗ del email (V0.7.3) generalizado: toda propuesta del sistema registra la reacción en Decision API | V0.9 |
| Decisiones y resultados | tabla `decisions` + `link_outcome` (doc 08 RFC-002) | V0.85/V0.9 |
| Herramientas utilizadas | `tool_calls` en traces + `agent_executions` | V0.5/V1.0 |
| Modelos (qué funcionó mejor) | `model_used` + tokens/duración/éxito por nodo en traces | V1.0 |
| Prompts efectivos/ineficientes | pares (goal del nodo → validation.ok) en traces; NO se guardan prompts crudos, se destilan plantillas | V1.1 |
| Workflows y automatizaciones | `automation_executions` + Automation Memory | V0.9 |
| Documentación leída / código generado / bugs | resultados de nodos con `source="tie"` en el MOS + `mem_error` | V1.0+ |

Conclusión de auditoría: **cero instrumentación nueva** — el diseño de traces
(11 B.1), Decision API y Error Memory ya era el collect del Learner. Único añadido:
el evento `mission.completed` (doc 14 §4.4) como disparador.

## 3. Validación y confianza (la cuarentena)

### 3.1 Escalera de confianza (para TODO tipo de aprendizaje, no solo skills)

```
OBSERVED ──▶ CANDIDATE ──▶ PROPOSED ──▶ VALIDATED ──▶ CONSOLIDATED     (+ DEPRECATED)
señal cruda   patrón con     visible al    en vigor      permanente: sobrevive
en traces     ≥3 evidencias  usuario/      (en uso       a la compactación
(no es        (umbral        auto-regla    real, con     (RFC-007: pinned)
conocimiento) MIN_REP)       de bajo       métricas)
                             riesgo
```

### 3.2 Rutas de validación por clase de riesgo

| Clase | Ejemplos | Ruta a VALIDATED |
|---|---|---|
| **Bajo** | preferencia personal observada ("prefiere respuestas cortas por Telegram"), pin de contexto | auto tras N=5 evidencias consistentes y 0 contradicciones; SIEMPRE visible y reversible en el panel |
| **Medio** | skill nueva, mejora de skill, plantilla de workflow | 3 ejecuciones OK reales (patrón autonomía email V0.7.3) **o** aprobación explícita del usuario — lo que llegue antes |
| **Alto** | regla de automatización sugerida, cambio de política de Model Router, doc de proyecto | SIEMPRE HITL: el usuario aprueba; la aprobación queda en Decision API |

Reglas transversales: toda propuesta es **no bloqueante** (notificación suave,
doc 09 §2.2); toda consolidación es **reversible** (deprecate + historia, nunca
borrado); el usuario tiene un **panel "Lo que Aithera ha aprendido"** (V1.1, doc
09) con undo por ítem. La confianza del usuario es EL activo — se protege con
transparencia, no con opacidad optimista.

### 3.3 Anti-contaminación

- Aprender solo de resultados con **señal externa** (validation.ok, feedback del
  usuario, outcome de decisión) — jamás de "el LLM dijo que salió bien" sin más:
  eso es un bucle de retroalimentación que refuerza sus propios errores.
- Una racha de suerte no es evidencia: MIN_REP=3 **en contextos distintos**
  (misiones diferentes, días diferentes) para CANDIDATE.
- `PrivacyFilter` también aquí: una skill jamás captura datos personales en su
  `definition` (nombres, emails, contenido privado se parametrizan). No es solo
  para la GSN (08 RFC-001): es higiene desde el nacimiento de la skill.

## 4. Mission Learning (el checklist del briefing → escrituras concretas)

Disparador: evento `mission.completed` → job del Learner (asíncrono, post-respuesta,
Ollama-first, ≤1 llamada LLM barata por misión, presupuesto ≤5 s). Cada pregunta
del briefing tiene UNA salida concreta — nada de reflexión sin consecuencia:

| Pregunta | Salida concreta | Destino (API MOS) |
|---|---|---|
| ¿Qué salió bien / mal? | nota de reflexión estructurada (2-5 líneas) enlazada a `mission_id` | Decision API (`decisions.mission_id` — delta #2 de doc 14 §4.1) |
| ¿Qué modelo funcionó mejor? | agregación en `model_stats` (por dominio/tipo de nodo: éxito, latencia, coste) | tabla del Learner (V1.2); la lee el Model Router |
| ¿Qué herramientas funcionaron? | `tool_stats` (error rate por tool/contexto) | ídem |
| ¿Qué errores aparecieron? | firma de error + contexto | Memory API (`ERROR`) — ya diseñado 11 A.3 |
| ¿Qué soluciones aparecieron? | par (firma de error → solución aplicada); si se repite ≥3 veces → candidato a skill preventiva | Memory API + LLL análisis 2 |
| ¿Qué debería recordar? | propuesta de pin (item que la compactación no debe destilar) | lifecycle RFC-007 (`pinned`) |
| ¿Qué debería olvidar? | propuesta de forget/archive (contexto efímero de la misión) | lifecycle / `forget()` |
| ¿Qué skill debería crearse? | candidato DRAFT con plantilla extraída | Skill API (LSL) — LLL análisis 1 |
| ¿Qué documentación actualizar? | propuesta de actualización de doc de proyecto | `mem_project` + vault (V1.2+) |
| ¿Qué contexto merece persistir? | promoción de notas de working → proyecto | Memory API (`PROJECT`) |

Nota de coste: para misiones triviales (camino corto) NO hay Mission Learning —
solo se acumulan contadores. Reflexionar sobre "¿qué hora es?" es reflection theater.

## 5. Reflection System — 5 escalas (no solo reflexión final)

| Escala | Cuándo | Quién | Mecanismo | Coste | Versión |
|---|---|---|---|---|---|
| **Intra-tarea** | durante un nodo | el AgentRuntime (Hermes la trae nativa; NullRuntime no reflexiona) | interna al runtime; lo aprendido sale SOLO vía `AgentResult.learned` | del runtime | V1.1 |
| **Entre nodos** | al cerrar cada nodo | executor del TIE | validation hook (doc 14 §3.4.7): schema/determinista; LLM solo si el nodo lo declara | ~0 / 1 llamada barata | V1.0 / V1.2 |
| **Post-misión** | `mission.completed` | Learner | Mission Learning (§4) | 1 llamada barata | V1.1 |
| **Semanal** | job APScheduler | Learner | LLL análisis 5 (doc 09): briefing de aprendizaje ("1 skill nueva, error_rate de X mejoró...") | batch nocturno | V1.1 |
| **Largo plazo** | mensual + con la compactación | Learner + lifecycle | Knowledge Evolution (§7): dedup, contradicciones, obsolescencia, patrones inter-proyecto (LLL análisis 3) | batch | V1.2 → V1.5 |

Restricciones duras heredadas del doc 09 §2.3: micro-batch, prioridad idle, ≤3%
CPU, cada ciclo escribe `MemoryJobRun` — el aprendizaje es invisible para el
usuario salvo por sus frutos (Principio 16).

## 6. Skill Evolution System (las skills son entidades vivas)

Base: `LocalSkill` + ciclo de vida del doc 09 §1.1-1.2, con los 2 campos de linaje
añadidos (`derived_from`, `superseded_by` — delta #1 de doc 14 §4.1).

### 6.1 Operaciones de evolución (todas son PROPUESTAS del Learner)

| Operación | Disparador (detección del LLL) | Efecto |
|---|---|---|
| **Improve** (version bump) | quality_score < 0.6 con patrón de fallo identificable (análisis 4) | nueva versión semver; la anterior queda en historia |
| **Split** | una skill con clusters de uso divergentes (misma skill, dos contextos con resultados distintos) | 2 hijas con `derived_from=[madre]`; madre → DEPRECATED con `superseded_by` |
| **Merge** | 2+ skills con similitud semántica alta + co-uso + solape de definición | 1 resultante con `derived_from=[a, b]`; las fuentes → DEPRECATED |
| **Specialize** | skill genérica con evidencia fuerte en UN proyecto (análisis 3) | hija con `projects=[X]` y definición afinada |
| **Deprecate** | calidad bajo umbral CON reemplazo existente, o 0 usos en N meses | DEPRECATED + `superseded_by`; jamás se borra (historia) |

Aplicación: clase de riesgo MEDIO (§3.2) — 3 ejecuciones OK de la skill resultante
o aprobación del usuario. El linaje completo es reconstruible siguiendo
`derived_from`/`superseded_by` — el "git log" de cada skill.

### 6.2 Métricas e historial

- Métricas en vivo (ya en `LocalSkill`): `use_count`, `evidence_count`,
  `error_rate`, `quality_score` = f(éxitos ponderados por recencia, feedback,
  cobertura de contextos) — recálculo en LLL análisis 4.
- **Historial**: tabla `skill_events` (V1.1, junto a la tabla `skills`):
  `id, skill_id (ix), event (created|validated|improved|merged|split|deprecated|
  executed_ok|executed_fail), payload JSON, actor (learner|user|runtime),
  created_at`. Es la fuente para métricas, para el panel del Hub y para que la
  GSN (V2.0+) tenga provenance real.
- Performance: caché RAM de skills LOCAL/VALIDATED (doc 09 §1.3) pasa a **LRU
  parcial** si el catálogo supera ~2k skills (respuesta a doc 14 §7.7).

## 7. Knowledge Evolution (cómo el conocimiento no se pudre)

Extiende RFC-007 (compactación) — la compactación gestiona VOLUMEN; esto gestiona
CALIDAD. Cuatro mecanismos, todos micro-batch nocturnos del Learner:

1. **Dedup en escritura** (V0.85 ya lo tiene: similitud > 0.97 → merge). El
   Learner añade dedup CONCEPTUAL (V1.2): mismo hecho con redacciones distintas
   → merge conservando la metadata más rica.
2. **Contradicciones**: al consolidar un hecho/preferencia/decisión, búsqueda de
   opuestos sobre la misma clave (mismo sujeto+kind). Conflicto → (a) si la
   evidencia nueva domina claramente: cadena `superseded_by` (el patrón de la
   tabla `decisions` §5, generalizado); (b) si no: se presenta al usuario ("antes
   preferías X, ahora observo Y — ¿cuál vale?"). Nunca coexisten dos verdades
   activas sobre la misma clave.
3. **Obsolescencia**: `last_used` + TTL por kind → propuesta de archive (no
   borrado; va al vault). Skills: cubierto por Deprecate (§6.1).
4. **Consistencia documental** (V1.2+): los docs de proyecto generados
   (`mem_project` + vault) se re-verifican contra las decisiones activas del
   proyecto; divergencia → propuesta de actualización.

V1.5+: detección de contradicciones basada en entidades vía Knowledge/Graph APIs
(Cognee/KuzuDB, 08 RFC-006) — el mecanismo de §7.2 es el mismo; mejora el recall.

## 8. Qué genera automáticamente el ALS — y qué no hará jamás solo

**Genera (como propuestas por la cuarentena §3)**: skills nuevas y mejoras;
detección de skills obsoletas; documentación de proyecto y actualizaciones;
plantillas de workflow (skills `kind=workflow`); mejores planificaciones (el
planner V1.2 recibe "misiones similares previas" del enricher); mejor selección
de modelos y herramientas (stats §4); pins/olvidos; reglas de automatización
sugeridas (AutomationLearner V1.2, doc 11 A.1 — ES este módulo).

**Jamás solo**: ejecutar una skill recién creada sin validación; cambiar una regla
de automatización activa; publicar nada fuera de la máquina (GSN V2.0+ siempre con
confirmación explícita, doc 09 §3); borrar conocimiento (solo deprecate/archive);
aprender de contenido marcado privado por el usuario.

## 9. Incorporación por versión

| Capacidad | V1.0 | V1.1 | V1.2 | V1.5 | V2.0+ |
|---|---|---|---|---|---|
| LLL análisis 1 (tareas repetidas → skill DRAFT) | ✅ (doc 09) | ✅ | ✅ | ✅ | ✅ |
| Mission Learning (§4) | — | ✅ | ✅ +stats | ✅ | ✅ |
| LLL análisis 2-5 + panel Hub | — | ✅ | ✅ | ✅ | ✅ |
| Cuarentena/escalera de confianza (§3) | básica (skills) | ✅ completa | ✅ | ✅ | ✅ |
| Skill Evolution (§6) + `skill_events` | — | tabla+métricas | ✅ merge/split/specialize | ✅ | ✅ +GSN |
| model_stats/tool_stats → Model Router | — | — | ✅ | ✅ | ✅ |
| AutomationLearner (reglas sugeridas) | — | — | ✅ | ✅ | ✅ |
| Knowledge Evolution (§7) | — | dedup+contradicciones básicas | ✅ | ✅ +grafo | ✅ |
| **Mission evals** (suite de misiones canónicas de regresión, pre-release) | — | — | ✅ | ✅ | ✅ |
| Reflexión predictiva (pre-cargar skill/contexto) | — | — | — | ✅ | ✅ |
| CIE (aprendizaje colectivo) | — | — | — | — | ✅ opcional |

Sprints: el ALS no añade fases nuevas al roadmap — se implementa DENTRO de las
existentes (V1.0 O4 el análisis 1; V1.1 H4 ampliado con Mission Learning + panel;
V1.2 los sprints de potenciación). Coherente con "nada amenaza la fecha de V1.0".

## 10. Revisión crítica — los riesgos del aprendizaje automático

| Riesgo | Realidad | Defensa |
|---|---|---|
| **Contaminación** (aprender basura de una racha de suerte) | el riesgo #1 de todo sistema self-improving | señal externa obligatoria + MIN_REP en contextos distintos + cuarentena + deprecate reversible |
| **Bucle de retroalimentación** (el sistema refuerza sus propios sesgos) | real: el LLM evalúa al LLM | §3.3: solo outcomes verificables o feedback humano cuentan como evidencia |
| **Sobre-aprendizaje de preferencias** (el usuario cambia; Aithera no) | real a años vista | recencia pondera quality_score; contradicciones (§7.2) preguntan, no asumen; TTL |
| **Coste silencioso** (reflexionar más de lo que se trabaja) | típico de reflection frameworks | Ollama-first, 1 llamada por misión, nada en camino corto, ≤3% CPU, presupuestos |
| **Privacidad** (skills que memorizan datos personales) | crítico si algún día hay GSN | PrivacyFilter en el NACIMIENTO de la skill (§3.3), no solo en el export |
| **Pérdida de confianza del usuario** (la IA "cambia sola") | fatal para el producto | panel de aprendizaje + undo + HITL en riesgo alto + nada opaco |
| **Proliferación de skills** (miles de skills-basura) | real en sistemas tipo Hermes | merge/dedup del Learner + umbral de evidencia para VALIDATED + deprecate por desuso |
| **El Learner como god-module** | riesgo de diseño | solo propone; fronteras del doc 16 §4.2 (no importa gateway/ai directo; escribe únicamente por APIs MOS/Skill) |

---
*Diseño 2026-07-12 (Fable 5). Extiende 09 (LSL/LLL); consume traces del TIE (14),
Decision/Error/Automation Memory (07/08/11). El AutomationLearner del doc 11 A.1
ES este módulo. Nada de este doc altera contratos del MOS más allá de los 4 deltas
listados en 14 §4.1.*
