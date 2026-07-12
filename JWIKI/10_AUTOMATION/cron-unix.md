# Cron — Unix clásico

## Resumen

**Cron** es el scheduler Unix clásico desde 1975. Sintaxis simple pero limitada. **NO usado en Aithera directamente** (APScheduler en V0.9+).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Sintaxis

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ day of week (0-6, SUN=0)
│ │ │ └─── month (1-12)
│ │ └───── day of month (1-31)
│ └─────── hour (0-23)
└───────── minute (0-59)
```

## Ejemplos

```cron
# Cada minuto
* * * * * /usr/local/bin/script.sh

# Cada 5 minutos
*/5 * * * * /usr/local/bin/script.sh

# Cada lunes 9am
0 9 * * 1 /usr/local/bin/weekly.sh

# Cada día 2am
0 2 * * * /usr/local/bin/nightly.sh

# Primer día del mes
0 0 1 * * /usr/local/bin/monthly.sh
```

## crontab -e (edit)

```bash
crontab -e  # edita
crontab -l  # lista
crontab -r  # elimina todas
```

## Limitaciones

- ❌ Solo Unix (Windows no tiene nativo).
- ❌ Solo minuto granularity.
- ❌ No retry automático.
- ❌ No monitoring built-in.
- ❌ No conditional execution (if X then run).

## Para Aithera

- ❌ NO usa cron directamente.
- ✅ APScheduler cross-platform + flexible.

## Fuentes

1. https://man7.org/linux/man-pages/man5/crontab.5.html

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified