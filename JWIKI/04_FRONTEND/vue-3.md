# Vue 3 — Alternativa a React

## Resumen

**Vue 3** es alternativa popular a React. Composition API excelente. Aithera V0.7.3 usa React, **NO Vue**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Vue 3 highlights

- ✅ Composition API (similar a React Hooks).
- ✅ TypeScript first-class.
- ✅ Single-file components (.vue).
- ✅ Reactive refs.
- ✅ Vue Router, Pinia (state).

## Vue vs React

| Aspecto | Vue 3 | React 18 |
|---|---|---|
| Ecosystem AI/3D | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Curva aprendizaje | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Type safety | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Contratar devs | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Para Aithera

React elegido por ecosistema AI/3D (React Three Fiber, LangChain.js). Vue sería válido pero menos componentes 3D.

## Hello World

```vue
<!-- App.vue -->
<template>
  <div>{{ message }}</div>
</template>

<script setup>
import { ref } from "vue";
const message = ref("Hello from Vue 3");
</script>
```

## Estado Aithera

NO se usa. Mencionar para referencia.

## Referencias cruzadas

- [JWIKI-080 react.md](./react.md)
- [JWIKI-082 svelte-5.md](./svelte-5.md)

## Fuentes

1. https://vuejs.org/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified