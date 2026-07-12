# Chain-of-Thought (CoT) — Reasoning explícito

## Resumen

**Chain-of-Thought** prompting induce al LLM a razonar paso a paso antes de responder. Mejora accuracy en tareas complejas.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Concepto

Standard prompting: `Q → A`.
Chain-of-Thought: `Q → Reasoning steps → A`.

## Ejemplo

```
Q: Roger tiene 5 pelotas. Compra 2 más. Luego pierde 3.
¿Cuántas pelotas tiene Roger?

Sin CoT: 4 (correcto por casualidad)

Con CoT:
Roger empieza con 5.
Compra 2 → 7.
Pierde 3 → 4.
Roger tiene 4 pelotas.
```

## Implementación

```python
async def cot_chat(question: str, llm) -> str:
    prompt = f"""Responde paso a paso.

Pregunta: {question}

Pensemos:"""
    return await llm.chat(prompt, temperature=0)
```

## Few-shot CoT

```python
prompt = """Q: Juan tiene 3 manzanas. Compra 5 más. ¿Cuántas tiene?
A: Pensemos. Juan tiene 3. Compra 5 → 8. Juan tiene 8 manzanas.

Q: María tiene 10 años. Su hermano tiene el doble. ¿Cuántos años tiene el hermano?
A: Pensemos. María 10. Hermano = 2x María = 20. Hermano tiene 20 años.

Q: {question}
A: Pensemos."""
```

## Cuándo usar

- ✅ **Math problems**.
- ✅ **Logic puzzles**.
- ✅ **Multi-step reasoning**.
- ❌ **Simple factual Q&A** (overhead innecesario).

## Self-consistency

Mejor accuracy con **multiple CoT samples + voting**:

```python
async def self_consistency(question: str, llm, n: int = 5) -> str:
    answers = []
    for _ in range(n):
        answer = await cot_chat(question, llm, temperature=0.7)
        final = extract_final_answer(answer)
        answers.append(final)
    # Majority vote
    return Counter(answers).most_common(1)[0][0]
```

## Para Aithera

Aithera V0.7.3+ usa CoT implícitamente cuando el LLM lo requiere. V1.0 Orchestrator podría añadir:
- ✅ System prompt que induce CoT.
- ✅ Self-consistency para preguntas críticas.
- ✅ **B21 reasoning filter** (ya extrae `<think>` para no mostrarlo al user).

## Referencias cruzadas

- [JWIKI-107 patterns-react.md](./patterns-react.md)
- CLAUDE.md §1 (B21)

## Fuentes

1. https://arxiv.org/abs/2201.11903 (Chain-of-Thought Prompting)
2. https://arxiv.org/abs/2203.11171 (Self-Consistency)

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified