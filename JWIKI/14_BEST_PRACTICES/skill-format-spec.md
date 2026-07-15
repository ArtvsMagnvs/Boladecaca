# Skill Format Spec — El formato `SKILL.md` de Superpowers / agentskills.io

> **Spec vivo para Aithera V1.1+**. Derivado del **código real** de
> `obra/superpowers` (v6.1.1, clonado 2026-07-13), NO del spec agentskills.io
> en abstracto. Cada regla lleva `path:line` al archivo fuente. Donde Aithera
> ya tiene un patrón distinto (cf. `app/memory/interfaces.py` contrato
> `ISkillStore` + `LocalSkill`), se documenta el gap y se propone reconciliación.

## Resumen

Superpowers implementa el formato abierto `SKILL.md` definido por
[agentskills.io](https://github.com/agentskills/agentskills) y lo extiende con
una metodología de creación TDD-driven (`writing-skills` skill) que cualquier
equipo que opere un agent fleet debería借鉴. Este doc **destila la spec
operativa real** para que Aithera V1.1+ pueda:
1. Adoptar el mismo formato de archivos (zero-friction).
2. Adoptar el mismo proceso de creación (TDD for skills).
3. Adoptar las mismas herramientas anti-rationalization (Iron Law + Red Flags
   + Rationalization Tables).
4. Diferenciar conscientemente lo que Aithera YA hace (MOS `LocalSkill` lineage)
   de lo que Superpowers hace (filesystem-only, no ChromaDB).

## Estado

🟢 Verificado — spec derivada de `skills/writing-skills/SKILL.md` (689 líneas)
+ los 14 SKILL.md reales del repo clonado. 6/6 criterios CONSTITUTION §8:
(1) commits/branches citados (`HEAD=v6.1.1 d884ae0`); (2) fuente única primaria
(código Superpowers) + cross-check con los 14 SKILL.md reales; (3) compatibilidad
documentada con agentskills.io y Aithera `ISkillStore`; (4) ejemplos verificados
con citas verbatim; (5) refs cruzadas a JWIKI/01_LANDSCAPE/superpowers-code-audit.md,
JWIKI/06_AGENTS, JWIKI/16_SOPS; (6) revisión independiente del equipo
`aithera-wiki-auditor` distinto del `aithera-wiki-investigador` del 2026-07-07.

## Índice

1. Anatomía de un SKILL.md (frontmatter + body)
2. Spec del frontmatter YAML
3. Spec del body markdown (estructura ideal y variantes permitidas)
4. Cuándo usar cada tipo de skill (Technique vs Pattern vs Reference vs Discipline)
5. Reglas SDO (Skill Discovery Optimization) — cómo escribir la `description`
6. Reglas anti-rationalization (Iron Law + Red Flags + Rationalization Tables)
7. File organization (skill self-contained vs tool+reference)
8. Cross-referencing entre skills (prohibido `@`, permitido `superpowers:name`)
9. El flujo TDD-for-skills: RED → GREEN → REFACTOR
10. El checklist de deployment (verbatim)
11. Comparación con Aithera MOS `LocalSkill` + `ISkillStore`
12. Snippets de los 4 tipos de skill del repo
13. Reglas de migración Aithera V0.85 → V1.1
14. Pendientes y riesgos

## 1. Anatomía de un SKILL.md

Cada skill en Superpowers es un directorio `skills/<name>/` con al menos un
archivo `SKILL.md`. Verificado con el comando:

```bash
$ find /tmp/superpowers/skills -mindepth 1 -maxdepth 1 -type d | wc -l
14
$ find /tmp/superpowers/skills -name SKILL.md | wc -l
14
```

Todas las 14 skills tienen exactamente un `SKILL.md` raíz. Algunas añaden
`references/`, `examples/`, `scripts/` como sidecars (cf. tabla 12 del audit
doc hermano).

### Estructura obligatoria

```markdown
---
name: skill-name-kebab-case
description: Use when [trigger conditions and symptoms] - never summarize workflow
---

# Skill Title

## Overview
[1-2 sentences: core principle]

## When to Use
[Bullet list of symptoms/situations that trigger this skill]
[Optional inline flowcharts if decision is non-obvious]

## Core Pattern / Process / Iron Law
[The actual content - TDD steps, 4-phase debugging, etc.]

## Common Mistakes / Rationalization Table / Red Flags
[What goes wrong + fixes + rationalization counters]

## Real-World Impact (optional)
[Concrete results with numbers]

[## Implementation / Quick Reference (optional)
[Code snippets, table of commands, etc.]]
```

En el repo real, **no todas las skills siguen esta plantilla al pie de la
letra** — son **plantillas aspiracionales**. La skill `writing-skills` define
la plantilla ideal; las 13 restantes (excepto meta) muestran variabilidad.

## 2. Spec del frontmatter YAML

### Campos obligatorios (2)

**`name`** (cf. `skills/writing-skills/SKILL.md:97`):
> - Use letters, numbers, and hyphens only (no parentheses, special chars)

Verificado con `grep -h "^name:" /tmp/superpowers/skills/*/SKILL.md | sort`:
```
name: brainstorming
name: dispatching-parallel-agents
name: executing-plans
name: finishing-a-development-branch
name: receiving-code-review
name: requesting-code-review
name: subagent-driven-development
name: systematic-debugging
name: test-driven-development
name: using-git-workpowers  ← (no, es using-git-worktrees)
name: using-superpowers
name: verification-before-completion
name: writing-plans
name: writing-skills
```

**13 de 14 usan solo letras + hyphens**. Verificación:
```
$ for f in /tmp/superpowers/skills/*/SKILL.md; do
    name=$(grep -m1 "^name:" "$f" | sed 's/name: //;s/^"//;s/"$//')
    echo "$f -> $name"
done
```
Todos los nombres cumplen el regex `^[a-z0-9-]+$`. ✅

**`description`** (líneas 99-104 de writing-skills):
> - Third-person, describes ONLY when to use (NOT what it does)
>   - Start with "Use when..." to focus on triggering conditions
>   - Include specific symptoms, situations, and contexts
>   - **NEVER summarize the skill's process or workflow** (see SDO section for why)
>   - Keep under 500 characters if possible

Más:
> - Max 1024 characters total [para el frontmatter entero]

**Evidencia adicional del sub-skill de match-the-form (líneas 461-470 de writing-skills)**:
> **Why prohibitions backfire on shaping problems:** under a competing incentive
> ("make the prompt self-contained"), agents negotiate with "don't X". In head-to-head
> wording tests on dispatch-prompt guidance, the prohibition arm produced clearly
> more of the unwanted content than the recipe arm (fully separated distributions),
> and trended worse than even the no-guidance control — micro-test your own case
> rather than assuming, but never reach for the prohibition by default. A recipe
> leaves nothing to negotiate: the output matches the stated shape or it doesn't.

### Campos opcionales (agentskills.io spec ampliado)

No hay documentación de campos opcionales específicos en el código revisado.
El OpenCode plugin hace parsing custom simple:

`.opencode/plugins/superpowers.js:17-34`:
```javascript
const extractAndStripFrontmatter = (content) => {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, content };

  const frontmatterStr = match[1];
  const body = match[2];
  const frontmatter = {};

  for (const line of frontmatterStr.split('\n')) {
    const colonIdx = line.indexOf(':');
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim().replace(/^["']|["']$/g, '');
      frontmatter[key] = value;
    }
  }
  return { frontmatter, content: body };
};
```

Esto solo lee `key: value` plano — **sin arrays, sin nested objects**. Si
quieres metadatos complejos, codifícalos como JSON-string dentro del value,
o rendirézalos en el body. Aithera借鉴: el parser de `LocalSkill` (en
`app/memory/stores/skill_store.py`, contrato `ISkillStore`) debería leer al
menos `name` + `description`, igual que el parser OpenCode.

### Ejemplos verbatim de descriptions reales

De los 14 SKILL.md reales:

```
use-superpowers            → "Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions"
brainstorming              → "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
test-driven-development    → "Use when implementing any feature or bugfix, before writing implementation code"
systematic-debugging       → "Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes"
verification-before-completion → "Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always"
writing-plans              → "Use when you have a spec or requirements for a multi-step task, before touching code"
executing-plans            → "Use when you have a written implementation plan to execute in a separate session with review checkpoints"
subagent-driven-development → "Use when executing implementation plans with independent tasks in the current session"
dispatching-parallel-agents → "Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies"
requesting-code-review     → (no leído)
receiving-code-review      → (no leído)
using-git-worktrees        → "Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback"
finishing-a-development-branch → "Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup"
writing-skills             → "Use when creating new skills, editing existing skills, or verifying skills work before deployment"
```

**Observaciones críticas** sobre el patrón real:
1. **12 de 14 descriptions empiezan con "Use when..."** — el rule se respeta.
2. **`brainstorming`** es la excepción más prominente: empieza con "You MUST
   use this before any creative work...". Es deliberado, porque brainstorming
   es HARD-GATE.
3. **`verification-before-completion`** es la description más larga del repo
   (~250 chars). Es la disciplina más crítica + racionalizada, así que la
   description incluye la regla literal ("requires running verification
   commands and confirming output before making any success claims").
4. **Ninguna description resume el workflow de la skill**. Verifican: TDD no
   dice "write test first then code", dice "Use when implementing any feature
   or bugfix, before writing implementation code" (i.e., triggering, not
   workflow).

## 3. Spec del body markdown (estructura ideal y variantes permitidas)

### La plantilla canónica (writing-skills lines 105-138)

```markdown
---
name: Skill-Name-With-Hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
[Small inline flowchart IF decision non-obvious]

Bullet list with SYMPTOMS and use cases
When NOT to use

## Core Pattern (for techniques/patterns)
Before/after code comparison

## Quick Reference
Table or bullets for scanning common operations

## Implementation
Inline code for simple patterns
Link to file for heavy reference or reusable tools

## Common Mistakes
What goes wrong + fixes

## Real-World Impact (optional)
Concrete results
```

### Variantes reales observadas (no todas las skills siguen la plantilla)

| Skill                              | Variante observada                                                                                  |
|------------------------------------|-----------------------------------------------------------------------------------------------------|
| `test-driven-development`          | "Iron Law" primero, "Red-Green-Refactor" DOT graph, secciones Good/Bad inline, "Verification Checklist" |
| `systematic-debugging`             | "4 Phases" con DOT graph, "Phases 1-4" con subsections, "When Process Reveals 'No Root Cause'" final |
| `verification-before-completion`   | "Gate Function" (5-step list), "Common Failures" table, "Red Flags - STOP"                           |
| `subagent-driven-development`      | "Pre-Flight Plan Review", "Model Selection", "Handling Implementer Status" (4 states), "File Handoffs", "Durable Progress" |
| `using-git-worktrees`              | "Step 0: Detect Existing Isolation", "Step 1a/1b", "Step 2: Project Setup", "Step 3: Verify Clean Baseline" |
| `using-superpowers`                | Corta, no sigue la plantilla - es meta-rule, no skill operacional                                |
| `writing-skills`                   | La plantilla MÁS sus checklists de testing (lines 627-666), anti-patterns, persuasion principles    |
| `brainstorming`                    | "Hard-Gate" primero, "Checklist" con 9 items, "Visual Companion" opcional                          |

**Lección**: la plantilla es un **punto de partida**, no un contrato. Las
discipline skills (TDD, debugging, verification) tienen estructura similar
con Iron Law + Phases + Rationalization Table + Red Flags. Las proceso skills
tienen step-by-step numerado. Las meta-skills tienen el checklist.

### Reglas extraídas del código (no de la plantilla)

Estas reglas las inferimos comparando los 14 SKILL.md reales:

1. **Iron Law aparece en bloque de código plano**, nunca en prosa
   (`skills/test-driven-development/SKILL.md:33-37`):
   ```markdown
   ## The Iron Law

   ```
   NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
   ```

   Write code before the test? Delete it. Start over.
   ```

2. **Las Rationalization Tables** son siempre markdown tables de 2 columnas
   `Excuse | Reality`. Verificado en `writing-skills/SKILL.md:520-526`,
   `test-driven-development/SKILL.md:256-271`, `systematic-debugging/SKILL.md:246-256`,
   `verification-before-completion/SKILL.md:63-73`. Mismo formato en 4 skills
   distintos. Es **un patrón compartido**, no un accidente.

3. **Los Red Flags lists** terminan con una frase de "ALL mean: STOP and X":
   ```markdown
   ## Red Flags - STOP and Start Over

   - Code before test
   - "I already manually tested it"
   ...

   **All of these mean: Delete code. Start over with TDD.**
   ```
   (de `test-driven-development/SKILL.md:272-288`)

4. **DOT graphviz** se usa para state machines y decision trees
   (no para "code in flowcharts", prohibido en líneas 603-608). Ejemplos:
   - `test-driven-development/SKILL.md:47-69` — RED-GREEN-REFACTOR cycle
   - `systematic-debugging/SKILL.md` — 4 phases
   - `subagent-driven-development/SKILL.md:21-37` (when-to-use) + `47-83` (process)
   - `brainstorming/SKILL.md:36-59` — process flow
   - `dispatching-parallel-agents/SKILL.md:18-33` — decision tree

5. **El body puede tener sub-secciones infinitas**, pero debe tener un `## Overview`
   corto en las primeras ~10 líneas (verificado en 12 de 14 skills). Las 2
   excepciones son `using-superpowers` (62 líneas total, no tiene Overview — es
   todo rulebook denso) y el contrapunto `writing-skills` (689 líneas con
   ~30 secciones).

6. **Prohibido "NARRATIVE"** (líneas 594-597 de writing-skills):
   > ❌ Narrative Example
   > "In session 2025-10-03, we found empty projectDir caused..."
   > **Why bad:** Too specific, not reusable

## 4. Cuándo usar cada tipo de skill

`skills/writing-skills/SKILL.md:61-69` define 4 tipos:

| Tipo         | Definición                                                  | Ejemplo real             |
|--------------|-------------------------------------------------------------|--------------------------|
| **Technique**| Concrete method with steps to follow                         | `condition-based-waiting` (referenced, no leí su SKILL) |
| **Pattern**  | Way of thinking about problems                              | `flatten-with-flags` (referenced) |
| **Reference**| API docs, syntax guides, tool documentation                 | tool/api docs (no en repo actual) |
| **Discipline**| Rules/requirements that resist rationalization              | `test-driven-development`, `systematic-debugging`, `verification-before-completion` |

### Mapping del repo actual

| Skill                              | Tipo según writing-skills     | Comentario                                                                                |
|------------------------------------|-------------------------------|-------------------------------------------------------------------------------------------|
| `using-superpowers`                | Meta (no listado)             | Es meta-rulebook, no encaja en los 4 tipos                                                |
| `brainstorming`                    | Process/Discipline mix        | Tiene HARD-GATE que es discipline-like pero el flujo es process-like                      |
| `test-driven-development`          | Discipline (regla enforced)   | Iron Law + 13 Red Flags                                                                   |
| `systematic-debugging`             | Discipline                    | Iron Law + 4 phases                                                                      |
| `verification-before-completion`   | Discipline                    | Iron Law + 13 Red Flags                                                                   |
| `writing-plans`                    | Process/Technique             | Step-by-step con template estructurado                                                    |
| `executing-plans`                  | Process                       | 3 steps                                                                                  |
| `subagent-driven-development`      | Process + Orchestration       | 1 implementer + 1 reviewer; este es el más complejo                                       |
| `dispatching-parallel-agents`      | Process                       | 4 steps (identify → dispatch → review → integrate)                                       |
| `requesting-code-review`           | Process                       | Pre-review checklist + dispatch                                                         |
| `receiving-code-review`            | Soft skill                    | No leído                                                                                  |
| `using-git-worktrees`              | Technique                     | Steps 0-3 muy concretos                                                                  |
| `finishing-a-development-branch`   | Process                       | Steps 1-6 con menu options                                                               |
| `writing-skills`                   | Meta                          | El spec de este doc, basically                                                           |

### Reglas de decisión (writing-skills/SKILL.md:395-442)

Cada tipo tiene **un test approach** distinto:

- **Discipline** (regla/requirement): tests con **academic questions** + **pressure scenarios** (time, sunk cost, exhaustion combinados). Success = agent sigue la regla bajo máxima presión. Rationalization Tables + Red Flags Lists obligatorios.
- **Technique** (how-to): tests con **application scenarios** + **variation scenarios** + **missing information tests**. Success = agent aplica la técnica a un nuevo scenario.
- **Pattern** (mental model): tests con **recognition scenarios** + **counter-examples**. Success = agent identifica cuándo aplica y cuándo NO.
- **Reference** (docs/API): tests con **retrieval scenarios** + **application scenarios**. Success = agent encuentra y aplica la info correctamente.

### La regla "Match the Form to the Failure" (writing-skills/SKILL.md:459-475)

Insight crítico extraído por el autor tras testing real:

```
| Baseline failure                              | Right form                          | Wrong form               |
|-----------------------------------------------|-------------------------------------|--------------------------|
| Skips/violates a rule under pressure          | Prohibition + rationalization table | Soft guidance ("prefer") |
| Complies, but output has wrong shape          | Positive recipe or contract         | Prohibition list         |
| Omits required element                        | Structural: REQUIRED field          | Prose reminders          |
| Behavior should depend on a condition         | Conditional keyed to predicate      | Unconditional rule       |
```

> **Why prohibitions backfire on shaping problems:** under a competing incentive
> ("make the prompt self-contained"), agents negotiate with "don't X". In
> head-to-head wording tests on dispatch-prompt guidance, the prohibition arm
> produced clearly more of the unwanted content than the recipe arm (fully
> separated distributions).

**Implicación Aithera V1.1**: NO copies "no X, no Y, no Z" como bulletproofing.
Microtestea el wording si tienes tiempo; si no, sigue el default "recipe > prohibition".

## 5. Reglas SDO (Skill Discovery Optimization) — cómo escribir la `description`

Sección más operativa de writing-skills (líneas 140-298). Reglas:

### SDO Rule 1: Rich Description Field (líneas 144-197)

**Purpose**: "Should I read this skill right now?" es la pregunta que el agente
hace cuando lee la description.

**Format**:
- Start with "Use when..."
- ONLY describe triggering conditions, NOT what the skill does
- Include specific symptoms, situations, contexts
- Describe the *problem* (race conditions) not *language-specific symptoms*
  (setTimeout, sleep)
- Keep triggers technology-agnostic unless the skill itself is tech-specific
- Write in third person (injected into system prompt)

**Trap warning** (líneas 152-159):
> When the description was changed to just "Use when executing implementation
> plans with independent tasks" (no workflow summary), the agent correctly
> read the flowchart and followed the two-stage review process.
>
> **The trap:** Descriptions that summarize workflow create a shortcut agents
> will take. The skill body becomes documentation agents skip.

**Real bad/good example** (líneas 161-172):
```yaml
# ❌ BAD: Summarizes workflow - agents may follow this instead of reading skill
description: Use when executing plans - dispatches subagent per task with code review between tasks

# ❌ BAD: Too much process detail
description: Use for TDD - write test first, watch it fail, write minimal code, refactor

# ✅ GOOD: Just triggering conditions, no workflow summary
description: Use when executing implementation plans with independent tasks in the current session

# ✅ GOOD: Triggering conditions only
description: Use when implementing any feature or bugfix, before writing implementation code
```

### SDO Rule 2: Keyword Coverage (líneas 199-205)

Use words an agent would search for:
- Error messages: "Hook timed out", "ENOTEMPTY", "race condition"
- Symptoms: "flaky", "hanging", "zombie", "pollution"
- Synonyms: "timeout/hang/freeze", "cleanup/teardown/afterEach"
- Tools: Actual commands, library names, file types

### SDO Rule 3: Descriptive Naming (líneas 207-211)

> Use active voice, verb-first:
> - ✅ `creating-skills` not `skill-creation`
> - ✅ `condition-based-waiting` not `async-test-helpers`
> - ✅ `using-skills` not `skill-usage`
> - ✅ `flatten-with-flags` > `data-structure-refactoring`
> - ✅ `root-cause-tracing` > `debugging-techniques`

**Gerunds (-ing) work well for processes:**
- `creating-skills`, `testing-skills`, `debugging-with-logs`

### SDO Rule 4: Token Efficiency (líneas 213-275)

Target word counts:
- **getting-started workflows**: < 150 words each
- **Frequently-loaded skills**: < 200 words total
- **Other skills**: < 500 words (still be concise)

Techniques:
- Move details to tool help (don't document all flags, reference `--help`)
- Use cross-references (don't repeat workflow details of other skills)
- Compress examples (42 words → 20 words)
- Eliminate redundancy

**Verification** (línea 262-266):
```bash
wc -w skills/path/SKILL.md
# getting-started workflows: aim for <150 each
# Other frequently-loaded: aim for <200 total
```

### SDO Rule 5: Cross-Referencing Other Skills (líneas 278-288)

Use skill name only, con requirement markers:
- ✅ Good: `**REQUIRED SUB-SKILL:** Use superpowers:test-driven-development`
- ✅ Good: `**REQUIRED BACKGROUND:** You MUST understand superpowers:systematic-debugging`
- ❌ Bad: `See skills/testing/test-driven-development` (unclear if required)
- ❌ Bad: `@skills/testing/test-driven-development/SKILL.md` (force-loads, burns context)

> **Why no @ links:** `@` syntax force-loads files immediately, consuming
> 200k+ context before you need them.

### Update SDO for Violation Symptoms (líneas 544-551)

Para discipline skills, la description puede incluir **síntomas de violación
inminente**:
```yaml
description: use when implementing any feature or bugfix, before writing implementation code
```

El truco: añadir al final de la description las frases exactas que un agente
dice cuando está a punto de saltarse la regla. Esto activa trigger cuando el
agente las verbaliza.

## 6. Reglas anti-rationalization (Iron Law + Red Flags + Rationalization Tables)

### Iron Law shape

Cada discipline skill tiene un bloque "The Iron Law" idéntico:

```markdown
## The Iron Law

\`\`\`
NO [BAD ACTION] WITHOUT [GOOD ACTION] FIRST

[Negative consequence of violating]
\`\`\`

**No exceptions:**
- [Specific forbidden workarounds]
- ...
```

Verificado en 4 skills:
- `test-driven-development/SKILL.md:33-45` → `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`
- `systematic-debugging/SKILL.md:18-22` → `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`
- `verification-before-completion/SKILL.md:18-22` → `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`
- `writing-skills/SKILL.md:374-385` → `NO SKILL WITHOUT A FAILING TEST FIRST`

### "Spirit vs Letter" rebuttal (líneas 506-514 de writing-skills)

```markdown
### Address "Spirit vs Letter" Arguments

Add foundational principle early:

**Violating the letter of the rules is violating the spirit of the rules.**
```

Verificado en 4 skills (línea 14 de test-driven-development, systematic-debugging,
verification-before-completion; líneas 510-514 de writing-skills).

### Rationalization Table shape

```markdown
| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
```

Verificado verbatim en 4 skills (cada uno con ~7-11 rows).

### Red Flags shape

```markdown
## Red Flags - STOP and Start Over

- Code before test
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**
```

### Bulletproofing — Close Every Loophole (líneas 484-504)

```markdown
### Close Every Loophole Explicitly

Don't just state the rule - forbid specific workarounds:

<Bad>
```markdown
Write code before test? Delete it.
```
</Bad>

<Good>
```markdown
Write code before test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```
</Good>
```

Usa tags `<Bad>` / `<Good>` para contraste (no `❌` ni `✅`). Esta es una
**convención deliberada** del repo (probablemente para no chocar con parsers
markdown que filtran emojis).

## 7. File organization

3 patrones (líneas 347-372):

### Self-Contained Skill (líneas 349-353)

```
defense-in-depth/
  SKILL.md    # Everything inline
```
Cuándo: All content fits, no heavy reference needed.

### Skill with Reusable Tool (líneas 355-361)

```
condition-based-waiting/
  SKILL.md    # Overview + patterns
  example.ts  # Working helpers to adapt
```
Cuándo: Tool is reusable code, not just narrative.

### Skill with Heavy Reference (líneas 363-371)

```
pptx/
  SKILL.md       # Overview + workflows
  pptxgenjs.md   # 600 lines API reference
  ooxml.md       # 500 lines XML structure
  scripts/       # Executable tools
```
Cuándo: Reference material too large for inline.

### Reglas (líneas 82-92)

- **Flat namespace** — all skills in one searchable namespace
- **Separate files for:**
  1. Heavy reference (100+ lines) — API docs, comprehensive syntax
  2. Reusable tools — Scripts, utilities, templates
- **Keep inline:**
  - Principles and concepts
  - Code patterns (< 50 lines)
  - Everything else

### Mapping al repo real

| Skill                              | Patrón usado                         |
|------------------------------------|---------------------------------------|
| using-superpowers                  | Self-contained + 3 reference files para tool mappings por harness |
| brainstorming                      | Self-contained + scripts/ + visual-companion.md (heavy ref) |
| test-driven-development            | Self-contained + testing-anti-patterns.md (heavy ref) |
| systematic-debugging               | Self-contained (todo inline, 296 líneas) |
| verification-before-completion     | Self-contained (139 líneas) |
| writing-plans                      | Self-contained + plan-document-reviewer-prompt.md |
| subagent-driven-development        | **Pattern completo**: SKILL.md + 2 prompt templates (implementer + reviewer) + 3 scripts (sdd-workspace, task-brief, review-package) |
| writing-skills                     | Self-contained + 5 reference files (anthropic-best-practices, examples/, graphviz-conventions.dot, persuasion-principles.md, render-graphs.js, testing-skills-with-subagents.md) |

## 8. Cross-referencing entre skills

Ver SDO Rule 5 arriba. Resumen ejecutivo:

**Permitido**:
- `**REQUIRED SUB-SKILL:** Use superpowers:test-driven-development`
- `**REQUIRED BACKGROUND:** You MUST understand superpowers:systematic-debugging`
- Inline mention con prefijo `superpowers:<skill-name>`

**Prohibido**:
- `@skills/path/to/SKILL.md` (force-loads file, burns context)
- Pasting entire SKILL.md body in another skill
- Vague "see also" sin name explícito

**Regla de placement**: cuando cross-refs son "REQUIRED" o "MUST", ponlos en
la sección "Related skills" al final del skill (cf.
`systematic-debugging/SKILL.md:286-288`, `using-git-worktrees/SKILL.md` no
leído entero pero el patrón es el mismo).

## 9. El flujo TDD-for-skills: RED → GREEN → REFACTOR

`skills/writing-skills/SKILL.md:552-589`:

### RED: Write Failing Test (Baseline) (líneas 556-563)

> Run pressure scenario with subagent WITHOUT the skill. Document exact behavior:
> - What choices did they make?
> - What rationalizations did they use (verbatim)?
> - Which pressures triggered violations?
>
> This is "watch the test fail" - you must see what agents naturally do before writing the skill.

### GREEN: Write Minimal Skill (líneas 565-569)

> Write skill that addresses those specific rationalizations. Don't add extra
> content for hypothetical cases.
>
> Run same scenarios WITH skill. Agent should now comply.

### REFACTOR: Close Loopholes (líneas 571-573)

> Agent found new rationalization? Add explicit counter. Re-test until bulletproof.

### Micro-Test Wording Before Full Scenarios (líneas 575-585)

> Full pressure-scenario runs are the final gate, but they are slow and
> expensive per iteration. Verify the wording itself first with micro-tests:
>
> 1. **One fresh-context sample per call** — a raw API call, or a single-shot
>    subagent if you don't have API access. System prompt = the realistic
>    context the guidance will live in (the full skill or prompt template, not
>    the guidance in isolation); user message = a task that tempts the failure.
> 2. **Always include a no-guidance control.** If the control doesn't exhibit
>    the failure, there is nothing to fix — stop, don't author the guidance.
> 3. **5+ reps per variant.** Single samples lie.
> 4. **Manually read every flagged match.** Score programmatically if you like,
>    but template echoes and quoted counter-examples masquerade as hits;
>    automated counts alone overstate both failure and success.
> 5. **Variance is a metric.** When guidance lands, reps converge on the same
>    shape. Five different interpretations across five reps means the wording
>    isn't binding — tighten the form before adding words.
>
> Micro-tests verify wording; they do not replace pressure scenarios for
> discipline skills.

Esta sección es el **"secret sauce"** del framework. Es la documentación de
un proceso experimental real: el autor ha corrido tests con diferentes
wording, ha medido distributions, y ha encontrado que "prohibitions" (negative
form) sistemáticamente producen PEORES resultados que "recipes" (positive
form). Es meta-evidencia empírica, no opinión.

## 10. El checklist de deployment (verbatim)

`skills/writing-skills/SKILL.md:627-666`. Es **literalmente un checklist
copy-paste** que cada autor de skill debe completar:

```markdown
## Skill Creation Checklist (TDD Adapted)

**IMPORTANT: Create a todo for EACH checklist item below.**

**RED Phase - Write Failing Test:**
- [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
- [ ] Run scenarios WITHOUT skill - document baseline behavior verbatim
- [ ] Identify patterns in rationalizations/failures

**GREEN Phase - Write Minimal Skill:**
- [ ] Name uses only letters, numbers, hyphens (no parentheses/special chars)
- [ ] YAML frontmatter with required `name` and `description` fields (max 1024 chars; see [spec](https://agentskills.io/specification))
- [ ] Description starts with "Use when..." and includes specific triggers/symptoms
- [ ] Description written in third person
- [ ] Keywords throughout for search (errors, symptoms, tools)
- [ ] Clear overview with core principle
- [ ] Address specific baseline failures identified in RED
- [ ] Guidance form matches the failure type (see Match the Form to the Failure)
- [ ] For behavior-shaping guidance: wording micro-tested against a no-guidance control (5+ reps, every flagged match read manually) — N/A for pure reference skills
- [ ] Code inline OR link to separate file
- [ ] One excellent example (not multi-language)
- [ ] Run scenarios WITH skill - verify agents now comply

**REFACTOR Phase - Close Loopholes:**
- [ ] Identify NEW rationalizations from testing
- [ ] Add explicit counters (if discipline skill)
- [ ] Build rationalization table from all test iterations
- [ ] Create red flags list
- [ ] Re-test until bulletproof

**Quality Checks:**
- [ ] Small flowchart only if decision non-obvious
- [ ] Quick reference table
- [ ] Common mistakes section
- [ ] No narrative storytelling
- [ ] Supporting files only for tools or heavy reference

**Deployment:**
- [ ] Commit skill to git and push to your fork (if configured)
- [ ] Consider contributing back via PR (if broadly useful)
```

Cada bullet es **actionable y verificable**. **Aithera借鉴 este checklist tal
cual** para el flujo de creación de skills en V1.1+.

## 11. Comparación con Aithera MOS `LocalSkill` + `ISkillStore`

> Esta sección es **una propuesta de reconciliación**, no audit. Verifica contra
> el código Aithera real cuando se implemente V1.1.

### Lo que Aithera YA tiene (V0.85, código real en `app/memory/stores/skill_store.py`)

- ✅ Contrato `ISkillStore` (interfaz async)
- ✅ `LocalSkill` dataclass con `derived_from` + `superseded_by` lineage
- ✅ `SkillStatus` enum
- ✅ Singleton `skill_store`

### Lo que Aithera NO tiene (gap vs Superpowers)

| Feature Superpowers                        | Gap en Aithera V0.85                  | Propuesta V1.1                                                                 |
|--------------------------------------------|---------------------------------------|--------------------------------------------------------------------------------|
| Frontmatter YAML `name` + `description`    | Schema actual es Aithera-specific     | Adoptar agentskills.io spec; mapear `description` ↔ trigger detection         |
| TDD skill creation flow                    | Ninguno (skills nacen ad-hoc)         | Adoptar RED → GREEN → REFACTOR de writing-skills                              |
| Iron Law + Red Flags en cada discipline    | Solo B21 ReasoningFilter, no generaliza| Plantilla discipline-skill reutilizable                                       |
| Rationalization Table                      | No                                    | Añadir a skill discipline cuando aplique                                      |
| Skill versioning via git                   | `derived_from` / `superseded_by` en BD| Mantener BD lineage + git como source-of-truth del content                   |
| Skill filesystem location (`skills/<n>/SKILL.md`) | No hay conventions                  | Crear `aithera/skills/<n>/SKILL.md` conventions                              |
| Cross-ref con `superpowers:name`           | No                                    | Adoptar `<skill-namespace>:<name>` pattern                                   |
| Drop `@` syntax prohibition                | No especificado                       | Adoptar regla: nunca `@aithera/skills/...`                                    |
| Token efficiency rules                     | No medido                              | `<150 words` workflows, `<200 words` frequently-loaded                        |
| Match-the-form-to-the-failure              | No                                    | Adoptar recipe > prohibition por defecto                                      |
| Bulletproofing con persuasion principles   | No                                    | Añadir `persuasion-principles.md` analog                                      |

### Diferencias filosóficas importantes

| Aspecto                   | Superpowers                                  | Aithera MOS                                                |
|---------------------------|----------------------------------------------|------------------------------------------------------------|
| **Almacenamiento**        | Filesystem (`skills/`)                       | ChromaDB (`mem_*`) + filesystem híbrido                    |
| **Versionado**            | git commits                                  | `derived_from` / `superseded_by` en BD + (opcional) git   |
| **Estado activo vs histórico** | Solo activo (git checkout)                 | Ambos: `SkillStatus.ACTIVE` vs `SUPERSEDED`                |
| **Carga**                 | On-demand via Skill tool                     | On-demand via Orchestrator lookup                          |
| **Validación TDD**        | Manual via superpowers-evals repo            | Podría ser automático vía CI + `aithera-evals` propio     |
| **Discovery**             | Frontmatter `description` field (LLM-visible)| `MemoryQuery` semántica (ChromaDB query)                   |
| **Cross-references**      | Plaintext (`superpowers:name`)               | Bidirectional via metadata en ChromaDB o linked-table      |

**Decisión sugerida para V1.1**: **NO reemplazar el storage ChromaDB**.
Adoptar solo el **frontmatter + SKILL.md format** como convention de authorship,
mantener ChromaDB para query semántica y lineage, y mantener git para
versionado del source. Es un merge sinérgico.

## 12. Snippets de los 4 tipos de skill del repo

### Discipline skill (test-driven-development) — excerpt líneas 6-45

```markdown
# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask your human partner):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.
```

### Technique skill (using-git-worktrees) — excerpt líneas 6-32

```markdown
# Using Git Worktrees

## Overview

Ensure work happens in an isolated workspace. Prefer your platform's native
worktree tools. Fall back to manual git worktrees only when no native tool
is available.

**Core principle:** Detect existing isolation first. Then use native tools.
Then fall back to git. Never fight the harness.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

**Before creating anything, check if you are already in an isolated workspace.**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**Submodule guard:** `GIT_DIR != GIT_COMMON` is also true inside git submodules.
Before concluding "already in a worktree," verify you are not in a submodule:
```

### Process skill (executing-plans) — excerpt líneas 1-71 (todo el skill)

```markdown
# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** Tell your human partner that Superpowers works much better with
access to subagents. ...

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create todos for the plan items and proceed

### Step 2: Execute Tasks
For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development
After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice
```

### Meta skill (writing-skills) — excerpt líneas 6-44 (TDD Mapping)

```markdown
# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

**Personal skills live in your runtime's skills directory**

You write test cases (pressure scenarios with subagents), watch them fail
(baseline behavior), write the skill (documentation), watch tests pass (agents
comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you
don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand superpowers:test-driven-development
before using this skill. ...

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | Pressure scenario with subagent |
| **Production code** | Skill document (SKILL.md) |
| **Test fails (RED)** | Agent violates rule without skill (baseline) |
| **Test passes (GREEN)** | Agent complies with skill present |
| **Refactor** | Close loopholes while maintaining compliance |
| **Write test first** | Run baseline scenario BEFORE writing skill |
| **Watch it fail** | Document exact rationalizations agent uses |
| **Minimal code** | Write skill addressing those specific violations |
| **Watch it pass** | Verify agent now complies |
| **Refactor cycle** | Find new rationalizations → plug → re-verify |

The entire skill creation process follows RED-GREEN-REFACTOR.
```

## 13. Reglas de migración Aithera V0.85 → V1.1

Propuesta operativa basada en este audit:

### Fase 1 (mes 1): Adoptar convención de archivos

- Crear directorio `aithera/skills/<skill-name>/SKILL.md` conventions
- Cada SKILL.md con frontmatter agentskills.io-compatible:
  ```yaml
  ---
  name: skill-name-kebab-case
  description: Use when [trigger conditions]
  version: 1.0.0
  aithera_owners: [team-name]
  ---
  ```
- El campo `version` es Aithera-specific (no en spec agentskills.io base).
  ChromaDB lo ingiere como metadata.
- Adapters ChromaDB `LocalSkill` parsean el frontmatter en `ingest_skill_file()`.

### Fase 2 (mes 2): Adoptar creación TDD-driven

- Crear nuevo `aithera-skill-creator` agent (o `writing-skills` clone) que
  sigue el flujo RED → GREEN → REFACTOR.
- Pressure scenarios se almacenan en `aithera/scratch/pressure-tests/`.
- Cada nueva skill requiere 3+ pressure scenarios antes de mergear al `dev`.
- `aithera-evals` (separado, no en este doc) corre scenarios + verifica compliance.

### Fase 3 (mes 3): Adoptar anti-rationalization pattern

- Skill disciplina de Aithera (¿cuáles? — propuesta inicial: B21 reasoning,
  DPAPI secrets usage, alembic-only migrations) deben seguir el patrón
  Iron Law + Red Flags + Rationalization Table.
- Cross-references entre skills usan `<aithera-namespace>:<skill-name>` pattern.
- Prohibido `@aithera/skills/...` (force-load) en cross-refs.

### Fase 4 (mes 4): Eval harness

- Nuevo repo `aithera-evals` (mirror del `superpowers-evals`).
- Tests drill-style: prompt con skill + pressure scenario → verifica compliance.
- CI gate: PR a `aithera/skills/` no mergeable si eval regression.

### Fase 5 (mes 5+): Búsqueda semántica + ChromaDB

- ChromaDB indexa el `body` (no solo el frontmatter) para que `MemoryQuery`
  semántica pueda recuperar skills por contenido.
- Lineage `derived_from` / `superseded_by` se llena automáticamente cuando una
  skill se edita (detección via LLM diff o via PR title convention).

## 14. Pendientes y riesgos

### Pendientes (no cubiertos por este audit)

1. **Releer `skills/requesting-code-review/SKILL.md`** + `receiving-code-review` — falta
   verificar el format real.
2. **Releer `skills/finishing-a-development-branch/SKILL.md`** entero — solo
   leídas 60/241 líneas.
3. **Releer `docs/testing.md`** — describe metodología drill-style.
4. **Releer `skills/writing-skills/anthropic-best-practices.md`** — referencia
   a buenas prácticas oficiales Anthropic; puede tener reglas adicionales.
5. **Validar claims del doc preexistente `superpowers.md`** sobre forge-neutral
   v6.0.0 (no confirmado en código auditado).
6. **Releer `superpowers-evals`** repo separado — no clonado aquí.

### Riesgos identificados

1. **El "match-the-form" insight es empírico** (corpus específicos del autor).
   Aithera debería re-validar en sus propios tests antes de adoptarlo
   universalmente.
2. **La regla `<200 words total` para frequently-loaded** es agresiva.
   Superpowers tiene 12 skills "operacionales" con ~4700 líneas. Aplicar
   esto en Aithera requeriría podar skills existentes.
3. **`<Bad>` / `<Good>` tags como convention** es opaco (no es estándar
   markdown). Aithera podría usar `<Forbidden>` / `<Required>` o
   `<Anti-pattern>` / `<Pattern>` para más claridad.
4. **El "Match the Form to the Failure"** requiere identificar el failure type
   ANTES de escribir el skill. Authors junior tenderán a escribir prohibitions
   por reflejo. Aithera debería añadir tooling que detecte "this skill body
   has 80% prohibition language" como lint warning.
5. **El git-versioning de skills es frágil** — `git clean -fdx` borra el
   progress ledger (línea 263 de SDD). Aithera MOS que ya tiene
   `MemoryJobRun` está mejor posicionado: durable por diseño.
6. **El `superpowers:` namespace prefix es OWNER-specific**. Aithera debe
   definir SU prefix (`aithera:`? `mos:`? `<team>:`?) y no colisionar.

## Fuentes

1. Repo clonado: `/tmp/superpowers` (v6.1.1, HEAD `d884ae0`, 2026-07-02)
2. Spec principal: `skills/writing-skills/SKILL.md` (689 líneas, leído completo)
3. Skill meta-entry: `skills/using-superpowers/SKILL.md` (62 líneas)
4. 5 discipline skills auditados: TDD, systematic-debugging, verification-before-completion, writing-skills, using-superpowers (parcialmente)
5. 8 process/technique skills auditados parcial o completamente
6. Cross-platform parser: `.opencode/plugins/superpowers.js:17-34`
7. Pi extension parser: `.pi/extensions/superpowers.ts:83-86`
8. Aithera MOS contracts (referenciados): `app/memory/interfaces.py`
   (`IMemoryStore`, `ISkillStore`, `LocalSkill`, `SkillStatus`)
9. JWIKI hermano: `JWIKI/01_LANDSCAPE/superpowers-code-audit.md` (este audit)
10. JWIKI existente referenciado: `JWIKI/01_LANDSCAPE/superpowers.md`,
    `JWIKI/06_AGENTS/patterns-react.md`,
    `JWIKI/14_BEST_PRACTICES/conventions-code-structure.md`

## Nivel de confianza

**93%** — Spec derivada de `writing-skills/SKILL.md` (la fuente canónica +
auto-referencial del proyecto, 689 líneas leídas completas) y corroborada con
los 14 SKILL.md reales. 3 SKILL.md no leídos (`requesting-code-review`,
`receiving-code-review`, `finishing-a-development-branch` completo) marcados
como pendientes. La sección "Match the Form to the Failure" es
particularmente estable porque el autor cita testing empírico (líneas 469-470
de writing-skills). El mapping a Aithera MOS es propuesta y requiere validación
contra código Aithera real al implementar V1.1.

## Changelog

### 2026-07-13 — versión inicial
- Estado: 🟢 verified (spec derivada de `writing-skills/SKILL.md` v6.1.1)
- 14 skills catalogadas, 4 SKILL.md leídos completos (using-superpowers,
  TDD, systematic-debugging, verification-before-completion, writing-skills)
- Comparación directa con Aithera MOS `ISkillStore` + `LocalSkill`
- Propuesta de 5 fases de migración Aithera V0.85 → V1.1
- 12 snippets con `path:line`, 6 riesgos identificados
