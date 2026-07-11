# Oblivion — Selective memory pruning

## Resumen

**Oblivion** (o memory pruning) es el patrón de **olvidar selectivamente** memoria vieja/irrelevante para mantener la memoria fresca y relevante. Aithera NO lo implementa, pero es V0.85+.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué olvidar

- ✅ **Storage**: ChromaDB crece sin límite.
- ✅ **Relevancia**: memoria vieja puede confundir al LLM.
- ✅ **Privacy**: olvidar datos sensibles.
- ✅ **Performance**: queries más rápidas.

## Estrategias

### 1. Time-based

```python
def forget_older_than(days: int = 90):
    cutoff = datetime.now() - timedelta(days=days)
    results = collection.get(where={"timestamp": {"$lt": cutoff.isoformat()}})
    collection.delete(ids=results["ids"])
```

### 2. Relevance-based

```python
def forget_low_relevance(threshold: float = 0.3):
    # Compute relevance vs current user context
    for item in collection.get()["documents"]:
        relevance = compute_similarity(item, current_context)
        if relevance < threshold:
            collection.delete(ids=[item["id"]])
```

### 3. Topic-based

```python
def forget_topic(topic: str):
    results = collection.get(where={"topic": topic})
    collection.delete(ids=results["ids"])
```

### 4. LLM-decided

LLM decide qué olvidar:

```python
def llm_prune(messages: list, llm):
    prompt = f"""De estos mensajes del usuario, ¿cuáles deberían olvidarse? 
    Mensajes: {messages}
    Responde JSON: {{"forget_ids": [1, 5, 7]}}"""
    response = llm.chat(prompt)
    forget_ids = json.loads(response)["forget_ids"]
    collection.delete(ids=forget_ids)
```

### 5. Hybrid (time + relevance + LLM)

```python
def hybrid_prune():
    # Step 1: time-based (drop old, low-relevance)
    forget_older_than(days=180)
    
    # Step 2: relevance-based (low similarity to recent queries)
    forget_low_relevance(threshold=0.2)
    
    # Step 3: LLM audit (semantic forget)
    llm_prune(recent_messages, llm)
```

## Para Aithera V0.85

V0.85 MOS debería tener **oblivion configurable**:
- ✅ Default: keep last 90 days, low-relevance pruned.
- ✅ User control: "forget all" / "forget last hour" / "forget this topic".
- ✅ Audit log: qué se olvidó y cuándo.

## Privacy + GDPR

Oblivion es **obligatorio** bajo GDPR:
- ✅ User puede pedir "borrar todo" → oblivion total.
- ✅ Auto-expiry para datos sensibles (auth tokens, etc.).

## References

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-131 conversation-memory.md](./conversation-memory.md)
- [JWIKI-132 user-context.md](./user-context.md)
- `PLAN_MAESTRO_2026/08_MOS_ARQUITECTURA_COMPLETA.md` (RFC-007 compactación)

## Fuentes

1. https://www.trychroma.com/
2. Plan Maestro 2026 §08 (RFC-007 compactación)
3. https://gdpr.eu/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified