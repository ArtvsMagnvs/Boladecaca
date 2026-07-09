# SolidJS — React-like con mejor performance

## Resumen

**SolidJS** es React-like con fine-grained reactivity (sin virtual DOM). Aithera NO usa SolidJS.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## SolidJS highlights

- ✅ **Fine-grained reactivity** (como Svelte).
- ✅ JSX familiar (como React).
- ✅ Performance top-tier.
- ✅ Bundle pequeño.

## Solid vs React

| Aspecto | SolidJS | React 18 |
|---|---|---|
| Paradigma | Signals | Hooks + VDOM |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Ecosystem | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Learning curve | ⭐⭐⭐⭐ (React-like) | ⭐⭐⭐ |

## Para Aithera

NO se usa. Mencionar para referencia.

## Hello World

```tsx
import { createSignal } from "solid-js";

function Counter() {
    const [count, setCount] = createSignal(0);
    return <button onClick={() => setCount(count() + 1)}>{count()}</button>;
}
```

## Referencias cruzadas

- [JWIKI-080 react.md](./react.md)
- [JWIKI-082 svelte-5.md](./svelte-5.md)

## Fuentes

1. https://www.solidjs.com/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified