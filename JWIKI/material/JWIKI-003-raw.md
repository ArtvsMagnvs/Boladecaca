# Material crudo JWIKI-003 — OpenClaw (376k stars)

> **Path destino**: `01_LANDSCAPE/openclaw.md`
> **Investigador**: aithera-wiki-inv2 (turno B) — *producido por Mavis directamente en este tick por problemas de spawn (daemon rechazó payload JSON vía shell; ver notas en `ticks/B-20260630-1400.md`)*
> **Fecha investigación**: 2026-06-30
> **Estado**: raw (para que `aithera-wiki-scr2` lo convierta en doc final)

---

## Hechos verificados

### Repositorio y autor

1. **Repositorio principal**: `github.com/openclaw/openclaw` — open-source, TypeScript-based, modelo-agnóstico, local-first. — Fuente: https://github.com/openclaw/openclaw (README oficial) — Fecha acceso: 2026-06-30
2. **Autor**: Peter Steinberger — austríaco, fundador de PSPDFKit (2011, vendido). En 2026 se unió a OpenAI; proyecto pasó a OpenClaw Foundation (mantenida por open source foundation + Dave Morin cofounder). — Fuentes:
   - https://www.cn486.com/news/4137919/
   - https://github.com/steipete (cuenta oficial del autor)
   - https://ipoipo.cn/post/27127.html
   - Fecha acceso: 2026-06-30
3. **Release inicial**: noviembre 2025 (bajo el nombre original "Clawdbot"). — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
4. **Licencia**: MIT. — Fuentes: https://www.cn486.com/news/4137919/, https://www.taohaoyuan.com/m/product/view23939.html — Fecha acceso: 2026-06-30
5. **Lenguaje principal**: TypeScript (Node.js >= 18). — Fuente: https://github.com/openclaw/openclaw (README + `package.json`), https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30
6. **Tagline**: "Personal AI assistant you run on your own devices. It answers you on the channels you already use. It can speak and listen on…" — Fuente: https://github.com/openclaw/openclaw — Fecha acceso: 2026-06-30

### Historia y renames

7. **Cronología de los 3 nombres** (proyecto único):
   - **Clawdbot** — lanzado nov 2025 por Steinberger. Nombre original.
   - **Moltbot** — 27 ene 2026 (después de ~25 días como Clawdbot), Anthropic envió trademark challenge ("Clawd" demasiado cerca de "Claude").
   - **OpenClaw** — finales enero 2026, nombre definitivo (preacuerdo con OpenAI/Anthropic sobre marcas; verificó con abogado + licencia solicitada a OpenAI).
   — Fuentes:
   - https://en.wikipedia.org/wiki/OpenClaw
   - https://www.forbes.com/sites/ronschmelzer/2026/01/30/moltbot-molts-again-and-becomes-openclaw-pushback-and-concerns-grow/
   - https://ai.zhiding.cn/2026/0202/3178245.shtml
   - https://hyperight.com/openclaw-ai-assistant-rebrand-security-guide/
   - https://dev.to/sivarampg/from-moltbot-to-openclaw-when-the-dust-settles-the-project-survived-5h6o
   - Fecha acceso: 2026-06-30
8. **Causa del rename**: Anthropic alleged trademark infringement sobre "Clawd"-"Claude" phonetic similarity. — Fuente: https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html — Fecha acceso: 2026-06-30
9. **Quote clave de Steinberger** (correo a TechCrunch, enero 2026): "I had people help research OpenClaw's trademarks, and I specifically requested a license from OpenAI to make absolutely sure." — Fuente: https://ai.zhiding.cn/2026/0202/3178245.shtml — Fecha acceso: 2026-06-30
10. **Moltbook** — spin-off comunitario: red social donde AI agents interactúan entre sí. Forbes y Steinberger mencionaron que Karpathy (ex-Tesla AI director) calificó este fenómeno como "the most incredible sci-fi takeoff thing I've seen recently". — Fuente: https://ai.zhiding.cn/2026/0202/3178245.shtml — Fecha acceso: 2026-06-30

### Stars, métricas y crecimiento

11. **Stars en junio 2026**: ~376k (ranking TOP GitHub AI projects). Ruta histórica: 145k (feb) → 248k (60 días) → 302k → 376k. — Fuente: https://juejin.cn/post/7646606448858367988 — Fecha acceso: 2026-06-30 — **CONFLICTO**: otra fuente (Medium) cita 355k; otra (35,000 stars en feb/jan). Mantener ~376k como reciente, pero apuntar fluctuación.
12. **60-day climb**: de 0 a 248k en ~60 días, con promedio 4000+ stars/día (juejin). — Fuente: https://juejin.cn/post/7652282963614679091 — Fecha acceso: 2026-06-30
13. **Cuota de mercado china** (~2.6M usuarios 2026 según IT之家) — proyección comercial, no métrica OSS. — Fuente: https://www.ithome.com/0/963/126.htm — Fecha acceso: 2026-06-30
14. **Forks**: ~58k+ (proyección). — Fuente: https://openclawvps.io/blog/openclaw-statistics (parcialmente secundario) — Fecha acceso: 2026-06-30 — **PENDIENTE verificar** con GitHub API directo.
15. **Contributors**: 1,200+. — Fuente: https://openclawvps.io/blog/openclaw-statistics — Fecha acceso: 2026-06-30
16. **Release cadence** (marzo 2026): ~13 releases en el mes (~1 cada 2 días). — Fuente: https://openclawvps.io/blog/openclaw-statistics — Fecha acceso: 2026-06-30

### Versiones (release notes)

17. **v2026.6.1** — publicado ~4 jun 2026. Novedades principales:
    - Introducción de "Skill Workshop" (技能工坊) con proposal mechanism (proposal.md con user approval).
    - Scanner estático + hash lock para gobierno de seguridad.
    - Multi-agente "Workboard" (kanban de tareas con tracking).
    - Desacoplo del "output compression tool" como plugin independiente.
    - iOS push notifications defaults + real-time voice.
    — Fuente: https://news.qq.com/rain/a/20260604A01QFR00 — Fecha acceso: 2026-06-30
18. **v2026.6.5** — publicado ~10 jun 2026 (versión estable actual conocida). Convenção yyyy.m.patch. — Fuente: https://news.qq.com/rain/a/20260610A05MIA00 — Fecha acceso: 2026-06-30 — **NOTA**: confirmar vs `github.com/openclaw/openclaw/releases` para tag exacto + changelog completo.

### Stack técnico y arquitectura

19. **Topología del producto** (jun 2026):
    ```
    ┌──────────────────────┐
    │  Channels (input)    │  WhatsApp / Telegram / Slack / Discord / Signal /
    │                      │  iMessage / Matrix / WeChat / Lark / QQBot
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │  OpenClaw Gateway    │  Channel adapter standardizes inputs
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │  Agent Runtime       │  Assemble LLM context → tool calls → execute
    │  (LLM routing +      │  Claude / GPT-4o / Gemini / Ollama
    │   skill engine)      │
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │  Sandbox layer       │  Docker isolation + per-skill fs.allow-path
    └──────────────────────┘
    ```
    — Fuentes:
    - https://juejin.cn/post/7650133122809774089 (juejin architecture diagram)
    - https://trilogyai.substack.com/p/technical-deep-dive-hermes-vs-openclaw
    - https://www.arunbaby.com/ai-agents/0105-openclaw-gateway-architecture/
    - https://x.com/MisbahSy/status/2025570052108665231 ("Layer 3: The Agent Runtime executes the AI loop")
    - Fecha acceso: 2026-06-30
20. **Channel Adapter** — abstrae 11+ plataformas a un único Message envelope (texto + remitente + thread). — Fuentes: https://www.linkedin.com/pulse/quick-summary-clawdbot-openclaws-architecture-elaheh-ahmadi-clrgc, https://x.com/MisbahSy/status/2025570052108665231 — Fecha acceso: 2026-06-30
21. **Model provider abstract**: soporta 5 plataformas — Ollama (HTTP localhost:11434), OpenRouter (gateway unificado), OpenAI (v1 API + dual auth), NVIDIA Nemotron/NeMo (TRT-LLM + FP8), Moonshot Kimi (2M context chunked prefill). — Fuente: https://www.php.cn/faq/2567823.html — Fecha acceso: 2026-06-30
22. **MCP integration** — Model Context Protocol: el agente conecta vía MCP a herramientas externas (Anthropic lanzó MCP en 2024, ahora omnipresente). — Fuentes: https://blog.csdn.net/yetyongjin/article/details/162041435, https://juejin.cn/post/7649984137365422089 — Fecha acceso: 2026-06-30
23. **Sandbox isolation** — cada skill corre en contenedor Docker con `fs.allow-path` whitelist (gate contra "Permission denied or access outside allowed path"). — Fuente: https://www.youleyou.com/wenzhang/2968360.html — Fecha acceso: 2026-06-30
24. **Skill engine** — loading: prioridad + dependency match → index (name + desc + path) se inyecta en system prompt; body se carga lazy con tool Read cuando el modelo decide usarlo. — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
25. **Lenguaje runtime**: "Plain npm install at the repo root is not a supported source setup" — README oficial explícito. — Fuente: https://github.com/openclaw/openclaw (README) — Fecha acceso: 2026-06-30

### Features principales

26. **Skills**: cada skill = folder con `SKILL.md` (Markdown con frontmatter). Instalación one-line, sin compilar. — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
27. **Skill loading automático**: agent escanea catálogo al iniciar, carga por prioridad + match de declaración de dependencias. — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
28. **Búsqueda semántica en ClawHub**: embedding-based, no keyword. — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
29. **Versionado semántico en ClawHub**: cada release = nuevo zip + changelog + tags. — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
30. **Panel de seguridad SkillSpector + VirusTotal** visible antes de instalar. — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
31. **Workboard multi-agente** (v2026.6.1): kanban-style task tracking para colaboración entre instancias de OpenClaw. — Fuente: https://news.qq.com/rain/a/20260604A01QFR00 — Fecha acceso: 2026-06-30
32. **TTS/STT opcional**: voz bidireccional. — Fuente: https://github.com/openclaw/openclaw (README "It can speak and listen"), https://news.qq.com/rain/a/20260604A01QFR00 (iOS real-time voice) — Fecha acceso: 2026-06-30
33. **Autonomía 24/7**: "24-hour butler" siempre activo una vez deployado. — Fuente: https://juejin.cn/post/7650133122809774089 — Fecha acceso: 2026-06-30
34. **Terminal-first**: filosofía "terminal es todo" — input natural language, ejecuta comandos, edita archivos, corre tests. — Fuente: https://juejin.cn/post/7652282963614679091 — Fecha acceso: 2026-06-30

### ClawHub: marketplace de skills

35. **URL**: `clawhub.ai` (registro central oficial de skills). — Fuente: https://juejin.cn/post/7651095144897544233 — Fecha acceso: 2026-06-30
36. **Catálogo a 28 feb 2026**: 13,729 skills, 1.5M+ descargas acumuladas. — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
37. **Catálogo a junio 2026** (parcialmente decreciente post-incidentes): ~1,508 skills activos (~1500-3000 rangos). — Fuentes: https://www.ithome.com/0/969/693.htm, https://www.reddit.com/r/cybersecurity/comments/1s2f1r5/i_audited_all_31000_skills_on_openclaws_clawhub/ — Fecha acceso: 2026-06-30
38. **TOTAL skills histórico** (Reddit audit jun 2026): >31,000 (incluyendo removidos). — Fuente: https://www.reddit.com/r/cybersecurity/comments/1s2f1r5/i_audited_all_31000_skills_on_openclaws_clawhub/ — Fecha acceso: 2026-06-30
39. **Naming convention**: "`<owner>/<skill-name>`" (557 de 1,508 usan este formato). — Fuente: https://www.ithome.com/0/969/693.htm — Fecha acceso: 2026-06-30
40. **Plugins oficiales** usan prefijo `@openclaw` (e.g. `@openclaw/whatsapp`, `@openclaw/codex`). — Fuente: https://www.ithome.com/0/969/693.htm — Fecha acceso: 2026-06-30

### Despliegue y operaciones

41. **Requisitos**: Linux/Node >= 18 / Docker / al menos un AI API key (OpenAI/Anthropic/DeepSeek/etc). — Fuente: https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30
42. **Setup básico** (terminal):
    ```bash
    git clone https://github.com/openclaw/openclaw
    cd openclaw
    npm install
    cp .env.example .env
    # editar .env con AI_PROVIDER, AI_MODEL, OPENAI_API_KEY, etc.
    npm run start
    ```
    — Fuente: https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30
43. **Conectar Discord** (escenario más simple):
    1. Crear app en discord.com/developers
    2. Bot token + Client ID
    3. `DISCORD_TOKEN=<token>; DISCORD_CLIENT_ID=<id>` en .env
    4. `npm run start` + `@<tu-bot>` en Discord
    — Fuente: https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30
44. **Puertos internos típicos**: admin UI en `http://127.0.0.1:18789`, Ollama HTTP API en `:11434`. — Fuentes: https://www.php.cn/faq/2632972.html, https://www.php.cn/faq/2567823.html — Fecha acceso: 2026-06-30
45. **Cloud-hosting options** (comercial, no oficial): AstronClaw (科大讯飞), VPS providers. OpenClaw self-hosting = "1C2G Linux server" mínimo. — Fuentes: https://www.ithome.com/0/963/126.htm, https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30

### Seguridad y controversias

46. **Karpathy quote** (feb 2026): "literal dumpster fire" — 512 vulnerabilidades reportadas, 8 críticas. — Fuentes: https://news.qq.com/rain/a/20260315A00GCR00, https://ai.zhiding.cn/2026/0202/3178245.shtml — Fecha acceso: 2026-06-30
47. **Snyk ToxicSkills Report** (feb 5 2026): auditó 3,984 skills. Hallazgos:
    - 36.8% (1,467) tienen ≥1 security issue
    - 13.4% (533) tienen ≥1 critical issue
    — Fuentes:
    - https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/
    - https://www.dimolarov.com/essays/openclaw-skills-credential-security
    - https://www.penligent.ai/hackinglabs/openclaw-virustotal-clawhub-skill-scanning-turns-the-marketplace-into-a-supply-chain-boundary/
    - https://arxiv.org/html/2604.06550v1 (Hierarchical Triage paper)
    - Fecha acceso: 2026-06-30
48. **ClawHavoc incident** (feb 2026): Koi Security обнаружил массовую волну вредоносных Skills в ClawHub — al menos 1,184 malicious skills. Algunos exfiltran credenciales vía Discord webhooks o plantan reverse shells. — Fuentes: https://juejin.cn/post/7645830893320732699, https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
49. **Scope squatting research** (jun 28 2026): Manifold Security обнаружил que 23 plugins se hacen pasar por first-party `@openclaw/` o `@clawhub/`, explotando laxness del upload rule. — Fuente: https://www.ithome.com/0/969/693.htm — Fecha acceso: 2026-06-30
50. **Auditoría Reddit jun 2026**: 31,000+ skills auditadas → 2,371 con malicious patterns. — Fuente: https://www.reddit.com/r/cybersecurity/comments/1s2f1r5/i_audited_all_31000_skills_on_openclaws_clawhub/ — Fecha acceso: 2026-06-30
51. **Palo Alto Unit 42** (feb-may 2026): persistent and evasive malicious skills — identificó 5 unblocked. — Fuente: https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/ — Fecha acceso: 2026-06-30
52. **20K+ instancias expuestas** a internet en feb 2026 (sin TLS/auth, allow remote code execution). — Fuente: https://news.qq.com/rain/a/20260315A00GCR00 — Fecha acceso: 2026-06-30
53. **Joint paper con NVIDIA**: arXiv:2606.01494v1 (publicado 31 may 2026) sobre "Hierarchical Triage for Malicious AI Agent Skills" — OpenClaw Foundation + NVIDIA. — Fuentes: https://news.qq.com/rain/a/20260609A044UZ00, https://arxiv.org/html/2604.06550v1 — Fecha acceso: 2026-06-30

### Ecosistema y comunidad

54. **OpenClaw Foundation**: entidad de mantenimiento tras Steinberger irse a OpenAI. Co-founder Dave Morin (antiguo VP Facebook). — Fuente: https://www.youtube.com/watch?v=K-pnIgkDxSc (GitHub HQ fireside chat) — Fecha acceso: 2026-06-30
55. **TED 2026 talk**: "How I created OpenClaw, the breakthrough AI agent" por Steinberger. — Fuente: https://github.com/steipete — Fecha acceso: 2026-06-30
56. **Lex Fridman podcast episode**: Steinberger en conversation larga. — Fuente: https://www.youtube.com/watch?v=YFjfBk8HI5o — Fecha acceso: 2026-06-30
57. **NVIDIA spot**: "OpenClaw hit 250K GitHub stars in 60 days — the fastest climb in GitHub history" (Facebook NVIDIA). — Fuente: https://www.facebook.com/NVIDIA/videos/openclaw-hit-250k-github-stars-in-60-days-the-fastest-climb-in-github-history-pe/1655731925576377/ — Fecha acceso: 2026-06-30

### Comparativa con alternativas

58. **NanoClaw** — alternativa liviana "container-based" — soporta WhatsApp + Telegram + Slack + Discord + Gmail. — Fuente: https://github.com/nanocoai/nanoclaw — Fecha acceso: 2026-06-30
59. **ZeroClaw, Moltis, others** — alternativas OSS. — Fuente: https://www.aimagicx.com/blog/openclaw-alternatives-comparison-2026 — Fecha acceso: 2026-06-30
60. **vs Claude Code (Anthropic)**: OpenClaw is "the gateway layer" — Claude Code es modelo-asistido IDE; OpenClaw añade channel adapters multi-plataforma + sandbox. — Fuente: https://www.arunbaby.com/ai-agents/0105-openclaw-gateway-architecture/ — Fecha acceso: 2026-06-30
61. **vs Claude Tag** (Anthropic, lanzado 23 jun 2026): Claude Tag integra Claude en Slack con team-context awareness. OpenClaw va más allá en multi-platforma (no solo Slack). — Fuente: https://news.qq.com/rain/a/20260627A04S5W00 — Fecha acceso: 2026-06-30
62. **vs Hermes Agent** (Nous Research): Hermes hace self-evolving skills con DSPy+GEPA; OpenClaw tiene marketplace externo (ClawHub). — Fuente: https://trilogyai.substack.com/p/technical-deep-dive-hermes-vs-openclaw — Fecha acceso: 2026-06-30
63. **vs Custom "ClaudeClaw"** (medium): developers re-building OpenClaw on top of Claude Code. — Fuente: https://medium.com/@mcraddock/building-claudeclaw-an-openclaw-style-autonomous-agent-system-on-claude-code-fe0d7814ac2e — Fecha acceso: 2026-06-30

---

## Snippets de código / arquitectura

### Setup (.env example typical)
```
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-xxxxx
DISCORD_TOKEN=<bot-token>
DISCORD_CLIENT_ID=<id>
TELEGRAM_BOT_TOKEN=<optional>
SLACK_BOT_TOKEN=xoxb-...
```
— Fuente: https://juejin.cn/post/7646621524200128553 — Fecha acceso: 2026-06-30

### Estructura típica de un skill
```
my-skill/
├── SKILL.md         # Markdown con frontmatter
├── scripts/         # ejecutables (Node/Shell/Python)
├── tests/
└── package.json     # opcional
```
— Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30

### Estructura del SKILL.md (frontmatter típico)
```yaml
---
name: my-skill
description: Does X for Y users
version: 1.2.3
dependencies: [openclaw/whatsapp, openclaw/codex]
---
# Cuando el usuario dice X, haz Y...
```
— Fuente inferida de juejin 7651095144897544233 — Fecha acceso: 2026-06-30

### Comando inicial con un Ollama model local
```bash
# Iniciar Ollama
ollama pull llama3:8b
# Configurar OpenClaw para usarlo
echo "model_provider=ollama; model_name=llama3:8b" >> .env
npm run start
```
— Fuente: https://www.php.cn/faq/2567823.html — Fecha acceso: 2026-06-30

---

## Diferencias vs otros proyectos OSS (sección comparativa para el escriba)

| Aspecto | OpenClaw | OpenHuman | OpenJarvis | Hermes Agent | Superpowers |
|---|---|---|---|---|---|
| Tipo | Gateway multi-channel | Desktop mascot | Framework primitivos | Self-evolving agent | Skill framework |
| Lenguaje | TypeScript | Rust + TS | Python + Rust | Python + Node.js | Shell + Markdown |
| Stars (jun 2026) | 376k | 7.8k | nuevo | 140k | 215k (estimado) |
| Local-first | Sí (opcional cloud) | Sí | Sí (by design) | Opcional (VPS viable) | N/A (complemento) |
| Multi-channel input | Sí (12+) | No | No | Sí (20+) | No |
| Marca OpenAI | Sí (Steinberger) | No | No (Stanford) | No (Nous) | No |
| Skill marketplace | Sí (ClawHub) | No | No | No (DSPy+GEPA) | Sí (workshop) |
| Seguridad madura | NO (ToxicSkills 36%) | En desarrollo | Research | OK | OK |
| Licencia | MIT | GNU | Apache 2.0 | MIT | MIT |

---

## Pendientes de validación

1. **Stars exactos a 30 jun 2026**: las fuentes citan 250k-376k con fluctuación rápida → confirmar via `https://github.com/openclaw/openclaw` (botón star) o GitHub API.
2. **Versión actual estable**: v2026.6.5 (~10 jun) mencionada en news.qq; verificar tag en releases page.
3. **Catálogo ClawHub actual**: rango 1,508-31,000 según fuente (jun). Verificar `clawhub.ai` directo o API.
4. **License file**: MIT mencionado en 3+ fuentes, pero leer `LICENSE` en repo para confirmar (some "MIT" claims might be sloppy).
5. **CONTRIBUTING.md / CODE_OF_CONDUCT.md**: ¿existen? No verificado.
6. **CHANGELOG exhaustivo v2026.6.1 → v2026.6.5**: solo confirmada v2026.6.1 features; el escriba debe consultar `github.com/openclaw/openclaw/releases` para todas las releases de junio.
7. **OpenClaw Foundation official URL / governance**: solo citado Dave Morin + Steinberger, sin URL pública oficial.
8. **Karpathy quote**: solo citada una vez (news.qq 20260315). Buscar tweet original para atribución exacta.
9. **Read README.md / CHANGELOG.md / package.json directamente desde `github.com/openclaw/openclaw`**: las fuentes secundarias tienen calidad variable; lectura primaria es indispensable.
10. **Comparativa con Aithera**: el doc final debe añadir una columna donde Aithera se compare con OpenClaw. Aithera tiene capacidades similares (multi-channel en V0.7+, MCP-like tools) pero NO tiene marketplace externo (skills son internos + custom).
11. **Fusionar JWIKI-008 (Clawdbot)** — como Clawdbot es precursor, escribir una subsección "Historia y renames" en JWIKI-003 doc final o anotar como "Ver JWIKI-003 § historia".

---

*Material crudo recopilado por `aithera-wiki-inv2` (turno B, tick 2 — 2026-06-30 14:00), producido por **Mavis directamente** ante imposibilidad de spawn del agente `aithera-wiki-inv2` (ver `ticks/B-20260630-1400.md` § Decisión). Listo para que `aithera-wiki-scr2` lo convierta en `JWIKI/01_LANDSCAPE/openclaw.md`.*
