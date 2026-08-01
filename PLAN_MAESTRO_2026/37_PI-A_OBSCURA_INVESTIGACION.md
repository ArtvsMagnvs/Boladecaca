# 37 — PI-A · Investigación Obscura → decisión GO/NO-GO (para PU9)

> **Sesión**: PI-A (doc 35), 2026-07-31, Fable 5. Investigación pura — **no se
> tocó código de producción**.
> **Método**: no solo lectura del repo. Se **descargó y ejecutó de verdad** el
> binario de Obscura (`v0.1.10`, build Linux x86_64) en el entorno de trabajo y
> se conectó Playwright por CDP contra él — las respuestas de abajo vienen de una
> prueba de concepto REAL, no de la documentación.
> **Repo**: [`h4ckf0r0day/obscura`](https://github.com/h4ckf0r0day/obscura)
> (Apache-2.0). Corrección del doc 35 confirmada: Obscura NO es un buscador web,
> es un navegador headless para agentes/scraping. Esta investigación **refina
> aún más** esa etiqueta (ver §Resumen).

---

## Resumen ejecutivo (léelo primero)

**Recomendación: NO-GO para V1.0** como motor del `browser_tool` ni como el
"navegador descargable 1-click" que se imaginó. **Con un GO CONDICIONAL y
ACOTADO para el futuro** (post-1.0, probablemente junto a Hermes V1.1) en un
papel muy distinto del que el plan asumía: **motor de LECTURA/scraping** para la
pata "leer el texto de una página", NO como el navegador interactivo.

**El hallazgo que lo decide** (verificado ejecutando el binario): Obscura
**no tiene motor de layout ni de pintado**. Ejecuta JavaScript real (V8) y habla
CDP, pero no renderiza píxeles. Su propio binario lo dice cuando le pides una
captura:

> *"Page.captureScreenshot is not supported by Obscura: no layout or paint
> engine. For visual snapshots, drive a real headless Chromium for the
> screenshot leg of your pipeline and use Obscura for the scraping leg."*

Es decir: **el propio proyecto recomienda usar Chromium real para lo visual y
Obscura solo para scrapear.** El `browser_tool` de Aithera se usa justo para lo
visual/interactivo ("abre YouTube y pon la canción", clicar botones, ver la
pantalla) — que es exactamente lo que Obscura NO hace.

---

## Las 5 preguntas del doc 35, respondidas

### P1 · ¿Hay binario nativo para Windows, o solo Docker/cargo? → **SÍ, binario nativo Windows** ✅

El release `v0.1.10` publica binarios PREINSTALADOS para las 5 plataformas, con
nombres exactos (verificados en los assets del release):

| Asset | Tamaño |
|---|---|
| `obscura-x86_64-windows.zip` | **41.1 MB** |
| `obscura-x86_64-linux.tar.gz` | 48.2 MB |
| `obscura-aarch64-linux.tar.gz` | 50 MB |
| `obscura-x86_64-macos.tar.gz` | 45.7 MB |
| `obscura-aarch64-macos.tar.gz` | 43.8 MB |

Cada zip trae dos ejecutables: `obscura` y `obscura-worker`. **No hace falta
Docker en la máquina del usuario final** — esto elimina la mayor razón de NO-GO
que el doc 35 anticipaba ("si solo hay Docker, probablemente NO-GO para V1.0").
Confirmado ejecutando el equivalente Linux: es un ELF nativo, arranca al
instante, sin dependencias de sistema pesadas. El zip de Windows es un binario
suelto — la instalación sería descomprimir y ejecutar, el patrón 1-click que
Aithera ya domina (Ollama/Kokoro/Codex).

*Veredicto P1: la distribución NO es un obstáculo. Es lo mejor de la
investigación para Obscura.*

### P2 · ¿Playwright de Python conecta limpio por CDP? → **SÍ conecta, pero solo la mitad de las acciones funcionan** ⚠️

Prueba REAL ejecutada — `obscura serve --port 9222` levanta un servidor CDP que
expone `/json/version` y `webSocketDebuggerUrl` **idénticos a Chrome**
(anuncia `"Browser": "Chrome/145.0.0.0"`, `"Protocol-Version": "1.3"`). Se
conectó con el MISMO código que usa el `browser_tool` de Aithera:

```python
browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")   # ✅ conectó
```

Resultado de las 4 acciones que el plan pedía probar (open_url / click /
get_text / screenshot), sobre `example.com` real:

| Acción del `browser_tool` | Resultado |
|---|---|
| `open_url` (`page.goto`) | ✅ **status 200**, navegación real |
| `get_text` (`inner_text`) | ✅ extrajo el texto real de la página |
| `get_html` / título | ✅ funciona (`page.title()` → "Example Domain") |
| `page.evaluate` (JS de V8) | ✅ ejecutó JS real (`6*7+6 = 48`); `navigator.webdriver = false` |
| **`click`** (clic sobre un `<a>`) | ❌ **TIMEOUT** — el localizador resolvió el enlace pero el clic no se completa: sin motor de layout no hay geometría donde clicar |
| **`screenshot`** | ❌ **error explícito**: "no layout or paint engine" |

*Veredicto P2: la conexión CDP es limpia y las acciones de LECTURA (abrir, leer
texto/HTML, ejecutar JS, leer/poner cookies) funcionan perfectamente. Las
acciones VISUALES/INTERACTIVAS (screenshot, click por geometría, scroll,
type-en-campo-posicionado) NO — no es un límite de configuración, es la
arquitectura del motor.*

### P3 · ¿El modo stealth pasa donde Chrome headless es bloqueado? → **Promete para SCRAPING, pero no resuelve el problema real de Aithera** ⚠️

El binario preinstalado SÍ trae la "stealth build feature" (verificado en los
símbolos del binario): "Stealth mode enabled (TLS fingerprint impersonation +
tracker blocking)", una blocklist de trackers (las ~3.520 dominios que menciona
el README), impersonación de huella TLS (JA3/JA4), y `navigator.webdriver = false`
de fábrica (Chrome real bajo Playwright lo expone como `true` salvo parcheo).
Todo esto es exactamente lo pensado para el problema "Google bloquea el tráfico
headless" **cuando scrapeas páginas públicas**.

**PERO** — y es la distinción clave — el problema real de Aithera con Google NO
es parecer humano al scrapear: es **mantener la sesión del usuario ya
autenticada** (el trabajo del 2026-07-23: Chrome real con perfil persistente
para que el login de Google sobreviva). Stealth ataca el anti-bot; no te hace
estar logueado como el usuario. Y no se pudo reproducir en vivo el bloqueo real
de Google desde este entorno (IP no representativa, resultado sería poco fiable)
— así que esta respuesta es "verificado el mecanismo, honesto sobre el límite".

*Veredicto P3: buen stealth para scraping público; irrelevante para el caso de
uso autenticado que motivó el Chrome persistente.*

### P4 · ¿Qué pierde el usuario respecto al Chrome con perfil persistente actual? → **Casi todo lo que motivó el diseño del 2026-07-23** ❌

Esta es la pregunta que más pesa, y la respuesta es dura:

1. **No hay login interactivo posible.** Aithera hoy hace que el usuario inicie
   sesión en Google UNA vez en la ventana de Chrome real, y las cookies /
   consentimientos sobreviven en el perfil persistente. En un motor **sin UI
   visual y sin capturas**, el usuario NO puede hacer un flujo de login de
   Google (OAuth + 2FA) — no hay pantalla que ver ni botón que pulsar. Todo el
   diseño de "sesión de Google compartida entre misiones" es **imposible** sobre
   Obscura.
2. **Persiste cookies, pero no es un perfil de Chromium (`user-data-dir`).**
   Obscura sí guarda las cookies en `--storage-dir` como un `cookies.json` plano
   (se vuelca al cerrar el proceso — en la prueba apareció tras apagar el
   servidor, no mientras corría). Es un **jar de cookies**, útil para la pata de
   scraping, pero NO es un perfil de Chromium con sesión de Google, contraseñas
   guardadas ni el `consent_learned.json` que Aithera aprende — y sobre todo no
   habilita el login interactivo del punto 1.
3. **No hay capturas de pantalla.** Rompe `browser_tool.screenshot` y cualquier
   flujo de "mira lo que hay en pantalla" / OCR visual (`desktop_tool`).
4. **Clics por geometría poco fiables.** "Abre YouTube y pon la canción"
   (pulsar un botón de play, interactuar con una SPA visualmente) es justo el
   tipo de tarea que se rompe — el clic sobre `<a>` ya falló en la prueba.

*Veredicto P4: sustituir el Chrome persistente por Obscura sería un retroceso
grande en el caso de uso interactivo/autenticado. No es un intercambio, es una
pérdida.*

### P5 · Madurez / licencia / mantenimiento → **Muy popular pero muy joven; licencia OK** ⚠️

| Señal | Dato |
|---|---|
| Licencia | **Apache-2.0** ✅ (permisiva, se puede empaquetar/distribuir sin fricción) |
| Estrellas / forks | **19.8k ⭐ / 1.4k forks** — visibilidad altísima |
| Versión | **v0.1.10** — serie 0.1.x: temprana, API aún inestable, cambios rompientes probables |
| Commits / issues | 366 commits, 23 issues abiertas, PRs activos — desarrollo vivo |
| Edad | Emergió a inicios/mediados de 2026 (artículos de mayo 2026) — proyecto joven |
| Bus factor | Handle único `h4ckf0r0day` + serie 0.1.x sugieren propiedad concentrada; el nº exacto de contribuidores no se pudo verificar (API de GitHub limitada en el entorno) — **riesgo no descartado** |

*Veredicto P5: la licencia es ideal para bundlear. La madurez (0.1.x, joven,
posible bus factor de 1) desaconseja hacerlo dependencia NÚCLEO de un instalador
1.0, aunque sí es apto como componente OPCIONAL y aislado.*

---

## Detalle técnico útil para PU9 (si algún día se hace)

- Comandos del binario: `serve` (servidor CDP persistente, el que usaría
  Aithera), `fetch`, `scrape`, y **`mcp`** (¡servidor MCP nativo!). El subcomando
  `mcp` es interesante para el futuro MCP-first de Aithera: Obscura podría
  enchufarse como un MCP de scraping sin pasar por CDP.
- Puerto CDP por defecto `9222`; `serve --host 127.0.0.1 --workers N`.
- Límite de script de 30 s por defecto (`OBSCURA_SCRIPT_DEADLINE_MS`).
- Seguridad razonable de fábrica: bloquea `file://` (`--allow-file-access` para
  habilitarlo) y red privada/SSRF (`--allow-private-network`) — hay que tenerlo
  en cuenta si alguna misión necesita localhost.
- Soporta subida de ficheros y streaming de descargas por CDP
  (`DOM.setFileInputFiles`, `Fetch.takeResponseBodyAsStream`) — la pata de
  scraping es completa.

---

## Recomendación final y encaje honesto

**NO-GO para lo que el doc 35 planteaba** (Obscura como motor alternativo del
`browser_tool` vía `BROWSER_ENGINE=chrome|obscura`, con degradación graciosa).
Motivos, por orden de peso:

1. **Arquitectónicamente es la herramienta equivocada para el `browser_tool`**:
   sin layout/paint no hay capturas, ni clics interactivos fiables, ni tareas
   visuales — y eso es el 90% de para qué existe el `browser_tool`. El propio
   Obscura te manda usar Chromium real para eso.
2. **No resuelve el problema real de Google** (mantener la sesión autenticada
   del usuario), que es lo que motivó el Chrome persistente.
3. **No permite el login interactivo** ni tiene perfil de Chromium: cambiar a
   Obscura sería perder el trabajo del 2026-07-23, no mejorarlo.
4. **v0.1.x** es demasiado joven para ser dependencia núcleo de un instalador
   que va a 1.0.

**GO CONDICIONAL y ACOTADO, para más adelante (post-1.0, natural junto a
Hermes V1.1)**: Obscura encaja de verdad como **motor de LECTURA/scraping
OPCIONAL**, complementario (no sustituto) del Chrome real — para la pata
"tengo una URL (de `search`), léeme su texto/HTML sin lanzar un Chrome pesado".
Ahí sus ventajas son reales: 41 MB, Apache-2.0, arranque instantáneo, stealth
para páginas públicas, CDP nativo Y `mcp` nativo. La ficha en Conexiones, si
alguna vez se hace, NO debería llamarse "Navegador para agentes" (induce a
error: no es interactivo) sino algo como **"Motor de lectura web para agentes"**,
y dejar clarísimo que el Chrome real sigue siendo el navegador de verdad.

### Coste estimado de PU9 según el camino

- **PU9 tal como estaba planteado** (Obscura = motor del `browser_tool`):
  **no procede** — no es un drop-in del navegador interactivo. Construirlo sería
  gastar el patrón 1-click para entregar algo que rompe la mitad de las acciones.
- **PU9 acotado** (Obscura = backend de lectura/scraping opcional, post-1.0):
  **pequeño-medio**. La instalación 1-click es el patrón ya construido 3 veces
  (hilo con progreso + estados idle/installing/done/failed + degradación
  honesta). El trabajo real sería: (a) un nuevo camino en el flujo
  `search → leer página` que, si Obscura está instalado, use su `serve`+CDP para
  extraer el texto en vez de lanzar Chrome; (b) degradación a Chrome si no está.
  Es aditivo y aislado; nada del `browser_tool` interactivo cambia. **No
  bloqueante para 1.0; candidato claro para la ola de scraping/Hermes.**

### Alternativa al DESEO original del usuario (buscador local descargable)

El deseo original era un "buscador web local descargable 1-click". Obscura no lo
es (navega/scrapea, no indexa/busca). La opción que SÍ encaja con ese deseo es
**SearXNG** — un metabuscador self-hosted (agrega resultados de varios motores,
sin depender de una API key de Brave/SerpAPI). Nota honesta: SearXNG es
Docker/Python, más pesado que Obscura, y para un instalador 1-click de escritorio
tiene fricción — por eso queda como **ficha futura a evaluar post-1.0**, no ahora.
El `search_tool` actual (Brave + SerpAPI con fallback) cubre el deseo de "buscar"
sin dependencias locales; SearXNG solo tendría sentido si el usuario quiere
independencia total de APIs de terceros.

---

## Decisión tomada (2026-07-31)

**NO-GO para 1.0 confirmado por el usuario, y Obscura se añade con Hermes** como
backend de LECTURA/scraping opcional (no como navegador). No se hace PU9 en el
bloque de pulido; el encaje concreto queda plegado en el plan de Hermes
(`10_HERMES_INTEGRATION_RFC.md` §6b) para que ese sprint lo recoja: camino nuevo
en `search → leer página` con Obscura si está instalado (degradación a Chrome si
no), instalación 1-click con el patrón Ollama/Kokoro/Codex, y a decidir al
implementar si se enchufa por CDP o por su `mcp` nativo (coherente con el
`AitheraToolProvider`/MCP de la §7 de Hermes). El `browser_tool` interactivo con
Chrome real NO se toca — Obscura solo cubre la pata de leer texto.

---

*Creado: 2026-07-31 (PI-A, Fable 5). Fuentes: repo oficial
`h4ckf0r0day/obscura` (README + releases + assets del `v0.1.10`) y **ejecución
real del binario** con prueba de concepto de Playwright `connect_over_cdp` en el
entorno de trabajo. Artículos de contexto (mayo 2026): githubdaily/Medium,
ai-engineering-trend/Medium, aibit.im, the-agent-report.com.*
