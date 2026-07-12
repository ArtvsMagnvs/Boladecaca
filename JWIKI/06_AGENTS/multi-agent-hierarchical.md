# Multi-Agent Jerárquico — Sub-agents + Manager

## Resumen

**Multi-agent jerárquico** tiene un manager agent que delega a sub-agents especializados. Patrón借鉴 CrewAI Hierarchical Process y Google ADK.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Estructura

```
Manager Agent
  ├── Researcher sub-agent (web_search, memory_search)
  ├── Coder sub-agent (filesystem, shell, git)
  └── Reviewer sub-agent (memory_search)
```

## Implementación

```python
class HierarchicalAgent:
    def __init__(self, manager_llm, sub_agents: dict):
        self.manager_llm = manager_llm
        self.sub_agents = sub_agents
    
    async def run(self, task: str) -> str:
        # 1. Manager decides which sub-agent to call
        plan = await self.manager_llm.chat(
            f"Tarea: {task}\nSub-agents disponibles: {list(self.sub_agents.keys())}\n"
            f"¿Qué sub-agent usar?"
        )
        
        # 2. Delegate to sub-agent
        sub_name = extract_sub_agent_name(plan)
        sub = self.sub_agents[sub_name]
        result = await sub.run(task)
        
        # 3. Manager synthesizes
        final = await self.manager_llm.chat(
            f"Tarea original: {task}\n"
            f"Output de {sub_name}: {result}\n"
            f"Sintetiza una respuesta final coherente."
        )
        return final
```

## Aithera V1.0+ plan

V1.0 Orchestrator借鉴 este patrón:
- ✅ **Orchestrator** (manager) clasifica intent.
- ✅ **Specialist agents** (coder, researcher, reviewer).
- ✅ **Synthesizer** combina resultados.

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Especialización | ❌ Más complejo de debuggear |
| ✅ Modular (add sub-agent) | ❌ Más costoso (multi-LLM calls) |
| ✅ Escalable | ❌ Manager puede equivocarse |

## CrewAI借鉴

CrewAI Hierarchical Process:
- Manager agent = "manager_llm" (configurable).
- Auto-delegation: manager decides qué agent usar.
- Aithera借鉴 este patrón en V1.0.

## Para Aithera V1.0

```python
# V1.0 Orchestrator
orchestrator = HierarchicalAgent(
    manager_llm=claude_opus_4_8,
    sub_agents={
        "researcher": ResearcherAgent(...),
        "coder": CoderAgent(...),
        "emailer": EmailAgent(...)
    }
)
```

## Referencias cruzadas

- [JWIKI-012 crewai.md](../01_LANDSCAPE/crewai.md)
- [JWIKI-014 google-adk.md](../01_LANDSCAPE/google-adk.md)
- [JWIKI-055 orchestrator-pattern.md](../02_ARCHITECTURE/orchestrator-pattern.md)

## Fuentes

1. https://docs.crewai.com/core-concepts/Processes/
2. https://google.github.io/adk-docs/agents/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified