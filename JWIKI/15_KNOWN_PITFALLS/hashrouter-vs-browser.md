# HashRouter vs BrowserRouter

## Resumen

**HashRouter** vs **BrowserRouter** en Electron. Aithera V0.7.3 usa **HashRouter** obligatorio (CLAUDE.md §2).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué HashRouter

Electron carga con `file://` protocol. BrowserRouter usa HTML5 history API que requiere server. HashRouter usa `#/ruta` que funciona con `file://`.

## Pitfalls

```tsx
// ❌ MAL en Electron
import { BrowserRouter } from "react-router-dom";
<BrowserRouter>
    <Routes>
        <Route path="/chat" element={<Chat />} />
    </Routes>
</BrowserRouter>
// Result: HashRouter vacío o error 404 al navegar.

// ✅ BIEN
import { HashRouter } from "react-router-dom";
<HashRouter>
    <Routes>
        <Route path="/chat" element={<Chat />} />
    </Routes>
</HashRouter>
```

## Migración futura

Si Aithera se despliega como web (PWA V1.0+), cambiar a BrowserRouter.

## Para Aithera

- ✅ V0.7.3: HashRouter (CLAUDE.md §2).

## Referencias cruzadas

- [JWIKI-096 routing-hashrouter.md](../04_FRONTEND/routing-hashrouter.md)
- CLAUDE.md §2

## Fuentes

1. https://reactrouter.com/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified