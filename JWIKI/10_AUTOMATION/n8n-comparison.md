# n8n — Alternativa visual low-code

## Resumen

**n8n** es plataforma de automation visual low-code (alternativa a Zapier/Make). **NO usado en Aithera** (overkill, requiere app extra).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
docker run -it --rm \
    --name n8n \
    -p 5678:5678 \
    -v ~/.n8n:/home/node/.n8n \
    n8nio/n8n
```

## Visual workflow

```
[Schedule Trigger] → [HTTP Request] → [IF condition] → [Send Email]
                                                    ↓
                                            [Slack Notify]
```

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Visual (drag-and-drop) | ❌ App extra a mantener |
| ✅ 400+ nodes (Gmail, Slack, etc.) | ❌ Self-hosted requiere Docker |
| ✅ Webhooks + cron built-in | ❌ Curva aprendizaje |
| ✅ Open source | ❌ Complejo para simple tasks |

## Para Aithera

- ❌ NO integrado (overkill para single-user).
- ⏳ V1.0+: considerar n8n como **alternativa opcional** para users que prefieren low-code.

## Referencias cruzadas

- [JWIKI-170 apscheduler.md](./apscheduler.md)

## Fuentes

1. https://n8n.io/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified