# Tree of Thoughts (ToT) — Búsqueda en árbol

## Resumen

**Tree of Thoughts** extiende CoT con búsqueda en árbol. Explora múltiples paths en paralelo y evalúa cada uno. Paper: Yao et al., 2023.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Concepto

- **CoT**: chain lineal (1 path).
- **ToT**: tree (N paths) con backtracking.

## Algorithm

```
1. Generate initial thoughts (breadth)
2. For each thought, evaluate (LLM-as-judge)
3. Expand top-K thoughts
4. Repeat until solution found or depth limit
```

## Implementación

```python
async def tree_of_thoughts(problem: str, llm, max_depth: int = 5, beam: int = 3) -> str:
    # Initial thoughts
    thoughts = await generate_thoughts(problem, llm, n=beam)
    
    for depth in range(max_depth):
        # Evaluate each thought
        scored = []
        for t in thoughts:
            score = await evaluate_thought(problem, t, llm)
            scored.append((score, t))
        
        # Sort by score
        scored.sort(reverse=True)
        thoughts = [t for _, t in scored[:beam]]  # top-K
        
        # Check if any is solution
        for t in thoughts:
            if await is_solution(problem, t, llm):
                return t
    
    return thoughts[0]  # best guess

async def generate_thoughts(problem: str, llm, n: int = 3) -> list[str]:
    prompt = f"""Problema: {problem}

Genera {n} approaches diferentes para resolverlo.
Cada approach debe ser un párrafo corto.

Approaches:
1."""
    response = await llm.chat(prompt, n=n, temperature=0.7)
    return parse_approaches(response)

async def evaluate_thought(problem: str, thought: str, llm) -> float:
    prompt = f"""Problema: {problem}
Approach: {thought}

Evalúa este approach del 1-10. ¿Resuelve el problema?
Solo el número."""
    response = await llm.chat(prompt, temperature=0)
    return float(response.strip())
```

## BFS vs DFS

- **BFS** (breadth-first): explorar todos los paths nivel por nivel.
- **DFS** (depth-first): ir profundo, backtrack si no funciona.

## Cuándo usar

- ✅ **Research** (multi-step analysis).
- ✅ **Problem solving** (math, logic, puzzles).
- ✅ **Game playing** (chess, Go).
- ❌ **Simple tasks** (overkill).

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Encuentra soluciones no obvias | ❌ Muy costoso (Nx LLM calls) |
| ✅ Robust via backtracking | ❌ Latencia alta |
| ✅ Optimal (con buen eval) | ❌ Requiere buen evaluator |

## Para Aithera V1.0+ (futuro)

V1.0 Orchestrator podría usar ToT para:
- ✅ Coding tasks (probar N approaches).
- ✅ Decision-making crítico.

Pero NO para chat normal (overhead innecesario).

## Referencias cruzadas

- [JWIKI-110 patterns-chain-of-thought.md](./patterns-chain-of-thought.md)

## Fuentes

1. https://arxiv.org/abs/2305.10601 (Tree of Thoughts paper)
2. https://github.com/princeton-nlp/tree-of-thought-llm

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified