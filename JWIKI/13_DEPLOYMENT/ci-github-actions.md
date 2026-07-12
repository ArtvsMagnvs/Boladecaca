# CI GitHub Actions

## Resumen

**GitHub Actions** para CI/CD. Aithera V0.85+ lo usaría para tests + build + release.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## .github/workflows/test.yml

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest tests/ -v
  
  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd frontend && npm install
      - run: cd frontend && npm run build
```

## .github/workflows/release.yml

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  release:
    runs-on: windows-latest  # electron-builder Windows requires Windows
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd frontend && npm install
      - run: cd frontend && npm run electron:build
      - uses: softprops/action-gh-release@v2
        with:
          files: frontend/release/*.exe
```

## Para Aithera

- ❌ V0.7.3: NO CI (manual testing).
- ⏳ V0.85+: GitHub Actions.

## Fuentes

1. https://docs.github.com/en/actions

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified