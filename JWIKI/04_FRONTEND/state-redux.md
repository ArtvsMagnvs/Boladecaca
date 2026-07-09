# Redux Toolkit — Alternativa state management

## Resumen

**Redux Toolkit** (RTK) es la librería de state management "oficial" de React. Aithera V0.7.3 usa Zustand, **NO Redux**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Redux vs Zustand

| Aspecto | Redux Toolkit | Zustand 4 |
|---|---|---|
| Boilerplate | medio | mínimo |
| DevTools | ✅ excel | ✅ bueno |
| Learning curve | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Bundle size | ~10KB | ~1KB |
| Async actions | createAsyncThunk | actions nativos |
| Ecosystem | enorme | medio |

## Para Aithera

Zustand elegido por simplicidad. Redux sería válido pero overkill.

## Hello World (Redux Toolkit)

```typescript
import { createSlice, configureStore } from "@reduxjs/toolkit";

const counterSlice = createSlice({
    name: "counter",
    initialState: { value: 0 },
    reducers: {
        increment: (state) => { state.value += 1; },
        decrement: (state) => { state.value -= 1; },
    },
});

const store = configureStore({ reducer: { counter: counterSlice.reducer } });

// Provider
<Provider store={store}>
    <App />
</Provider>

// Uso
const count = useAppSelector((s) => s.counter.value);
const dispatch = useAppDispatch();
```

## Para Aithera — NO usar

Redux es overkill para Aithera (single-user, simple state).

## Referencias cruzadas

- [JWIKI-084 state-zustand.md](./state-zustand.md)
- [JWIKI-086 state-jotai.md](./state-jotai.md)

## Fuentes

1. https://redux-toolkit.js.org/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified