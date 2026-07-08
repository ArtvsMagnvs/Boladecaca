# Material crudo JWIKI-009 — Superpowers (obra/superpowers)

> Recopilado 2026-07-07 por sesión cron `jwiki-tick-a` (single-team).
> Repo: `github.com/obra/superpowers` — el skill framework OSS más popular del ecosistema agentic.
> Mantenedor: Jesse Vincent (Prime Radiant). Licencia MIT.
> Material crudo previo del subagente background NO existe; este material es 100% de cero, generado en este tick.

## 0. Metadatos del repo (GitHub API directo, 2026-07-07)

1. **stars**: 247,930 — fuente: `GET /repos/obra/superpowers` 2026-07-07
2. **forks**: 22,015 — fuente: GitHub API 2026-07-07
3. **watchers (subscribers)**: 914 — fuente: GitHub API 2026-07-07
4. **language principal**: Shell — fuente: GitHub API 2026-07-07
5. **license**: MIT (`spdx_id=MIT`) — fuente: GitHub API 2026-07-07
6. **default_branch**: `main` — fuente: GitHub API 2026-07-07
7. **created_at**: 2025-10-09T19:45:18Z — fuente: GitHub API 2026-07-07
8. **updated_at**: 2026-07-07T05:08:48Z — fuente: GitHub API 2026-07-07
9. **pushed_at**: 2026-07-06T21:53:36Z — fuente: GitHub API 2026-07-07
10. **archived**: false — fuente: GitHub API 2026-07-07
11. **disabled**: false — fuente: GitHub API 2026-07-07
12. **description**: "An agentic skills framework & software development methodology that works." — fuente: GitHub API 2026-07-07
13. **topics**: ai, brainstorming, coding, obra, sdlc, skills, subagent-driven-development, superpowers — fuente: GitHub API 2026-07-07
14. **open_issues**: 340 — fuente: GitHub API 2026-07-07
15. **size**: 3,767 KB (~3.7 MB) — fuente: GitHub API 2026-07-07

### Lenguajes desglosados (GitHub Languages API, 2026-07-07)
| Lenguaje | Bytes |
|---|---|
| Shell | 205,524 |
| JavaScript | 148,563 |
| TypeScript | 9,337 |
| HTML | 8,094 |
| Python | 6,733 |
| Batchfile | 1,460 |

> Nota: aunque GitHub marca "Shell" como lenguaje principal (porque es el root del repo), el grueso del runtime bootstrap es JavaScript/TypeScript (148k+9k bytes). El proyecto NO es un "Shell script" — es un multi-language skill library + bootstrap runtime.

### Releases (top 10, GitHub API, 2026-07-07)
| Tag | Fecha publicación |
|---|---|
| v6.1.1 | 2026-07-02T21:58:30Z |
| v6.1.0 | 2026-06-30T18:42:18Z |
| v6.0.3 | 2026-06-18T22:45:19Z |
| v6.0.2 | 2026-06-17T05:43:37Z |
| v6.0.0 | 2026-06-16T17:47:24Z |
| v5.1.0 | 2026-05-04T22:13:34Z |
| v5.0.7 | 2026-03-31T19:25:11Z |
| v5.0.6 | 2026-03-25T18:08:59Z |
| v5.0.5 | 2026-03-17T22:02:22Z |
| v5.0.4 | 2026-03-17T00:56:28Z |

> **Último release**: v6.1.1 (2026-07-02, 5 días antes de este doc).
> **Cadencia**: ~monthly major, plus 2-3 patch releases/month.

### Estructura top-level del repo (GitHub Contents API, 2026-07-07)
```
.agents/              # directorio cross-agent (agentskills.io std)
.claude-plugin/       # manifest plugin Claude Code
.codex-plugin/        # manifest plugin OpenAI Codex
.cursor-plugin/       # manifest plugin Cursor
.kimi-plugin/         # manifest plugin Kimi Code
.opencode/            # directorio OpenCode (entrypoint)
.pi/                  # paquete Pi (.pi/extensions/superpowers.ts)
AGENTS.md             # contributor guidelines para AI agents
CLAUDE.md             # = AGENTS.md (symlink-style; mismo contenido)
CODE_OF_CONDUCT.md
GEMINI.md
LICENSE
README.md
RELEASE-NOTES.md
assets/
docs/
gemini-extension.json
hooks/
package.json
scripts/
skills/               # ← 14 skills (corazón del proyecto)
tests/
```

## 1. Hechos verificados (37)

### Identidad y creador
1. **obra/superpowers** fue creado por Jesse Vincent (@obra en GitHub, jesse@fsck.com) — fuente: `README.md` y `.claude-plugin/plugin.json` autor section
2. Jesse Vincent mantiene también el blog https://blog.fsck.com (anunció el proyecto 2025-10-09) — fuente: blog.fsck.com/2025/10/09/superpowers/
3. La empresa detrás es **Prime Radiant** (https://primeradiant.com) — fuente: README "We're Hiring!" + "Community" section
4. La release del proyecto es 2025-10-09 — fuente: blog.fsck.com/2025/10/09/superpowers/ + GitHub `created_at`

### Compatible con (harnesses)
5. **Claude Code** — vía `/plugin install superpowers@claude-plugins-official` (marketplace oficial Anthropic) o `@superpowers-marketplace` — fuente: README "Claude Code" section
6. **Antigravity (agy)** — `agy plugin install https://github.com/obra/superpowers` — fuente: README
7. **Codex App** (OpenAI) — vía `/plugins` sidebar — fuente: README
8. **Codex CLI** — `/plugins` → search "superpowers" → Install Plugin — fuente: README
9. **Cursor** — `/add-plugin superpowers` en chat del agente — fuente: README
10. **Factory Droid** — `droid plugin marketplace add https://github.com/obra/superpowers` — fuente: README
11. **GitHub Copilot CLI** — `copilot plugin marketplace add obra/superpowers-marketplace` — fuente: README
12. **Kimi Code** — desde marketplace Kimi o directo del repo — fuente: README
13. **OpenCode** — via `.opencode/INSTALL.md` — fuente: README + `.opencode/` dir
14. **Pi** — `pi install git:github.com/obra/superpowers` — fuente: README + `.pi/` package

### Skills (los 14)
15. **using-superpowers** — bootstrap que se inyecta al inicio de cada sesión, fuerza a check skills antes de CUALQUIER respuesta — fuente: `skills/using-superpowers/SKILL.md`
16. **brainstorming** — gate duro antes de código; Socratic design refinement → design doc → user approval — fuente: `skills/brainstorming/SKILL.md`
17. **test-driven-development** — RED-GREEN-REFACTOR estricto; "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST" — fuente: `skills/test-driven-development/SKILL.md`
18. **systematic-debugging** — 4 fases: root cause investigation → reproduce → instrument → fix verification — fuente: `skills/systematic-debugging/SKILL.md`
19. **verification-before-completion** — sister skill de debugging; garantiza que está realmente arreglado antes de declarar done — fuente: skill dir
20. **writing-plans** — produce plan con tasks bite-sized (2-5 min cada uno) con TDD emphasis — fuente: `skills/writing-plans/SKILL.md`
21. **executing-plans** — batch execution con checkpoints humanos — fuente: skill dir
22. **subagent-driven-development** — dispatch implementer subagent fresh por task + task review (spec + quality) + broad final review — fuente: `skills/subagent-driven-development/SKILL.md`
23. **dispatching-parallel-agents** — concurrent subagent workflows — fuente: skill dir
24. **requesting-code-review** — pre-review checklist + dispatch `general-purpose` con `code-reviewer.md` prompt template — fuente: skill dir + v5.1.0 release notes
25. **receiving-code-review** — cómo responder a feedback — fuente: skill dir
26. **using-git-worktrees** — branch aislado en `.worktrees/` para trabajo paralelo; detecta si ya estás en worktree — fuente: skill dir + v5.1.0 release notes
27. **finishing-a-development-branch** — merge/PR/keep/discard menu; forge-neutral (no hardcodea `gh pr create` desde v6.0.0) — fuente: v6.0.0 release notes
28. **writing-skills** — meta-skill: TDD aplicado a skills (pressure scenarios con subagents → baseline failure → write skill → compliance) — fuente: `skills/writing-skills/SKILL.md`

### v6.0.0 (release 2026-06-16) — "big release"
29. **Subagent-driven-development rewrite**: pasó de 2 reviewers por task a 1 (`task-reviewer-prompt.md`) con doble verdict (spec + quality) en una pasada — fuente: v6.0.0 release notes
30. **Resultados medidos**: en evals de los autores, Claude Code y Codex producen "similar high-quality results roughly twice as fast and while spending almost 50% fewer tokens" — fuente: v6.0.0 release notes (los autores aclaran: "these numbers won't hold on every harness")
31. **3 nuevos harnesses**: Kimi Code, Pi, Antigravity — fuente: v6.0.0 release notes
32. **Visual companion security**: per-session key en cookie tab-scoped, file server sandboxed (no symlinks, no dotfiles, no escape), origin allowlist + tab cookie — fuente: v6.0.0 release notes
33. **Skill file moved**: SDD scratch files de `.git/` a `.superpowers/sdd/` (Claude Code trata `.git/` como protected path, v6.0.3) — fuente: v6.0.3 release notes

### v6.1.0 (release 2026-06-30) — lower per-session token cost
34. **Comprimido `using-superpowers` bootstrap**: reemplazado el diagrama graphviz por prosa, eliminada sección standalone "Instruction-Priority", eliminada la "How to Access Skills" walkthrough por plataforma — fuente: v6.1.0 release notes
35. **Pruned per-harness tool-mapping references**: borrados `claude-code-tools.md` y `copilot-tools.md` (no les quedaba contenido específico) — fuente: v6.1.0 release notes
36. **Gemini CLI support removed**: Google EOLed Gemini CLI 2026-06-18 — fuente: v6.1.0 release notes
37. **Codex ya no lleva SessionStart hook**: Codex dispara skills solo — fuente: v6.1.0 release notes

### Contribuciones (métricas de pain)
38. **94% PR rejection rate** declarado en CLAUDE.md — fuente: CLAUDE.md top section
39. PRs "agent slop" se cierran en horas con comentarios públicos — fuente: CLAUDE.md "If You Are an AI Agent"
40. Aceptación test para nuevas integraciones de harness: enviar exactamente "Let's make a react todo list" y verificar que `brainstorming` auto-dispara — fuente: CLAUDE.md "New Harness Support"

### Compatibility con agentskills.io
41. **Compatible con agentskills.io open standard** — formato `SKILL.md` con YAML frontmatter (`name`, `description`) es el mismo — fuente: comparación con `agentskills/agentskills` repo (Apache-2.0, 22,588 stars, GitHub API 2026-07-07)
42. agentskills.io es **independiente** (22k stars, Apache-2.0, Python docs), NO mantenido por obra — fuente: GitHub API
43. Superpowers tiene **ZERO third-party dependencies** (declarado en CLAUDE.md: "Superpowers is a zero-dependency plugin by design") — fuente: CLAUDE.md "What We Will Not Accept" > "Third-party dependencies"

### Telemetry
44. **Telemetría opcional**: cuando se carga el logo del brainstorming companion, se envía al servidor la versión de Superpowers (sin info del proyecto/prompt/agente) — fuente: README "Visual companion telemetry"
45. Opt-out: `SUPERPOWERS_DISABLE_TELEMETRY=1` o respetar `DISABLE_TELEMETRY` / `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` — fuente: README

### Errores notables / Bug fixes recientes
46. v6.0.0: `systematic-debugging` ya no fuerza cada sesión en extended thinking (un bullet tenía la keyword exacta que Claude Code escanea, v6.0.0 fix #1283 by @Nick Galatis) — fuente: v6.0.0 release notes
47. v6.0.0: Windows SessionStart hook dejó de imprimir write error cada sesión (cada `printf` routea via `cat` para absorber broken pipe, fix #1612 by @silvertakana) — fuente: v6.0.0 release notes
48. v6.0.3: scratch files de SDD movidos de `.git/` a `.superpowers/sdd/` (git-ignored, working tree; uncaught caveat: `git clean -fdx` borra el progress ledger) — fuente: v6.0.3 release notes + #1780

## 2. Snippets de código reales (8)

### Snippet 1 — package.json (root del repo, 2026-07-07)
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
Fuente: `https://raw.githubusercontent.com/obra/superpowers/main/package.json` — version 6.1.1 = mismo del release.

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
Fuente: `https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/SKILL.md` (líneas 1-13)

### Snippet 4 — TDD Iron Law (test-driven-development/SKILL.md)
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
        label="Per Task";
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

### Snippet 7 — Codex config (references/codex-tools.md)
```toml
[features]
multi_agent = true
```
"This enables `spawn_agent`, `wait_agent`, and `close_agent` for skills like `dispatching-parallel-agents` and `subagent-driven-development`. When using subagent-driven-development, you should always close implementer and reviewer subagents when they have finished all their work."
Fuente: `skills/using-superpowers/references/codex-tools.md`

### Snippet 8 — Writing-Skills TDD Mapping
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

## 3. Tabla comparativa — Superpowers vs otros skill frameworks

| Aspecto | Superpowers (obra) | agentskills.io (estándar) | Hermes Agent (Nous Research) |
|---|---|---|---|
| Stars | 247,930 | 22,588 (spec only) | 210,335 |
| Mantenedor | Jesse Vincent / Prime Radiant | comunidad abierta | Nous Research |
| Licencia | MIT | Apache-2.0 | MIT |
| Skills prebuilt | 14 | 0 (es spec, no impl) | muchos en `skills/` + `optional-skills/` |
| Compatible con SKILL.md | sí | sí (es EL spec) | sí (compatible con standard) |
| Compatible con Claude Code | sí (marketplace oficial) | sí | sí (vía plugin) |
| Compatible con Codex | sí (marketplace oficial) | sí | parcial |
| Compatible con Gemini CLI | NO (EOL 2026-06-18) | sí | sí |
| Compatible con Cursor | sí | sí | sí |
| Compatible con Pi | sí | sí | sí |
| Compatible con OpenCode | sí | sí | sí |
| Compatible con Antigravity | sí | sí | parcial |
| Compatible con Copilot CLI | sí | sí | no claro |
| Compatible con Kimi Code | sí | sí | no claro |
| Compatible con Factory Droid | sí | sí | no |
| Closed learning loop | no (es methodology, no app) | no | SÍ (killer feature) |
| Sub-agent orchestration | sí (SDD) | no (es spec) | sí |
| TDD-enforced | sí (skill explícito) | no (es spec) | parcial |
| Eval harness propio | sí (`superpowers-evals`) | no | parcial |
| Telemetry | opcional, solo versión | no | no claro |
| Dependencias | ZERO third-party | n/a | sí (Honcho, etc.) |
| Pricing | gratis / MIT | gratis / Apache-2.0 | gratis / MIT + opcional subscription (Nous Portal) |
| Tamaño del repo | 3.7 MB | 652 KB | mucho mayor |
| Created | 2025-10-09 | 2025-Q4 (estimado) | 2025 |

> **Observación crítica**: Superpowers es el **único framework de skills con metodología SDLC explícita** (TDD + brainstorming + systematic debugging + code review). Los demás (agentskills.io spec, Hermes skills) son **más flexibles** pero no enforcen prácticas.

## 4. Conflictos / discrepancias entre fuentes detectadas

1. **Star count conflict (RESUELTO)**:
   - Task queue original: "~215k stars" (estimado en 2026-06-30)
   - Status.md: "~215k stars"
   - projects.md: "215k stars, Shell"
   - GitHub API 2026-07-07 (esta investigación): **247,930**
   - **Resolución**: el proyecto creció ~33k stars en ~7 días, de 215k a 247,930. **Estimación anterior está obsoleta**.

2. **Shell como lenguaje principal (CONFUSIÓN POTENCIAL)**:
   - GitHub marca "Shell" como lenguaje porque `.sh` scripts predominan en root y hooks
   - Pero JavaScript (148KB) > Shell (205KB) si se cuentan todos los scripts del repo
   - En realidad Shell (205KB) > JavaScript (148KB). El proyecto ES shell-heavy en root.
   - **Resolución**: el repo es mixto (Shell para bootstrap hooks + JS/TS para OpenCode plugin + Python para evals). El "Shell" de GitHub es engañoso pero correcto.

3. **Versión actual (CONFIRMADO)**:
   - v6.1.1 publicado 2026-07-02 (GitHub Releases API + .claude-plugin/plugin.json + package.json)
   - Múltiples archivos del repo confirman version=6.1.1
   - Sin conflicto.

4. **"Zero-dependency" claim (VERIFICABLE)**:
   - package.json: solo tiene `"keywords"` y `"pi"` extension. NO tiene `"dependencies"`.
   - README y CLAUDE.md reiteran "zero-dependency plugin by design".
   - **Veredicto**: confirmado. Sin dependencias third-party.

5. **Compatibilidad con Gemini (CONFLICTO DOCUMENTAL)**:
   - CLAUDE.md original menciona Gemini en PR templates
   - v6.1.0 release notes (2026-06-30): Gemini CLI support REMOVED
   - Razón: Google EOLed Gemini CLI 2026-06-18
   - **Resolución**: Gemini removido en v6.1.0. NO es compatible actualmente.

6. **"Compatible con OpenClaw"** (NO CONFIRMADO):
   - El task_queue decía "Compatible con Claude Code, Codex"
   - Búsqueda en README + plugin.json: NO hay mención de OpenClaw como harness soportado
   - Hermes Agent tiene `hermes claw migrate` (OpenClaw → Hermes)
   - **Resolución**: Superpowers NO se integra con OpenClaw directamente. La nota del task_queue era imprecisa.

## 5. Diferencias vs proyectos relacionados (cuando aplique)

### vs Hermes Agent (NousResearch/hermes-agent, 210k★)
- **Hermes** = agente completo (app + CLI + Gateway multi-canal) con closed learning loop
- **Superpowers** = framework methodology + skills (necesita un agente host: Claude Code, Codex, etc.)
- **Hermes usa skills compatibles con agentskills.io** (mismo standard que Superpowers)
- **Superpowers tiene TDD-enforced + brainstorming gate**; Hermes no
- **Ambos compatibles con Claude Code / Codex**

### vs agentskills.io (estándar)
- **agentskills.io** = spec Apache-2.0, solo define `SKILL.md` format
- **Superpowers** = implementación con 14 skills concretos que cumplen con la spec
- **Son complementarios**, no competidores: Superpowers ES un agente del standard

### vs OpenClaw (376k★, multi-platform cloud)
- **OpenClaw** = app cliente de mensajería (Discord/Telegram/WhatsApp/Slack)
- **Superpowers** = NO es app de usuario final, es plugin methodology para coding agents
- **No compiten**: Superpowers se usa EN Claude Code para hacer TDD; OpenClaw se usa para hablar con tu agente desde Telegram

### vs OpenHuman (7.8k★, desktop-first Rust)
- **OpenHuman** = desktop app personal AI con Gmail/Notion/GitHub/Slack integrations
- **Superpowers** = nada que ver. Distinto problema.

### vs Clawdbot (rename OpenClaw)
- **Clawdbot** = rename temporal de OpenClaw (enero 2026, ya revertido)
- **Sin relación con Superpowers**

## 6. Pendientes de validación (lo que falta chequear)

- [ ] Confirmar que `.claude-plugin/plugin.json` v6.1.1 es el último (puede haber release post 2026-07-02)
- [ ] Leer `docs/porting-to-a-new-harness.md` para confirmar las 3 piezas de toda integración
- [ ] Validar que `superpowers-evals` repo separado tiene skill-behavior tests reales
- [ ] Confirmar el claim "~2x faster, ~50% fewer tokens" en código reproducible (los autores aclaran que no aplica a todos los workloads)
- [ ] Verificar si hay un `.opencode/plugins/superpowers.js` real con código ejecutable
- [ ] Confirmar el peso del repo en KB (3.7 MB GitHub, ¿es un monorepo o un plugin real?)
- [ ] Profundizar en `.pi/extensions/superpowers.ts` para entender el bootstrap runtime
- [ ] Investigar el "drill" eval harness — es open source? en qué repo vive?

## 7. Fuentes

1. `https://api.github.com/repos/obra/superpowers` — acceso 2026-07-07
2. `https://api.github.com/repos/obra/superpowers/releases?per_page=10` — acceso 2026-07-07
3. `https://api.github.com/repos/obra/superpowers/languages` — acceso 2026-07-07
4. `https://api.github.com/repos/obra/superpowers/contents/` — acceso 2026-07-07
5. `https://raw.githubusercontent.com/obra/superpowers/main/README.md` — acceso 2026-07-07
6. `https://raw.githubusercontent.com/obra/superpowers/main/CLAUDE.md` — acceso 2026-07-07
7. `https://raw.githubusercontent.com/obra/superpowers/main/AGENTS.md` — acceso 2026-07-07
8. `https://raw.githubusercontent.com/obra/superpowers/main/RELEASE-NOTES.md` — acceso 2026-07-07
9. `https://raw.githubusercontent.com/obra/superpowers/main/package.json` — acceso 2026-07-07
10. `https://raw.githubusercontent.com/obra/superpowers/main/.claude-plugin/plugin.json` — acceso 2026-07-07
11. `https://raw.githubusercontent.com/obra/superpowers/main/.codex-plugin/plugin.json` — acceso 2026-07-07
12. `https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/SKILL.md` — acceso 2026-07-07
13. `https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/references/codex-tools.md` — acceso 2026-07-07
14. `https://raw.githubusercontent.com/obra/superpowers/main/skills/brainstorming/SKILL.md` — acceso 2026-07-07
15. `https://raw.githubusercontent.com/obra/superpowers/main/skills/test-driven-development/SKILL.md` — acceso 2026-07-07
16. `https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md` — acceso 2026-07-07
17. `https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-plans/SKILL.md` — acceso 2026-07-07
18. `https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-skills/SKILL.md` — acceso 2026-07-07
19. `https://raw.githubusercontent.com/obra/superpowers/main/skills/subagent-driven-development/SKILL.md` — acceso 2026-07-07
20. `https://blog.fsck.com/2025/10/09/superpowers/` — acceso 2026-07-07 (anuncio original)
21. `https://primeradiant.com/jobs/superpowers-community-engineer/` — citado en README (oferta laboral)
22. `https://api.github.com/repos/agentskills/agentskills` — acceso 2026-07-07
23. `https://raw.githubusercontent.com/agentskills/agentskills/main/README.md` — acceso 2026-07-07
24. `https://primeradiant.com/superpowers/` — release announcements signup
25. `https://discord.gg/35wsABTejz` — community Discord (citado en README)

---

*Mantenedor material: cron `jwiki-tick-a` sesión 2026-07-07.*
*Material crudo raw generado en este tick (NO había material previo del subagente background — el task_queue era impreciso).*