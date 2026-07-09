# Frameworks de Agentes — Comparativa

## Resumen

Comparativa de frameworks de agentes LLM. Aithera V0.7.3 tiene `AgentManager` propio, no usa framework externo. Ver [JWIKI-106 aithera-agent-manager.md](./aithera-agent-manager.md).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Frameworks

| Framework | Stars | Paradigma | Aithera |
|---|---|---|---|
| **LangGraph** | 36.6k | State machines | ❌ |
| **CrewAI** | 55k | Crews of agents | ❌ |
| **AutoGen** | 59.5k | Actor model | ❌ |
| **Google ADK** | 20.5k | Vertex-native | ❌ |
| **OpenAI Agents SDK** | 28k | Handoffs | ❌ |
| **Semantic Kernel** | 23k | .NET-style | ❌ |
| **LlamaIndex** | 43k | RAG agents | ❌ |
| **Smolagents** | 22k | Lightweight | ❌ |
| **Strands (AWS)** | n/a | Bedrock-native | ❌ |
| **Aithera AgentManager** | n/a | Custom | ✅ V0.5+ |

## Por qué Aithera tiene su propio

- ✅ **Control total**: sin dependencia externa.
- ✅ **Aligned con FastAPI + SQLAlchemy**.
- ✅ **Tool integration custom** (8 tools Aithera-specific).
- ❌ Menos features que frameworks maduros.

## Comparativa paradigmas

- **LangGraph**: state machines, ciclo de control fino.
- **CrewAI**: role-based agents, sequential/hierarchical.
- **AutoGen**: conversaciones multi-agent, actor model.
- **Google ADK**: Vertex AI integration.
- **OpenAI Agents SDK**: handoffs nativos.

## Para Aithera V1.0

V1.0 Orchestrator借鉴:
- LangGraph state machines.
- CrewAI roles.
- Superpowers skills (agentskills.io).

V1.0 probablemente migre a un framework maduro o implemente su propio Orchestrator con esos patrones.

## Referencias cruzadas

- [JWIKI-105 langgraph-deep.md](./langgraph-deep.md)
- [JWIKI-106 aithera-agent-manager.md](./aithera-agent-manager.md)
- [JWIKI-117 agent-loops.md](./agent-loops.md)

## Fuentes

1. https://github.com/langchain-ai/langgraph
2. https://github.com/crewAIInc/crewAI
3. https://github.com/microsoft/autogen
4. https://google.github.io/adk-docs/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified