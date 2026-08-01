# 38 — PI-B · Obsidian como frontend de la memoria — investigación + propuesta

> **Sesión**: PI-B (doc 35), 2026-07-31, Fable 5. Investigación pura — **no se
> tocó código de producción**. Entrega: propuesta honesta con recomendación
> para V1.0 (doc 35 pide 1-2 páginas).
> **Método**: análisis del código REAL del vault/memoria de Aithera
> (`memory/vault.py`, `lifecycle.py`, `summarizer.py`, `profile.py`,
> `decision_service.py`, `memory/router.py`) + verificación del estado actual de
> Obsidian por web. Nada asumido: lo que se afirma del vault sale de leer el
> archivo, no de suponer.

---

## Resumen ejecutivo (léelo primero)

**Recomendación: GO a la Opción 1 (Obsidian como frontend de LECTURA), por coste
bajo y beneficio real — pero NO bloquea el instalador de 1.0**: es un pulido que
puede entrar antes o justo después. **Opción 2 (ingestar las notas del usuario)
opcional post-1.0. Opción 3 (Obsidian como backend de memoria) DESCARTADA.**

El motivo por el que sale barato: **Aithera YA escribe un vault Markdown.** No
hay que construir un sistema nuevo; hay que (a) mover ese vault a una carpeta que
el usuario abra con Obsidian, y (b) enriquecer lo que ya escribe con frontmatter
YAML + wikilinks para que el graph view sea útil. Es trabajo localizado en
`vault.py` + un ajuste de carpeta en la UI. Cero dependencias nuevas, cero
cambios en ChromaDB, y fuera del camino caliente (el vault es best-effort,
nocturno/por-decisión).

**La honestidad que exige el usuario ("si no nos sirve, no nos sirve")**: el
beneficio es NICHO. El graph view de Obsidian solo aporta si el usuario de verdad
vive en Obsidian. Para quien no lo use, es esfuerzo invisible. Por eso: GO, pero
sin prioridad sobre el instalador.

---

## Punto de partida REAL (lo que ya existe, verificado en código)

`app/memory/vault.py` escribe hoy en `%APPDATA%/Aithera/vault/YYYY/MM/`
(reubicable con `AITHERA_VAULT_PATH`, env var que YA existe), tres tipos de nota,
desde tres puntos cableados y confirmados:

| Nota | Fichero | Escritor real (cableado) |
|---|---|---|
| Resumen diario | `YYYY-MM-DD-resumen.md` | `summarizer.py` (job nocturno) |
| Decisión | `{decision.id}-decision.md` | `decision_service.py` (cada decisión) |
| Archivo de poda | `YYYY-MM-{tipo}-archive.md` | `lifecycle.py` (antes de podar items viejos) |

**Formato actual**: solo `#` encabezados + etiquetas en negrita
(`**Motivo**`, `**Proyecto**`, `**Estado**`, `**Mision**`). **Hoy NO hay**:
frontmatter YAML, ni un solo `[[wikilink]]`, ni notas-entidad (no existe una nota
`Cordyceps.md` a la que enlazar). El proyecto/decisión/día son texto plano, no
nodos enlazados.

**Matiz importante y honesto** (corrige el listado optimista del doc 35): de las
4 cosas que el plan quería enriquecer —"resúmenes diarios, decisiones, hechos del
perfil, cierres de milestone"—, **solo las 2 primeras llegan al vault hoy**. Los
**hechos del perfil** (`profile.py`) y los **cierres de milestone / distilado de
proyecto** (WPMS W4) van únicamente a ChromaDB (`mem_personal`/`mem_project`),
NO al vault. Espejarlos es parte del trabajo de la Opción 1, no algo ya hecho.

**Estado de Obsidian (verificado, 2026)**: un vault de Obsidian es literalmente
una carpeta de archivos Markdown — Obsidian los LEE y renderiza, no hace falta
que la app esté corriendo para que Aithera escriba. El frontmatter YAML
("Properties") es el mecanismo estándar de metadatos estructurados; los
`[[wikilinks]]` resuelven por NOMBRE de nota en todo el vault (agnóstico a
carpetas) y son lo que alimenta el graph view. Existe incluso una corriente 2026
de "usar el vault de Obsidian como memoria/grafo de un agente IA" — relevante,
pero es justo lo que la Opción 3 matiza abajo.

---

## Las 4 preguntas del doc 35, respondidas

### Opción 1 · Como frontend (lectura) → **GO. Coste bajo, la opción que merece la pena** ✅

¿Basta con apuntar el vault a una carpeta que el usuario abre con Obsidian +
enriquecer lo escrito? **Sí, y es barato.** El trabajo concreto:

1. **Reubicar el vault a una carpeta del usuario** (no `%APPDATA%`, que está
   escondido). Ya existe `AITHERA_VAULT_PATH`; solo falta un campo en Ajustes +
   botón "elegir carpeta" — el MISMO selector de carpeta ya construido para
   `repo_path` de proyecto (Electron IPC `dialog:pick-folder`, W2e). Trivial.
2. **Frontmatter YAML** en cada nota (`type`, `date`, `project`, `tags`, ids).
   Es lo que hace que Obsidian trate cada nota como un objeto con propiedades
   filtrable. Cambio localizado en las 3 funciones de `vault.py`.
3. **Wikilinks + notas-entidad**: que un resumen diario enlace a los proyectos/
   decisiones que menciona (`[[Cordyceps]]`, `[[decisión-abc]]`), que una
   decisión enlace a su proyecto y su misión, que un cierre de milestone enlace
   a su proyecto. Para que esos enlaces resuelvan a NODOS reales (no a enlaces
   "huérfanos"), Aithera escribe además una **nota por proyecto** (`Cordyceps.md`
   con su frontmatter) que se actualiza al vuelo. Pequeño helper de slug +
   escritura idempotente.
4. **Espejar lo que falta** (opcional dentro de la Opción 1): cablear
   `profile.py` (hechos del perfil) y el distilado de milestone/proyecto para que
   también escriban su nota — mismo patrón best-effort que las 3 existentes.

Resultado: el usuario abre su carpeta en Obsidian y ve un grafo real —
proyectos ↔ decisiones ↔ días ↔ hechos— que se actualiza solo cada noche y con
cada decisión. **Sin dependencias nuevas, sin tocar ChromaDB, sin latencia**
(el vault ya es best-effort y off-hot-path).

### Opción 2 · Como fuente (lectura inversa: ingestar las notas del usuario) → **Opcional, post-1.0** ⚠️

¿Ingestar las notas que el usuario escribe en Obsidian hacia `mem_personal`?
**Técnicamente trivial** — es EL patrón del job de ingesta M2 (`ingestion.py`):
leer los `.md` de una carpeta, trocear, `store()` con `dedup_key = ruta + mtime`.
Pero abre problemas reales de **volumen y ruido**: el vault de un usuario puede
tener miles de notas de temas ajenos a Aithera, y meterlas todas en la memoria
semántica ensucia el contexto del chat. **Recomendación**: post-1.0, **opt-in**,
solo **subcarpetas elegidas** (no el vault entero), con tope de tamaño. Cuando se
haga, es pequeño-medio. No para 1.0.

### Opción 3 · Como backend de memoria → **DESCARTADA (con razón)** ❌

¿Podría Markdown plano sustituir el MOS? **No, y hay que decirlo claro.** La
memoria de Aithera es SEMÁNTICA: `memory_router.context()` hace búsqueda
vectorial (ChromaDB + embeddings) con **presupuesto de latencia duro de 300 ms**
en el camino del chat, dedup por coseno, colecciones tipadas. Markdown plano en
disco no puede dar recuperación semántica sub-segundo sin **reconstruir por
encima justo lo que ya es ChromaDB** (habría que embeder e indexar los .md — o
sea, reinventar el MOS). Obsidian es un buen ESPEJO de lectura humana; no es un
motor de recuperación. Se descarta salvo hallazgo sorprendente, que no lo hay.

### Opción 4 · Sincronía y conflictos → **Resuelto por diseño: Aithera escribe solo en lo suyo** ✅

Si Aithera escribe y el usuario edita en Obsidian, ¿qué pasa? **Se evita el
conflicto por construcción**: Aithera escribe SOLO en su propia subcarpeta
(p. ej. `<vault>/Aithera/`), con ficheros identificados por id/fecha
(append-only o sobrescritura de su propio fichero). Las notas del usuario son
**solo-lectura** para Aithera, salvo la ingesta opcional de la Opción 2. Así
Aithera nunca edita un fichero que el usuario edita. Refinamiento opcional: si el
usuario modifica a mano una nota escrita por Aithera, un chequeo de `mtime`
evitaría sobrescribirla en la siguiente pasada (pequeño extra, no imprescindible
— documentar el comportamiento basta).

---

## Recomendación final y coste

- **Opción 1 (frontend de lectura): GO**, por coste bajo y beneficio visible
  para quien use Obsidian. **No bloquea el instalador de 1.0** — es un pulido que
  cabe antes o justo después, a decisión del usuario. Honestidad: si no vives en
  Obsidian, no te aporta; por eso GO-pero-sin-prioridad.
- **Opción 2 (ingesta inversa): opcional, post-1.0**, opt-in y con límites.
- **Opción 3 (backend): descartada.**
- **Opción 4 (conflictos): resuelto** con la subcarpeta append-only de Aithera.

**Coste estimado de la sesión de implementación (si GO Opción 1): pequeño-medio,
~1 sesión.** Desglose:
- Reubicar vault + selector de carpeta en Ajustes: pequeño (env var ya existe,
  selector ya construido).
- Frontmatter YAML en las 3 funciones de `vault.py`: pequeño.
- Wikilinks + notas-entidad por proyecto (+ slug helper): pequeño-medio.
- Espejar perfil + cierres de milestone (para que el grafo tenga esos nodos):
  pequeño (mismo patrón best-effort).
- Sin dependencias nuevas, sin migración, sin tocar ChromaDB ni el camino
  caliente. Test: verificar que los `.md` escritos parsean como frontmatter
  válido y que los wikilinks resuelven (un test de formato, no de latencia).

---

## Qué queda en manos del usuario

- **Decisión**: ¿GO a la Opción 1 como sesión de pulido (PU-nueva), y cuándo —
  antes o después del instalador? Mi consejo: después, salvo que uses Obsidian a
  diario, en cuyo caso antes tiene sentido.
- Si dices GO, detallo la sesión ejecutable (diseño contra `vault.py` con el
  formato exacto de frontmatter/wikilinks y los tests). Igual que en PI-A, esto
  es solo la investigación; el fix/implementación es aparte.

---

*Creado: 2026-07-31 (PI-B, Fable 5). Fuentes: código real del vault/memoria de
Aithera (`memory/vault.py` y consumidores) + estado actual de Obsidian
verificado por web (vault = carpeta Markdown, Properties/frontmatter YAML,
wikilinks por nombre, graph view; corriente 2026 "Obsidian como memoria de
agente"). Sin cambios de código en esta sesión.*
