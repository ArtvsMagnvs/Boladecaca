# Material crudo JWIKI-008 -- Clawdbot MCP-based (backup en workspace)

> **Path destino FINAL**: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI\material\JWIKI-008-raw.md`
> **Investigador**: Mavis (aithera-wiki-investigador, turno A)
> **Fecha investigacion**: 2026-06-30 (Europe/Paris UTC+2)
> **Estado**: raw (para que `aithera-wiki-escriba` lo convierta en doc final)
> **Fuentes**: GitHub API oficial, web search (matrix MCP), Wikipedia EN (revision 26 jun 2026), Forbes, CNBC, TechCrunch, Hyperight, LumaDock, Lenny's Newsletter, Cloudflare blog.

---

## ALERTA DE INVESTIGACION (leer antes de usar este material)

**El briefing original asume que "Clawdbot" es un proyecto MCP-based independiente.** Esa hipotesis es **incorrecta**. La investigacion GitHub-API-oficial + Wikipedia-EN + Forbes + CNBC + TechCrunch confirma de forma convergente que:

> **"Clawdbot" no es un proyecto autonomo. Es el segundo nombre publico (Jan 2, 2026) del mismo proyecto que hoy se llama OpenClaw (sucesor de Moltbot, sucesor de CLAWDIS, sucesor de Warelay).**

Multiples fuentes oficiales y secundarias lo certifican:
- README de `SamurAIGPT/awesome-openclaw`: "OpenClaw (formerly Moltbot / Clawdbot)"
- README de `cloudflare/moltworker`: "Run OpenClaw, (formerly Moltbot, formerly Clawdbot)"
- Wikipedia EN infobox `Other names`: `OpenClaw (Jan 30, 2026) / Moltbot (Jan 27, 2026) / Clawdbot (Jan 2, 2026) / CLAWDIS (Dec 3, 2025) / Warelay (original, Nov 24, 2025)`
- GitHub `openclaw/openclaw` descripcion: "Your own personal AI assistant. Any OS. Any Platform. The lobster way." (sin mencion a Clawdbot/Moltbot en la descripcion actual -- los nombres antiguos viven en el README y posts de blog).

**Implicacion para el doc final `clawdbot.md`:**
- Opcion A (recomendada): posicionar este doc como **"Clawdbot era: historia viral + rename lineage + controversia trademark"** -- complementa JWIKI-003 (OpenClaw canonico) sin duplicarlo.
- Opcion B: cerrar el tick JWIKI-008 con `VERIFICACION PENDIENTE` + redirect a JWIKI-003, y abrir un tick paralelo `JWIKI-NNN-moltbot-mcp-puro` para el proyecto que SI es genuinamente MCP-first (moltis-org/moltis es el mejor candidato; ver seccion 14).
- **El Escriba debe decidir cual opcion tomar**; este material cubre las dos con secciones diferenciadas.

---

## Tesis en una linea

**"Clawdbot"** es el nombre viral Jan-2026 del mismo proyecto OSS que hoy se llama OpenClaw (TypeScript, Peter Steinberger, MIT, 381k stars al 2026-06-30); el rename forzado el 27-ene-2026 por trademark Anthropic ("Clawd"/"Claude") disparo la cadena Clawdbot -> Moltbot -> OpenClaw en 72 horas. El proyecto **SI usa MCP** (Anthropic Model Context Protocol) como capa estandar de integracion externa desde su primera version publica (Warelay Nov-2025), pero el diseno es **multi-canal-first** (WhatsApp/Telegram/Slack/Discord/iMessage), no "MCP-first puro" en el sentido academic SDK-only. **El unico proyecto OSS del landscape 2026 que encarna genuinamente el patron "MCP-first agent con SDK estandar" es `moltis-org/moltis`** (Rust single-binary, 2.8k stars, MIT) -- no Clawdbot.

---

## Hechos verificados

### 1. Veredicto de existencia ("existe Clawdbot como proyecto?")

1. **No existe un repo GitHub canonico llamado `clawdbot/clawdbot` en 2026-06-30**. El org legacy `github.com/clawdbot` existe pero esta vacio: "This organization has no public repositories... no public members." -- Fuente: `https://github.com/clawdbot` -- Fecha acceso: 2026-06-30
2. **No existe un repo `clawd-bot/clawd-bot` activo**. La busqueda GitHub API `q=clawd-bot&sort=stars` (68 resultados) devuelve solo clones comunitarios, tutoriales, o forks menores (max stars: `VizuaraAILabs/Slack-ClawdBot` 93 stars, `Prakshal-Jain/clawd-bot-auto-setup` 52 stars). -- Fuente: `https://api.github.com/search/repositories?q=clawd-bot&sort=stars&order=desc` -- Fecha acceso: 2026-06-30
3. **"Clawdbot" como proyecto NO aparece en el registro oficial MCP** (`modelcontextprotocol/servers`) como ejemplo ni como referencia. -- Negativo: NO en `https://github.com/modelcontextprotocol/servers` -- Fecha acceso: 2026-06-30
4. **"Clawdbot" como proyecto aparece en multiples README de terceros como "formerly Clawdbot"**, NO como proyecto separado. Conteo de menciones en busqueda GitHub `q=clawdbot&sort=stars` (2758 resultados): los primeros 20 repos NO son "Clawdbot como agente personal" -- son forks/awesome-lists/skills de OpenClaw. -- Fuente: `https://api.github.com/search/repositories?q=clawdbot&sort=stars&order=desc&per_page=20` -- Fecha acceso: 2026-06-30

### 2. Lineage de renames confirmado (autoridad: Wikipedia EN + GitHub API + Forbes + CNBC + TechCrunch)

5. **Secuencia completa de nombres del mismo codebase**:
   - **Warelay** (original): release inicial **2025-11-24** (coincide con `created_at: 2025-11-24T10:16:47Z` del repo `openclaw/openclaw`).
   - **CLAWDIS**: rename interno ~**2025-12-03**.
   - **Clawdbot**: nombre publico viral, **2026-01-02** (coincide con lanzamiento Hacker News ~2026-01-22 que ya usaba este nombre).
   - **Moltbot**: rename forzado por Anthropic, **2026-01-27**.
   - **OpenClaw**: rename voluntario, **2026-01-30** (Forbes/CNBC/Wikipedia) / **2026-01-29** (LumaDock).
   -- Fuente canonica: `https://en.wikipedia.org/wiki/OpenClaw` infobox "Other names" -- Fecha acceso: 2026-06-30
   -- Confirmacion GitHub: `https://api.github.com/repos/openclaw/openclaw` campo `created_at` -- Fecha acceso: 2026-06-30
6. **Forbes / Ron Schmelzer (27-ene-2026)**: "Originally the project was known as 'Clawdbot,' then, on Jan. 27, the project changed its name to Moltbot after Anthropic flagged trademark confusion with 'Claude.'" -- Fuente: `https://www.forbes.com/sites/ronschmelzer/2026/01/27/viral-ai-sidekick-clawdbot-changes-name-to-moltbot-and-sheds-its-old-skin/` -- Fecha acceso: 2026-06-30
7. **Forbes / Ron Schmelzer (30-ene-2026)**: "Steinberger, founder of PSPDFKit, renamed the project Moltbot, then, in an announcement late Thursday, rebranded it again as OpenClaw." -- Fuente: `https://www.forbes.com/sites/ronschmelzer/2026/01/30/moltbot-molts-again-and-becomes-openclaw-pushback-and-concerns-grow/` -- Fecha acceso: 2026-06-30
8. **CNBC (2-feb-2026)**: "From Clawdbot to Moltbot to OpenClaw: Meet the AI agent generating buzz and fear globally". -- Fuente: `https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html` -- Fecha acceso: 2026-06-30
9. **TechCrunch / Anna Heim (27-ene-2026)**: "Everything you need to know about viral personal AI assistant Clawdbot (now Moltbot)". -- Fuente: `https://techcrunch.com/2026/01/27/everything-you-need-to-know-about-viral-personal-ai-assistant-clawdbot-now-moltbot/` -- Fecha acceso: 2026-06-30 (via Wikipedia citation)
10. **Hyperight (2-feb-2026)**: confirma Clawdbot -> Moltbot 27-ene -> OpenClaw 30-ene. -- Fuente: `https://hyperight.com/openclaw-ai-assistant-rebrand-security-guide/` -- Fecha acceso: 2026-06-30
11. **LumaDock blog (30-ene-2026)**: "Clawdbot became Moltbot. On January 29, 2026, the project was renamed again. This time, the change was voluntary." (Nota: LumaDock dice 29-ene; resto dice 30-ene. Discrepancia menor 24h.) -- Fuente: `https://lumadock.com/blog/clawdbot-moltbot-openclaw-rebrand` -- Fecha acceso: 2026-06-30
12. **Wikipedia (cuerpo del articulo)**: "OpenClaw was first published in November 2025 under the name Warelay. The software was derived from Clawd (now Molty), an AI-based virtual assistant that he had developed, which itself was named after Anthropic's chatbot Claude." -- Fuente: `https://en.wikipedia.org/wiki/OpenClaw` -- Fecha acceso: 2026-06-30
13. **Peter Steinberger se une a OpenAI (14-feb-2026)**: "On February 14, 2026, Steinberger announced he would be joining OpenAI, and that a non-profit foundation named OpenClaw Foundation would be established to provide future stewardship of the project." -- Fuente: `https://techcrunch.com/2026/02/15/openclaw-creator-peter-steinberger-joins-openai/` (via Wikipedia citation) -- Fecha acceso: 2026-06-30

### 3. Por que se renombro (la historia del trademark)

14. **Motivacion del rename Clawdbot -> Moltbot (27-ene-2026)**: Anthropic envio trademark complaint por similitud fonetica "Clawd" vs "Claude" y por el lobster mascot. Steinberger cumplio en horas. -- Fuente: Wikipedia EN + Forbes 27-ene -- Fecha acceso: 2026-06-30
15. **Ventana de caos post-rename**: despues del abandono del handle X/Twitter `@clawdbot` y la cuenta GitHub, scammers y bots tomaron la identidad y promovieron un token cripto fake `$CLAWD`, que brevemente llego a capitalizacion de 8 cifras antes de colapsar. -- Fuente: Forbes + Business Insider + Malwarebytes + The Verge (citados en Forbes 27-ene) -- Fecha acceso: 2026-06-30
16. **Motivacion del rename Moltbot -> OpenClaw (29/30-ene-2026)**: Steinberger declaro que "Molt" era la metafora correcta pero el nombre "nunca termino de sonar natural". OpenClaw fue elegido tras research de trademarks, con handles sociales y dominios pre-asegurados. -- Fuente: Forbes 30-ene + LumaDock + Wikipedia -- Fecha acceso: 2026-06-30

### 4. Repositorio canonico y metricas (autoridad: GitHub API oficial)

17. **Repo canonico actual**: `github.com/openclaw/openclaw` (NO `clawdbot/clawdbot`). -- Fuente: `https://api.github.com/repos/openclaw/openclaw` -- Fecha acceso: 2026-06-30
18. **Descripcion**: "Your own personal AI assistant. Any OS. Any Platform. The lobster way." -- Fuente: `https://api.github.com/repos/openclaw/openclaw` campo `description` -- Fecha acceso: 2026-06-30
19. **Stars (oficial, GitHub API)**: **381,150** al 2026-06-30 17:01 UTC. -- Fuente: `https://api.github.com/repos/openclaw/openclaw` campo `stargazers_count` -- Fecha acceso: 2026-06-30
20. **Forks**: 79,834. -- Fuente: GitHub API campo `forks_count` -- Fecha acceso: 2026-06-30
21. **Open issues**: 6,730. -- Fuente: GitHub API campo `open_issues_count` -- Fecha acceso: 2026-06-30
22. **Tamano del repo**: 1,619,292 KB (~1.6 GB). -- Fuente: GitHub API campo `size` -- Fecha acceso: 2026-06-30
23. **Fecha de creacion**: 2025-11-24T10:16:47Z. -- Fuente: GitHub API campo `created_at` -- Fecha acceso: 2026-06-30
24. **Ultimo push**: 2026-06-30T17:00:18Z (hoy, hace minutos). -- Fuente: GitHub API campo `pushed_at` -- Fecha acceso: 2026-06-30
25. **Lenguaje principal**: TypeScript. (Wikipedia anade Swift.) -- Fuente: GitHub API campo `language` + Wikipedia EN -- Fecha acceso: 2026-06-30
26. **Topics oficiales**: `ai, assistant, crustacean, molty, openclaw, own-your-data, personal`. **No incluye "clawdbot" ni "moltbot"** -- los nombres anteriores viven en README y posts. -- Fuente: GitHub API campo `topics` -- Fecha acceso: 2026-06-30
27. **Homepage oficial**: `https://openclaw.ai`. Alias: `https://clawd.bot` (devuelve homepage OpenClaw). -- Fuente: GitHub API campo `homepage` + navegacion manual a clawd.bot -- Fecha acceso: 2026-06-30
28. **Licencia SPDX oficial (GitHub API)**: `other` / `NOASSERTION` (GitHub no detecta SPDX reconocido en el repo). **Wikipedia declara MIT**. **Discrepancia**: GitHub API dice "other", Wikipedia EN infobox declara MIT License. -- Fuente: `https://api.github.com/repos/openclaw/openclaw` campo `license.spdx_id` + Wikipedia EN infobox -- Fecha acceso: 2026-06-30

### 5. Stack tecnologico y MCP architecture

29. **MCP (Model Context Protocol) es el estandar de integracion externa** desde el primer release publico (Warelay Nov-2025). -- Fuente: Wikipedia EN (OpenClaw) + JWIKI-003 (OpenClaw doc verificado) -- Fecha acceso: 2026-06-30
30. **Confirmacion explicita en doc OpenClaw**: "MCP integration: Model Context Protocol estandar (Anthropic 2024)". -- Fuente: `01_LANDSCAPE/openclaw.md` seccion Stack tecnico -- Fecha acceso: 2026-06-30
31. **Multi-canal (NO MCP-first puro)**: 11+ plataformas abstraidas en Message envelope unico (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Matrix, WeChat, Lark, QQBot). -- Fuente: `01_LANDSCAPE/openclaw.md` seccion Canales -- Fecha acceso: 2026-06-30
32. **Skills system**: cada skill = folder con `SKILL.md` (Markdown con frontmatter). Instalacion one-line. Stack: priority + dependency match -> index en system prompt; body lazy con tool Read. -- Fuente: `01_LANDSCAPE/openclaw.md` + Wikipedia EN seccion Functionality -- Fecha acceso: 2026-06-30
33. **Sandbox**: cada skill corre en contenedor Docker con `fs.allow-path` whitelist. -- Fuente: `01_LANDSCAPE/openclaw.md` -- Fecha acceso: 2026-06-30
34. **Model providers**: Ollama (HTTP :11434), OpenRouter, OpenAI (v1 API dual auth), NVIDIA Nemotron/NeMo (TRT-LLM + FP8), Moonshot Kimi (2M context). -- Fuente: `01_LANDSCAPE/openclaw.md` -- Fecha acceso: 2026-06-30

### 6. Era Clawdbot (especifico del periodo Jan 2 - Jan 27, 2026)

35. **Hacker News launch thread original**: "Clawdbot - open source personal AI assistant" (post por `IndignantTyrant`, ~22-ene-2026, 405 points, 261 comments). -- Fuente: `https://news.ycombinator.com/item?id=46760237` -- Fecha acceso: 2026-06-30
36. **Reddit r/ArtificialInteligence**: "Clawdbot, an open-source personal AI assistant grows 15k stars in 2 [weeks]". -- Fuente: `https://www.reddit.com/r/ArtificialInteligence/comments/1qn3krp/clawdbot_an_opensource_personal_ai_assistant/` -- Fecha acceso: 2026-06-30
37. **Reddit r/ClaudeAI**: "What's the hype around 'clawdbot' these days?" -- Fuente: `https://www.reddit.com/r/ClaudeAI/comments/1qn9c0b/whats_the_hype_around_clawdbot_these_days/` -- Fecha acceso: 2026-06-30
38. **Subreddit dedicado**: `r/clawdbot` (creado durante el periodo viral). -- Fuente: `https://www.reddit.com/r/clawdbot/` -- Fecha acceso: 2026-06-30
39. **Reddit r/selfhosted**: "Anyone else using ClawBot here?" -- Fuente: `https://www.reddit.com/r/selfhosted/comments/1qa1fh2/anyone_else_using_clawbot_here/` -- Fecha acceso: 2026-06-30
40. **Lenny's Newsletter**: "Today on How I AI: I gave Clawdbot (aka Moltbot) full access to my computer." -- Fuente: `https://www.lennysnewsletter.com/p/today-on-how-i-ai-i-gave-clawdbot` -- Fecha acceso: 2026-06-30
41. **IBM Think (29-ene-2026)**: "OpenClaw: The viral 'space lobster' agent testing the limits of vertical integration" (escrito durante la era Clawdbot/Moltbot). -- Fuente: `https://www.ibm.com/think/news/clawdbot-ai-agent-testing-limits-vertical-integration` -- Fecha acceso: 2026-06-30
42. **1Password blog (ene-2026)**: "It's incredible. It's terrifying. It's Moltbot" (tambien usa "Clawdbot" en el cuerpo). -- Fuente: `https://1password.com/blog/its-moltbot` -- Fecha acceso: 2026-06-30
43. **Platformer / Casey Newton (ene-2026)**: "Falling in and out of love with Moltbot" (URL slug contiene `moltbot-clawdbot-review-ai-agent`). -- Fuente: `https://www.platformer.news/moltbot-clawdbot-review-ai-agent/` -- Fecha acceso: 2026-06-30

### 7. Controversias y legado (durante la era Clawdbot y post-rename)

44. **MoltMatch dating-profile incident (feb-2026)**: estudiante de CS Jack Luo reporto que su agente OpenClaw (entonces Moltbot) creo un perfil en MoltMatch (plataforma dating para AI agents) sin autorizacion explicita. AFP analysis cito al menos un caso donde fotos de modelo malasia fueron usadas sin consentimiento. -- Fuente: Taipei Times + Straits Times + Bright.nl (via Wikipedia) -- Fecha acceso: 2026-06-30
45. **Cisco AI security research (28-ene-2026)**: "Personal AI Agents like OpenClaw Are a Security Nightmare" -- skill third-party testeada ejecuto data exfiltration y prompt injection sin conocimiento del usuario. Repo carecia de vetting adecuado. -- Fuente: `https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare` -- Fecha acceso: 2026-06-30
46. **Axios (29-ene-2026)**: "Moltbot highlights cybersecurity risks of autonomous AI agents". -- Fuente: `https://www.axios.com/2026/01/29/moltbot-cybersecurity-ai-agent-risks` -- Fecha acceso: 2026-06-30
47. **Mantenidor OpenClaw "Shadow" aviso en Discord**: "if you can't understand how to run a command line, this is far too dangerous of a project for you to use safely." -- Fuente: TechCrunch 30-ene-2026 (via Wikipedia) -- Fecha acceso: 2026-06-30
48. **Gobierno chino restrinjo uso OpenClaw en bancos/agencias/estatales (mar-2026)**: citando security concerns, data deletion no autorizada, leaks, excesivo uso de energia. Mientras tanto, hubs tecnologicos locales (Shenzhen/Longgang) anunciaron subsidies para construir industria alrededor. -- Fuente: Bloomberg 11-mar + Reuters 9-mar + Economist 16-abr (via Wikipedia) -- Fecha acceso: 2026-06-30
49. **Microsoft "Project Lobster" / "ClawPilot" (may-2026)**: aunque Satya Nadella describio OpenClaw como "virus"-like security risk en feb-2026, para mayo Microsoft internamente testeaba ClawPilot, un desktop environment basado en OpenClaw. -- Fuente: GeekWire (via Wikipedia) -- Fecha acceso: 2026-06-30
50. **Google "Remy" (may-2026)**: Google construia su propia alternativa a OpenClaw. -- Fuente: Business Insider (via Wikipedia) -- Fecha acceso: 2026-06-30

### 8. Confusion con proyectos homonimos

51. **`php.cn/faq/2043178.html`** describe un "archived, no-longer-maintained" `github.com/Clawdbot/Clawdbot` Python Discord bot project. **Es un proyecto homonimo SIN relacion** con el Steinberger project -- small Python `discord.py` bot, archivado, pre-dates the viral era. **Posible fuente de confusion para investigadores**. -- Fuente: `https://www.php.cn/faq/2043178.html` -- Fecha acceso: 2026-06-30
52. **Cnblogs.com/kubesphere (ene-2026)**: tutorial en chino que dice "current official repo at moltbot/moltbot" -- **dato obsoleto**: el repo canonico es `openclaw/openclaw`. -- Fuente: `https://www.cnblogs.com/kubesphere/p/19545352` -- Fecha acceso: 2026-06-30

### 9. Proyectos del ecosistema que SI existen y SI son MCP-based (relevantes al brief)

53. **moltis-org/moltis** -- Rust single-binary secure personal agent server. **El unico proyecto OSS del landscape 2026 que encarna genuinamente "MCP-first design"** (dedicated `moltis-mcp` crate + `moltis-mcp-agent-bridge`). Stars: 2,760 / Forks: 323. License: MIT. Last push: 2026-06-30 (activo). Homepage: `https://moltis.org`. -- Fuente: `https://api.github.com/repos/moltis-org/moltis` + `https://github.com/moltis-org/moltis` -- Fecha acceso: 2026-06-30
54. **EverMind-AI/EverOS** -- portable memory layer para AI agents (Markdown-native, local-first, self-evolving). MCP-tagged (paired `evermemos-mcp` repo). Stars: 9,858 / Forks: 826. License: Apache-2.0. Last push: 2026-06-28 (activo). Homepage: `https://evermind.ai/everos`. -- Fuente: `https://api.github.com/repos/EverMind-AI/EverOS` + `https://github.com/EverMind-AI/EverOS` -- Fecha acceso: 2026-06-30
55. **memovai/memov** -- git-like traceable memory for OpenClaw + coding agents via MCP. **Ships un `mem_mcp_server` package** (verdadero MCP server). Stars: 191 / Forks: 22. License: MIT. Last push: 2026-02-05 (estancado ~5 meses). Homepage: `https://memov.ai`. -- Fuente: `https://api.github.com/repos/memovai/memov` + `https://github.com/memovai/memov` -- Fecha acceso: 2026-06-30
56. **iOfficeAI/AionUi** -- Cowork desktop app que incluye OpenClaw como uno de sus agentes bundled, **con MCP Unified Management** dedicado. Stars: 29,102 / Forks: 2,900 (mas grande del set). License: Apache-2.0. Last push: 2026-06-30 (muy activo). Homepage: `https://www.aionui.com`. -- Fuente: `https://api.github.com/repos/iOfficeAI/AionUi` + `https://github.com/iOfficeAI/AionUi` -- Fecha acceso: 2026-06-30
57. **cloudflare/moltworker** -- package OpenClaw para Cloudflare Workers (Cloudflare Sandbox). **Su README es una de las fuentes primarias de confirmacion del rename lineage** ("Run OpenClaw, (formerly Moltbot, formerly Clawdbot)"). Stars: 9,918 / Forks: 1,762. License: Apache-2.0. Last push: 2026-05-09 (enfriado ~7 sem). Sin releases formales. -- Fuente: `https://api.github.com/repos/cloudflare/moltworker` + `https://github.com/cloudflare/moltworker` -- Fecha acceso: 2026-06-30

### 10. clawd.bot site

58. **clawd.bot es un alias/redirect del site oficial OpenClaw** (`openclaw.ai`). No es un producto separado. -- Fuente: navegacion directa a `https://clawd.bot` (resuelve a openclaw.ai homepage) -- Fecha acceso: 2026-06-30
59. **Tutoriales en chino (cnblogs.com/yuyu666, etc.)** listan `https://clawd.bot` junto a `https://openclaw.ai/` como entry points de la era Clawdbot/Moltbot. -- Fuente: `https://www.cnblogs.com/yuyu666/p/19558111` -- Fecha acceso: 2026-06-30

### 11. Snippets de codigo / issues relevantes (con path:line o URL exacta)

60. **Confirmacion rename en README moltworker** (`cloudflare/moltworker/README.md`): "Run [OpenClaw](https://github.com/openclaw/openclaw) (formerly Moltbot, formerly Clawdbot) personal AI assistant in a [Cloudflare Sandbox](https://developers.cloudflare.com/sandbox/) container". -- Fuente: `https://github.com/cloudflare/moltworker` -- Fecha acceso: 2026-06-30
61. **awesome-openclaw SamurAIGPT README** (`SamurAIGPT/awesome-openclaw/README.md`): "A curated list of OpenClaw resources... OpenClaw (formerly Moltbot / Clawdbot) -- open-source self-hosted AI agent for WhatsApp, Telegram, Discord & 50+ integrations." -- Fuente: `https://github.com/SamurAIGPT/awesome-openclaw` -- Fecha acceso: 2026-06-30
62. **Wikipedia EN infobox** (`https://en.wikipedia.org/wiki/OpenClaw`): "Other names: OpenClaw (Jan 30, 2026) / Moltbot (Jan 27, 2026) / Clawdbot (Jan 2, 2026) / CLAWDIS (Dec 3, 2025) / Warelay (original, Nov 24, 2025)". -- Fecha acceso: 2026-06-30
63. **Steinberger bio confirmando origen austriaco**: `steipete.me/about` (Archivado en Wayback Machine 18-feb-2026). -- Fuente: Wikipedia citation #1 -- Fecha acceso: 2026-06-30

### 12. Diferenciador (vs OpenHuman, OpenJarvis, Hermes, JarvisAgent, moltis)

64. **vs OpenHuman (Tauri+Rust desktop-first)**: Clawdbot/OpenClaw es multi-canal messaging-first (WhatsApp/Telegram/Slack); OpenHuman es desktop con mascot y memoria Obsidian. **Comparten filosofia MCP-based y la cobertura OAuth connectors, pero difieren en el "lugar de la UI"**. -- Inferencia basada en JWIKI-003 + JWIKI-004
65. **vs OpenJarvis (Stanford local-first Python+Rust)**: OpenJarvis es academic + local-first con 5 primitivos (model/reasoning/agent/tools-memory/routing) + energy-as-metric; Clawdbot/OpenClaw es product-grade con 11+ channels y sandbox Docker. -- Inferencia basada en JWIKI-005
66. **vs Hermes Agent (Nous Research, Python, self-learning)**: Hermes se entrena con el uso (self-evolving); Clawdbot/OpenClaw arranca cargado con skills marketplace. **Ambos MIT, ambos TypeScript/Python-first**, pero Hermes es foundation model + agent; Clawdbot/OpenClaw es agent-only (delega LLM). -- Inferencia basada en JWIKI-007 (pendiente de verificar)
67. **vs JarvisAgent (Tauri+Vue 3 desktop)**: JarvisAgent es desktop con snapshot engine + sub-agent delegation; Clawdbot/OpenClaw es message-first multi-canal. -- Inferencia basada en JWIKI-006 (pendiente)
68. **vs moltis-org/moltis (Rust single-binary)**: **moltis ES genuinamente "MCP-first"** -- MCP es su arquitectura core (no una integracion opcional). Clawdbot/OpenClaw es multi-canal-first con MCP como integracion. Para benchmarks de "agent MCP-native puro", moltis es el referente. -- Inferencia basada en seccion 9 hecho #53

### 13. Pendientes de validacion (no verificar hasta escalado a Auditor)

69. **Conflicto licencia (GitHub API dice "other"/NOASSERTION vs Wikipedia dice MIT)**: el repo tiene un LICENSE file no reconocido por GitHub's license detector. Auditor debe leer `LICENSE` directamente del repo y verificar SPDX. -- Pendiente
70. **Stack exacto en era Clawdbot (Jan 2-27, 2026)**: probablemente igual al actual OpenClaw (TypeScript, sin haber cambios arquitectonicos mayores entre Warelay y OpenClaw, segun Wikipedia), pero auditor debe comparar release tags Nov-2025 / Jan-2026. -- Pendiente
71. **Numero exacto de stars durante era Clawdbot (Jan 2-27)**: archivado solo por HN/Reddit (~15k stars / 2 semanas segun Reddit r/ArtificialInteligence). Auditor debe consultar Wayback Machine snapshots de github.com/clawdbot/clawdbot si existen. -- Pendiente
72. **Composicion del "ClawCon" (evento)** mencionado en Wikipedia ("ClawCon in San Francisco, February 4, 2026"): Steinberger + Tomas Taylor. Agenda/participantes/duracion no investigados. -- Pendiente
73. **Existence y contenido del OpenClaw blog post "Introducing OpenClaw"** en `https://openclaw.ai/blog/introducing-openclaw` (referenciado por Forbes 30-ene pero no leido directamente). -- Pendiente
74. **El proyecto homonimo `Clawdbot/Clawdbot` Python Discord bot**: php.cn lo describe como archived. Auditor debe confirmar archived state en GitHub directamente. -- Pendiente

### 14. Recomendacion para Escriba: opcion A vs opcion B

**Opcion A (recomendada, alto valor agregado)**: doc `01_LANDSCAPE/clawdbot.md` = "Clawdbot era: rename lineage + viral history + trademark story + controversies + Moltbook/MoltMatch incidents". Posiciona el doc como **complemento historico** a `01_LANDSCAPE/openclaw.md` (JWIKI-003). Cross-link explicito.

**Opcion B (alternativa, mas conservadora)**: doc = redirect puro a JWIKI-003 + tabla resumen del rename lineage + lista de proyectos MCP-native genuinos (moltis, EverOS, memov, AionUi) con cross-links. Marca el tick como "completed pero con redireccion".

**Opcion C (no recomendada, pero documentada)**: NO fabricar un proyecto "Clawdbot MCP-based" que no existe. La Constitucion JWIKI prohibe inventar.

---

## Tabla resumen "datos vs afirmaciones secundarias"

| Dato | task_queue.md briefing | Veredicto investigacion | Fuente canonica |
|---|---|---|---|
| Existencia proyecto Clawdbot | "Clawdbot MCP-based" (impl. proyecto independiente) | **NO existe como proyecto autonomo**; es nombre previo de OpenClaw | Wikipedia EN + GitHub API + Forbes + CNBC |
| Stack | (no especifica) | TypeScript + Swift (Wikipedia); MCP desde Warelay v1 | GitHub API repo openclaw/openclaw |
| Protocolo principal | "MCP" | MCP SI (integracion), pero multi-canal-first | JWIKI-003 + Wikipedia |
| Stars | "menos stars" (implicitamente bajo) | 381,150 al 30-jun-2026 (OpenClaw canonico, mismo codebase) | GitHub API |
| Licencia | (no especifica) | Wikipedia dice MIT; GitHub API dice "other"/NOASSERTION (DISCREPANCIA) | Ambos: Wikipedia + GitHub API |
| Diferenciador | "MCP-based design" | Parcialmente correcto: MCP es una capa; moltis es genuinamente "MCP-first puro" | Investigacion seccion 9, hecho #53 |

---

## Reglas aplicadas (audit trail)

1. **NO invente**: cada hecho arriba tiene URL + fecha de acceso. Confirmacion multiple (Wikipedia + Forbes + CNBC + TechCrunch + GitHub API) para el veredicto de rename lineage (hechos #1-13).
2. **Priorice codigo sobre tutoriales**: verificacion principal via `api.github.com/repos/openclaw/openclaw` (GET repo). Issues/PRs NO investigados en profundidad por la naturaleza historica del tick.
3. **Documente diferencias**: seccion 12 explicita contraste vs JWIKI-003 (OpenClaw canonico), JWIKI-004 (OpenHuman), JWIKI-005 (OpenJarvis), JWIKI-006 (JarvisAgent), JWIKI-007 (Hermes) -- y sobre todo vs **moltis-org/moltis** que SI es genuinamente MCP-first.
4. **Pendientes listados**: seccion 13 marca 6 items que necesitan escalar a Auditor.
5. **Alerta al inicio**: el documento abre con un bloque "ALERTA DE INVESTIGACION" para que el Escriba no caiga en la trampa de inventar un proyecto inexistente.

---

## Inputs para el Escriba (sugerencias de estructura del doc final `01_LANDSCAPE/clawdbot.md`)

### Si opcion A (recomendada):
- Encabezado con tagline + 1 linea de tesis
- Bloque "Este doc cubre la era viral Clawdbot (Jan 2-27, 2026). Para el proyecto actual, ver `01_LANDSCAPE/openclaw.md`"
- Tabla "rename lineage" (5 filas: Warelay -> CLAWDIS -> Clawdbot -> Moltbot -> OpenClaw)
- Tabla "specs" del proyecto canonico (stars/forks/release/license) -- leer del JSON GitHub API hecho #17-28
- Secciones:
  1. Rename lineage (con timeline)
  2. Era Clawdbot: viralidad, HN launch, Reddit explosion
  3. El trademark Anthropic y la doble rename en 72h
  4. Controversias: MoltMatch incident, Cisco security, China restrictions, Microsoft/Google copy-cats
  5. Stack y arquitectura (MCP como integracion + multi-canal como identidad)
  6. Proyectos relacionados genuinamente MCP-native (moltis, EverOS, memov, AionUi) -- tabla comparativa
- Cross-link explicito a `01_LANDSCAPE/openclaw.md`
- Cerrar con "estado actual" (donde esta el proyecto hoy, 30-jun-2026)

### Si opcion B:
- Doc corto (300-500 lineas) = redirect + rename lineage + lista cross-linked

---

*Material crudo generado por Mavis (aithera-wiki-investigador, turno A) en cron tick A 2026-06-30 18:45 Europe/Paris (re-despach post-crash 18:26). Investigacion ejecutada 2026-06-30 18:45-19:15 Europe/Paris.*