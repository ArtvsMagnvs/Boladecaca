# Pinia — State management para Vue

## Resumen

**Pinia** es la librería de state management oficial de Vue 3 (reemplazo de Vuex). Aithera NO usa Vue, **NO usa Pinia**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pinia highlights

- ✅ Composition API friendly.
- ✅ TypeScript first-class.
- ✅ Modular stores.
- ✅ DevTools.

## Hello World

```typescript
import { defineStore } from "pinia";

export const useChatStore = defineStore("chat", () => {
    const messages = ref<ChatMessage[]>([]);
    function addMessage(msg: ChatMessage) { messages.value.push(msg); }
    return { messages, addMessage };
});
```

## Para Aithera

NO se usa. Mencionar solo para referencia.

## Referencias cruzadas

- [JWIKI-081 vue-3.md](./vue-3.md)
- [JWIKI-084 state-zustand.md](./state-zustand.md)

## Fuentes

1. https://pinia.vuejs.org/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified