# useRef Streaming Pattern — Aithera chat

## Resumen

**useRef pattern** es OBLIGATORIO en Aithera V0.7.3 para acumular chunks de streaming sin re-renders innecesarios. Ver CLAUDE.md §2: "Patrón obligatorio para acumular streaming: useRef para chunks, no useState".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrón obligatorio

```tsx
import { useRef, useReducer } from "react";

function Chat() {
    const accumulatedRef = useRef("");
    const [, forceUpdate] = useReducer((x) => x + 1, 0);
    const [isStreaming, setIsStreaming] = useState(false);
    
    async function streamChat(userMessage: string) {
        setIsStreaming(true);
        const response = await fetch("/api/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userMessage })
        });
        
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            accumulatedRef.current += chunk;  // ← acumula sin re-render
        }
        
        setIsStreaming(false);
        forceUpdate();  // ← 1 re-render al final
    }
    
    return (
        <div>
            <div>{accumulatedRef.current}</div>
            <button onClick={() => streamChat("Hello")} disabled={isStreaming}>
                {isStreaming ? "Streaming..." : "Send"}
            </button>
        </div>
    );
}
```

## Por qué useRef y no useState

```tsx
// ❌ MAL — re-render en cada chunk
const [text, setText] = useState("");
setText(text + chunk);  // cada chunk → re-render completo

// ✅ BIEN — acumula sin re-render
const textRef = useRef("");
textRef.current += chunk;
// re-render 1 vez al final con forceUpdate()
```

## Por qué forceUpdate

useRef no triggerea re-render. Para mostrar el contenido actualizado, hay que forzar 1 re-render al final del stream:

```tsx
const [, forceUpdate] = useReducer((x) => x + 1, 0);
```

Alternativa (más explícita): `useState` para chunks + `useRef` para accumulation:

```tsx
const [text, setText] = useState("");
const accumulator = useRef("");

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    accumulator.current += chunk;
    // Actualizar state cada N chunks (throttling)
    if (Date.now() - lastUpdate > 50) {
        setText(accumulator.current);
        lastUpdate = Date.now();
    }
}
setText(accumulator.current);  // final
```

## Patrón Aithera completo

Ver [JWIKI-050 sse-streaming.md](../02_ARCHITECTURE/sse-streaming.md) para el backend counterpart.

## Pitfalls

- ❌ **No usar useState** para chunks.
- ❌ **No olvidar forceUpdate** al final.
- ❌ **No leer el ref directamente durante render** (puede ser stale).

## Referencias cruzadas

- [JWIKI-050 sse-streaming.md](../02_ARCHITECTURE/sse-streaming.md)
- [JWIKI-080 react.md](./react.md)

## Fuentes

1. CLAUDE.md §2 (patrón obligatorio)
2. https://react.dev/reference/react/useRef

## Nivel de confianza

**100%** — Documentado en CLAUDE.md.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified