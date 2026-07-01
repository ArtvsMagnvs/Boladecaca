# Material crudo JWIKI-004 -- OpenHuman desktop-first Rust+TS

> **Path destino**: `01_LANDSCAPE/openhuman.md`
> **Investigador**: Mavis (aithera-wiki-investigador, turno A)
> **Fecha investigacion**: 2026-06-30 (Europe/Paris UTC+2)
> **Estado**: raw (para que `aithera-wiki-escriba` lo convierta en doc final)
> **Fuentes**: GitHub API oficial, web search (matrix MCP), Reddit, blogs tecnicos, redes del fundador.

---

## Tesis en una linea

OpenHuman es un **agente personal con cara**: desktop-first, Tauri+Rust, con sincronizacion automatica cada 20 min desde 100+ OAuth connectors, memoria local jerarquica en SQLite, vault Obsidian-compat y un **mascot** que habla (ElevenLabs TTS con lip-sync) y se une como participante real a Google Meet. Contrasta con OpenClaw y Hermes (CLI-first) y con ChatGPT/Claude Cowork (chat-scoped) -- su propuesta es "context in minutes, not weeks", inspirada por el workflow Obsidian-Wiki de Karpathy.

---

## Hechos verificados

### 1. Repositorio y organizacion (autoridad: GitHub API oficial)

1. **Repositorio (canonico)**: `github.com/tinyhumansai/openhuman`. Activo, NO archivado, NO deshabilitado. -- Fuente: `https://api.github.com/repos/tinyhumansai/openhuman` -- Fecha acceso: 2026-06-30
2. **Organizacion**: `tinyhumansai` (alias comercial "TinyHumans" o "Tiny Humans AI"). -- Fuente: README oficial + LinkedIn `https://www.linkedin.com/company/tinyhumansai` -- Fecha acceso: 2026-06-30
3. **Fundador**: Steven Enamakel (handle `@senamakel` en GitHub y X). Bio: "Chef Buildoooor at @tinyhumansai - When you're going to change the world, don't ask for permission." -- Fuente: `https://x.com/senamakel` -- Fecha acceso: 2026-06-30
4. **Perfil GitHub del fundador**: "engineer specializing in deep-tech, web3, AI. I've been a builder first and a founder second." -- Fuente: `https://github.com/senamakel` -- Fecha acceso: 2026-06-30
5. **Antecedente del fundador (AlphaSignal)**: "Steven Enamakel, the founder, tried to set up an open-source AI agent for his dad earlier this year. Three hours of API keys, YAML, and a..." (motivacion declarada del proyecto). -- Fuente: `https://alphasignalai.substack.com/p/how-openhuman-works-and-how-to-set` -- Fecha acceso: 2026-06-30
6. **Stars (oficial, GitHub API)**: **33,923** al 2026-06-30 11:50 UTC. -- Fuente: `https://api.github.com/repos/tinyhumansai/openhuman` (campo `stargazers_count`) -- Fecha acceso: 2026-06-30
7. **Forks**: 3,293. -- Fuente: GitHub API campo `forks_count` -- Fecha acceso: 2026-06-30
8. **Subscriptores (watchers reales, no stars)**: 177. -- Fuente: GitHub API campo `subscribers_count` -- Fecha acceso: 2026-06-30
9. **Open issues**: 204. -- Fuente: GitHub API campo `open_issues_count` -- Fecha acceso: 2026-06-30
10. **Tamano del repo**: 127,429 KB (~127 MB). -- Fuente: GitHub API campo `size` -- Fecha acceso: 2026-06-30
11. **Fecha de creacion del repo**: 2026-02-18. -- Fuente: GitHub API campo `created_at` -- Fecha acceso: 2026-06-30
12. **Ultimo push al repo**: 2026-06-30 11:47:29 UTC (es decir, **hoy**). -- Fuente: GitHub API campo `pushed_at` -- Fecha acceso: 2026-06-30

### 2. Licencia

13. **Licencia SPDX oficial**: **GPL-3.0** (NO MIT, NO "GNU" generico). -- Fuente: GitHub API `https://api.github.com/repos/tinyhumansai/openhuman` (campo `license.key = "gpl-3.0"`, `license.name = "GNU General Public License v3.0"`, `license.spdx_id = "GPL-3.0"`) -- Fecha acceso: 2026-06-30
14. **Implicacion**: copyleft fuerte. Cualquier fork/modificacion distribuida debe mantener el codigo abierto bajo GPL-3.0. Distinta de OpenClaw (MIT) y Hermes (MIT). -- Fuente: comparativa en README oficial `https://github.com/tinyhumansai/openhuman#openhuman-vs-other-agent-harnesses` -- Fecha acceso: 2026-06-30
15. **Confirmacion cruzada**: juejin article `https://juejin.cn/post/7641852892249030702` corrobora "GPL-3.0 con LICENSE en el repo; no es MIT". -- Fecha acceso: 2026-06-30

### 3. Stack tecnologico (autoridad: GitHub API languages + README)

16. **Lenguaje dominante**: **Rust -- 60,5% (32,6 MB)** del total del codigo fuente. -- Fuente: `https://api.github.com/repos/tinyhumansai/openhuman/languages` -- Fecha acceso: 2026-06-30
17. **Frontend**: **TypeScript -- 36,6% (19,8 MB)**. -- Misma fuente -- Fecha acceso: 2026-06-30
18. **Otros lenguajes**: JavaScript (1,6%), Shell (1,0%), CSS (0,1%), HTML, Swift, PowerShell, Python, Dockerfile, Ruby. -- Misma fuente -- Fecha acceso: 2026-06-30
19. **Shell de escritorio**: **Tauri 2.0** (oficial). -- Fuente: README oficial + Contributing ("pnpm 10.10.0, Rust 1.93.0, **Tauri/CEF** sources") -- Fecha acceso: 2026-06-30
20. **Frontend framework**: **React** + **TypeScript**. -- Fuente: README (referencias a `pnpm --filter openhuman-app dev:app` y a "React + TypeScript frontend" en blog CSDN) -- Fecha acceso: 2026-06-30
21. **Estructura de modulos Rust (~80 sub-modulos)** segun disection de CSDN: `openhuman-core` (binario en `src/main.rs`), `rpc/` (JSON-RPC dispatcher), `openhuman/` crate con sub-modulos `agent/`, `memory/`, etc. -- Fuente: `https://blog.csdn.net/luolaihua2018/article/details/161323420` -- Fecha acceso: 2026-06-30
22. **Persistencia local**: SQLite en maquina del usuario. -- Fuente: README oficial (`"hierarchical summary trees stored in SQLite on your machine"`) -- Fecha acceso: 2026-06-30
23. **Vault paralelo**: archivos `.md` compatibles con **Obsidian** (Karpathy-style wiki). -- Fuente: README oficial (`"The same chunks land as .md files in an Obsidian-compatible vault"`) -- Fecha acceso: 2026-06-30
24. **Integraciones OAuth**: capa **Composio** (gestionada por defecto; opcional con Composio directo). -- Fuente: README oficial (`"Managed integrations use OpenHuman''s Composio connector layer"`) -- Fecha acceso: 2026-06-30
25. **Servidor MCP**: soporta el ecosistema MCP (Smithery + registro oficial). -- Fuente: README oficial (`"browses the open Model Context Protocol ecosystem"`) -- Fecha acceso: 2026-06-30
26. **AI local opcional**: **Ollama** como backend para inferencia local. -- Fuente: README oficial (`"Use optional local AI via Ollama for supported on-device workloads"`) -- Fecha acceso: 2026-06-30
27. **WebView**: **CEF** (Chromium Embedded Framework) vendoreado como submodule. -- Fuente: README (`"vendored Tauri/CEF sources"`) -- Fecha acceso: 2026-06-30

### 4. Releases y versionado

28. **Ultima release estable (oficial)**: **v0.58.0** -- "OpenHuman v0.58.0", publicada **2026-06-26 18:40:08 UTC**. -- Fuente: `https://api.github.com/repos/tinyhumansai/openhuman/releases/latest` y `https://github.com/tinyhumansai/openhuman/releases/tag/v0.58.0` -- Fecha acceso: 2026-06-30
29. **Tamano de la release v0.58.0**: **124 PRs, 133 commits** desde v0.57.53. -- Fuente: release notes de v0.58.0 -- Fecha acceso: 2026-06-30
30. **Highlight principal de v0.58.0**: **Super Context** (deterministic `context_scout` agent en cada hilo nuevo, prepende contexto relevante sin tool call). -- Fuente: release notes v0.58.0 -- Fecha acceso: 2026-06-30
31. **Historial de versiones recientes (tags estables)**: v0.57.10 (2026-06-02), v0.57.11, v0.57.13, v0.57.18, v0.57.39, v0.57.40, v0.57.44, v0.57.52, v0.57.53, v0.58.0 (2026-06-26). -- Fuente: GitHub API `https://api.github.com/repos/tinyhumansai/openhuman/tags` -- Fecha acceso: 2026-06-30
32. **Tags staging** observados: `v0.57.1-staging`, `v0.57.2-staging`, `v0.57.34-staging`, `v0.57.42-staging`, `v0.57.46-staging`, `v0.57.56-staging`, `v0.58.1-staging` (inestable). -- Fuente: misma API tags -- Fecha acceso: 2026-06-30
33. **Estado de la rama**: **default branch = main**, activa con commits diarios. -- Fuente: GitHub API `default_branch` -- Fecha acceso: 2026-06-30

### 5. **CONFLICTOS RESUELTOS** (frente al task_queue.md)

34. **Conflicto v0.53.43 vs v0.54.7**: ambos numeros circulan en fuentes secundarias pero NO aparecen como tags oficiales en `api.github.com/repos/tinyhumansai/openhuman/tags`. **Veredicto**: el proyecto esta actualmente en **v0.58.0 (2026-06-26)**. Las versiones v0.53.43 y v0.54.7 eran snapshots de blogs (`knightli.com` cita v0.53.43 en mayo 2026, `CSDN` cita v0.54.7 ~junio 2026). El proyecto ha avanzado 5 minor + 4 patch desde entonces. **NO usar esos numeros**; usar v0.58.0 como referencia estable actual. -- Fuentes:
    - Negativo: NO en `https://api.github.com/repos/tinyhumansai/openhuman/tags` (no aparecen esos tags) -- 2026-06-30
    - Secundarias obsoletas: `https://www.knightli.com/2026/05/15/openhuman-open-source-personal-ai-agent/` (v0.53.43), `https://blog.csdn.net/luolaihua2018/article/details/161323420` (v0.54.7) -- 2026-06-30
    - Oficial: `https://github.com/tinyhumansai/openhuman/releases/latest` (v0.58.0) -- 2026-06-30
35. **Conflicto stars**: task_queue.md cita 7,8k; CSDN 6,5k; juejin 23k; alphasignalai 29k; LevelUp "29K-Star"; reddi text 8k+; txtmix 6,595; **GitHub API oficial 33,923** (timestamp 2026-06-30 11:50 UTC). **Usar como canon el dato de la API**. -- Fuente canonica: `https://api.github.com/repos/tinyhumansai/openhuman` -- Fecha acceso: 2026-06-30

### 6. Features diferenciadoras

36. **Tagline oficial (README)**: "OpenHuman is your **Personal AI super intelligence**: local memory, managed services where needed, simple and powerful." -- Fuente: README oficial -- Fecha acceso: 2026-06-30
37. **Mascot (cara de escritorio)**: avatar animado que habla, reacciona, **se une a Google Meet como participante real** (live meeting agent), lip-sync con TTS. -- Fuente: README oficial + `https://tinyhumans.gitbook.io/openhuman/features/mascot` -- Fecha acceso: 2026-06-30
38. **Memory Tree**: base de conocimiento local-first. Datos normalizados a **chunks de <=3k tokens**, scored, folded into jerarquias de summary trees en SQLite. -- Fuente: README oficial (`"canonicalized into 3k-token Markdown chunks, scored, and folded into hierarchical summary trees stored in SQLite on your machine"`) -- Fecha acceso: 2026-06-30
39. **Obsidian Wiki compat**: los mismos chunks se serializan como `.md` files en un vault Obsidian que el usuario puede abrir y editar. Inspirado por Karpathy''s obsidian-wiki workflow. -- Fuente: README oficial + link a `https://x.com/karpathy/status/2039805659525644595` -- Fecha acceso: 2026-06-30
40. **Auto-fetch cada 20 min**: cada conexion activa es recorrida, se traen datos frescos, se canonicalizan en memory tree. **El agente ya sabe manana lo que necesitas antes de pedirlo**. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
41. **SuperContext (nuevo en v0.58.0)**: en el primer turno de cada thread nuevo, un `context_scout` read-only prepende contexto relevante. Sin tool call, sin esperas. -- Fuente: release notes v0.58.0 -- Fecha acceso: 2026-06-30
42. **Goals & Todos**: lista humana `MEMORY_GOALS.md` para metas largo plazo; cada thread puede llevar un goal durable con budget de tokens; kanban task board por conversacion; task list personal. -- Fuente: README oficial + `https://tinyhumans.gitbook.io/openhuman/features/goals-and-todos` -- Fecha acceso: 2026-06-30
43. **Theme Studio**: 5 familias (Classic, Ocean, Sepia, Matrix, HAL 9000) en light/dark/auto; editor visual de color tokens con contrast warnings; export/import a JSON. -- Fuente: README oficial + `https://tinyhumans.gitbook.io/openhuman/features/theming` -- Fecha acceso: 2026-06-30
44. **TokenJuice (smart token compression)**: capa de compresion antes de mandar a LLM. HTML a Markdown, long URLs shortened, dedup + summarize via rule overlay. **Reduccion declarada: hasta 80%** de tokens. Preserva CJK y emoji grapheme-by-grapheme. -- Fuente: README oficial (`"Reducing cost & latency by up to 80%"`) + `https://tinyhumans.gitbook.io/openhuman/features/token-compression` -- Fecha acceso: 2026-06-30
45. **Batteries included**: web search, web-fetch scraper, coder toolset (filesystem, git, lint, test, grep), native voice (STT in, ElevenLabs TTS out, mascot lip-sync). -- Fuente: README oficial -- Fecha acceso: 2026-06-30
46. **Model routing gestionado**: backend OpenHuman elige LLM adecuado por workload (reasoning / fast / vision). Una sola subscripcion, todos los modelos. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
47. **Privacy**: data workflow queda **local**, encriptado local. -- Fuente: README oficial -- Fecha acceso: 2026-06-30

### 7. Integraciones OAuth (compilacion verificada)

48. **100+ conectores curados** via Composio. Explicitos en README: **Gmail, Notion, GitHub, Slack, Stripe, Calendar, Drive, Linear, Jira**. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
49. **5,000+ servidores MCP** navegables desde Smithery + registro MCP oficial. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
50. **90,000+ Skills** en catalogo instalable on demand. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
51. **Backend opcional `agentmemory`**: OpenHuman puede proxy a la herramienta `rohitg00/agentmemory` para usar el mismo durable store entre Claude Code, Cursor, Codex y OpenCode. -- Fuente: README oficial + `https://github.com/rohitg00/agentmemory` + `https://tinyhumans.gitbook.io/openhuman/features/obsidian-wiki/agentmemory-backend` -- Fecha acceso: 2026-06-30

### 8. Voz e interaccion humano-maquina

52. **STT in**: input por voz via stack nativo. -- Fuente: README oficial (`"native voice (STT in, ElevenLabs TTS out, mascot lip-sync, live Google Meet agent)"`) -- Fecha acceso: 2026-06-30
53. **TTS out via ElevenLabs** (externo, pagado). -- Fuente: README oficial + `https://tinyhumans.gitbook.io/openhuman/features/voice` -- Fecha acceso: 2026-06-30
54. **Mascot lip-sync en vivo**: el avatar sincroniza la boca con la salida TTS. -- Fuente: README oficial + `https://ai-bot.cn/openhuman/` -- Fecha acceso: 2026-06-30

### 9. Plataformas soportadas e instalacion

55. **SO soportados**: macOS, Linux (Debian/Ubuntu signed apt repo, Arch via AUR), Windows (.msi firmado). -- Fuente: README oficial -- Fecha acceso: 2026-06-30
56. **Native package paths (preferred)**: Homebrew tap `tinyhumansai/core`; apt repo firmado en `https://tinyhumansai.github.io/openhuman/apt/`; AUR `openhuman-bin`; .msi firmado. -- Fuente: README oficial (seccion Install/Recommended install) -- Fecha acceso: 2026-06-30
57. **Script install (warning - sin verificacion)**: `curl -fsSL https://raw.githubusercontent.com/tinyhumansai/openhuman/main/scripts/install.sh | bash` -- **SIN firma**, el repo lo marca explicitamente como no verificado. -- Fuente: README oficial -- Fecha acceso: 2026-06-30
58. **Issue #2463**: Wayland en Linux + Arch `sharun: Interpreter not found!` -- solucion documentada en issue, pero el `.deb` lo evita. -- Fuente: `https://github.com/tinyhumansai/openhuman/issues/2463` -- Fecha acceso: 2026-06-30
59. **Issue #2620**: sobre scripts no firmados, cerrado despues de promover native packages (pero sin `install.sh.asc` aun). -- Fuente: `https://github.com/tinyhumansai/openhuman/issues/2620` -- Fecha acceso: 2026-06-30

### 10. Contribuidores y contribucion

60. **Contribuidores distinguidos (v0.58.0)**: senamakel (32 PRs), Mega Mind (M3gA-Mind) (23), oxoxDev (22), Cyrus Gray (graycyrus) (20), sanil-23 (7), YellowSnnowmann (4), Subharup Nandi (1), Felix (2), Martian (2), Shabnam (2), obchain (3), ly-wang19 (1), plus github-actions[bot] y Steven Enamakel''s Droid (senamakel-droid, 3 PRs). -- Fuente: release notes v0.58.0 -- Fecha acceso: 2026-06-30
61. **Workflow contribucion**: fork/PR + AI agent opcional (`CONTRIBUTING-BEGINNERS.md` con prompt copy-paste para guiar al agente). Requiere Git, Node.js 24+, pnpm 10.10.0, Rust 1.93.0 (con rustfmt + clippy), CMake, Ninja, ripgrep, platform desktop build prerequisites. -- Fuente: README oficial (Contributing from source) -- Fecha acceso: 2026-06-30
62. **Rewards**: merch gratis + acceso especial a Discord para contributors. -- Fuente: README oficial -- Fecha acceso: 2026-06-30

### 11. Posicionamiento vs competencia (segun el propio OpenHuman)

63. **Tabla comparativa en README** (frente a Claude Cowork / OpenClaw / Hermes Agent):

| Dimension | Claude Cowork | OpenClaw | Hermes Agent | **OpenHuman** |
|---|---|---|---|---|
| Open-source | Proprietary | MIT | MIT | **GNU (GPL-3.0)** |
| Simple to start | Desktop + CLI | Terminal-first | Terminal-first | **Clean UI, minutos** |
| Cost | Sub + add-ons | BYO models | BYO models | **One sub + TokenJuice** |
| Memory | Chat-scoped | Plugin-reliant | Self-learning | **Memory Tree + Obsidian vault + opcional agentmemory** |
| Integraciones | Few | BYO | BYO | **100+ OAuth / 5k+ MCP / 90k+ Skills** |
| Auto-fetch | None | None | None | **20-min sync to memory** |
| API sprawl | Extra keys | BYOK | Multi-vendor | **One account** |
| Model routing | Single model | Manual | Manual | **Built-in** |
| Native tools | Code-only | Code-only | Code-only | **Code + search + scraper + voice** |

    -- Fuente: README oficial (seccion "OpenHuman vs Other Agent Harnesses") -- Fecha acceso: 2026-06-30

### 12. Traccion, senales de mercado y comunidad

64. **#1 en Product Hunt (badge presente en README)**. -- Fuente: `https://www.producthunt.com/products/openhuman` (badge embed image) -- Fecha acceso: 2026-06-30
65. **Trending GitHub #7** mencionado en TikTok (whitewhoadie). -- Fuente: `https://www.tiktok.com/@whitewhoadie/video/7638298657888013582` -- Fecha acceso: 2026-06-30
66. **r/openclaw thread** (Has anyone tried OpenHuman? #1 on PH, >8k GitHub stars in 7 days). -- Fuente: `https://www.reddit.com/r/openclaw/comments/1tfr1co/has_anyone_tried_openhuman_1_on_ph_8k_github/` -- Fecha acceso: 2026-06-30
67. **r/tinyhumansai subreddit activo** (creado Feb 26 2026). -- Fuente: `https://www.reddit.com/r/tinyhumansai/` -- Fecha acceso: 2026-06-30
68. **Trendshift trending badge** en README (23680). -- Fuente: `https://trendshift.io/repositories/23680` -- Fecha acceso: 2026-06-30
69. **Top 10 fastest growing AI repos this week** (Reddit r/artificial). -- Fuente: `https://www.reddit.com/r/artificial/comments/1tnjhts/top_10_fastest_growing_ai_repos_this_week/` -- Fecha acceso: 2026-06-30
70. **Founder tweet (29 mayo)**: "Soon... OpenHuman. 1mn Github stars. I''m going to go for it." (`@titused` quoting `@senamakel`). -- Fuente: `https://x.com/titused` -- Fecha acceso: 2026-06-30
71. **r/AISEOInsider debate**: "OpenHuman Github is getting attention because it makes AI agents feel easier for normal people to try." -- Fuente: `https://www.reddit.com/r/AISEOInsider/comments/1tpnwtc/openhuman_github_vs_hermes_agent_is_actually_wild/` -- Fecha acceso: 2026-06-30
72. **Post en r/toshicoin**: video showcase `https://www.youtube.com/watch?v=cQslR1zB6Zk`. -- Fuente: `https://www.reddit.com/r/toshicoin/comments/1tqqpj2/showcasing_openhuman_ai/` -- Fecha acceso: 2026-06-30

### 13. Snippets de codigo / issues relevantes (con path:line o URL exacta)

73. **PR #3947 en `tinyhumansai/openhuman`**: mejora memory flow. -- Fuente: release notes v0.58.0 linking `https://github.com/tinyhumansai/openhuman/pull/3947` -- Fecha acceso: 2026-06-30
74. **PR #3946**: `fix(tauri): identify foreign process on core port + consent-gated force-quit (#3331)`. -- Fuente: `https://github.com/tinyhumansai/openhuman/pull/3946` -- Fecha acceso: 2026-06-30
75. **PR #3932**: `fix(composio): pin toolkit_versions=latest in direct-mode tool listings`. -- Fuente: `https://github.com/tinyhumansai/openhuman/pull/3932` -- Fecha acceso: 2026-06-30
76. **Issue #1909** (clicky-style companion loop): "OpenHuman should reuse its own in-process Rust core, Tauri shell, and existing voice / screen-intelligence / provider-surface work." -- Fuente: `https://github.com/tinyhumansai/openhuman/issues/1909` -- Fecha acceso: 2026-06-30

### 14. Diferenciador (vs OpenClaw, OpenJarvis, Hermes)

77. **vs OpenClaw (TypeScript CLI-first)**: OpenHuman es desktop-first Tauri+Rust, con cara (mascot). OpenClaw es puro CLI/plugin. -- Inferencia basada en JWIKI-002 raw + JWIKI-003 (OpenClaw)
78. **vs OpenJarvis (Stanford local-first)**: OpenJarvis es local-first pero Python+Rust academic. OpenHuman es desktop commercial con mascot y managed services por defecto. -- Inferencia basada en JWIKI-002 raw
79. **vs Hermes Agent (Nous Research, self-learning)**: Hermes aprende de tu uso; OpenHuman arranca cargado via OAuth connectors. -- Inferencia basada en JWIKI-002 raw
80. **vs ChatGPT/Claude Cowork**: open source + local memory + 100+ connectors vs proprietary chat-scoped. -- Inferencia basada en README OpenHuman

### 15. Pendientes de validacion (no verificar hasta escalado a Auditor)

81. **Numero exacto de commits** no extraido. README open issues = 204 (GitHub API). Total commits history NO verificado a nivel numerico (solo inferencia por 124 PRs/133 commits en v0.58.0).
82. **Funding / financiacion del equipo tinyhumansai**: NO encontrado en fuentes consultadas. Marca `VERIFICACION PENDIENTE`. Sugerencia: nuevo punto JWIKI dedicado `01_LANDSCAPE/tinyhumansai-org.md`.
83. **Composio vs OAuth directo**: OpenHuman ofrece ambos modos pero los limites del modo "direct" (que requisitos tecnicos) no fueron explorados. Sugerencia: nuevo punto `09_INTEGRATIONS/composio-direct-mode.md`.
84. **Comparativa exhaustiva con OpenClaw a nivel feature**: parcialmente cubierta por tabla del README (hecho #63). Auditor debe verificar si la tabla es parcial o completa.
85. **Tamano del codigo Rust en MB**: openhuman crate ~80 sub-modulos (CSDN, hecho #21). Auditor confirmar con `find crates/ -type f -name "*.rs" | wc -l` desde el repo clonado.
86. **Politica de privacidad/telemetria**: declarada como "encrypted locally, treated as yours" (README). NO se encontro policy doc publico. Sugerencia: nuevo punto `11_SECURITY/openhuman-privacy.md`.

### 16. Tabla resumen "datos vs afirmaciones secundarias"

| Dato | task_queue.md | JWIKI-002 raw (hecho #19, #18) | GitHub API oficial (canon) | Notas |
|---|---|---|---|---|
| Stars | 7,8k (jun 2026) | "rango 7.8k" | **33.923** (2026-06-30 11:50 UTC) | Triplicado en 4 meses |
| Version actual | v0.53.43 (mayo 2026) | v0.54.7 | **v0.58.0** (2026-06-26) | 5 minor + 4 patch avance |
| Licencia | (no especifica) | "GNU" generico | **GPL-3.0** SPDX | Concretar |
| Stack | Rust + Tauri + React/TS | "Rust + Tauri + React/TypeScript" | Rust 60,5% + TS 36,6% + Tauri 2.0 + CEF | OK, confirmado |
| Stars confirmacion: NO usar 7.8k | -- | -- | **Stars historicos crecientes**: 1737 commits (163.com), 3.4k stars old, 6.5k (CSDN May), 23k (juejin May), 29k (alphasignalai), 8k+ in 7 days (Reddit), **actual 33,923 (GitHub)** |

---

## Reglas aplicadas (audit trail)

1. **NO invente**: cada hecho arriba tiene URL + fecha de acceso. Cuando una fuente secundaria contradice la oficial, gana la oficial (GitHub API).
2. **Priorice codigo sobre tutoriales**: verificacion principal via `api.github.com/repos/tinyhumansai/openhuman` (GET repo, GET languages, GET tags, GET releases/latest).
3. **Documente diferencias**: seccion 5 marca explicitamente las versiones secundarias obsoletas (v0.53.43, v0.54.7) vs la canonica (v0.58.0).
4. **Pendientes listados**: seccion 15 marca 6 items que necesitan escalar a Auditor o nuevo punto JWIKI.
5. **No invento cifras**: en la seccion 16 mantengo el rastro completo (task_queue -> JWIKI-002 raw -> API oficial).

---

## Inputs para el Escriba (sugerencias de estructura del doc final `01_LANDSCAPE/openhuman.md`)

- Encabezado con tagline + 1 linea de tesis
- Tabla "specs" (stars/forks/release/license) en el top
- Secciones: Repositorio, Stack, Releases timeline, Features, Integraciones OAuth, Voz, Plataformas, Contribuidores, Posicionamiento vs competencia, Senales de mercado, Limitaciones conocidas, Referencias
- Incluir la tabla comparativa del README (hecho #63) pero advertencia: "tabla del vendor, verificar contra analisis independientes antes de citar como evidencia neutral"
- Cerrar con seccion "Conflictos resueltos durante la investigacion" (v0.53.43/v0.54.7/v0.58.0 y stars 7.8k vs 33.923) -- esto ayuda al Auditor a entender de donde viene cada cifra.

---

*Mantenido por Mavis (orquestador, turno A) segun rol `aithera-wiki-investigador`. Investigacion ejecutada 2026-06-30 13:45-13:55 Europe/Paris.*
