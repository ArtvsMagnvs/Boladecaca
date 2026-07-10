# PROMPT DEFINITIVO PARA FABLE5 — DISEÑO COMPLETO DEL MOS (V0.85 → V2.0+)

> **Propósito**: Fable5 debe diseñar la arquitectura COMPLETA del Memory Operating
> System de Aithera, desde V0.85 hasta V2.0+. Esto es un documento de DISEÑO PURO:
> sin código de implementación, sin sprints. El resultado esperado es un conjunto de
> RFCs técnicos que definan contratos, tecnologías, capas, APIs y estrategia de
> evolución del sistema de memoria durante los próximos 5-10 años.
>
> **Relación con PROMPT_01**: PROMPT_01 pide el plan de implementación de V0.85.
> Este PROMPT_03 pide el diseño de la visión completa que V0.85 debe prefigurar.
> Fable5 debe leer AMBOS. El diseño completo informa los contratos del skeleton.

---

## 1. FILOSOFÍA — LO QUE NO ES EL MOS

El MOS no es ninguna de estas cosas:

- **No es una base de datos**: las bases de datos almacenan. El MOS entiende,
  conecta, razona sobre el conocimiento y decide qué recordar.
- **No es un sistema RAG**: el RAG recupera documentos similares. El MOS
  transforma la información en conocimiento estructurado con relaciones,
  provenance y gobernanza.
- **No es la memoria de un chatbot**: los chatbots olvidan entre sesiones. El MOS
  acumula conocimiento durante años, a través de proyectos, runtimes y modelos.
- **No pertenece a ningún modelo de IA**: si Aithera cambia de Claude a GPT a
  Hermes a un modelo futuro, el MOS no cambia. La memoria pertenece a Aithera.

**La analogía correcta**: el MOS es una mezcla de Wikipedia (conocimiento colectivo
estructurado), Git (versionado e historia de decisiones), Linux (modularidad, cada
componente hace una sola cosa), Stack Overflow (conocimiento técnico validado por
la comunidad), PubMed (provenance y citación de fuentes) y un Sistema Operativo
(gestiona recursos de conocimiento como el OS gestiona CPU y RAM). Todo esto,
adaptado al aprendizaje de agentes de IA.

---

## 2. ARQUITECTURA DE DOS NIVELES

El MOS se organiza en dos niveles que Fable5 debe diseñar por separado.

### NIVEL INTERNO — Los componentes técnicos (invisible al usuario)

Son los subsistemas que procesan y almacenan información. El usuario nunca
interactúa directamente con ellos:

| Componente | Descripción | Tecnología de referencia |
|------------|-------------|--------------------------|
| **Conversational Memory** | Historial de conversaciones, embeddings, RAG | ChromaDB (V0.85) → Qdrant (V1.x+) |
| **Working Memory** | Estado vivo del agente en una sesión activa | Letta |
| **Semantic Memory** | Hechos, conceptos, relaciones semánticas | Qdrant + KuzuDB |
| **Episodic Memory** | Experiencias completas con contexto causal | Graphiti + Zep |
| **Knowledge Engine** | Documentación, PDFs, repositorios, APIs indexadas | Cognee |
| **Decision Memory** | Decisiones técnicas con alternativas y resultado | PostgreSQL + KuzuDB |
| **Error Memory** | Errores, causas, soluciones, patrones detectados | PostgreSQL + ChromaDB |
| **Tool Memory** | Qué herramientas funcionan mejor para qué tareas | PostgreSQL |
| **Automation Memory** | Reglas, workflows, automatizaciones aprendidas | PostgreSQL |
| **Skill Memory** | Skills detectadas, generadas o importadas | Skill Engine propio |
| **Context Memory** | Contexto activo del usuario: proyectos, objetivos | Mem0 |

**Regla de oro**: ningún componente del nivel interno puede ser accedido
directamente por el Orchestrator, el chat o Hermes. Todo acceso es a través
de las APIs del nivel lógico (sección 4).

### NIVEL LÓGICO — Las cuatro capas (visible arquitectónicamente)

Son las cuatro abstracciones públicas del MOS. El Orchestrator, Hermes y las
automatizaciones hablan con estas capas, nunca con los componentes internos:

```
┌─────────────────────────────────────────────────────────────┐
│                  AITHERA (usuario)                          │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                 ┌────────────────▼────────────────┐
                 │    MEMORY OPERATING SYSTEM       │
                 │                                  │
                 │  ┌──────────────────────────┐    │
                 │  │  CAPA 1: PRIVATE MEMORY  │    │ ← V0.85
                 │  └──────────────────────────┘    │
                 │  ┌──────────────────────────┐    │
                 │  │  CAPA 2: PROJECT MEMORY  │    │ ← V1.0-V1.2
                 │  └──────────────────────────┘    │
                 │  ┌──────────────────────────┐    │
                 │  │  CAPA 3: GLOBAL SKILL    │    │ ← V2.0+
                 │  │         NETWORK          │    │
                 │  └──────────────────────────┘    │
                 │  ┌──────────────────────────┐    │
                 │  │  CAPA 4: COLLECTIVE      │    │ ← V2.0+
                 │  │         INTELLIGENCE     │    │
                 │  └──────────────────────────┘    │
                 └─────────────────────────────────-┘
```

---

## 3. LAS CUATRO CAPAS LÓGICAS — DISEÑO DETALLADO

### CAPA 1 — PRIVATE MEMORY (V0.85)

**Qué contiene**: toda la información personal del usuario que nunca puede salir
de su dispositivo ni filtrarse a ninguna otra capa.

Categorías de información:
- Preferencias y hábitos de trabajo
- Objetivos personales y profesionales
- Proyectos y su estado
- Contactos, relaciones, nombres
- Emails y calendarios (indexados, no copiados)
- Credenciales, tokens, API keys (cifradas con DPAPI)
- Formas de trabajar, rutinas detectadas
- Decisiones personales tomadas
- Errores cometidos y soluciones encontradas
- Skills personales desarrolladas

**Principio de aislamiento**: la Private Memory debe estar separada por diseño
arquitectónico, no solo por permisos. Debe ser imposible por construcción que
un agente envíe contenido de Private Memory a la red. El aislamiento no es una
regla — es una restricción estructural de la arquitectura.

**Implementación por versión**:
- V0.85: ChromaDB local, sin acceso externo, colecciones aisladas
- V1.x: Qdrant local con cifrado en reposo, vault Markdown
- V2.0+: Private Memory Node aislado, sin conexión con GSN ni CIE

### CAPA 2 — PROJECT MEMORY (V1.0–V1.2)

**Qué contiene**: la memoria de cada proyecto, separada por proyecto, con su
propio sistema de permisos.

Estructura por proyecto:
```
ProjectMemory/
  ├── Aithera/
  │   ├── roadmap/       (decisiones de arquitectura, versiones)
  │   ├── bugs/          (errores encontrados, soluciones aplicadas)
  │   ├── architecture/  (decisiones técnicas con alternativas)
  │   ├── decisions/     (por qué se eligió X sobre Y)
  │   ├── skills/        (skills específicas del proyecto)
  │   ├── context/       (estado actual, objetivos, deuda técnica)
  │   └── docs/          (documentación técnica indexada)
  ├── Videojuego/
  └── Empresa/
```

**Permisos**: la Project Memory puede compartirse entre dispositivos o con
colaboradores autorizados. Debe existir un sistema de permisos granular
(read / write / admin por proyecto y por usuario).

**Relación con la memoria episódica**: cada bug resuelto, cada decisión técnica,
cada experimento fallido queda registrado en Episodic Memory bajo el proyecto
correspondiente. La Project Memory es la vista organizada de esa historia.

### CAPA 3 — GLOBAL SKILL NETWORK (V2.0+)

**Lo que es**: una red distribuida mundial de conocimiento TÉCNICO reutilizable.
No es una red social. No almacena conversaciones, usuarios ni datos privados.

**Lo que contiene exclusivamente**:
- Skills validadas y versionadas
- Workflows probados y benchmarkeados
- Patrones de arquitectura con evidencias
- Buenas prácticas con métricas de efectividad
- Automatizaciones reutilizables
- Documentación técnica de referencia

**Lo que JAMÁS contiene**:
- Conversaciones
- Preferencias personales
- Datos de usuarios
- Nombres, emails, proyectos privados
- Nada que pueda identificar a ninguna persona

**Diseño como plataforma abierta**: la GSN no es exclusiva de Aithera. Debe
diseñarse desde el principio como una plataforma a la que otros asistentes
(con otros runtimes, otros modelos, otras arquitecturas) puedan conectarse,
siempre respetando el protocolo. Fable5 debe diseñar:
- API pública con autenticación y rate limiting
- Sistema de versionado de skills (semver)
- Sistema de permisos de contribución
- Mecanismo de validación previa a publicación
- Protocolo de compatibilidad entre versiones
- Sistema de retiro y archivado de skills obsoletas
- Mecanismo de prevención de contaminación del ecosistema

### CAPA 4 — COLLECTIVE INTELLIGENCE ENGINE (V2.0+)

**Lo que es**: el componente más avanzado. No almacena información — la analiza
para generar conocimiento nuevo. Opera exclusivamente sobre información anonimizada
y previamente autorizada por la GSN.

**Lo que hace**:
1. Detecta que miles de instancias resuelven el mismo problema de formas distintas
2. Compara las soluciones estadísticamente
3. Detecta qué enfoque produce mejores resultados
4. Genera una propuesta de nueva Skill o mejora de Skill existente
5. Envía la propuesta al sistema de validación (Guardians)
6. Si es aprobada, la publica en la GSN con provenance completo

**Ejemplos concretos de detección de patrones**:
- "El workflow X produce un 35% menos de errores que Y en proyectos Python"
- "Los agentes que aplican el patrón Z antes de codificar necesitan 2x menos
  iteraciones para completar la tarea"
- "La Skill de refactoring A está obsoleta: la nueva versión B tiene 10x
  más adopción y mejores métricas"

**Principio fundamental**: el CIE propone, nunca decide. Toda propuesta pasa por
los Guardians antes de tocar la GSN.

---

## 4. LAS APIS DEL MOS — CONTRATOS PÚBLICOS

Fable5 debe diseñar estas APIs como interfaces formales. Son el contrato que
jamás cambia (aunque la implementación evolucione):

### Memory API
```
add(content, type, project?, metadata?) → MemoryId
search(query, type?, project?, top_k?) → [Memory]
update(id, content, metadata?) → void
delete(id, reason?) → void
context(query, max_tokens?) → ContextWindow
forget(scope, criteria?) → int  # borra por criterio
```

### Decision API
```
storeDecision(decision, reason, alternatives, project?) → DecisionId
searchDecisions(query, project?) → [Decision]
linkDecisionToOutcome(id, outcome, impact) → void
getDecisionHistory(project?) → [Decision]
```

### Skill API
```
create(name, definition, source, project?) → SkillId
improve(id, improvement, evidence) → SkillVersion
validate(id) → ValidationResult
publish(id) → void  # solo si pasa validación y está en GSN
list(project?, tags?) → [Skill]
execute(id, params) → SkillResult
```

### Knowledge API
```
index(source, type, project?) → void  # PDF, URL, repo, manual
retrieve(query, project?) → [KnowledgeChunk]
link(id1, id2, relation) → void
getGraph(entity, depth?) → KnowledgeGraph
```

### Graph API
```
linkEntities(entity1, entity2, relation, weight?) → void
findRelations(entity, relation?, depth?) → [Entity]
shortestPath(from, to) → [Entity]
```

### Context API
```
buildContext(query, max_tokens, sources?) → Context
compress(context, target_tokens) → Context
summarize(context, format?) → string
```

**Regla para Fable5**: cada API debe ser una interfaz Python (`Protocol` o `ABC`),
no una clase concreta. La implementación concreta es intercambiable. El Orchestrator
y Hermes solo ven las interfaces, nunca la implementación.

---

## 5. SISTEMAS ESPECIALIZADOS DENTRO DEL MOS

### 5.1 Sistema de Decisiones

Cada decisión técnica importante se almacena con:

```
Decision {
    id: UUID
    title: str
    body: str                    # la decisión en sí
    reason: str                  # por qué se tomó
    alternatives: [Alternative]  # qué más se consideró
    date: datetime
    project: str | None
    outcome: str | None          # se rellena después
    impact: Enum(HIGH|MED|LOW)
    status: Enum(ACTIVE|SUPERSEDED|ARCHIVED)
    superseded_by: DecisionId | None
}
```

Propósito: nunca repetir el mismo debate técnico. Si alguien (o un agente) pregunta
"¿por qué usamos PostgreSQL en lugar de MongoDB?", el sistema recupera la decisión
con todas sus alternativas y el outcome observado.

### 5.2 Sistema de Errores

Todo error se convierte en conocimiento:

```
ErrorRecord {
    id: UUID
    title: str
    cause: str
    solution: str
    time_to_solve: duration
    project: str | None
    files_affected: [str]
    runtime: str               # Hermes, Claude, etc.
    model: str
    tools_used: [str]
    pattern_tag: str | None    # si es parte de un patrón detectado
}
```

El sistema detecta automáticamente cuando el mismo tipo de error aparece repetidamente
y genera una entrada en Skill Memory para evitarlo en el futuro.

### 5.3 Skill Engine

Las Skills son la unidad atómica de conocimiento reutilizable. Una Skill es:
- Independiente del runtime (funciona con Hermes, con Claude nativo, con cualquier
  runtime futuro)
- Independiente del modelo (no asume que el modelo es Claude Opus o Llama 3)
- Versionada (semver: 1.0.0 → 1.1.0 si mejora, 2.0.0 si cambia el contrato)
- Trazable (provenance: quién la creó, cuándo, con qué evidencia)
- Validada (no entra en la GSN sin pasar por Guardians)

Ciclo de vida de una Skill:
```
DETECTED (por Hermes o por el usuario)
    ↓
DRAFT (guardada en Private Memory, solo para el usuario)
    ↓
VALIDATED (el usuario o un agente verifica que funciona)
    ↓
LOCAL (disponible en todas las sesiones del usuario)
    ↓ (si el usuario decide publicarla)
PROPOSED (enviada a la GSN con provenance)
    ↓ (si los Guardians la aprueban)
PUBLISHED (disponible para toda la red)
    ↓ (si supera umbral de uso/calidad)
PROMOTED (marcada como skill de referencia)
```

---

## 6. GUARDIANS — ARQUITECTURA DE PROTECCIÓN

Los Guardians son un tipo especial de agentes que NO trabajan para el usuario.
Trabajan exclusivamente para proteger la integridad del conocimiento colectivo.

**Principio**: los Guardians son el sistema inmunológico del MOS. No crean conocimiento;
lo protegen de la degradación, contaminación y manipulación.

### 6.1 Funciones de los Guardians

**Validación de contenido**:
- Detectar spam y contenido repetido (deduplicación semántica)
- Detectar skills falsas o incorrectas (validación técnica)
- Detectar malas prácticas presentadas como buenas
- Detectar código malicioso en workflows
- Detectar intentos de introducir información privada en la GSN

**Validación de calidad**:
- Detectar aprendizaje de baja calidad o insuficientemente evidenciado
- Detectar skills obsoletas (ya existe una versión mejor)
- Detectar duplicados con minor variaciones
- Evaluar la evidencia que respalda cada skill (¿cuántos casos la validan?)

**Protección del sistema**:
- Detectar intentos de manipular el Collective Intelligence Engine
- Detectar intentos de sesgar el conocimiento colectivo
- Supervisar la integridad del sistema
- Detectar y aislar corrupciones

**Resolución de contradicciones**:
- Detectar cuando dos skills o decisiones son incompatibles
- Comparar las evidencias de cada versión
- Proponer resolución o crear ramas si no hay consenso

### 6.2 Arquitectura de los Guardians

Los Guardians son instancias de `AgentRuntime` (ver PROMPT_02) con un perfil
especializado:

```python
class GuardianRuntime(AgentRuntime):
    """
    Runtime especializado para protección del conocimiento colectivo.
    No responde a usuarios. Solo procesa propuestas de la GSN y del CIE.
    """
    capabilities = {"validation", "deduplication", "conflict_detection", "provenance_audit"}
    
    async def validate_skill_proposal(self, proposal: SkillProposal) -> ValidationResult:
        ...
    
    async def detect_contradiction(self, skill1: Skill, skill2: Skill) -> ConflictReport:
        ...
    
    async def audit_provenance(self, skill: Skill) -> ProvenanceAudit:
        ...
```

**Importante**: los Guardians no tienen acceso a Private Memory ni a Project Memory.
Solo pueden leer y escribir en la GSN y el CIE. Esta es una restricción arquitectónica,
no un permiso. Fable5 debe diseñar cómo se implementa este aislamiento.

---

## 7. PROVENANCE, GOVERNANCE, CONTRADICTIONS Y ACCESS CONTROL

### 7.1 Provenance

Toda pieza de conocimiento en la GSN debe poder rastrear su origen completo:

```
Provenance {
    created_by: AgentRuntimeType       # HermesRuntime, AithereNativeRuntime...
    created_in_version: str            # versión de Aithera
    created_context: str               # qué tarea generó la skill
    evidence_count: int                # cuántos casos la respaldan
    validations_passed: [ValidationId] # qué Guardians la validaron
    change_log: [ChangeEntry]          # toda la historia de modificaciones
    supersedes: SkillId | None         # skill anterior que reemplaza
}
```

### 7.2 Governance

No cualquier instancia puede publicar en la GSN. Fable5 debe diseñar:

- **Quién puede proponer**: cualquier instancia autenticada de Aithera
- **Quién valida**: al menos N Guardians independientes (configuración del sistema)
- **Proceso de revisión**: propuesta → validación automática → revisión Guardian →
  aprobación → publicación
- **Versionado**: semver estricto, sin romper compatibilidad en minor versions
- **Retiro**: proceso formal para marcar skills como deprecated o retiradas
- **Archivado**: las skills retiradas no se borran, se archivan con historia

### 7.3 Contradictions

Cuando el CIE detecta dos skills o decisiones contradictorias:

1. Crear una `ConflictReport` con ambas versiones y sus evidencias
2. Los Guardians analizan las evidencias
3. Si hay consenso claro: la versión con más/mejor evidencia prevalece
4. Si no hay consenso: se crean dos branches (A y B) con sus contextos
5. El historial de la contradicción queda en Provenance
6. Los usuarios pueden elegir qué branch usar en su contexto

### 7.4 Access Control — Aislamiento arquitectónico

El principio fundamental: la información privada no puede llegar a la GSN por
**diseño**, no por **permisos**. Los permisos se pueden saltar; el diseño no.

Fable5 debe proponer mecanismos de aislamiento arquitectónico para:
- Que Private Memory nunca tenga una ruta de escritura directa a la GSN
- Que Project Memory solo pueda llegar a la GSN a través de Skill API (extrayendo
  solo el conocimiento técnico generalizable, nunca el contexto privado)
- Que el CIE opere solo sobre datos ya anonimizados y validados por Guardians

---

## 8. TECNOLOGÍAS Y SU ROL EN LA ARQUITECTURA FINAL

Fable5 debe evaluar y diseñar cómo encajan estas tecnologías en el MOS. En V0.85
se usa el mínimo. En versiones futuras se incorporan las demás.

| Tecnología | Rol en el MOS | Versión de incorporación |
|------------|---------------|--------------------------|
| **ChromaDB** | Conversational Memory, Private Memory (V0.85) | V0.85 (ya existe) |
| **Qdrant** | Vector DB de producción (reemplaza ChromaDB) | V1.x |
| **KuzuDB** | Knowledge Graph (relaciones entre entidades) | V1.0–V1.2 |
| **Mem0** | Private Memory / Context Memory automatizado | V1.x |
| **Letta** | Working Memory (estado de agente por sesión) | V1.1 (con Hermes) |
| **Graphiti + Zep** | Episodic Memory (experiencias con contexto causal) | V1.2+ |
| **Cognee** | Knowledge Engine (docs, repos, PDFs estructurados) | V1.2+ |
| **PostgreSQL** | Decisiones, errores, configuración, logs (ya existe) | V0.85 (ya existe) |
| **Markdown + Git** | Vault legible, documentación histórica | V0.85 (opcional) |

**Principio para Fable5**: el diseño de las interfaces (`IMemoryStore`, `ISkillStore`,
etc.) debe ser agnóstico respecto a la tecnología subyacente. Si en V1.x se migra
de ChromaDB a Qdrant, el Orchestrator y Hermes no deben notar el cambio.

### Estrategia de migración sin trauma

Fable5 debe diseñar la estrategia de migración tecnológica:
- V0.85 → V1.x: ChromaDB → Qdrant. Cómo migrar datos sin downtime.
- V1.x → V2.0+: añadir KuzuDB y Mem0 sin modificar las interfaces existentes.
- Rollback: si una tecnología nueva falla, cómo volver a la anterior.

---

## 9. CÓMO CONECTA EL DISEÑO COMPLETO CON V0.85

El diseño completo del MOS informa el diseño del skeleton de V0.85 de dos formas:

**1. Los contratos de interfaz son los definitivos**: las interfaces `IMemoryStore`,
`ISkillStore`, etc. que Fable5 define en PROMPT_01 (V0.85) deben ser las mismas
que usará el MOS completo en V2.0+. No son interfaces "provisionales". Son las
interfaces que durarán 10 años.

**2. Los nombres de capas son los definitivos**: las colecciones ChromaDB de V0.85
deben estar nombradas según las capas lógicas del MOS (no según la tecnología).
Por ejemplo: no `conversational_chromadb`, sino `mem_conversational`. Cuando se
migre a Qdrant, el nombre de la capa no cambia.

**3. Los tipos de memoria son los definitivos**: los 5 tipos de V0.85 (`mem_conversational`,
`mem_personal`, `mem_project`, `mem_skill`, `mem_decision`) son un subconjunto de
los 11 tipos del nivel interno. Los 6 restantes se añaden en versiones posteriores
sin cambiar los 5 originales.

---

## 10. MISIÓN DE FABLE5 PARA ESTE DOCUMENTO

Fable5 debe producir los siguientes entregables (todo diseño, sin código):

1. **RFC-001: Arquitectura general del MOS** — diagrama completo de componentes,
   capas, flujos de datos y puntos de extensión.

2. **RFC-002: APIs del MOS** — especificación formal de todas las APIs (sección 4),
   con tipos completos, pre/post condiciones y ejemplos de uso.

3. **RFC-003: Guardians** — diseño de la arquitectura de Guardians: cómo se instancian,
   qué procesan, cómo se comunican con la GSN, qué permisos tienen.

4. **RFC-004: Global Skill Network** — diseño de la red: protocolo de publicación,
   sistema de versionado, API pública, gobernanza, prevención de contaminación.

5. **RFC-005: Collective Intelligence Engine** — diseño del motor: cómo detecta
   patrones, cómo propone skills, cómo interactúa con Guardians.

6. **RFC-006: Estrategia de migración tecnológica** — cómo evolucionar de ChromaDB
   a la stack completa sin trauma ni downtime.

7. **Mapa de evolución**: tabla que muestra qué componentes del MOS están activos
   en cada versión (V0.85, V1.0, V1.2, V2.0+).

8. **Detección de riesgos**: para cada capa y componente, qué puede fallar, cómo
   se detecta y cómo se mitiga.

---

## 11. DOCUMENTOS DE CONTEXTO QUE FABLE5 DEBE LEER

1. `CLAUDE.md` — stack real del proyecto, modelos, decisiones §18
2. `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` — roadmap actual
3. `PLAN_MAESTRO_2026/FABLE5_PROMPTS/PROMPT_01_MEMORY_MOS_V085.md` — skeleton V0.85
4. `PLAN_MAESTRO_2026/FABLE5_PROMPTS/PROMPT_02_HERMES_INTEGRATION.md` — cómo Hermes usa el MOS
5. `PLAN_MAESTRO_2026/FABLE5_PROMPTS/PROMPT_04_ROADMAP_ADAPTATION.md` — cómo V0.9/V1.0/V1.1 se adaptan
6. `backend/app/memory/memory_manager.py` — estado actual del sistema de memoria

---

*Documento creado: 2026-07-09. Este es el diseño de la visión completa del MOS.
No contiene plan de implementación (ese está en PROMPT_01). La implementación
de capas avanzadas (GSN, CIE, Guardians) pertenece a V2.0+, pero los contratos
se definen ya en V0.85 para evitar migraciones traumáticas.*
