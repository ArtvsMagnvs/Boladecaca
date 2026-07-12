# React 18 Strict Mode — Double Render

## Resumen

**React 18 strict mode** ejecuta effects 2x en dev. Aithera V0.7.3 puede tener effects que asumen single execution.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Issue

```tsx
// ❌ Asume single execution
useEffect(() => {
    const ws = new WebSocket("...");
    return () => ws.close();
}, []);
```

En strict mode dev:
1. Mount → ws created.
2. Unmount (simulated) → ws closed.
3. Mount → ws created AGAIN.

## Fix

```tsx
// ✅ Idempotent
useEffect(() => {
    const ws = new WebSocket("...");
    return () => ws.close();
}, []);  // cleanup function is key

// O si necesitas singleton:
useEffect(() => {
    let cancelled = false;
    fetchData().then(data => {
        if (!cancelled) setData(data);
    });
    return () => { cancelled = true; };
}, []);
```

## Para Aithera

- ✅ V0.7.3: usar cleanup functions.

## Referencias cruzadas

- [JWIKI-080 react.md](../04_FRONTEND/react.md)
- CLAUDE.md §2

## Fuentes

1. https://react.dev/reference/react/StrictMode

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified