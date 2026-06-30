# JWIKI WORKFLOW — Loop autónomo de documentación

> Cómo el equipo procesa la task queue de forma autónoma, sin que el usuario tenga que dar una orden por cada punto.

## Arquitectura del loop

```
┌────────────────────────────────────────────────────────────────────┐
│                    ORQUESTADOR (Mavis)                             │
│  Cron self-reminder cada 15-30 min → tick de la queue              │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ lee task_queue.md
                           ┌──────────────────┐
                           │  ¿Hay puntos 🔴  │
                           │  sin dependencias │
                           │  pendientes?      │
                           └──────────────────┘
                                   │ sí
                                   ▼
                           ┌──────────────────┐
                           │ Despachar al      │
                           │ agente correcto   │
                           └──────────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
     ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
     │  Investigador│      │  Escriba     │      │  Validador   │
     │  investiga   │      │  escribe     │      │  de dominio  │
     │              │      │              │      │  (aithera-*) │
     │  ↓           │      │  ↓           │      │              │
     │  material    │      │  borrador    │      │  valida      │
     │  crudo       │      │  completo    │      │  contra      │
     │  con fuentes │      │              │      │  código      │
     └──────────────┘      └──────────────┘      └──────────────┘
             │                     │                     │
             └─────────────────────┴─────────────────────┘
                                   ▼
                           ┌──────────────────┐
                           │   Auditor        │
                           │   6 criterios    │
                           │                  │
                           │   ✅ verified    │
                           │   ❌ rejected    │
                           └──────────────────┘
                                   │
                                   ▼
                           ┌──────────────────┐
                           │ Update queue     │
                           │ Update status.md │
                           │ Update CHANGELOG │
                           │ Update wiki-map  │
                           │ Próximo tick     │
                           └──────────────────┘
```

## Tick del orquestador

Cada cron fire (15-30 min), el orquestador ejecuta:

1. **Lee** `JWIKI/00_INDEX/task_queue.md` y `wiki-map.md`.
2. **Encuentra** el primer punto con estado `pending` cuyas dependencias estén todas `verified` o `done`.
3. **Marca** ese punto como `in_progress`.
4. **Despacha** según el tipo de punto:
   - **Investigación pura** (Landscape, AI Providers overview): Investigador solo.
   - **Documentación basada en código** (Backend, Frontend, Agentes): Investigador + agente de dominio (aithera-backend, aithera-frontend, etc.).
   - **Voice / Integrations**: Investigador + aithera-voz / aithera-integraciones.
   - **Memory / Tooling**: Investigador + aithera-memoria / aithera-agentes.
   - **Security**: Investigador + aithera-devops (auditoría de seguridad).
   - **Best practices / Known pitfalls**: Escriba consolida reportes del equipo `aithera-*`.
   - **SOPs**: Escriba + validador de dominio.
5. **Espera** el resultado (los agentes reportan via scratchpad o `mavis communication send`).
6. **Marca** el punto como `done` cuando el borrador está listo.
7. **Llama** a Auditor para validación.
8. **Si Auditor aprueba**: `verified`, actualizar status.md, CHANGELOG, wiki-map.
9. **Si Auditor rechaza**: `rejected`, abrir punto de rework (nuevo ID con sufijo `-RW1`), reasignar.
10. **Salir** del tick (la próxima vez el cron nos despierta).

## Despachar un punto

Para cada punto, el orquestrador:

1. Lee la sección "Notes" del punto en la cola (de ahí saca dependencias, fuentes esperadas, scope).
2. Decide **batching**: ¿este punto se puede procesar junto con N-1 y N+1 (relacionados)? Si sí, despacha los 3 juntos con dependencias internas documentadas.
3. Genera el prompt de despacho:

```markdown
@Aithera Investigador — procesa JWIKI-NNN: <path>.
Notas de la cola: <copy de Notes>.
Investiga, recopila material con fuentes, devuelve a Aithera Escriba.
```

4. Envía via `mavis communication send` o scratchpad.

## Procesamiento por agente

### Aithera Investigador (`aithera-wiki-investigador`)

Cuando Investigador recibe un despacho:

1. Lee `task_queue.md` para ver las "Notes" del punto.
2. Lanza búsquedas paralelas (GitHub, Reddit, HN, papers, YouTube).
3. Lee código fuente de los repos relevantes (openclaw, openhuman, open-jarvis, etc.).
4. Compila **material crudo** con formato:

```markdown
## Material crudo JWIKI-NNN

### Hechos verificados
1. [Hecho] — Fuente: <URL> — Fecha acceso: YYYY-MM-DD
2. [Hecho] — Fuente: <URL>

### Snippets de código
[path:line] código

### Diferencias entre proyectos
- OpenClaw: ...
- OpenHuman: ...
- OpenJarvis: ...

### Pendientes de validación
- [Algo que necesita check contra código por validador de dominio]
```

5. Envía material a Escriba via scratchpad o comunicación.

### Aithera Escriba (`aithera-wiki-escriba`)

Cuando Escriba recibe material:

1. Lee material de Investigador + consulta task_queue para path destino.
2. Aplica `JWIKI/00_INDEX/TEMPLATE.md`.
3. Escribe el documento completo.
4. Marca punto como `done` en task_queue.md.
5. Despacha a validador de dominio (agente `aithera-*` relevante) si el doc menciona código/APIs.
6. Cuando recibe feedback de validadores, integra correcciones.
7. Despacha a Auditor para los 6 criterios.

### Validador de dominio (agente `aithera-*`)

Cuando un `aithera-*` recibe un doc para validar:

1. Lee el documento JWIKI.
2. Verifica cada afirmación técnica contra código fuente (lee archivos directo del repo).
3. Marca cada afirmación como:
   - ✅ Verificada
   - ⚠️ Parcialmente correcta (con detalle)
   - ❌ Incorrecta (con explicación)
4. Devuelve a Escriba con el reporte.

### Aithera Auditor (`aithera-wiki-auditor`)

Cuando Auditor recibe un doc:

1. Aplica los **6 criterios** (ver CONSTITUTION.md §8):
   - [ ] Código revisado (commit/branch citados).
   - [ ] Fuentes contrastadas (mín. 2 independientes para afirmaciones clave).
   - [ ] Compatibilidad documentada (proyectos + versiones).
   - [ ] Ejemplos verificados (testeados o con ref a tests).
   - [ ] Referencias cruzadas añadidas.
   - [ ] Revisión independiente realizada.
2. Si ✅ todos: emite `verified` y Escriba lo publica (status.md, CHANGELOG.md, wiki-map.md).
3. Si ❌ alguno: emite `rejected` con detalle. Escriba reabre.

## Feedback loop desde desarrollo

**Cuando los agentes `aithera-*` (desarrollo de Aithera) descubren algo nuevo o un bug**,
**siempre** envía un "dev report" a Escriba:

```markdown
## Dev Report — YYYY-MM-DD

**Agente**: aithera-backend / aithera-frontend / etc.
**Tarea**: <qué estaba haciendo>
**Stack**: Aithera V0.7 / OpenClaw latest / etc.

### Hallazgos relevantes
1. [Algo que aprendió o descubrió]
   - Fuente: <código / log / output>
   - Impacto: <qué docs JWIKI debería actualizar>

### Errores / incompatibilidades encontradas
1. [Error X]
   - Condición: <cuándo ocurre>
   - Workaround: <si lo hay>

### Sugerencias a la wiki
1. Actualizar JWIKI-XXX: <qué cambiar>
2. Crear JWIKI-NNN: <nuevo doc sugerido>
```

Escriba lee cada dev report y:
- Si el hallazgo contradice algo en JWIKI → abre rework del doc.
- Si es info nueva → busca/abre el doc correspondiente y lo enriquece.
- Si no encaja en ningún doc existente → crea un nuevo punto JWIKI con sufijo `-FEEDBACK`.

## Final global audit

Cuando todos los puntos JWIKI-001..250 están `verified`, el orquestador lanza `JWIKI-AUDIT-01..04`:

1. **AUDIT-01** Auditor cross-check:
   - Lee todos los docs en orden.
   - Verifica que cada link interno funciona.
   - Detecta contradicciones entre docs (ej: doc A dice X, doc B dice Y).
   - Emite lista de fixes.

2. **AUDIT-02** Auditor verifica coherencia de versiones:
   - Cada doc declara versiones compatibles.
   - Las tablas comparativas son coherentes con los docs individuales.

3. **AUDIT-03** Auditor verifica nivel de confianza ≥80% global:
   - Si hay docs 🟡 (en progreso), reabrirlos.
   - Si hay 🔴 PENDIENTE, escalarlos a Mavis para decidir abandono.

4. **AUDIT-04** Escriba exporta PDF consolidado y publica `JWIKI-EXPORT-v1.0.pdf`.

## Cómo NO romper el loop

| ❌ No hagas | ✅ Haz |
|---|---|
| Saltarte pasos (publicar sin validar) | Siempre Investigador → Escriba → Validador → Auditor |
| Trabajar dos puntos en paralelo sin documentar relación | Documentar dependencia explícita en task_queue |
| Inventar info cuando falta fuente | Marcar `pending` con nota de qué falta |
| Cerrar un punto sin pasar por Auditor | Aunque sea trivial |
| Dejar el `current` puntero atrás | Actualizarlo en cada tick |

## Señales de vida del sistema

Si pasan 3 ticks sin avance, el orquestador debe:

1. **Diagnosticar**: ¿qué agente está bloqueado? ¿Investigador sin fuentes? ¿Escriba esperando validación? ¿Auditor sin contexto?
2. **Escalar al usuario** si el bloqueo es externo (ej: API keys agotadas, acceso bloqueado).
3. **Marcar como `⚫ Abandonado`** los puntos donde no haya avance posible.

---

*Workflow v1.0 — 2026-06-30.*