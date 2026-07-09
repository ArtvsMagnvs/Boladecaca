# Svelte 5 — Alternativa compile-time

## Resumen

**Svelte 5** es un framework que compila a vanilla JS (sin runtime overhead). Aithera V0.7.3 usa React, **NO Svelte**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Svelte highlights

- ✅ **Compile-time**: sin runtime virtual DOM.
- ✅ **Reactive declarations** (`$:` syntax).
- ✅ **Runes** (Svelte 5): nueva API reactiva.
- ✅ Bundle size mínimo.
- ✅ Performance top-tier.

## Svelte 5 runes

```svelte
<script>
  let count = $state(0);
  let doubled = $derived(count * 2);
  
  function increment() {
    count++;
  }
</script>

<button onclick={increment}>
  Count: {count}, Doubled: {doubled}
</button>
```

## Svelte vs React

| Aspecto | Svelte 5 | React 18 |
|---|---|---|
| Bundle size | ⭐⭐⭐⭐⭐ (más pequeño) | ⭐⭐⭐ |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Ecosystem AI | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Learning curve | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Maturity | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Para Aithera

React elegido por ecosistema. Svelte sería opción para nuevos proyectos con prioridad bundle size.

## Referencias cruzadas

- [JWIKI-080 react.md](./react.md)
- [JWIKI-081 vue-3.md](./vue-3.md)

## Fuentes

1. https://svelte.dev/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified