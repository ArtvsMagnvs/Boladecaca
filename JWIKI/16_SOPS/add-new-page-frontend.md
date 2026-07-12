# SOP — Añadir página React

## Cuándo
Necesitas una nueva vista en el frontend.

## Pasos

1. **Crear archivo**:
```tsx
// frontend/src/pages/NewPage.tsx
import React from "react";

export function NewPage() {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold">New Page</h1>
        </div>
    );
}
```

2. **Añadir ruta**:
```tsx
// frontend/src/App.tsx
import { NewPage } from "./pages/NewPage";

<Routes>
    ...
    <Route path="/new-page" element={<NewPage />} />
</Routes>
```

3. **Añadir al sidebar**:
```tsx
// frontend/src/components/layout/Sidebar.tsx
<NavLink to="/new-page">New Page</NavLink>
```

4. **API client** (si necesita datos):
```tsx
// frontend/src/services/newPageApi.ts
import { api } from "../lib/api";

export async function getItems() {
    return await api.get("/api/new-resource/");
}
```

## Verificación

- [ ] Página carga en `/new-page`.
- [ ] Sidebar link funciona.

## Referencias cruzadas

- [JWIKI-080 react.md](../04_FRONTEND/react.md)

---

*Estado: 🟢 verified*