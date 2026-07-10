# PROMPT DEFINITIVO PARA FABLE5 — LOCAL SKILL LIBRARY Y LOCAL LEARNING LOOP

> **Propósito**: Este documento cierra una laguna crítica en el diseño del MOS.
> Los documentos anteriores (PROMPT_01, PROMPT_03) diseñan las Capas 3 y 4 del MOS
> (Global Skill Network y Collective Intelligence Engine) como features de red/V2.0+.
> Esto es incorrecto: Aithera debe ser **totalmente autosuficiente en local**, con su
> propia red de skills y su propio motor de inteligencia, sin necesitar ningún usuario
> adicional ni conexión de red. La red global es una EXTENSIÓN opcional, no un
> PRERREQUISITO para aprender.
>
> **Principio rector**: Aithera sin red debe ser tan inteligente como Hermes en local.
> Aithera con red debe ser más inteligente que cualquier instancia individual.

---

## 1. EL ERROR DE DISEÑO QUE ESTE DOCUMENTO CORRIGE

En PROMPT_03, las Capas 3 y 4 se describen como:
- Capa 3 (Global Skill Network) → V2.0+, requiere red, requiere múltiples usuarios
- Capa 4 (Collective Intelligence Engine) → V2.0+, requiere muchas instancias

Esto es correcto para las versiones GLOBALES. Pero falta su equivalente local:

```
LO QUE FALTABA EN EL DISEÑO:
Capa 3-LOCAL: Local Skill Library     → siempre, sin red, una sola instancia
Capa 4-LOCAL: Local Learning Loop     → siempre, sin red, una sola instancia

LO QUE YA ESTABA DISEÑADO (opcional, requiere red):
Capa 3-GLOBAL: Global Skill Network   → V2.0+, multi-instancia, con red
Capa 4-GLOBAL: Collective Intel. Eng. → V2.0+, multi-instancia, con red
```

**El principio correcto**: un usuario que nunca conecta su Aithera a internet debe
tener un sistema de aprendizaje tan bueno como uno conectado, simplemente acotado a
sus propios datos. El conocimiento colectivo de la red amplifica el aprendizaje —
pero el aprendizaje no depende de la red.

---

## 2. LOCAL SKILL LIBRARY — DISEÑO

### 2.1 Qué es

La Local Skill Library (LSL) es la biblioteca de skills personal de cada instancia
de Aithera. Es el equivalente local de la Global Skill Network, con exactamente las
mismas features de calidad (versionado, validación, provenance, ciclo de vida), pero
privada y sin necesidad de red.

Diferencias con la GSN:
- LSL: una sola instancia, privada, siempre disponible offline
- GSN: miles de instancias, pública (solo conocimiento técnico anonimizado), requiere red

La LSL no es un subset de la GSN — es una librería independiente. Si el usuario
se conecta a la GSN, puede SINCRONIZAR su LSL con ella (subir skills locales
validadas, descargar skills globales útiles). Pero la LSL funciona perfectamente sin
esa sincronización.

### 2.2 Ciclo de vida de una skill en la LSL

```
DETECTED
  ↓  [Hermes o el Local Learning Loop detectan tarea repetida]
DRAFT
  ↓  [se guarda como borrador, sin validar]
VALIDATED
  ↓  [el usuario confirma que funciona, o el LLL la valida automáticamente]
LOCAL  ←──── punto de reposo normal para la mayoría de skills
  ↓  [si el usuario quiere compartirla]
PROPOSED_TO_GSN  [entra en el proceso de los Guardians]
  ↓
GLOBAL (en la GSN)
```

### 2.3 Estructura de una skill en la LSL

```python
@dataclass
class LocalSkill:
    id: UUID
    name: str
    version: str                      # semver: "1.0.0"
    description: str
    definition: dict                  # instrucciones/prompt/workflow
    input_schema: dict                # qué recibe
    output_schema: dict               # qué devuelve
    runtime_agnostic: bool            # True = funciona con cualquier runtime
    
    # Provenance (mismo sistema que la GSN, pero local)
    created_by: str                   # "hermes_detection" | "user" | "local_learning_loop"
    created_at: datetime
    evidence_count: int               # cuántas veces se ha ejecutado con éxito
    last_used: datetime
    use_count: int
    
    # Calidad
    status: SkillStatus               # DRAFT | VALIDATED | LOCAL | PROPOSED | DEPRECATED
    quality_score: float              # 0-1, calculado por LLL basado en resultados
    error_rate: float                 # % de ejecuciones que fallaron
    
    # Contexto
    projects: list[str]               # en qué proyectos se usa
    tags: list[str]
    
    # Sincronización (si el usuario conecta la GSN)
    gsn_id: UUID | None               # ID en la GSN si está publicada
    gsn_version: str | None           # versión que está en GSN (puede diferir de la local)
    gsn_last_sync: datetime | None
```

### 2.4 Versión de incorporación

La LSL se activa en **V1.1** (cuando Hermes empieza a detectar y generar skills).
En V0.85 ya existe el básico de Skill Memory (ChromaDB), pero el ciclo de vida
completo, el quality_score, el error_rate y la estructura formal se implementan en V1.1.

En V0.85 → V1.0: Skill Memory básico (guardar, buscar, ejecutar)
En V1.1: LSL completa (ciclo de vida, métricas, provenance, validación)
En V2.0+: Sincronización con GSN (opcional)

---

## 3. LOCAL LEARNING LOOP — DISEÑO

### 3.1 Qué es

El Local Learning Loop (LLL) es el motor de inteligencia personal de Aithera. Es
el equivalente local del Collective Intelligence Engine, pero opera sobre los datos
de UN SOLO usuario para detectar sus propios patrones, generar sus propias skills
y optimizar sus propios workflows.

No necesita a nadie más. No necesita red. Aprende de lo que Aithera ya sabe sobre
ti: tus conversaciones, tus proyectos, tus errores, tus decisiones, tus workflows.

### 3.2 Qué hace el LLL

**Detección de tareas repetidas**:
Cuando Aithera ejecuta la misma secuencia de acciones 3+ veces, el LLL la detecta
y propone convertirla en skill:
```
[Chat: "genera un docstring para esta función" × 15 veces en 2 semanas]
    ↓
LLL detecta: tarea repetida con alta frecuencia
    ↓
LLL propone: "He detectado que repites frecuentemente la generación de docstrings.
              ¿Quieres que cree una skill 'docstring_generator' con tu estilo preferido?"
    ↓
Usuario: "sí" → skill pasa a DRAFT → se valida automáticamente si funciona 3 veces más
```

**Detección de patrones de error**:
```
Error: "imports circulares en módulos Python" (detectado 4 veces en 2 meses)
    ↓
LLL: "Detectado patrón de error recurrente. Generando skill 'prevent_circular_imports'
      basada en tus soluciones anteriores."
```

**Detección de skills transferibles entre proyectos**:
```
Skill "format_sql_query" usada en Proyecto A con éxito
    ↓
LLL detecta: Proyecto B tiene estructura similar, misma tecnología
    ↓
LLL: "La skill 'format_sql_query' que usas en Aithera podría ser útil en tu proyecto
      de videojuego. ¿Quieres añadirla a ese proyecto también?"
```

**Evaluación de calidad de skills existentes**:
```
Skill "code_review_python" tiene error_rate=0.32 (32% de fallos)
    ↓
LLL: "La skill 'code_review_python' falla en 1 de cada 3 usos.
      He detectado el patrón: falla cuando el código tiene más de 200 líneas.
      ¿Quieres que la divida en dos skills: una para <200 líneas y otra para archivos grandes?"
```

**Generación de briefings de aprendizaje**:
```
LLL genera semanalmente: "Esta semana has aprendido:
- Nueva skill detectada: 'git_commit_conventional'
- Skill mejorada: 'python_refactor' (error_rate de 0.28 → 0.09)
- Patrón detectado: tardas 3x más cuando no tienes contexto de proyecto activo
- Recomendación: activa siempre el contexto de proyecto antes de tareas complejas"
```

### 3.3 Arquitectura del LLL

```python
class LocalLearningLoop:
    """
    Motor de aprendizaje personal. Se ejecuta como job asyncio en background.
    NO bloquea el event loop. Procesa en micro-batches.
    """
    
    async def run_cycle(self, memory: IMemoryStore, skill_library: LocalSkillLibrary):
        """
        Ciclo de análisis. Se ejecuta cada 6h en background.
        Micro-procesado: nunca más de 50 items por ciclo para no impactar rendimiento.
        """
        await self._detect_repeated_tasks(memory, skill_library)
        await self._evaluate_skill_quality(skill_library)
        await self._detect_transferable_skills(memory, skill_library)
        await self._detect_error_patterns(memory)
        await self._generate_improvement_proposals()
    
    async def _detect_repeated_tasks(self, memory, skill_library):
        """
        Analiza las últimas N conversaciones/ejecuciones buscando secuencias repetidas.
        Si la misma secuencia aparece >= MIN_REPETITIONS, propone skill.
        """
        ...
    
    async def _evaluate_skill_quality(self, skill_library):
        """
        Recalcula quality_score y error_rate de cada skill activa.
        Propone mejoras o deprecación si la calidad baja del umbral.
        """
        ...
```

**Cuándo se ejecuta**: como asyncio background task en el `lifespan` de FastAPI.
- Ciclo completo: cada 6 horas (configurable)
- Micro-análisis: cuando el usuario cierra una conversación (post-hoc, no bloqueante)
- Análisis urgente: cuando se detecta 3 errores del mismo tipo en la misma sesión

### 3.4 Versión de incorporación

V1.0 (básico): detección de tareas repetidas + propuesta de skills
V1.1 (con Hermes): detección de patrones compleja + evaluación de calidad + briefings
V1.2+: análisis predictivo (qué skill necesitarás para la tarea que estás describiendo)

---

## 4. SINCRONIZACIÓN CON LA RED GLOBAL (OPCIONAL)

Si el usuario activa la conexión a la GSN y el CIE:

### 4.1 Subida (Local → Global)

```
Usuario: "publicar mis skills validadas"
    ↓
LLL selecciona: skills en estado LOCAL con quality_score > 0.85 y evidence_count > 10
    ↓
Privacy filter: elimina referencias a proyectos privados, nombres, datos personales
    ↓
Propuesta de publicación: usuario revisa qué se va a publicar
    ↓
Usuario confirma → skill entra en proceso de Guardians de la GSN
```

**Nunca automático**: la subida a la red siempre requiere confirmación explícita.

### 4.2 Descarga (Global → Local)

```
GSN tiene skill "advanced_sql_optimization" que el usuario no tiene
LLL detecta que el usuario ejecuta queries SQL frecuentemente
    ↓
LLL: "La Global Skill Network tiene 12 skills de optimización SQL con alta calidad.
      ¿Quieres descargarlas a tu biblioteca local?"
    ↓
Usuario confirma → skills descargadas a LOCAL (no VALIDATED automáticamente)
    ↓
LLL evalúa en los siguientes usos → si funciona bien, pasa a VALIDATED
```

### 4.3 Aprendizaje bidireccional con el CIE

```
LLL: [detecta patrón local] "Los proyectos Python con más de 3 módulos circulares
      fallan el 70% de las veces en las primeras 2 semanas"

CIE: [devuelve insight global] "Globalmente, el patrón coincide con 12,000 instancias.
      El 94% de casos se resuelve con la skill 'dependency_injection_pattern'. Tu
      instancia tiene una variante personal que es 15% más efectiva en tu stack."
```

---

## 5. MAPA DE EVOLUCIÓN — LOCAL vs GLOBAL

| Componente | V0.85 | V1.0 | V1.1 | V2.0+ |
|------------|-------|------|------|-------|
| Skill Memory básico | ✅ ChromaDB | ✅ | ✅ | ✅ |
| Local Skill Library completa | ❌ stub | ❌ | ✅ | ✅ |
| Local Learning Loop básico | ❌ | ✅ básico | ✅ completo | ✅ |
| Sincronización con GSN | ❌ | ❌ | ❌ | ✅ opcional |
| Contribución al CIE | ❌ | ❌ | ❌ | ✅ opcional |
| Panel "Lo que Aithera ha aprendido" | ❌ | ❌ | ✅ | ✅ |

---

## 6. CÓMO ACTUALIZAR LOS DOCUMENTOS ANTERIORES

Fable5 debe propagar este diseño a los documentos anteriores:

**PROMPT_03**: En la tabla de tecnologías y en el mapa de evolución, añadir LSL y LLL
como componentes locales de Capa 3 y Capa 4. Reescribir la descripción de Capa 3
para distinguir claramente LSL (local, siempre) de GSN (red, opcional).

**PROMPT_04 (Roadmap Adaptation)**: V1.0 debe incluir el LLL básico. V1.1 debe incluir
LSL completa. V2.0+ es cuando se activan las versiones de red (GSN y CIE global).

**PROMPT_01 (V0.85 Skeleton)**: Añadir Skill Memory como "stub de LSL" — las colecciones
y contratos de V0.85 deben ser los mismos que usará la LSL completa en V1.1.

---

## 7. MISIÓN DE FABLE5

1. **Diseñar la LSL como componente formal**: contratos, ciclo de vida completo,
   `LocalSkill` dataclass con todos los campos, `LocalSkillLibrary` como servicio.

2. **Diseñar el LLL como servicio background**: arquitectura del job asyncio,
   estrategia de micro-batching para no impactar rendimiento, los 4-5 análisis
   principales con sus algoritmos (no implementación, solo diseño).

3. **Diseñar el protocolo de sincronización GSN ↔ LSL**: cómo se sube, cómo se
   baja, qué filtros de privacidad existen, qué confirma el usuario.

4. **Actualizar la tabla de evolución del MOS** en PROMPT_03 y PROMPT_04 para
   reflejar LSL y LLL como componentes locales de Capa 3 y Capa 4.

5. **Definir la regla de autosuficiencia**: Aithera en V1.1 sin red debe ser
   funcionalmente equivalente a Aithera en V2.0+ con red para el caso de un solo
   usuario. La red solo añade la inteligencia colectiva de otros usuarios — no
   elimina ninguna capacidad de la instancia local.

---

*Documento creado: 2026-07-09. Corrige la laguna de PROMPT_03 donde las Capas 3 y 4
se diseñaban solo como features de red. LSL y LLL son los equivalentes locales que
hacen que Aithera sea autosuficiente sin conexión.*
