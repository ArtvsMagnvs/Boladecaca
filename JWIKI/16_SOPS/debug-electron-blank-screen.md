# SOP — Debug Electron blank screen

## Síntomas
- App abre pero muestra pantalla en blanco.

## Pasos

1. **Abrir DevTools** (Ctrl+Shift+I).

2. **Revisar Console**:
- Errores JS rojos.
- Network errors.

3. **Verificar que Vite dev server** está corriendo (si dev):
```bash
# Terminal 2
cd frontend
npm run dev
# → http://localhost:5173
```

4. **Verificar build** (si prod):
```bash
ls frontend/dist/index.html
```

5. **Si "Module not found"**: limpiar cache:
```bash
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

6. **Si "HashRouter no funciona"**: verificar import en App.tsx.

## Causas comunes

- ❌ Build no completado.
- ❌ Import path incorrecto.
- ❌ HashRouter olvidado.

## Referencias cruzadas

- [JWIKI-094 desktop-electron.md](../04_FRONTEND/desktop-electron.md)
- [JWIKI-237 hashrouter-vs-browser.md](../15_KNOWN_PITFALLS/hashrouter-vs-browser.md)

---

*Estado: 🟢 verified*