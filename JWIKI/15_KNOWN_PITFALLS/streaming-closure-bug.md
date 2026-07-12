# Streaming Closure Bug — Aithera V0.2

## Resumen

**Streaming closure bug** ocurrió en V0.2: la variable de acumulación se cerraba incorrectamente dentro del SSE stream, perdiendo chunks.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Bug original

```tsx
// ❌ Bug V0.1
function Chat() {
    const [text, setText] = useState("");
    
    async function streamChat() {
        const reader = response.body.getReader();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            setText(text + new TextDecoder().decode(value));  // <- closure!
        }
    }
}
```

Problema: `text` es stale por closure. Cada `setText(text + ...)` usa el `text` del closure inicial, no el actualizado.

## Fix

```tsx
// ✅ Fix V0.2 (CLAUDE.md §2)
function Chat() {
    const accumulatedRef = useRef("");
    const [, forceUpdate] = useReducer((x) => x + 1, 0);
    
    async function streamChat() {
        const reader = response.body.getReader();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            accumulatedRef.current += new TextDecoder().decode(value);
        }
        forceUpdate();
    }
    
    return <div>{accumulatedRef.current}</div>;
}
```

## Lección

- ❌ **No usar useState** para acumular chunks (re-renders innecesarios + closure bug).
- ✅ **Usar useRef** + forceUpdate al final.

## Para Aithera

- ✅ V0.2+: fixed y documentado en CLAUDE.md §2.

## Referencias cruzadas

- [JWIKI-099 useref-streaming.md](../04_FRONTEND/useref-streaming.md)
- CLAUDE.md §2

## Fuentes

1. CLAUDE.md §2

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified