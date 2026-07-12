# SOP — Build electron-builder

## Cuándo
Release nueva versión de Aithera.

## Pasos

1. **Update version** en `frontend/package.json` y `backend/app/core/config.py`.

2. **Bump version** en `backend/app/main.py` (VERSION string).

3. **Commit + tag**:
```bash
git add -A
git commit -m "release: v0.8.0"
git tag v0.8.0
```

4. **Build**:
```bash
cd frontend
npm install
npm run electron:build
# → release/Aithera Setup 0.8.0.exe
```

5. **Test installer** en Windows VM.

6. **Upload to GitHub Releases**:
```bash
gh release create v0.8.0 release/*.exe --generate-notes
```

## Verificación

- [ ] Installer funciona en Windows limpio.
- [ ] App arranca sin errores.
- [ ] Auto-update detecta nueva versión (V0.85+).

## Rollback

- Delete release tag.
- Mark git tag as deleted.

## Referencias cruzadas

- [JWIKI-204 electron-builder.md](../13_DEPLOYMENT/electron-builder.md)

---

*Estado: 🟢 verified*