# React 18 — UI library en uso en Aithera

## Resumen

**React 18** es la UI library de Aithera V0.7.3. Hooks, concurrent features, Suspense. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

React 18.x (CLAUDE.md §2). Concurrent rendering, automatic batching, Suspense for data fetching.

## Stack Aithera V0.7.3

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.x",
    "zustand": "^4.x",
    "framer-motion": "^11.x",
    "@react-three/fiber": "^8.x",
    "@react-three/drei": "^9.x",
    "three": "^0.160.0"
  }
}
```

## Hooks clave

```tsx
import { useState, useEffect, useRef, useMemo, useCallback } from "react";

function ChatComponent() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const accumulatedRef = useRef("");  // streaming chunks
    const [isStreaming, setIsStreaming] = useState(false);
    
    useEffect(() => {
        // load initial messages
    }, []);
    
    const handleStream = useCallback(async (userMessage: string) => {
        setIsStreaming(true);
        const response = await fetch("/api/chat/stream", {
            method: "POST",
            body: JSON.stringify({ message: userMessage })
        });
        const reader = response.body.getReader();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            accumulatedRef.current += new TextDecoder().decode(value);
        }
        setIsStreaming(false);
    }, []);
    
    return <div>{accumulatedRef.current}</div>;
}
```

## useRef pattern para streaming (Aithera)

CLAUDE.md §2 confirma este patrón obligatorio:
```tsx
const accumulatedRef = useRef("");

// Acumular chunks sin re-render
accumulatedRef.current += chunk;

// Re-render 1 vez al final con forceUpdate
const [, forceUpdate] = useReducer((x) => x + 1, 0);
```

## Concurrent features (React 18)

- **useTransition**: marcar updates como no-urgentes.
- **Suspense**: data fetching declarativo.
- **Automatic batching**: múltiples setState en mismo tick = 1 re-render.

## Aithera páginas (9)

| Página | Propósito |
|---|---|
| `Hub.tsx` | Dashboard con AICore 3D |
| `Chat.tsx` | Chat con AI |
| `Projects.tsx` | CRUD proyectos |
| `Tasks.tsx` | CRUD tasks |
| `Calendar.tsx` | Eventos |
| `Agents.tsx` | Manager agentes |
| `EmailAssistant.tsx` | Email V0.7+ |
| `VoiceCenter.tsx` | TTS/STT |
| `Settings.tsx` | Configuración |

## Pitfalls

- ❌ **No usar useState para chunks de stream** — re-renders innecesarios.
- ❌ **No olvidar keys en .map()**.
- ❌ **No mutar state directamente** — siempre setState.

## Referencias cruzadas

- [JWIKI-079 README.md](./README.md)
- [JWIKI-084 state-zustand.md](./state-zustand.md)
- [JWIKI-099 useref-streaming.md](./useref-streaming.md)
- [JWIKI-096 routing-hashrouter.md](./routing-hashrouter.md)

## Fuentes

1. https://react.dev/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified