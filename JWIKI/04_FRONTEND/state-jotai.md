# Jotai — Atomic state management

## Resumen

**Jotai** es state management atómico (atomic) para React. Similar a Recoil. Aithera V0.7.3 usa Zustand, **NO Jotai**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Jotai highlights

- ✅ **Atoms**: state units independientes.
- ✅ **No Provider needed** (similar a Zustand).
- ✅ **Bottom-up** approach.
- ✅ **Derived atoms** con `atom()` + `useMemo`.

## Hello World

```typescript
import { atom, useAtom } from "jotai";

const countAtom = atom(0);
const doubledAtom = atom((get) => get(countAtom) * 2);

function Counter() {
    const [count, setCount] = useAtom(countAtom);
    const [doubled] = useAtom(doubledAtom);
    
    return <button onClick={() => setCount(c => c + 1)}>
        {count} (doubled: {doubled})
    </button>;
}
```

## Jotai vs Zustand

| Aspecto | Jotai | Zustand 4 |
|---|---|---|
| Paradigma | Atoms | Store |
| API | hooks | hooks |
| Provider | no | no |
| Derived state | `atom(get => ...)` | selectors |
| Use case | muchos small states | few big stores |

## Para Aithera

NO se usa. Zustand es más simple para Aithera.

## Referencias cruzadas

- [JWIKI-084 state-zustand.md](./state-zustand.md)
- [JWIKI-085 state-redux.md](./state-redux.md)

## Fuentes

1. https://jotai.org/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified