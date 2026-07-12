# Code Signing — Windows

## Resumen

**Code signing** autentica el binario Windows (evita SmartScreen warnings). **NO configurado en Aithera V0.7.3**. Necesario para V0.85+ si se distribuye fuera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Cert providers

| Provider | Cost | Aithera |
|---|---|---|
| **DigiCert** | $400+/año | ⏳ |
| **Sectigo (Comodo)** | $200+/año | ⏳ |
| **Certum** | $30/año (open source friendly) | ⏳ |
| **Self-signed** | gratis | ❌ trusted only by you |

## Setup

```json
{
  "win": {
    "certificateFile": "path/to/cert.pfx",
    "certificatePassword": "env.CSC_KEY_PASSWORD"
  }
}
```

## Para Aithera

- ❌ V0.7.3: unsigned (SmartScreen warning).
- ⏳ V0.85+: Certum o similar (cheap, open-source friendly).

## Referencias cruzadas

- [JWIKI-204 electron-builder.md](./electron-builder.md)

## Fuentes

1. https://learn.microsoft.com/en-us/windows/win32/seccrypto/cryptsigndatacert
2. https://docs.microsoft.com/en-us/windows-hardware/drivers/dashboard/get-a-code-signing-certificate

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified