# PROMPT DEFINITIVO PARA FABLE5 — INTEGRACIÓN DE HERMES EN AITHERA

> **Propósito de este documento**: Briefing técnico + filosófico completo para que
> Fable5 diseñe el plan de integración de Hermes (Nous Research) en Aithera,
> considerando todo el PLAN_MAESTRO_2026 previo y las decisiones estratégicas del
> "Aithera Master Specification" (Memory System Prompts GPT.docx).
>
> **Qué debe entregar Fable5 tras leer esto**: Un documento de integración técnica
> para V1.1 Hermes que incluya arquitectura de adaptadores, interfaz AgentRuntime,
> plan de sprints y actualización del roadmap. Debe ser coherente con el diseño
> del MOS descrito en `PROMPT_01_MEMORY_MOS_V085.md`.

---

## 1. LA DECISIÓN ESTRATÉGICA MÁS IMPORTANTE

**Hermes NO es el núcleo de Aithera. Hermes es un motor intercambiable.**

Esta decisión es inviolable y cambia completamente cómo se diseña la integración.
Hermes se trata exactamente igual que se trata Claude, GPT o cualquier otro
proveedor de IA: como una implementación concreta detrás de una interfaz abstracta.

La analogía con el sistema actual:
```
Actual (proveedores IA):
    AIManager → IProvider → [OllamaProvider | OpenAIProvider | AnthropicProvider | ...]

Con Hermes (runtimes de agentes):
    Orchestrator → AgentRuntime → [HermesRuntime | FutureRuntime | ...]
```

Hermes es un `HermesRuntime`. Si en 2028 aparece un runtime mejor, se crea
`NewRuntime` y se registra. Aithera no pierde ni un byte de memoria ni una skill.

---

## 2. QUÉ APORTA HERMES (Y QUÉ NO LE PERTENECE)

### 2.1 Lo que Hermes aporta a Aithera

Hermes (https://hermes-agent.nousresearch.com/) es un sistema de agentes con
capacidades que Aithera aún no tiene y que sería costoso construir desde cero:

- **Prompt Builder avanzado**: construcción inteligente de prompts multi-etapa
- **Context Builder**: gestión de ventana de contexto con compresión y priorización
- **Planner**: descomposición de tareas complejas en pasos
- **Reflection Loop**: el agente evalúa su propio output y decide si es suficiente
- **Learning Loop**: aprende de sus errores y éxitos a lo largo del tiempo
- **Tool Use sofisticado**: uso de herramientas con retry, fallback y validación
- **Skill Detection**: detecta automáticamente qué skills necesita para una tarea
- **Skill Generation**: puede generar nuevas skills a partir de tareas repetidas
- **Gestión de sesiones**: mantiene contexto entre conversaciones largas
- **Gestión de Profiles**: perfiles de comportamiento por tipo de tarea

### 2.2 Lo que Hermes NO posee en la integración con Aithera

Hermes es el motor de razonamiento. Pero TODO el conocimiento, la memoria y las
herramientas pertenecen a Aithera:

| Activo | Propietario | Razón |
|--------|-------------|-------|
| Memoria conversacional | Aithera (MOS) | Si cambia el runtime, la memoria persiste |
| Memoria de proyectos | Aithera (MOS) | Idem |
| Skills aprendidas | Aithera (Skill Store) | Portables entre runtimes |
| Herramientas (ToolManager) | Aithera | Ya con whitelist y approval gates |
| Contexto de usuario | Aithera (MOS) | Privacidad y portabilidad |
| Knowledge base | Aithera (MOS) | El conocimiento no migra con el runtime |
| MCP connections | Aithera | Independientes del runtime |

**Resumen**: Hermes piensa. Aithera recuerda y decide qué ejecutar.

---

## 3. PRINCIPIO FUNDAMENTAL DE INTEGRACIÓN

**No modificar el núcleo de Hermes. Sustituir solo sus providers.**

Hermes tiene un sistema de providers para acceder a memoria, skills, herramientas
y contexto. En lugar de modificar Hermes internamente, se crean **adapters de
Aithera que implementan las interfaces de providers de Hermes**.

Hermes cree que trabaja con sus sistemas nativos. En realidad, todo pasa por
las APIs internas de Aithera:

```
Hermes.memory.save("recordar X")
    ↓
AitheraMemoryProvider.save()       ← adapter de Aithera
    ↓
MemoryAPI interna de Aithera
    ↓
MOS (IMemoryStore → LocalMemoryStore → ChromaDB)
```

Hermes nunca escribe directamente en archivos Markdown propios, en su SQLite
propio ni en ningún sistema que no sea Aithera. Si lo hiciera, ese conocimiento
quedaría atrapado en Hermes y no sería portable.

---

## 4. INTERFAZ `AgentRuntime` — EL CONTRATO CENTRAL

Esta interfaz se diseña en **V1.0 (Orchestrator)** y se implementa por primera
vez en **V1.1 (HermesRuntime)**. Es el contrato que hace que Hermes sea
intercambiable.

```python
# backend/app/orchestrator/runtime.py (V1.0)
from abc import ABC, abstractmethod
from typing import AsyncIterator
from app.memory.interfaces import IMemoryStore
from app.tools.tool_manager import ToolManager

class AgentRuntime(ABC):
    """
    Interfaz que todo runtime de agentes debe implementar.
    
    El Orchestrator NUNCA depende de HermesRuntime directamente.
    Siempre depende de AgentRuntime. Esto garantiza que Hermes
    sea sustituible sin tocar el Orchestrator.
    """

    @abstractmethod
    async def execute_task(
        self,
        task: "AgentTask",
        memory: IMemoryStore,
        tools: ToolManager,
        approval_gate: "ApprovalGate",
    ) -> "AgentResult":
        """
        Ejecuta una tarea delegada por el Orchestrator.
        
        El runtime recibe memoria y tools de Aithera.
        NUNCA los gestiona por su cuenta.
        """
        ...

    @abstractmethod
    async def stream_task(
        self,
        task: "AgentTask",
        memory: IMemoryStore,
        tools: ToolManager,
        approval_gate: "ApprovalGate",
    ) -> AsyncIterator["AgentChunk"]:
        """Versión streaming de execute_task."""
        ...

    @abstractmethod
    async def health_check(self) -> "RuntimeHealth":
        """Estado del runtime: disponible, modelo cargado, latencia estimada."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        """
        Qué puede hacer este runtime.
        Ejemplo: {"planning", "reflection", "skill_generation", "tool_use"}
        El Orchestrator usa esto para decidir qué runtime usar para qué tarea.
        """
        ...
```

Fable5 debe definir también: `AgentTask`, `AgentResult`, `AgentChunk`,
`RuntimeHealth`, `ApprovalGate`. Estos son los contratos que conectan
Orchestrator ↔ AgentRuntime.

---

## 5. LOS ADAPTERS DE AITHERA PARA HERMES

En V1.1 se crean estos adapters en `backend/app/hermes/providers/`:

### 5.1 `AitheraMemoryProvider`

```python
# backend/app/hermes/providers/memory_provider.py
class AitheraMemoryProvider:
    """
    Implementa la interfaz de memory provider que Hermes espera,
    pero guarda TODO en el MOS de Aithera (IMemoryStore).
    
    Hermes nunca sabe que existe ChromaDB.
    Hermes nunca sabe que existe SQLAlchemy.
    Hermes cree que habla con su propio sistema de memoria.
    """
    def __init__(self, memory_store: IMemoryStore):
        self._store = memory_store
    
    # Métodos que Hermes llama (según su API):
    async def save(self, key: str, value: str, metadata: dict) -> None:
        await self._store.store(
            content=value,
            memory_type=MemoryType.SKILL,  # o según metadata
            source="hermes",
            metadata=metadata,
        )
    
    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        results = await self._store.search(query, top_k=top_k)
        return [r.content for r in results]
```

### 5.2 `AitheraSkillProvider`

```python
# backend/app/hermes/providers/skill_provider.py
class AitheraSkillProvider:
    """
    Hermes detecta y genera skills. Este provider las guarda en
    el Skill Store de Aithera, no en los archivos de Hermes.
    """
    def __init__(self, skill_store: ISkillStore):
        self._store = skill_store
    
    async def save_skill(self, name: str, definition: dict) -> None:
        await self._store.store_skill(name, definition, source="hermes_generated")
    
    async def load_skill(self, name: str) -> dict | None:
        return await self._store.get_skill(name)
    
    async def list_skills(self) -> list[str]:
        return await self._store.list_skills()
```

### 5.3 `AitheraToolProvider`

```python
# backend/app/hermes/providers/tool_provider.py
class AitheraToolProvider:
    """
    Hermes ve las herramientas de Aithera como si fueran sus herramientas
    nativas. Pero toda ejecución pasa por el ToolManager de Aithera,
    con su whitelist y sus approval gates.
    
    Hermes NUNCA ejecuta herramientas directamente.
    """
    def __init__(self, tool_manager: ToolManager, approval_gate: ApprovalGate):
        self._tools = tool_manager
        self._gate = approval_gate
    
    async def execute_tool(self, tool_name: str, params: dict) -> dict:
        # Pasa por el gate antes de ejecutar
        if self._tools.requires_approval(tool_name):
            await self._gate.request_approval(tool_name, params)
        return await self._tools.execute(tool_name, params)
```

### 5.4 `AitheraContextProvider`

```python
# backend/app/hermes/providers/context_provider.py
class AitheraContextProvider:
    """
    Hermes construye contexto para sus prompts. Este provider
    enriquece ese contexto con memoria de Aithera: emails relevantes,
    proyectos activos, decisiones pasadas.
    """
    def __init__(self, memory_store: IMemoryStore):
        self._store = memory_store
    
    async def get_context(self, query: str) -> str:
        memories = await self._store.search(query, top_k=8)
        return self._format_context(memories)
```

---

## 6. FASES DE INTEGRACIÓN — ALINEADAS CON EL ROADMAP

### FASE 1 — V1.0: Preparar el terreno (Orchestrator)

En V1.0 se construye el Orchestrator. En este mismo sprint:
- Definir la interfaz `AgentRuntime` (ver sección 4)
- Definir los contratos `AgentTask`, `AgentResult`, `AgentChunk`
- El Orchestrator usa `AgentRuntime` sin ninguna implementación concreta todavía
- La implementación por defecto es `NullRuntime` (sin agentes externos, solo el
  flujo de chat actual)
- Los approval gates (V0.9) ya están construidos; `AgentRuntime` los reutiliza

**Hermes Desktop** en esta fase: herramienta de exploración y desarrollo. El equipo
(usuario + IA) lo usa para entender cómo funciona Hermes internamente, qué providers
expone, qué interfaces implementa. Esto alimenta el diseño de los adapters de V1.1.

### FASE 2 — V1.1: Integración inicial de Hermes Runtime

Objetivo: el Orchestrator puede delegar tareas a Hermes cuando conviene.

Trabajo de esta fase:
1. Investigar la API real de Hermes (qué providers expone, cómo se instancia,
   si es local o requiere servidor, licencia, restricciones)
2. Crear `HermesRuntime(AgentRuntime)` en `backend/app/hermes/runtime.py`
3. Crear los 4 adapters: `AitheraMemoryProvider`, `AitheraSkillProvider`,
   `AitheraToolProvider`, `AitheraContextProvider`
4. Inyectar los adapters en Hermes al instanciarlo
5. Tests de integración: verificar que Hermes usa los adapters y no sus sistemas nativos
6. Routing en el Orchestrator: qué tareas van a `HermesRuntime` vs `NullRuntime`

**Hermes Desktop en esta fase**: sigue disponible como herramienta de ingeniería
para el desarrollador. NO como interfaz del usuario final. El usuario interactúa
exclusivamente con el Hub de Aithera.

### FASE 3 — V1.2: MCP + Multi-instancia de Hermes

Las herramientas del ecosistema MCP (Model Context Protocol) se integran a través
de `AitheraToolProvider`, no directamente en Hermes. Hermes ve las tools MCP como
si fueran tools nativas de Aithera.

En esta fase, múltiples instancias de `HermesRuntime` pueden existir con perfiles
distintos:
- `ResearchHermesRuntime` — configurado para investigación profunda
- `CodingHermesRuntime` — configurado para tareas de código
- `CalendarHermesRuntime` — configurado para gestión de agenda

Cada instancia tiene su configuración y objetivo, pero **comparten el mismo MOS**.
No comparten conversaciones. Comparten conocimiento.

### FASE 4 — V1.4/V1.5: Hermes invisible

El usuario deja de usar Hermes Desktop completamente. Toda la experiencia está en
el Hub de Aithera. Hermes es un componente interno.

### FASE FUTURA — Si Aithera supera a Hermes

Si el Orchestrator y los sistemas propios de Aithera superan técnicamente a Hermes,
se crea una nueva implementación de `AgentRuntime` (`AitheraNativeRuntime`). Se
registra. Se prueba. Se migra el tráfico gradualmente. Hermes queda como fallback o
se desactiva. El conocimiento ya pertenece a Aithera — no se pierde nada.

---

## 7. PREGUNTAS QUE FABLE5 DEBE INVESTIGAR ANTES DE DISEÑAR V1.1

Antes de escribir el plan detallado de V1.1, Fable5 necesita responder:

1. **¿Cómo se instancia Hermes?** ¿Es un proceso separado (servidor), una librería
   Python importable, o una API REST? Esto determina cómo se integra en el
   `lifespan` de FastAPI.

2. **¿Qué interfaces/providers expone Hermes?** ¿Tiene una API de providers
   formal (como se asume en este documento) o hay que hacer ingeniería inversa?

3. **¿Cuál es la licencia de Hermes?** ¿Permite integración comercial/personal
   de esta forma? ¿Hay restricciones de uso?

4. **¿Hermes requiere conexión a internet?** Si necesita llamar a APIs externas
   de Nous Research, hay implicaciones de privacidad y disponibilidad.

5. **¿Qué modelo/runtime usa Hermes por defecto?** ¿Se puede configurar para
   usar el `AIManager` de Aithera como proveedor de LLM?

6. **¿Cuánto pesa en memoria?** El backend de Aithera ya tiene ChromaDB +
   sentence-transformers. Añadir Hermes no puede llevar el consumo a niveles
   inviables en un PC personal.

Fable5 debe incluir una sección "Investigación previa a V1.1" en su plan que
aborde estas preguntas como primer sprint de esa fase.

---

## 8. INTERFAZ DE USUARIO — HERMES ES INVISIBLE PARA EL USUARIO

El Hub de Aithera es el único punto de contacto del usuario. No hay "panel de
Hermes". No hay "chat de Hermes". No hay "Skills de Hermes".

Lo que el usuario SÍ verá en el Hub (a partir de V1.1):
- Las capacidades que tiene Aithera (que internamente usan Hermes)
- Las skills que Aithera ha aprendido (que Hermes detectó/generó, pero que
  pertenecen a Aithera)
- El panel de agentes (que internamente orquesta instancias de HermesRuntime)

Lo que el usuario NO verá:
- Que existe Hermes
- Que Hermes es un proceso separado
- Que hay múltiples instancias de runtime

**Principio**: el usuario interactúa con Aithera. Aithera elige qué motor usar.
Igual que cuando el usuario habla con Aithera no sabe si está usando Claude Opus
o Llama 3 — tampoco sabe si la tarea la ejecuta un runtime de Hermes o uno
nativo de Aithera.

---

## 9. ACTUALIZACIÓN DEL ROADMAP QUE FABLE5 DEBE PRODUCIR

Fable5 debe actualizar `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` con:

### 9.1 Nueva sección V1.0 (Orchestrator) — añadir

- Definición formal de la interfaz `AgentRuntime`
- Contratos `AgentTask`, `AgentResult`
- `NullRuntime` como implementación inicial
- Nota: V1.0 prepara la infraestructura; Hermes llega en V1.1

### 9.2 Reescribir sección V1.1 (Hermes)

La sección actual es vaga ("pendiente de diseño"). Con este documento, Fable5
puede escribirla con el mismo nivel de detalle que las secciones de V0.7.2-3 y V0.8.

Debe incluir:
- Las 4 fases de integración (sección 6 de este documento)
- Los 4 adapters con su descripción
- El plan de investigación previa (sección 7)
- Criterios de cierre: "Hermes ejecuta una tarea usando la memoria de Aithera
  sin escribir en ningún archivo propio de Hermes"

### 9.3 Añadir sección "Filosofía ACI"

Una sección corta al inicio del roadmap que documente:
- Qué es la ACI (Aithera Cognitive Infrastructure)
- Qué es el MOS (Memory Operating System)
- La interfaz `AgentRuntime` como mecanismo de extensión
- El principio "la memoria pertenece a Aithera"

---

## 10. DOCUMENTOS DE CONTEXTO QUE FABLE5 DEBE LEER ANTES DE DISEÑAR

En orden de prioridad:

1. `CLAUDE.md` — estado real del repositorio, stack, decisiones de diseño §18
2. `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` — roadmap actual
3. `PLAN_MAESTRO_2026/FABLE5_PROMPTS/PROMPT_01_MEMORY_MOS_V085.md` — diseño del
   MOS que Hermes usará a través de sus adapters
4. `PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md` — patrón de adapter de referencia
   (el Gateway usa el mismo patrón ChannelAdapter que usarán los AgentRuntime)
5. `backend/app/ai/ai_manager.py` — referencia de cómo Aithera ya gestiona
   múltiples proveedores intercambiables (el mismo patrón, aplicado a agentes)
6. `backend/app/tools/tool_manager.py` — el ToolManager que HermesRuntime usará
   a través de `AitheraToolProvider`

---

## 11. LO QUE FABLE5 NO DEBE DISEÑAR AÚN

Estas decisiones se toman cuando haya más información sobre Hermes real:

- Cómo arrancar/detener Hermes en el `lifespan` (depende de si es lib o server)
- El formato exacto de `AgentTask` y `AgentResult` (depende de la API real de Hermes)
- Si se necesita un proceso supervisor para las instancias de Hermes
- Cómo gestionar el consumo de memoria de múltiples instancias simultáneas

Fable5 puede proponer diseños tentativos para estos puntos, pero deben marcarse
explícitamente como **[pendiente de investigación de Hermes API]**.

---

## 12. MISIÓN DE FABLE5 PARA ESTE DOCUMENTO

1. **RFC de integración Hermes**: documento técnico formal que cubra la interfaz
   `AgentRuntime`, los 4 adapters y el protocolo de comunicación Orchestrator ↔ Hermes.

2. **Plan de investigación V1.1**: qué hay que descubrir sobre Hermes antes de
   escribir código, y cómo (docs, repo OSS, Discord de Nous Research, prueba local).

3. **Sprints de V1.1**: asumiendo que la investigación previa revela respuestas
   positivas (Hermes es una lib Python, permite configurar providers, es viable
   en local), cuál es el plan de sprints con Opus 4.8.

4. **Plan de contingencia**: si la investigación revela que Hermes no tiene API
   de providers, o que no permite la integración de la forma planificada, qué
   hacer en su lugar (¿otro runtime? ¿construir capacidades de Hermes de forma
   nativa en Aithera?).

5. **Actualización del roadmap V1.0 y V1.1** como se describe en la sección 9.

---

*Documento creado: 2026-07-09 — Integración Hermes planificada para V1.1, posterior
al Orchestrator (V1.0). El diseño de los adapters depende del diseño del MOS
(PROMPT_01_MEMORY_MOS_V085.md). Ambos documentos deben leerse juntos.*
