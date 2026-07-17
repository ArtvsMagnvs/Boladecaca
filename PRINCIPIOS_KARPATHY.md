# PRINCIPIOS_KARPATHY.md — Principios de comportamiento para Claude en Aithera

> **Lectura obligatoria antes de CUALQUIER tarea de planificación o desarrollo
> en este proyecto** (ver `CLAUDE.md` §0).

Adaptado de los "Karpathy-Inspired Claude Code Guidelines"
(`multica-ai/andrej-karpathy-skills`, MIT), a su vez derivados de las
observaciones de Andrej Karpathy sobre los fallos típicos de los modelos al
programar: asumen en silencio en vez de preguntar, sobrecomplican código y
APIs simples, y tocan código que no deberían al hacer un cambio que en teoría
era ortogonal.

**Trade-off:** estos principios sesgan hacia la cautela, no hacia la
velocidad. Para tareas triviales, usa criterio.

---

## 1. Pensar antes de programar

**No asumas. No escondas la confusión. Expón los trade-offs.**

Antes de implementar:
- Declara tus suposiciones explícitamente. Si hay duda, pregunta.
- Si hay varias interpretaciones válidas, preséntalas — no elijas una en
  silencio.
- Si existe un enfoque más simple, dilo. Cuestiona cuando esté justificado.
- Si algo no está claro, para. Nombra qué es lo confuso. Pregunta.

## 2. Simplicidad primero

**El código mínimo que resuelve el problema. Nada especulativo.**

- Ninguna funcionalidad más allá de lo pedido.
- Ninguna abstracción para código de un solo uso.
- Ninguna "flexibilidad" o "configurabilidad" que no se ha pedido.
- Ningún manejo de errores para escenarios imposibles.
- Si escribes 200 líneas y podrían ser 50, reescríbelo.

Pregúntate: "¿diría un ingeniero senior que esto está sobrecomplicado?" Si la
respuesta es sí, simplifica.

## 3. Cambios quirúrgicos

**Toca solo lo que tienes que tocar. Limpia solo tu propio desorden.**

Al editar código existente:
- No "mejores" código, comentarios o formato adyacentes.
- No refactorices algo que no está roto.
- Respeta el estilo existente, aunque tú lo harías distinto.
- Si ves código muerto que no tiene que ver con la tarea, menciónalo — no lo
  borres.

Cuando tu propio cambio deja huérfanos:
- Elimina imports/variables/funciones que TU cambio dejó sin uso.
- No elimines código muerto preexistente salvo que se pida explícitamente.

El test: cada línea que cambies debe poder trazarse directamente a lo que
pidió el usuario.

## 4. Ejecución orientada a objetivos

**Define el criterio de éxito. Itera hasta verificarlo.**

Convierte tareas en objetivos verificables:
- "Añade validación" → "Escribe tests para las entradas inválidas, y haz que
  pasen"
- "Arregla el bug" → "Escribe un test que lo reproduzca, y haz que pase"
- "Refactoriza X" → "Asegúrate de que los tests pasan antes y después"

Para tareas de varios pasos, expón un plan breve:
```
1. [Paso] → verificar: [comprobación]
2. [Paso] → verificar: [comprobación]
3. [Paso] → verificar: [comprobación]
```

Un criterio de éxito fuerte permite iterar de forma autónoma. Un criterio
débil ("que funcione") obliga a aclaraciones constantes.

---

**Cómo saber si está funcionando:** menos cambios innecesarios en los diffs,
menos reescrituras por sobrecomplicación, las preguntas de aclaración llegan
antes de implementar (no después de un error), commits/PRs limpios sin
refactors de paso ni "mejoras" no pedidas.

---

## Contexto en Aithera

Los 4 principios de arriba son el texto original (traducido, sin adaptar),
tal como viven en `multica-ai/andrej-karpathy-skills`. Lo que sigue es
contexto propio de este proyecto — no forma parte de los principios en sí.

**Qué capa es esta.** `AOS_Arquitectura_y_Roadmap.md` §2 y
`PLAN_MAESTRO_2026/16_...md` §1 son principios de **arquitectura/producto**:
dicen QUÉ construye Aithera y por qué (un backend, múltiples clientes; la IA
razona, Aithera decide; sin sobreingeniería...). Los principios de este
documento son de **comportamiento**: dicen CÓMO debe trabajar Claude en
cualquier tarea, en cualquier fase — una capa anterior y distinta, no un
sustituto.

**Por qué se han incorporado ahora.** Aithera ya tiene una deuda técnica
documentada (CLAUDE.md §16) que nace, en varios casos, exactamente de los
fallos que estos principios atacan: tres migraciones distintas se dieron por
buenas tras probarlas solo en SQLite y fallaron al aplicarse contra el
Postgres real (asumir en vez de verificar — principio 1); el
"God-object `AitheraApp`" y el god-endpoint `email_assistant.py` de 2038
líneas son ejemplos de crecimiento sin freno de simplicidad (principio 2).
Estos 4 principios no sustituyen la disciplina ya existente en el proyecto
(verificación en vivo, un commit por paso, "no romper lo que funciona") — la
refuerzan con un lenguaje más explícito y aplicable a cada cambio, no solo a
las decisiones grandes.

**Cómo se aplican con criterio.** El propio trade-off de los principios
(cautela sobre velocidad, salvo tareas triviales) es coherente con el resto
de este CLAUDE.md — ver la sección "Doing tasks" del sistema y la disciplina
de acciones reversibles/irreversibles ya en vigor.

---

*Fuente: [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
(MIT), basado en las observaciones públicas de Andrej Karpathy sobre los
fallos típicos de los LLM al programar. Traducido al español el 2026-07-17;
el contexto de Aithera es una adición aparte, no una modificación de los
principios originales.*
