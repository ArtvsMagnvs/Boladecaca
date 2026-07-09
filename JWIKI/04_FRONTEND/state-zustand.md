# Zustand 4 — State management en Aithera

## Resumen

**Zustand 4** es la librería de state management de Aithera V0.7.3. Minimalista, sin boilerplate, ideal para React. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Zustand 4.x (CLAUDE.md §2).

## Por qué Zustand

- ✅ **Minimalista**: 1KB.
- ✅ **Sin Provider**: no necesita `<StoreProvider>`.
- ✅ **TypeScript first-class**.
- ✅ **Hook-based API**.
- ✅ **No re-renders innecesarios** (selectors).

## Hello World

```typescript
import { create } from "zustand";

interface AppState {
    chatMessages: ChatMessage[];
    setChatMessages: (msgs: ChatMessage[]) => void;
    aiStatus: AIStatus | null;
    setAiStatus: (status: AIStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
    chatMessages: [],
    setChatMessages: (chatMessages) => set({ chatMessages }),
    aiStatus: null,
    setAiStatus: (aiStatus) => set({ aiStatus }),
}));

// Uso
function Chat() {
    const messages = useAppStore((s) => s.chatMessages);
    const setMessages = useAppStore((s) => s.setChatMessages);
    // Solo re-render si messages cambia, no si aiStatus cambia
}
```

## Selectors (clave para performance)

```typescript
// ❌ Re-render si CUALQUIER parte del state cambia
const state = useAppStore();

// ✅ Solo re-render si messages cambia
const messages = useAppStore((s) => s.chatMessages);
```

## Aithera stores

| Store | Contenido |
|---|---|
| `useAppStore` | State global (chat, AI status) |
| `useChatStore` | Chat messages, streaming state |
| `useSettingsStore` | User preferences |
| `useAgentStore` | Agents list, executions |

## Best practices

- ✅ **Selectors específicos**: nunca `useAppStore()` sin selector.
- ✅ **Actions en el store**: no en componentes.
- ✅ **Dividir stores por dominio**: chat, settings, agents separados.

## Pitfalls

- ❌ **No usar `useAppStore()` sin selector** — re-renders innecesarios.
- ❌ **No mutar state directamente** — siempre `set({ key: value })`.
- ❌ **No poner state derivado en el store** — usar `useMemo` o selector.

## Referencias cruzadas

- [JWIKI-080 react.md](./react.md)
- [JWIKI-085 state-redux.md](./state-redux.md)
- [JWIKI-086 state-jotai.md](./state-jotai.md)

## Fuentes

1. https://github.com/pmndrs/zustand
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified