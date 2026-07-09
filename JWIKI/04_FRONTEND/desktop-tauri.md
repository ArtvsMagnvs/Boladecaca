# Tauri 2 — Alternativa desktop wrapper

## Resumen

**Tauri 2** es alternativa moderna a Electron. Rust backend + WebView nativo. **NO usado en Aithera V0.7.3** (usa Electron 29).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tauri vs Electron

| Aspecto | Tauri 2 | Electron 29 |
|---|---|---|
| Tamaño binario | ⭐⭐⭐⭐⭐ (5-20MB) | ⭐⭐ (80-200MB) |
| Runtime | WebView nativo | Chromium + Node.js |
| Backend | Rust | Node.js |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Madurez | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Para Aithera

Electron elegido por madurez + ecosistema + AI/ML libraries (Node). Tauri sería válido para V0.85+ si bundle size es crítico.

## Hello World (Tauri)

```rust
// src-tauri/src/main.rs
fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![my_command])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn my_command(name: &str) -> String {
    format!("Hello, {}!", name)
}
```

```vue
<!-- src/App.vue -->
<template>
  <button @click="greet">Greet</button>
</template>

<script setup>
import { invoke } from "@tauri-apps/api/tauri";
const greet = () => invoke("my_command", { name: "Aithera" });
</script>
```

## Comparativa con JWIKI-006 (JarvisAgent)

JarvisAgent (myismu) usa Tauri 2 + Vue 3 + Rust. Es un ejemplo concreto de Tauri en producción. Ver [JWIKI-006](../01_LANDSCAPE/jarvisagent.md).

## Referencias cruzadas

- [JWIKI-094 desktop-electron.md](./desktop-electron.md)
- [JWIKI-204 electron-tauri.md](../13_DEPLOYMENT/electron-tauri.md)
- [JWIKI-006 jarvisagent.md](../01_LANDSCAPE/jarvisagent.md)

## Fuentes

1. https://tauri.app/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified