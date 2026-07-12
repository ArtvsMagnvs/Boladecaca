# Reflexion Pattern — Auto-corrección

## Resumen

**Reflexion** es un patrón donde el agent reflexiona sobre sus errores y los usa para mejorar en el siguiente intento. Paper: Shinn et al., 2023.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Concepto

1. Agent intenta tarea.
2. Si falla, genera **reflexión** sobre el error.
3. Reflexión + tarea original → próximo intento.
4. Repite N veces.

## Implementación

```python
async def reflexion_agent(task: str, llm, tools, max_trials: int = 3) -> str:
    history = []
    
    for trial in range(max_trials):
        # Construir prompt con history
        prompt = f"Tarea: {task}\n\n"
        if history:
            prompt += "Historial:\n" + "\n".join([
                f"Trial {i+1}: {r['output']}\nReflexión: {r['reflection']}"
                for i, r in enumerate(history)
            ]) + "\n\n"
        
        # Agent intenta
        output = await react_agent(prompt, llm, tools)
        
        # Evaluar resultado
        success, critique = await llm.evaluate(task, output)
        
        if success:
            return output
        
        # Generar reflexión
        reflection = await llm.chat(
            f"La tarea era: {task}\nEl output fue: {output}\n"
            f"La crítica: {critique}\n"
            f"Reflexiona: ¿qué salió mal? ¿cómo mejorar?"
        )
        
        history.append({
            "output": output,
            "reflection": reflection,
            "critique": critique
        })
    
    return history[-1]["output"]  # best attempt
```

## Cuándo usar

- ✅ **Coding tasks** (bug fix con tests).
- ✅ **Reasoning tasks** (math, logic).
- ✅ **Tool use** (cuando tool falla).
- ❌ **Simple chat** (overkill).

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Auto-corrección sin user | ❌ Costoso (múltiples LLM calls) |
| ✅ Aprende de errores | ❌ Puede converger a respuestas incorrectas |
| ✅ Robusto | ❌ Latencia Nx |

## Aithera借鉴 (V1.0)

V1.0 Orchestrator podría usar Reflexion para:
- ✅ Coding agents (Claude Code Agent).
- ✅ Tool use con fallos.
- ✅ Email auto-reply (mejorar drafts).

## Referencias cruzadas

- [JWIKI-107 patterns-react.md](./patterns-react.md)
- [JWIKI-108 patterns-plan-execute.md](./patterns-plan-execute.md)

## Fuentes

1. https://arxiv.org/abs/2303.11381 (Reflexion paper)
2. https://github.com/noahshinn/reflexion

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified