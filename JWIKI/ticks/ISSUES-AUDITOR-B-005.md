## JWIKI-005 Auditor B — Issues menores no bloqueantes (2026-07-01 11:01)

> Logged por Mavis en sesion mvs_f3ce04f0f9c14c0a84ba618cc69a3113 tras veredicto=`verified` del Auditor B (messageId 218, single-line reformateado por bug PowerShell). Fuente: `JWIKI/01_LANDSCAPE/openjarvis.md` 53899 bytes / 630 lineas / 23 fuentes.

### Issues marcados en task_queue como `ISSUES-PENDIENTES-MENORES-AUDITOR-B-005`:

1. **projects.md desactualizado** (severidad: baja, no bloquea)
   - Problema: `JWIKI/01_LANDSCAPE/projects.md` menciona OpenJarvis v0.5.x; doc real verificado es v1.0.2.
   - Accion recomendada: escriba turno A o B en proximo slot libre re-lee+actualiza la fila OpenJarvis en projects.md con v1.0.2 + repo `open-jarvis/OpenJarvis`.
   - Status: PENDIENTE — loggear en `task_queue.md` para cleanup.

2. **Inconsistencia canales** (severidad: trivial)
   - Problema: doc openjarvis.md menciona "30+ channels" en linea 56 y "26+ channels" en linea 261 — mismas listas, conteos diferentes.
   - Accion recomendada: harmonizar a "26+ channels" (numero declarado en `src/openjarvis/channels/`) o recontar y declarar el oficial (28-30 rangos plausibles).
   - Status: PENDIENTE.

3. **Caracteres chinos `借鉴`** (severidad: cosmético)
   - Problema: 2 ocurrencias del caracter chino "借鉴" (lineas 9 y 531) embebidas en texto espanol — claramente copy-paste del briefing original.
   - Accion recomendada: reemplazar por "参考 aplicables" o "借鉴-aplicables" segun contexto.
   - Status: PENDIENTE.

4. **Code refs sin commit SHA-pin** (severidad: mejora opcional)
   - Problema: doc cita URLs `raw.githubusercontent.com/open-jarvis/OpenJarvis/main/...` sin SHA de commit.
   - Accion recomendada: anadir SHA-pin (formato short: 7 chars) en los 5 URLs mas citados cuando el repo lo permita.
   - Status: PENDIENTE.

### Decision root sobre estos issues

> "ISSUES-PENDIENTES=projects-md-y-channels-26vs30-no-bloquean-pipeline-loggear-en-task_queue-para-proxima-sesion-cleanup"

(Pipes-format del root messageId sin asignar; recibido 2026-07-01 11:01:19 Europe/Paris)

### Reglas aplicadas

- No bloquean pipeline JWIKI principal.
- Documentados aqui para que proxima sesion de cleanup pueda tomarlos.
- NO se re-despacha auditor ni escriba por estos 4 issues (veredicto=verified).

---

*Mantenido por Mavis (orquestador). Auditor B messageId 218 sobre JWIKI-005 veredicto=verified. Wiki-map.md + task_queue.md ya actualizados por el agente.*
