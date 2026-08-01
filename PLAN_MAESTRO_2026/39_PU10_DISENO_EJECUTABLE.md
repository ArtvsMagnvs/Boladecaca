# 39 — PU10 · Diseño ejecutable: memoria visible y corregible

> **Qué es este documento**: el diseño EJECUTABLE de PU10 (doc 35), contrastado
> línea a línea contra el código real (2026-07-31, Fable 5). Mismo formato que
> los diseños del doc 34: archivo, función, cambio exacto, tests. **Quien
> ejecute esta sesión implementa y verifica — no rediseña.**
>
> **Origen**: conversación de diseño con el usuario tras cerrar PI-B. La
> pregunta era "si fueras un humano que quiere interacción visual con la
> memoria, ¿cómo lo harías?". La respuesta corta está en §0; de cinco ideas
> evaluadas, tres se construyen y dos se descartan **explícitamente** (§6) para
> que nadie las reintroduzca por su cuenta.

---

## 0. La tesis (por qué el diseño es este y no un panel bonito)

**La memoria útil no es una pantalla, son tres gestos dentro de la
conversación.** Nadie entra a "revisar su memoria" por gusto: se toca la
memoria en dos momentos, cuando Aithera dice algo raro (¿de dónde ha salido
eso?) y cuando dice algo mal (eso bórralo). Los dos ocurren EN EL CHAT, no en
Ajustes.

Sobrevive UNA pantalla — el inventario "lo que sé de ti" — porque la confianza
necesita una lista que puedas leer de arriba abajo. Todo lo demás vive en el
flujo.

Los tres bloques, por orden de valor:

| Bloque | Qué resuelve | Dónde vive |
|---|---|---|
| **A · Procedencia** | "¿de dónde has sacado eso?" + corregirlo ahí mismo | Chat |
| **B · Inventario** | "¿qué sabes de mí?" + fijar / borrar / ver qué se va a olvidar | Ajustes → Memoria |
| **C · Olvidar hablando** | borrado en bloque ("olvida todo lo de X") | Chat / mini-chat |

---

## 1. Punto de partida REAL (verificado, no supuesto)

| Hecho del código | Dónde | Por qué importa |
|---|---|---|
| `context()` devuelve **un `str`** con atribución textual; por dentro llama `search(top_k=8)` y **descarta los `MemoryItem`** | `memory/stores/local_store.py:277`, `memory/router.py:115` | Los ids ya existen una línea antes de tirarse. El bloque A es recuperarlos, no calcularlos. |
| `MemoryItem` tiene **`id`** | `memory/interfaces.py:48-57` | Hay con qué identificar cada recuerdo en la UI. |
| id = **`{memory_type}:{dedup_key\|uuid}`**; `retrieve()` resuelve el store partiendo por `":"` | `local_store.py:118-121`, `router.py:98-105` | El borrado/edición por id sigue ese MISMO patrón, sin inventar resolución nueva. |
| `pinned` lo respeta el podador y **NADIE lo escribe** (0 endpoints, 0 frontend) | `memory/lifecycle.py:64-77` | Capacidad muerta: el botón "fijar" es casi gratis en backend. |
| Ventana HOT dinámica `30→21→14→7` | `lifecycle.py:61`, `_effective_hot_days()` | Da el "se olvida en N días" del bloque B. |
| `update` = `retrieve()` + `store()` con el MISMO `dedup_key`; `delete` = `forget()` | `tools/memory_tool.py:166-193` | **Ya existe el camino único de escritura.** Los endpoints nuevos lo reusan; NO se duplica. |
| Los bloques de memoria del chat ya se **cachean por (sesión, tema)** | `chat_service._SESSION_CTX`, `_memory_blocks_session` | El bloque A no añade I/O: los items salen de un cálculo que ya se hace. |
| `GET /memory/profile` y `DELETE /memory/profile/{key}` ya existen | `api/endpoints/memory.py:270,279` | El bloque B extiende, no crea. |
| ⚠️ `/api/memory/context*` está **OCUPADO** por la colección legacy `user_context` | `api/endpoints/memory.py:116-148` | **Colisión de nombres**: los endpoints nuevos NO pueden llamarse `/context`. |
| `Settings.tsx` pesa **131 KB**; `components/voice/VoicePanel.tsx` es el precedente de extraer un panel | `pages/Settings.tsx:40` (tab "memoria"), `:1873-2010` | El panel de Memoria se EXTRAE, no se mete más en Settings.tsx. |

---

## 2. Bloque A · Procedencia en el chat (el núcleo de la sesión)

### A.1 — Backend: recuperar los items sin romper el contrato congelado

**`memory/interfaces.py`** — añadir un dataclass (adición pura, no toca los
métodos congelados):

```python
@dataclass(frozen=True)
class MemoryContext:
    """Lo que context() ya construye, con las FUENTES que hoy se descartan."""
    text: str                      # idéntico a lo que devuelve context()
    items: list[MemoryItem]        # los items reales, con id
```

**`memory/stores/local_store.py`** — nace `context_with_sources(...)` con el
cuerpo ACTUAL de `context()`, y **`context()` pasa a delegar**:

```python
async def context(self, query, max_tokens=1500, memory_types=None, project_id=None) -> str:
    return (await self.context_with_sources(query, max_tokens, memory_types, project_id)).text
```

> **INVARIANTE que el test vigila**: `context()` y `context_with_sources().text`
> devuelven EXACTAMENTE lo mismo, porque hay UNA implementación. Si alguien
> duplica el cuerpo, el test cae.

**`memory/router.py`** — `context_with_sources()` gemelo del `context()`
existente. Para un store que no la implemente (el stub `distributed_store.py`),
degrada con `getattr(store, "context_with_sources", None)` → si no está,
devuelve `MemoryContext(text=await store.context(...), items=[])`.

> **Decisión deliberada — por qué NO se añade el método al ABC `IMemoryStore`**:
> es un contrato CONGELADO (doc 07 M1) y añadir un método abstracto rompería
> toda implementación que no lo tenga (hoy, el stub distribuido). El duck-typing
> con `getattr` es el mismo patrón que ya usa `automation/engine._interpret_result`
> (comprueba `.ok` por duck-typing a propósito, para no crear un ciclo de
> imports). Precedente propio del proyecto, no una excepción inventada aquí.

### A.2 — Cómo llegan las fuentes a la interfaz

**`services/chat_service.py`** — `_SESSION_CTX` pasa a guardar también los
items: la tupla cacheada gana un elemento (`(query, blocks, expiry, ver, items)`),
que `_compute_memory_blocks` rellena desde `context_with_sources`. **Cero I/O
nuevo**: es el mismo cálculo que ya se hace, guardando lo que ya venía.

Nuevo accesor público del módulo:

```python
def recall_sources(session_id: str) -> list[dict]:
    """Los recuerdos EN JUEGO en esta conversación (los que se pasaron al
    modelo). Vacío si no hay nada cacheado para esa sesión."""
```

**`api/endpoints/memory.py`** — `GET /api/memory/recall?session_id=…`
→ `{items: [{id, content, memory_type, source, created_at, pinned}], count}`.

> **Nombre**: `recall`, NO `context` — `/api/memory/context*` ya está ocupado
> por la colección legacy `user_context` (ver §1). Colisión real evitada.

> **Decisión deliberada — alternativas descartadas**:
> · *Enhebrar los items por la cadena de llamadas* (`build_system_prompt` →
>   `NullRuntime` → `AgentTask` → pipeline): obligaría a tocar contratos
>   CONGELADOS (`AgentTask`) para transportar algo que el caché ya tiene.
> · *Emitir un evento SSE `sources`* (el parser de T4b ya despacha por `event:`,
>   así que encajaría): mismo problema — hay que subir los items desde
>   `build_system_prompt` hasta el emisor del stream, atravesando el TIE. Se
>   descarta por invasivo, no por imposible; si algún día hace falta
>   granularidad POR MENSAJE, esta es la vía y el parser ya está listo.

> **Alcance HONESTO de lo que se muestra** (y su etiqueta en la UI): el caché es
> por **(sesión, tema)**, así que los chips reflejan *"la memoria en juego en
> esta conversación"*, no *"lo que usé para esta frase"*. Es lo correcto además
> por otro motivo: **no se puede saber si el modelo usó de verdad un recuerdo**;
> afirmarlo sería exactamente el tipo de mentira pequeña que S2·S6/NEW-7 llevan
> dos bloques erradicando. La copia de la UI dice "he tenido esto en cuenta",
> nunca "usé esto".
>
> **Degradación**: sin `session_id` o en chat de proyecto/misión no hay caché →
> `recall` devuelve vacío → no salen chips. Aceptado: los chips viven en la
> charla, que es donde el usuario conversa.

### A.3 — Editar / borrar / fijar un recuerdo

**`memory/router.py`** — dos métodos nuevos que siguen el patrón de `retrieve()`
(resolver el store por el prefijo del id):

```python
async def update_item(self, item_id: str, *, content=None, metadata_patch=None) -> Optional[str]
async def forget_by_id(self, item_id: str) -> bool
```

`update_item` reusa el mecanismo YA EXISTENTE (`retrieve` + `store` con el mismo
`dedup_key`, tal cual `memory_tool._update`). **`tools/memory_tool.py::_update`/
`_delete` se reescriben para llamar a estos métodos** — un solo camino de
escritura para el chat, la tool y los endpoints, nunca tres copias.

**`api/endpoints/memory.py`**:
- `PATCH /api/memory/items/{item_id}` · body `{content?: str, pinned?: bool}`
- `DELETE /api/memory/items/{item_id}`

> **A verificar al implementar** (no se pudo probar en el sandbox, sin Chroma
> real): que el borrado por id use el `delete(ids=[…])` de la colección y no un
> `where` de metadata — `forget()` filtra por metadata y el id es el id de
> Chroma. Si `forget()` no sirve, `forget_by_id` va directo a la colección. Es
> el único punto del diseño que exige comprobación en vivo.

### A.4 — Frontend: el chip

**`pages/Chat.tsx`** — `ChatBubble` (línea 918, ya memoizado) acepta
`sources?: MemorySource[]`. Al terminar una respuesta (tras `streamChat`, junto
a los callbacks `onStatus`/`onMission` de la línea 371) se llama
`api.getRecallSources(sid)` y se adjuntan al último mensaje del asistente.

Reglas de la UI, que son las que evitan que esto sea ruido:

1. **Solo si hubo memoria.** Sin items, no hay chip — un chip permanente se
   vuelve mobiliario y deja de verse.
2. **Colapsado por defecto**: una línea discreta ("he tenido en cuenta 3 cosas
   que sé de ti") que despliega al clicar. No 3 chips gritando bajo cada
   respuesta.
3. **Borrar con DESHACER, no con confirmación.** Un `ConfirmDialog` en cada
   corrección hace que el usuario deje de corregir; un "deshacer" de 5 s no.
   `components/ConfirmDialog.tsx` (U1) se reserva para lo destructivo de
   verdad (bloque C).
4. **Fijar es un clic**, sin diálogo.

**`lib/api.ts`** — `getRecallSources`, `updateMemoryItem`, `deleteMemoryItem`
(junto al resto de `/memory/*`, líneas 1120-1141).

---

## 3. Bloque B · El inventario ("lo que sé de ti")

**`components/memory/MemoryPanel.tsx` (NUEVO)** — se EXTRAE la pestaña Memoria
de `Settings.tsx` (131 KB; sección actual en `:1873-2010`), siguiendo el
precedente exacto de `components/voice/VoicePanel.tsx`. `Settings.tsx` queda
montando el panel, sin crecer.

Tres zonas (las del plan de PU10) con lo nuevo:

1. **Lo que Aithera sabe de ti** — `GET /memory/profile` (ya existe) + por cada
   hecho: **fijar** (`PATCH .../items/{id}` con `pinned`) y borrar (ya existe).
2. **Estado de la memoria** — stats por tipo, última ingesta, próximo resumen
   (datos ya disponibles; presentarlos limpio).
3. **Mini-chat de memoria** — bloque C.

**El "se va a olvidar", PLEGADO en la zona 1 (no es pantalla nueva)**: cada item
se muestra **atenuado** cuando le quedan pocos días de ventana HOT, con su
"se olvida en N días"; al fijarlo vuelve a opaco. Un panel dedicado a "lo que
voy a olvidar" no lo abriría nadie; un item que se apaga en una lista que ya
miras, sí.

Para eso, el backend expone el pronóstico junto a cada item:

**`memory/lifecycle.py`** — helper **read-only** (no toca la poda):

```python
def prune_forecast(created_at, metadata) -> Optional[int]:
    """Días que le quedan a un item antes de entrar en la poda, o None si está
    protegido (pinned / urgente / daily_summary — ver _is_protected) o si su
    tipo no se poda. Usa _effective_hot_days(): la ventana REAL (30→21→14→7),
    no la nominal."""
```

Se añade como campo `prunes_in_days` en la respuesta del inventario. **Ni una
línea de la lógica de poda cambia** — solo se lee.

---

## 4. Bloque C · Olvidar hablando

Ya está en el plan de PU10 (mini-chat + "guarda esto en la memoria" desde el
chat normal). Lo único que este diseño añade: **enruta al mismo
`memory_router.forget_by_id`/`forget` de §A.3** — un solo camino de escritura,
como el propio plan exige. Un borrado en bloque ("olvida todo lo de Cordyceps")
SÍ pasa por `ConfirmDialog` con el número de items afectados: es destructivo y
no trivialmente reversible.

---

## 5. Tests (`tests/test_pu10_memoria.py`, NUEVO)

**Contrato / no-divergencia**
1. `context()` devuelve EXACTAMENTE `context_with_sources().text` sobre el mismo
   corpus (la invariante de una sola implementación).
2. `context_with_sources()` devuelve items **con `id` no vacío** y en el mismo
   orden que aparecen en el texto.
3. Un store SIN `context_with_sources` (doble del stub) degrada a
   `MemoryContext(text=…, items=[])` sin lanzar.
4. El filtro de proyecto (C-1b) se respeta también en la variante nueva: un item
   de otro `project_id` no aparece **ni en el texto ni en los items**.

**Procedencia**
5. `recall_sources(session_id)` devuelve los items tras un turno de chat real
   (con el LLM doblado en la frontera); sin sesión → `[]`.
6. `GET /api/memory/recall` sin `session_id` → `[]`, nunca 500.

**Escritura (el que de verdad importa)**
7. `PATCH .../items/{id}` con `pinned:true` → el item **sobrevive a una pasada
   REAL de poda** que sí borra a su vecino no fijado. Integración con
   `lifecycle`, no un mock: es la prueba de que el botón hace lo que promete.
8. `PATCH` con `content` → el contenido cambia **y el id se conserva** (mismo
   `dedup_key`), y el nuevo texto aparece en el `context()` siguiente.
9. `DELETE .../items/{id}` → desaparece de `retrieve()` y del `context()`.
10. `memory_tool._update`/`_delete` y los endpoints acaban en la MISMA función
    del router (un solo camino de escritura).

**Pronóstico**
11. Item viejo no protegido → `prunes_in_days` coherente con `_effective_hot_days`.
12. Item `pinned` / `urgente` / `daily_summary` → `None` (nunca se poda).

**Honestidad de la UI**
13. El payload de `recall` **no contiene ningún campo que afirme uso**
    (`used`, `applied`…): solo lo que se pasó al modelo. Congela la decisión de
    §A.2 para que nadie la "mejore" luego.

**Comprobaciones de mutación** (restaurar byte a byte tras cada una):
- Duplicar el cuerpo de `context()` en vez de delegar → cae el test 1.
- Quitar el `pinned` del `metadata_patch` en `update_item` → cae el 7.
- Hacer que `prune_forecast` ignore `_is_protected` → cae el 12.

**Regresión obligatoria**: `test_memory_contracts`, `test_memory_context`,
`test_lifecycle`, `test_module_boundaries` (el panel nuevo y los métodos nuevos
tienen que quedar dentro de las fronteras del barrel `app.memory`).

---

## 6. Lo que esta sesión NO construye (y por qué — no reintroducir)

- **Línea de tiempo de días.** Descartada: duplica lo que el briefing (PU4) ya
  cuenta, y "¿qué hice la semana pasada?" se **escribe** más rápido de lo que se
  scrollea. Interfaz que compite con una pregunta, pierde.
- **Constelación / mapa semántico de embeddings.** Descartada pese a ser
  atractiva: es la misma trampa que el graph view de Obsidian, más cara
  (proyección UMAP/t-SNE, dependencia nueva, job nocturno, canvas interactivo)
  y con unos miles de items se ven manchas, no estructura. Se miraría dos veces.
  **Se reabriría solo si** la memoria crece a decenas de miles de items Y el
  borrado en bloque por conversación (§4) se queda corto — es decir, cuando
  tenga un TRABAJO, no un "queda bonito".
- **Obsidian como interfaz.** Sigue donde lo dejó PI-B (doc 38): exportación
  para quien quiera sus archivos, no frontend de la memoria.

---

## 7. Tamaño y orden

**Tamaño**: media. **Modelo**: Sonnet, esfuerzo alto (es plomería precisa sobre
contratos congelados, no diseño). **Orden dentro del bloque**: A.1 → A.2 → A.3
(backend completo y testeado) → B (backend del pronóstico) → A.4 + B (frontend
juntos, una sola pasada de UI) → C.

**Criterio de cierre**: (1) en una conversación normal, una respuesta que usó
memoria muestra su procedencia, y desde ahí se puede borrar un recuerdo y ver
que **deja de influir** en la respuesta siguiente; (2) un hecho fijado desde
Ajustes sobrevive a una poda real; (3) los dos ejemplos literales del usuario
que ya pedía PU10 siguen funcionando end-to-end.

---

*Creado: 2026-07-31 (Fable 5). Diseño contrastado contra el código real:
`memory/{interfaces,router,lifecycle}.py`, `memory/stores/local_store.py`,
`services/chat_service.py`, `tools/memory_tool.py`,
`api/endpoints/memory.py`, `pages/{Chat,Settings}.tsx`, `lib/api.ts`.
Sin cambios de código en esta sesión — esto es el plano.*
