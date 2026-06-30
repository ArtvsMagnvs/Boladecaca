# CONTRIBUTING — Cómo contribuir a la JWIKI

> Reglas para añadir o modificar documentos de la JWIKI.

## Principios

1. **Lee primero `CONSTITUTION.md`** — esas reglas son inviolables.
2. **Sigue `00_INDEX/TEMPLATE.md`** — todo doc nuevo usa esa plantilla.
3. **Cita fuentes siempre** — sin fuente, no publicamos.
4. **Marca `VERIFICACIÓN PENDIENTE`** si algo no puedes verificar.
5. **No dupliques docs** — busca primero en `00_INDEX/wiki-map.md`.

## Workflow para un doc nuevo

1. **Identifica el dominio correcto** (01-16) según `00_INDEX/architecture.md`.
2. **Comprueba que no exista** buscando en `00_INDEX/wiki-map.md` o `task_queue.md`.
3. **Si no existe**, añade un punto a `00_INDEX/task_queue.md` con:
   - ID (`JWIKI-NNN`)
   - Path destino
   - Estado `pending`
   - Notes (qué cubre, fuentes esperadas)
4. **Espera al orquestrador** — Mavis despachará al Investigador.

## Workflow para revisar/validar un doc

1. **Lee el documento** completo.
2. **Aplica los 6 criterios** de validación (ver `CONSTITUTION.md` §8):
   - [ ] Código revisado
   - [ ] Fuentes contrastadas (mín. 2)
   - [ ] Compatibilidad documentada
   - [ ] Ejemplos verificados
   - [ ] Referencias cruzadas añadidas
   - [ ] Revisión independiente realizada
3. **Emite veredicto**:
   - ✅ `verified` → doc publicado
   - ❌ `rejected` → reabrir con detalle, ID con sufijo `-RW1`
4. **Reporta al orquestrador** via scratchpad o comunicación.

## Reglas de nombrado

- **Carpetas de dominio**: `NN_DOMAIN` (NN = número, DOMAIN = nombre en mayúsculas con guiones bajos).
- **Archivos**: `kebab-case.md` (todo minúsculas, palabras separadas por guión).
- **Subcarpetas permitidas**: solo cuando un dominio tiene >10 docs.

## Versionado

- Cambios menores (typos, aclaraciones): commit directo.
- Cambios mayores (nuevo dominio, modificación de constitución): tag anotado (`v1.1`, `v2.0`).
- El changelog vive en cada documento (sección al final) y en commits de git.

## Cómo NO contribuir

| ❌ No hagas | ✅ Haz |
|---|---|
| Publicar sin fuentes citadas | Marcar `VERIFICACIÓN PENDIENTE` |
| Inventar ejemplos | Usar ejemplos reales de repos OSS |
| Copiar y pegar documentación literal | Sintetizar y relacionar |
| Crear docs duplicados | Buscar primero en `wiki-map.md` |
| Saltarse la plantilla | Rellenar TODAS las secciones |

---

*Contributing v1.0 — 2026-06-30.*