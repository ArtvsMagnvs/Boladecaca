# HashRouter — Routing para Electron file://

## Resumen

Aithera V0.7.3 usa **HashRouter** (no BrowserRouter) porque la app Electron carga con `file://` protocol. CLAUDE.md §2 lo confirma como patrón obligatorio.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué HashRouter

En Electron, la app se carga desde `file://...` (no desde un server HTTP). BrowserRouter usa HTML5 history API que requiere server-side routing. **HashRouter usa `#/ruta`** que funciona con `file://`:

```
file:///path/to/app/index.html#/chat
file:///path/to/app/index.html#/projects
```

## Implementación

```tsx
import { HashRouter, Routes, Route } from "react-router-dom";

function App() {
    return (
        <HashRouter>
            <Routes>
                <Route path="/" element={<Hub />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/tasks" element={<Tasks />} />
                <Route path="/calendar" element={<Calendar />} />
                <Route path="/agents" element={<Agents />} />
                <Route path="/email" element={<EmailAssistant />} />
                <Route path="/voice" element={<VoiceCenter />} />
                <Route path="/settings" element={<Settings />} />
            </Routes>
        </HashRouter>
    );
}
```

## HashRouter vs BrowserRouter

| Aspecto | HashRouter | BrowserRouter |
|---|---|---|
| URL format | `/#/ruta` | `/ruta` |
| Server-side | ❌ no necesario | ✅ necesario |
| History API | ❌ | ✅ |
| file:// support | ✅ | ❌ |
| SEO | ❌ (hash no indexado) | ✅ |
| Aithera | ✅ (Electron) | ❌ |

## Cuando SÍ usar BrowserRouter

- Web app desplegada con server (Nginx, Vercel).
- SEO importante.

## Para Aithera

HashRouter es **obligatorio** mientras use Electron con `file://`. Si Aithera migra a web (V0.85+), puede cambiar a BrowserRouter o MemoryRouter.

## Pitfalls

- ❌ **BrowserRouter en Electron** — links no funcionan.
- ❌ **Asumir paths absolutos** — HashRouter necesita `#` prefix.

## Referencias cruzadas

- [JWIKI-094 desktop-electron.md](./desktop-electron.md)
- [JWIKI-080 react.md](./react.md)

## Fuentes

1. https://reactrouter.com/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified