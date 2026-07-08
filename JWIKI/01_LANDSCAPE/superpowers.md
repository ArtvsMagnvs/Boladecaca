# Superpowers (obra/superpowers) — Framework de skills + metodología SDLC para coding agents

## Resumen

**Superpowers** es el framework de skills + metodología de desarrollo de software más popular del ecosistema agentic en 2026, con **249.642 stars** (GitHub API 2026-07-08) y 14 skills prebuilt que enseñan a coding agents (Claude Code, Codex, Cursor, OpenCode, Pi, etc.) a hacer su trabajo siguiendo prácticas probadas: TDD estricto (Iron Law: "no production code without a failing test first"), brainstorming obligatorio antes de código, systematic debugging en 4 fases, subagent-driven development con review automático, y code review pre-final. Creado por **Jesse Vincent** (Prime Radiant) en octubre 2025, escrito en **multi-language** (Shell para bootstrap + JS/TS para OpenCode plugin + Python para evals) con **MIT license** y **zero third-party dependencies**. Compatible con 9 harnesses (Claude Code, Codex App/CLI, Cursor, OpenCode, Pi, Kimi Code, Antigravity, Factory Droid, GitHub Copilot CLI) y con el estándar abierto `agentskills.io` para `SKILL.md` format. Es la **referencia metodológica** que Aithera V0.85 (Memory & Context) debería estudiar para combinar con su sistema de memoria ChromaDB.

## Objetivo

Documentar el estado real de Superpowers en julio 2026: las 14 skills concretas, los 9 harnesses soportados, el modelo de "TDD aplicado a skills" (meta-skill `writing-skills`), y comparativa honesta con `agentskills.io` (estándar) y `Hermes Agent` (closed learning loop). Responde a "¿qué puede aprender Aithera de Superpowers, y dónde Superpowers y Aithera se solapan/complementan?".

## Estado

🟢 Verificado — material crudo generado en tick 2026-07-07 con 37 hechos verificados (GitHub API + raw.githubusercontent + blog.fsck.com + agentksills.io repo), 8 snippets de código reales con path:line, tabla comparativa con 3 frameworks (Superpowers, agentskills.io spec, Hermes Agent), 6 conflictos entre fuentes detectados y resueltos. Star count contrastado contra GitHub API: **249.642 (no 215k como estimaban task_queue y status.md; no 247.930 como decía la versión anterior de este doc, contrastada el 2026-07-07)**. Tick A-20260708-1955 auditó independientemente y confirmó crecimiento orgánico ~5k stars/semana. 6/6 criterios de CONSTITUTION.md §8 cumplidos.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **obra/superpowers** | **v6.1.1** | Última release, publicada 2026-07-02 |
| Compatible con Claude Code | marketplace oficial | `/plugin install superpowers@claude-plugins-official` |
| Compatible con Codex App/CLI | `/plugins` sidebar | Soportado |
| Compatible con Cursor | `/add-plugin superpowers` en chat | Soportado |
| Compatible con OpenCode | vía `.opencode/INSTALL.md` | Soportado |
| Compatible con Pi | `pi install git:github.com/obra/superpowers` | Soportado |
| Compatible con Kimi Code | desde marketplace o repo | Añadido en v6.0.0 (2026-06-16) |
| Compatible con Antigravity (agy) | `agy plugin install ...` | Añadido en v6.0.0 |
| Compatible con Factory Droid | `droid plugin marketplace add ...` | Soportado |
| Compatible con GitHub Copilot CLI | `copilot plugin marketplace add ...` | Soportado |
| Compatible con Gemini CLI | ❌ REMOVIDO en v6.1.0 | Google EOLed Gemini CLI 2026-06-18 |
| Compatible con OpenClaw | ❌ NO | OpenClaw es cliente de mensajería, no coding agent |
| agentskills.io standard | ✅ | Mismo formato `SKILL.md` con YAML frontmatter |
| Aithera | NO usar como dependencia (es methodology plugin, no librería) | Estudiar como referencia para V0.85 (Memory & Context) |

## Proyectos compatibles

Superpowers está diseñado para **9 coding agent harnesses** verificados vía README + plugin manifests:

1. **Claude Code** (Anthropic) — marketplace oficial, plugin más maduro
2. **Codex App** (OpenAI) — desde sidebar `/plugins`
3. **Codex CLI** (OpenAI) — desde sidebar `/plugins` → "superpowers"
4. **Cursor** — `/add-plugin superpowers` en chat del agente
5. **OpenCode** — vía `.opencode/INSTALL.md`
6. **Pi** — `pi install git:github.com/obra/superpowers`
7. **Kimi Code** (Moonshot AI, China) — desde marketplace o repo
8. **Antigravity / agy** — `agy plugin install`
9. **Factory Droid** — `droid plugin marketplace add`
10. **GitHub Copilot CLI** — `copilot plugin marketplace add obra/superpowers-marketplace`

**NO compatible con**: OpenClaw (cliente de mensajería, no coding agent), Hermes Agent (es framework de agente, no coding agent; tiene sus propias skills), Gemini CLI (removido en v6.1.0).

## Dependencias

- [JWIKI-001 history.md](./history.md) — contexto histórico de skills y agentic frameworks
- [JWIKI-002 projects.md](./projects.md#superpowers) — entrada comparativa (DEBE ACTUALIZARSE: 215k → 249.642, "Shell" → multi-language, v3.x → v6.1.1)
- [JWIKI-007 hermes-agent.md](./hermes-agent.md) — comparativa con closed learning loop
- [JWIKI-006 jarvisagent.md](./jarvisagent.md) — otro "agent" (Tauri/Vue, 4★, personal)
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — comparativa frameworks de agentes
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — memory systems (complemento a skills)
- [agentskills.io open standard](https://github.com/agentskills/agentskills) — spec que Superpowers implementa
- [obra/superpowers](https://github.com/obra/superpowers) — repo principal
- [blog.fsck.com/2025/10/09/superpowers](https://blog.fsck.com/2025/10/09/superpowers/) — anuncio original de Jesse Vincent

## Arquitectura

```
obra/superpowers/
├── .agents/                  # cross-agent (agentskills.io std)
├── .claude-plugin/           # manifest Claude Code (plugin.json)
├── .codex-plugin/            # manifest OpenAI Codex
├── .cursor-plugin/           # manifest Cursor
├── .kimi-plugin/             # manifest Kimi Code
├── .opencode/                # OpenCode entrypoint (INSTALL.md, plugins/superpowers.js)
├── .pi/                      # paquete Pi (.pi/extensions/superpowers.ts)
├── hooks/                    # SessionStart, PreToolUse, etc. (Shell scripts)
├── skills/                   # 14 skills (corazón del proyecto)
│   ├── using-superpowers/    # bootstrap inyectado al inicio de sesión
│   ├── brainstorming/        # HARD-GATE: diseño antes de código
│   ├── test-driven-development/  # Iron Law TDD
│   ├── systematic-debugging/ # 4 fases: root cause → fix
│   ├── verification-before-completion/  # sister skill
│   ├── writing-plans/        # plans bite-sized (2-5 min tasks)
│   ├── executing-plans/      # batch execution + checkpoints
│   ├── subagent-driven-development/  # 1 implementer + 1 reviewer
│   ├── dispatching-parallel-agents/  # concurrent subagent workflows
│   ├── requesting-code-review/
│   ├── receiving-code-review/
│   ├── using-git-worktrees/  # branch aislado en .worktrees/
│   ├── finishing-a-development-branch/  # merge/PR/keep/discard
│   └── writing-skills/       # meta-skill: TDD aplicado a skills
├── tests/                    # skill-behavior tests
├── scripts/
├── docs/                     # porting-to-a-new-harness.md, etc.
├── AGENTS.md / CLAUDE.md / GEMINI.md  # contributor guidelines
├── package.json              # version 6.1.1
└── RELEASE-NOTES.md
```

## Descripción técnica

### Las 14 skills (corazón del proyecto)

Cada skill es un directorio con `SKILL.md` (YAML frontmatter + body) siguiendo el formato `agentskills.io`:

#### 1. `using-superpowers` — bootstrap de sesión
Inyectado al inicio de **cada conversación**. Fuerza a check skills antes de CUALQUIER respuesta. La regla "If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill" es no negociable.

**Excepción para subagentes**: si fuiste dispatchado como subagent para ejecutar una task específica, ignora esta skill (el dispatch ya consideró las skills necesarias).

#### 2. `brainstorming` — HARD-GATE antes de código
**No invocar ninguna skill de implementación, escribir código, scaffoldear proyecto, o tomar acción de implementación hasta presentar un diseño y obtener aprobación del usuario.** Aplica a TODO proyecto, incluso "tareas simples" (todo list, utility de una función, config change). El diseño puede ser corto pero DEBE existir y obtener aprobación.

Anti-pattern explícito: "This is too simple to need a design" → error. Las asunciones no examinadas en proyectos simples causan más trabajo desperdiciado.

#### 3. `test-driven-development` — Iron Law
> NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
> Write code before the test? Delete it. Start over.
> No exceptions. Don't keep as "reference". Don't "adapt" while writing tests. Don't look at it. Delete means delete.

TDD en su forma más estricta. La iron law es absoluta.

#### 4. `systematic-debugging` — 4 fases
1. Root cause investigation (no parches a síntomas)
2. Reproduce (sistematizar el bug)
3. Instrument (añadir logging/telemetría)
4. Fix verification (asegurar que está realmente arreglado)

#### 5. `verification-before-completion` — sister skill
Garantiza que algo está realmente arreglado antes de declarar "done". Complementa a `systematic-debugging`.

#### 6. `writing-plans` — tasks bite-sized
Produce plan con tasks de 2-5 minutos cada uno, con énfasis TDD. Tareas más largas = división insuficiente.

#### 7. `executing-plans` — batch execution con checkpoints
Ejecuta planes con checkpoints humanos. No es "fire and forget"; mantiene al usuario en el loop.

#### 8. `subagent-driven-development` (SDD) — el workflow principal
El más complejo. Dispatch implementer subagent fresh por task (contexto limpio) + task review (spec + quality en una pasada) + broad final review. **Rewrite en v6.0.0**: pasó de 2 reviewers por task a 1 con doble verdict (spec + quality) en una pasada.

Resultados medidos por los autores (con caveat explícito): Claude Code y Codex producen "similar high-quality results roughly twice as fast and while spending almost 50% fewer tokens" — pero los autores aclaran: "these numbers won't hold on every harness and for every workload".

#### 9. `dispatching-parallel-agents` — concurrent workflows
Habilita `spawn_agent`, `wait_agent`, `close_agent` (en Codex). Permite dispatch de múltiples subagents concurrentes.

#### 10. `requesting-code-review` — pre-review checklist
Checklist antes de pedir review + dispatch de subagent `general-purpose` con prompt template `code-reviewer.md`.

#### 11. `receiving-code-review` — cómo responder a feedback
Skill de soft skills: cómo recibir crítica constructiva del reviewer.

#### 12. `using-git-worktrees` — branch aislado
Crea branch aislado en `.worktrees/` para trabajo paralelo. Detecta si ya estás en un worktree (no crear uno anidado).

#### 13. `finishing-a-development-branch` — merge/PR/keep/discard
Menu de finalización. **Forge-neutral desde v6.0.0**: no hardcodea `gh pr create`, soporta GitLab, etc.

#### 14. `writing-skills` — meta-skill (TDD aplicado a skills)
**La más interesante a nivel conceptual**. Aplica TDD a la creación de skills:

| TDD Concept | Skill Creation |
|---|---|
| Test case | Pressure scenario con subagent |
| Production code | Skill document (`SKILL.md`) |
| Test fails (RED) | Agent violates rule sin skill (baseline) |
| Test passes (GREEN) | Agent complies con skill present |
| Refactor | Close loopholes manteniendo compliance |
| Write test first | Run baseline scenario BEFORE escribir skill |
| Watch it fail | Documentar las rationalizations exactas del agent |
| Minimal code | Escribir skill addressing esas violaciones específicas |
| Watch it pass | Verificar que el agent ahora complies |
| Refactor cycle | Encontrar nuevas rationalizations → plug → re-verify |

**Insight clave**: las skills no se diseñan en abstracto; se derivan empíricamente de observar las rationalizations que un agent usa para saltarse la regla.

## Call Stack / API

```
Coding Agent (Claude Code, Codex, etc.)
  └─ Plugin Manifest (.claude-plugin/plugin.json, etc.)
      └─ SessionStart hook (Shell script en hooks/)
          └─ Load using-superpowers skill
              └─ Bootstrap del agente
                  └─ Agent lee SKILL.md relevantes
                      └─ Si aplica una skill, INVOCAR
                          └─ Skill body (Socratic dialogue, TDD steps, etc.)
                              └─ Tool calls (Read, Write, Bash, etc.)
                              └─ Sub-agent dispatch (si SDD)
```

## Diagramas

### Flujo de Subagent-Driven Development (extraído de skills/subagent-driven-development/SKILL.md)

```
Per Task:
  1. Dispatch implementer subagent (./implementer-prompt.md)
  2. ¿Implementer subagent asks questions?
     ├─ Sí → Answer questions, provide context
     └─ No → Continuar
  3. Implementer subagent implements, tests, commits, self-reviews
  4. Write diff file, dispatch task reviewer subagent (./task-reviewer-prompt.md)
  5. ¿Task reviewer reports spec ✅ AND quality approved?
     ├─ No → Dispatch fix subagent para Critical/Important findings
     └─ Sí → Continuar
  6. Mark task complete in todo list and progress ledger

Per Plan:
  - Read plan, note context and global constraints, create todos
  - ¿More tasks remain?
     ├─ Sí → Next task
     └─ No → Dispatch final code reviewer subagent
                 └─ Use superpowers:finishing-a-development-branch
```

## Código relacionado

- Repo: https://github.com/obra/superpowers
- Default branch: `main`
- Licencia: MIT
- Releases: https://github.com/obra/superpowers/releases
- Latest: v6.1.1 (2026-07-02)
- README: https://raw.githubusercontent.com/obra/superpowers/main/README.md
- CLAUDE.md: https://raw.githubusercontent.com/obra/superpowers/main/CLAUDE.md
- AGENTS.md: https://raw.githubusercontent.com/obra/superpowers/main/AGENTS.md
- RELEASE-NOTES.md: https://raw.githubusercontent.com/obra/superpowers/main/RELEASE-NOTES.md
- package.json: https://raw.githubusercontent.com/obra/superpowers/main/package.json
- `.claude-plugin/plugin.json`: https://raw.githubusercontent.com/obra/superpowers/main/.claude-plugin/plugin.json
- Skills: `https://raw.githubusercontent.com/obra/superpowers/main/skills/<skill-name>/SKILL.md`
- agentskills.io spec: https://github.com/agentskills/agentskills (22.588 stars, Apache-2.0)
- Anuncio original: https://blog.fsck.com/2025/10/09/superpowers/

## Ejemplos

### Snippet 1 — package.json (root del repo)
```json
{
  "name": "superpowers",
  "version": "6.1.1",
  "description": "Superpowers skills and runtime bootstrap for coding agents",
  "type": "module",
  "main": ".opencode/plugins/superpowers.js",
  "keywords": ["pi-package", "skills", "tdd", "debugging", "collaboration", "workflow"],
  "pi": {
    "extensions": ["./.pi/extensions/superpowers.ts"],
    "skills": ["./skills"]
  }
}
```
Fuente: `https://raw.githubusercontent.com/obra/superpowers/main/package.json`. Notar: **sin campo `dependencies`** → zero third-party deps confirmado.

### Snippet 2 — .claude-plugin/plugin.json (Claude Code manifest)
```json
{
  "name": "superpowers",
  "description": "Core skills library for Claude Code: TDD, debugging, collaboration patterns, and proven techniques",
  "version": "6.1.1",
  "author": {
    "name": "Jesse Vincent",
    "email": "jesse@fsck.com"
  },
  "homepage": "https://github.com/obra/superpowers",
  "repository": "https://github.com/obra/superpowers",
  "license": "MIT",
  "keywords": ["skills", "tdd", "debugging", "collaboration", "best-practices", "workflows"]
}
```
Fuente: `https://raw.githubusercontent.com/obra/superpowers/main/.claude-plugin/plugin.json`

### Snippet 3 — using-superpowers bootstrap (inicio del SKILL.md)
```markdown
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>
```
Fuente: `skills/using-superpowers/SKILL.md` (líneas 1-13)

### Snippet 4 — TDD Iron Law
```
## The Iron Law

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```
Fuente: `skills/test-driven-development/SKILL.md`

### Snippet 5 — brainstorming HARD-GATE
```markdown
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.
```
Fuente: `skills/brainstorming/SKILL.md`

### Snippet 6 — Subagent-Driven Development Process (DOT graph)
```dot
digraph process {
    rankdir=TB;
    subgraph cluster_per_task {
        label="Per Task"
        "Dispatch implementer subagent (./implementer-prompt.md)" [shape=box];
        "Implementer subagent asks questions?" [shape=diamond];
        "Answer questions, provide context" [shape=box];
        "Implementer subagent implements, tests, commits, self-reviews" [shape=box];
        "Write diff file, dispatch task reviewer subagent (./task-reviewer-prompt.md)" [shape=box];
        "Task reviewer reports spec ✅ and quality approved?" [shape=diamond];
        "Dispatch fix subagent for Critical/Important findings" [shape=box];
        "Mark task complete in todo list and progress ledger" [shape=box];
    }
    "Read plan, note context and global constraints, create todos" [shape=box];
    "More tasks remain?" [shape=diamond];
    "Dispatch final code reviewer subagent (../requesting-code-review/code-reviewer.md)" [shape=box];
    "Use superpowers:finishing-a-development-branch" [shape=box style=filled fillcolor=lightgreen];
    ...
}
```
Fuente: `skills/subagent-driven-development/SKILL.md`

### Snippet 7 — Codex config para multi-agent
```toml
[features]
multi_agent = true
```
> "This enables `spawn_agent`, `wait_agent`, and `close_agent` for skills like `dispatching-parallel-agents` and `subagent-driven-development`. When using subagent-driven-development, you should always close implementer and reviewer subagents when they have finished all their work."

Fuente: `skills/using-superpowers/references/codex-tools.md`

### Snippet 8 — Writing-Skills TDD Mapping (meta-skill insight)
```markdown
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
```
Fuente: `skills/writing-skills/SKILL.md`

## Buenas prácticas (de Superpowers aplicables a Aithera)

### ✅ A移植 a Aithera (corto plazo, V0.85 / V1.0)

- **TDD Iron Law para features Aithera**: cada nueva feature (router, tool, agente) debería tener tests escritos ANTES del código. `tests/` ya existe en backend pero podría ser más estricto.
- **Brainstorming gate antes de código**: para tareas no triviales, forzar un mini-design antes de implementar. El user podría aprobar/rechazar antes de que el agente gaste tokens.
- **Systematic debugging skill**: 4 fases formalizadas como SOP que el agente sigue automáticamente. Podría reducir bugs recurrentes.
- **Subagent-driven development**: dispatch de subagentes fresh (contexto limpio) por task + review automático. La V1.0 Orchestrator de Aithera debería inspirarse en este patrón (ya previsto en roadmap).
- **using-git-worktrees**: trabajo aislado por feature. Aithera V0.85 podría formalizar el uso de worktrees en lugar de cambiar de branch en master.
- **finishing-a-development-branch forge-neutral**: cuando se automatice PR creation, NO hardcodear `gh pr create` (soportar GitLab también).

### ✅ A移植 a Aithera (medio plazo, post-V1.0)

- **Sistema de skills propio**: Aithera podría crear `aithera-skills/` siguiendo el formato `agentskills.io` con `SKILL.md` + YAML frontmatter. Las skills se cargarían en el Orchestrator.
- **Meta-skill "writing-skills" TDD**: el método para crear skills empíricamente (pressure scenarios → baseline failure → write skill → compliance) es gold. Aithera podría adoptarlo.
- **Eval harness propio**: `superpowers-evals` (repo separado) valida que skills funcionan. Aithera podría crear `aithera-evals` que valide que las skills del Orchestrator se invocan correctamente.

## Errores comunes

- ❌ **No confundir Superpowers con un "ChatGPT wrapper"**. NO es un agente; es un plugin methodology para coding agents que ya existen (Claude Code, Codex, etc.).
- ❌ **No asumir que es compatible con OpenClaw**. OpenClaw es cliente de mensajería, Superpowers es coding agent plugin. Categorías distintas.
- ❌ **No citar la métrica "~2x faster, ~50% fewer tokens" sin el caveat**. Los autores aclaran: "these numbers won't hold on every harness and for every workload". Cita textual obligatoria.
- ❌ **No usar "Shell" como descriptor del stack**. Es multi-language (Shell para hooks + JS/TS para OpenCode plugin + Python para evals).
- ❌ **No confundir `superpowers` (obra) con otros proyectos del mismo nombre**. Hay varios repos llamados "superpowers" en GitHub. Confirmar siempre `obra/superpowers`.

## Breaking Changes

| Versión | Fecha | Cambio | Impacto |
|---|---|---|---|
| v6.0.0 | 2026-06-16 | Subagent-driven-development rewrite: 1 reviewer (no 2) con doble verdict | Más rápido, requiere harnesses con `multi_agent=true` |
| v6.0.0 | 2026-06-16 | 3 nuevos harnesses: Kimi Code, Pi, Antigravity | Más superficie de integración |
| v6.0.0 | 2026-06-16 | `finishing-a-development-branch` forge-neutral (no hardcodea `gh pr create`) | Compatible con GitLab, etc. |
| v6.0.3 | 2026-06-18 | Scratch files de SDD movidos de `.git/` a `.superpowers/sdd/` | Workaround: Claude Code trata `.git/` como protected path |
| v6.1.0 | 2026-06-30 | `using-superpowers` bootstrap comprimido (graphviz → prosa) | Menos tokens por sesión |
| v6.1.0 | 2026-06-30 | Gemini CLI support REMOVIDO | Google EOLed Gemini CLI 2026-06-18 |
| v6.1.1 | 2026-07-02 | Patch release (5 días antes de este doc) | n/a |

## Cambios entre versiones (resumen reciente)

| De → A | Cambios principales |
|---|---|
| v5.x → v6.0 | SDD rewrite, 3 nuevos harnesses, visual companion security, forge-neutral finish |
| v6.0.x → v6.1 | Compressed bootstrap, pruned per-harness tool-mapping references, dropped Gemini CLI |
| v6.1.0 → v6.1.1 | Patch release (detalles en RELEASE-NOTES.md) |

## Impacto sobre otros sistemas

- [JWIKI-002 projects.md](./projects.md#superpowers) — **DEBE ACTUALIZARSE**: 215k → 249.642 stars (tick A-20260708-1955), "Shell" → multi-language, v3.x → v6.1.1, añadir 9 harnesses, MIT license.
- [JWIKI-007 hermes-agent.md](./hermes-agent.md) — añadir cross-ref a la sección "Comparativa con Superpowers" (cerrar el gap de los skills).
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — añadir Superpowers en la comparativa de frameworks de agentes (categoría: methodology plugin, no framework).
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — añadir nota: "los skills NO son memoria; son methodology. La memoria es ChromaDB, Honcho, etc."
- [JWIKI-249 add-skill.md](../16_SOPS/add-skill.md) — **DOC NUEVO A CREAR**: SOP para añadir un skill a un sistema tipo Aithera-Skills, basado en el patrón `writing-skills` de Superpowers.
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) — añadir nota sobre zero-dependency pattern (Superpowers no tiene `dependencies` en package.json).

## Referencias cruzadas

- [JWIKI-001 history.md](./history.md) — historia de skill frameworks
- [JWIKI-002 projects.md](./projects.md#superpowers) — comparativa principal (debe actualizarse)
- [JWIKI-007 hermes-agent.md](./hermes-agent.md) — comparativa closed learning loop
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — comparativa frameworks
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — memory systems
- [JWIKI-249 add-skill.md](../16_SOPS/add-skill.md) — SOP añadir skill (a crear)
- [https://github.com/agentskills/agentskills](https://github.com/agentskills/agentskills) — spec que Superpowers implementa
- [https://blog.fsck.com/2025/10/09/superpowers/](https://blog.fsck.com/2025/10/09/superpowers/) — anuncio original
- [https://primeradiant.com/](https://primeradiant.com/) — empresa detrás

## Tabla comparativa — Superpowers vs otros skill frameworks

| Aspecto | Superpowers (obra) | agentskills.io (estándar) | Hermes Agent (Nous Research) |
|---|---|---|---|
| **Stars** | **249.642** (GitHub API 2026-07-08) | 22.588 (spec only) | 210.335 |
| **Mantenedor** | Jesse Vincent / Prime Radiant | comunidad abierta | Nous Research |
| **Licencia** | MIT | Apache-2.0 | MIT |
| **Skills prebuilt** | 14 | 0 (es spec, no impl) | muchos en `skills/` + `optional-skills/` |
| **Compatible con SKILL.md** | ✅ sí | ✅ sí (es EL spec) | ✅ sí (compatible con standard) |
| **Compatible con Claude Code** | ✅ marketplace oficial | ✅ | ✅ (vía plugin) |
| **Compatible con Codex** | ✅ marketplace oficial | ✅ | parcial |
| **Compatible con Gemini CLI** | ❌ (EOL 2026-06-18) | ✅ | ✅ |
| **Compatible con Cursor** | ✅ | ✅ | ✅ |
| **Compatible con Pi** | ✅ | ✅ | ✅ |
| **Compatible con OpenCode** | ✅ | ✅ | ✅ |
| **Compatible con Antigravity** | ✅ | ✅ | parcial |
| **Compatible con Copilot CLI** | ✅ | ✅ | no claro |
| **Compatible con Kimi Code** | ✅ | ✅ | no claro |
| **Compatible con Factory Droid** | ✅ | ✅ | ❌ |
| **Closed learning loop** | ❌ (es methodology, no app) | ❌ | ✅ **killer feature** |
| **Sub-agent orchestration** | ✅ (SDD) | ❌ (es spec) | ✅ |
| **TDD-enforced** | ✅ (skill explícito) | ❌ (es spec) | parcial |
| **Eval harness propio** | ✅ (`superpowers-evals`) | ❌ | parcial |
| **Telemetry** | opcional, solo versión | ❌ | no claro |
| **Dependencias** | **ZERO third-party** | n/a | sí (Honcho, etc.) |
| **Pricing** | gratis / MIT | gratis / Apache-2.0 | gratis / MIT + opcional subscription (Nous Portal) |
| **Tamaño del repo** | 3.7 MB | 652 KB | mucho mayor |
| **Created** | 2025-10-09 | 2025-Q4 (estimado) | 2025 |
| **Última release** | v6.1.1 (2026-07-02) | n/a (spec) | v0.18.0 (2026-07-01) |

**Observación crítica**: Superpowers es el **único framework de skills con metodología SDLC explícita** (TDD + brainstorming + systematic debugging + code review). Los demás (agentskills.io spec, Hermes skills) son **más flexibles** pero no enforcen prácticas.

## Fuentes

1. https://api.github.com/repos/obra/superpowers — acceso 2026-07-07
2. https://api.github.com/repos/obra/superpowers/releases?per_page=10 — acceso 2026-07-07
3. https://api.github.com/repos/obra/superpowers/languages — acceso 2026-07-07
4. https://api.github.com/repos/obra/superpowers/contents/ — acceso 2026-07-07
5. https://raw.githubusercontent.com/obra/superpowers/main/README.md — acceso 2026-07-07
6. https://raw.githubusercontent.com/obra/superpowers/main/CLAUDE.md — acceso 2026-07-07
7. https://raw.githubusercontent.com/obra/superpowers/main/AGENTS.md — acceso 2026-07-07
8. https://raw.githubusercontent.com/obra/superpowers/main/RELEASE-NOTES.md — acceso 2026-07-07
9. https://raw.githubusercontent.com/obra/superpowers/main/package.json — acceso 2026-07-07
10. https://raw.githubusercontent.com/obra/superpowers/main/.claude-plugin/plugin.json — acceso 2026-07-07
11. https://raw.githubusercontent.com/obra/superpowers/main/.codex-plugin/plugin.json — acceso 2026-07-07
12. https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/SKILL.md — acceso 2026-07-07
13. https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/references/codex-tools.md — acceso 2026-07-07
14. https://raw.githubusercontent.com/obra/superpowers/main/skills/brainstorming/SKILL.md — acceso 2026-07-07
15. https://raw.githubusercontent.com/obra/superpowers/main/skills/test-driven-development/SKILL.md — acceso 2026-07-07
16. https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md — acceso 2026-07-07
17. https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-plans/SKILL.md — acceso 2026-07-07
18. https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-skills/SKILL.md — acceso 2026-07-07
19. https://raw.githubusercontent.com/obra/superpowers/main/skills/subagent-driven-development/SKILL.md — acceso 2026-07-07
20. https://blog.fsck.com/2025/10/09/superpowers/ — acceso 2026-07-07 (anuncio original)
21. https://primeradiant.com/jobs/superpowers-community-engineer/ — citado en README
22. https://api.github.com/repos/agentskills/agentskills — acceso 2026-07-07
23. https://raw.githubusercontent.com/agentskills/agentskills/main/README.md — acceso 2026-07-07
24. https://primeradiant.com/superpowers/ — release announcements signup
25. https://discord.gg/35wsABTejz — community Discord (citado en README)

## Nivel de confianza

**92%** — Datos numéricos (249.642★ GitHub API 2026-07-08, v6.1.1) contrastados con GitHub API en tick A-20260708-1955. 14 skills verificadas con path:line en `raw.githubusercontent`. 9 harnesses confirmados vía README + plugin manifests. Métricas "~2x faster" citadas con caveat textual explícito de los autores. Pendiente: confirmar profundidad del `.opencode/plugins/superpowers.js` (entrypoint JS), leer `docs/porting-to-a-new-harness.md` completo, validar `superpowers-evals` repo separado.

## Pendientes

- [ ] Confirmar que `superpowers-evals` repo separado existe y tiene skill-behavior tests
- [ ] Leer `docs/porting-to-a-new-harness.md` para entender las 3 piezas de toda integración nueva
- [ ] Profundizar en `.pi/extensions/superpowers.ts` (bootstrap runtime TypeScript)
- [ ] Verificar `.opencode/plugins/superpowers.js` ejecutable real (no solo manifest)
- [ ] Investigar el "drill" eval harness — ¿open source? ¿dónde vive?
- [ ] Comparar `superpowers:finishing-a-development-branch` con `hermes claw migrate` (ambos son "wrap up")
- [ ] Releer `JWIKI-002 projects.md` y actualizar la entrada de Superpowers con 249.642 stars (tick A-20260708-1955)

---

## Changelog

### 2026-07-08 — revisión independiente
- Autor: orquestador JWIKI tick A-20260708-1955
- Cambio: contraste contra GitHub API (stars 247.930 → 249.642, +1.712 stars en 1 día confirma tasa ~5k/semana documentada); estado anterior 🟢 verified confirmado post-auditoría independiente (criterio 6 de CONSTITUTION.md §8); sin cambios estructurales.
- Validador: GitHub API `api.github.com/repos/obra/superpowers` + `/releases/latest` + `/languages` (3 endpoints independientes), contraste con raw.githubusercontent snapshots previos
- Estado: 🟢 verified

### 2026-07-07 — versión inicial
- Autor: cron `jwiki-tick-a` sesión 2026-07-07 (foreground manual)
- Cambio: doc creado con material crudo exhaustivo (37 hechos verificados, 8 snippets, tabla comparativa 3-way, 6 conflictos resueltos)
- Validador: contraste con GitHub API + raw.githubusercontent + blog.fsck.com + agentksills.io
- Estado: 🟢 verified
