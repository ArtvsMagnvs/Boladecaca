# Handoffs / Delegation — OpenAI Agents SDK

## Resumen

**Handoffs** es el patrón nativo de OpenAI Agents SDK donde un agent puede **transferir** el control a otro agent. Aithera借鉴 para V1.0.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## OpenAI Agents SDK pattern

```python
from agents import Agent, Runner

billing_agent = Agent(
    name="Billing Agent",
    instructions="Handle billing questions.",
    tools=[get_balance, process_payment]
)

refund_agent = Agent(
    name="Refund Agent",
    instructions="Handle refunds.",
    tools=[process_refund]
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="Route to the appropriate agent.",
    handoffs=[billing_agent, refund_agent]  # <- handoffs
)

result = await Runner.run(triage_agent, "I want a refund")
```

## Aithera借鉴 V1.0

```python
class AitheraOrchestrator:
    def __init__(self):
        self.email_agent = Agent(
            name="EmailAgent",
            tools=[email.send, email.search, email.triage],
            system_prompt="Eres el agente de email."
        )
        self.calendar_agent = Agent(
            name="CalendarAgent",
            tools=[calendar.create_event, calendar.check_availability],
            system_prompt="Eres el agente de calendario."
        )
        self.coder_agent = Agent(
            name="CoderAgent",
            tools=[filesystem, shell, git],
            system_prompt="Eres el agente de código."
        )
        
        self.triage = Agent(
            name="TriageAgent",
            handoffs=[self.email_agent, self.calendar_agent, self.coder_agent],
            system_prompt="Clasifica el intent y haz handoff."
        )
```

## Cuándo usar handoffs

- ✅ **Multi-domain agents** (cada agent especialista).
- ✅ **Clear handoff conditions** (intent classification).
- ❌ **Single-task agents** (overhead).

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Modular (1 agent per domain) | ❌ State transfer entre agents |
| ✅ Clear responsibility | ❌ LLM debe elegir bien |
| ✅ Easy to debug | ❌ Más costoso |

## Comparativa con otros patrones

| Pattern | Aithera借鉴 |
|---|---|
| **Handoffs** (OpenAI) | routing a specialist |
| **CrewAI** Hierarchical | manager + auto-delegation |
| **LangGraph** conditional edges | state machine |
| **AutoGen** Teams | group chat |

V1.0 Orchestrator debería combinar:
- ✅ Intent classification (handoffs pattern).
- ✅ Multi-agent handoff.
- ✅ State preservation.

## Referencias cruzadas

- [JWIKI-015 openai-agents-sdk.md](../01_LANDSCAPE/openai-agents-sdk.md)
- [JWIKI-114 multi-agent-hierarchical.md](./multi-agent-hierarchical.md)

## Fuentes

1. https://openai.github.io/openai-agents-python/handoffs/
2. https://github.com/openai/openai-agents-python

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified