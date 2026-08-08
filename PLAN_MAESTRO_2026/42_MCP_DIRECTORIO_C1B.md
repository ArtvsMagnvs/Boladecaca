# 42 — DIRECTORIO DE MCPs + /COMANDO + USO POR CONTEXTO (C1b)

> **Origen**: petición directa del usuario (2026-08-08), al arrancar C1:
> *"quiero que investigues cómo podemos añadir un repositorio de MCP
> disponibles de forma sencilla, de la misma forma que existe en Claude: una
> lista por tipos, con sus nombres, descripción para qué sirve cada uno y un
> botón de Conectar […] y que Aithera pueda utilizarlo de dos formas: por
> comando (/github) o por contexto (si pido la ruta naval de Barcelona a
> Mallorca y tengo el MCP de Nausika conectado, Aithera lo usa y elabora la
> respuesta con lo que Nausika devuelve)."*
>
> **Estado**: ✅ **EJECUTADA (2026-08-08, Opus)**. Lo que sigue es el diseño
> tal como se escribió; al final (§6) está el cierre con lo que cambió al
> implementarlo y lo que quedó pendiente de probar en vivo.

---

## 0. Qué dejó hecho C1 (la base sobre la que todo esto se monta)

- `app/mcp/`: conectar un servidor (stdio/SSE/HTTP-streamable) = una fila de
  config + secretos DPAPI; sus tools entran al ToolManager con gate SIEMPRE,
  permiso `mcp.use`, sandbox de argumentos y sanitización. Registro/baja EN
  CALIENTE. UI manual en Ajustes → Conexiones.
- Lo que C1b añade es EXCLUSIVAMENTE descubrimiento y enrutado: que el
  usuario no tenga que saber qué comando teclear, y que Aithera sepa CUÁNDO
  usar cada servidor. Cero superficie de seguridad nueva — todo lo que se
  conecta pasa por la puerta de C1.

---

## 1. Investigación — el ecosistema de registros (verificado en vivo, 2026-08-08)

**El registro OFICIAL (`registry.modelcontextprotocol.io`) es la fuente
correcta** y hace innecesario depender de agregadores comerciales:

- REST público SIN autenticación para lectura. Probado en vivo:
  `GET /v0/servers?search=github&limit=2` → 200 con resultados relevantes.
  Existe también `/v0.1/` (API freeze v0.1). Paginación por `nextCursor`.
- **La forma de cada entrada mapea 1:1 a nuestro `MCPServerConfig`**
  (verificado contra respuestas reales):
  - `name` (reverse-DNS: `com.pulsemcp/remote-filesystem`), `description`,
    `title`, `version`, `repository.url` (procedencia visible).
  - **stdio**: `packages[]` con `registryType: "npm"|"pypi"`,
    `identifier`, `runtimeHint: "npx"`, `runtimeArguments`, y
    `environmentVariables[]` con `name`/`description`/`isRequired`/
    `isSecret`/`default` — LITERALMENTE los campos del formulario de
    conexión, con sus textos de ayuda incluidos.
  - **remoto**: `remotes[]` con `type: "streamable-http"`, `url`, y
    `headers[]` con `isSecret`/`isRequired` — mapea a nuestro transporte
    `http` + headers cifrados (la desviación al alza de C1 de soportar
    streamable-http es lo que hace esto posible: la mayoría de entradas
    remotas del registro usan ese transporte, no SSE).
- Agregadores (Smithery, PulseMCP, mcp.so): útiles como inspiración de UI,
  pero muchos publican YA en el registro oficial (se vieron entradas
  `ai.smithery/*` con sus URLs). No añadir dependencia de ninguno.
- **Realidad del registro que obliga a un diseño en DOS niveles**: es
  comunitario y ENORME — para "github" devuelve docenas de servidores de
  terceros de calidad variable. Un usuario normal no puede elegir ahí. De
  ahí: catálogo CURADO primero, búsqueda del registro como segundo nivel.

---

## 2. Diseño — Pieza A: el directorio con botón «Conectar»

### Nivel 1 — Catálogo CURADO (lo que se ve al abrir)

`frontend/src/data/mcpCatalog.json` (patrón `skillsCatalog.json` de PU2:
estático, sin fetch en runtime, autosuficiencia local). ~20-30 servidores
estrella, por categorías: Desarrollo (GitHub, GitLab, Sentry), Productividad
(Notion, Linear, Slack, Todoist), Datos (Postgres, SQLite), Web (Fetch,
Firecrawl), Diseño (Figma), Pagos (Stripe), etc. Cada entrada:

```json
{
  "slug": "github",
  "category": "desarrollo",
  "title": "GitHub",
  "description_es": "Repositorios, issues, pull requests y commits de tus proyectos en GitHub.",
  "config": {"transport": "stdio", "command": "npx",
             "args": ["-y", "@modelcontextprotocol/server-github"]},
  "secrets": [{"env": "GITHUB_PERSONAL_ACCESS_TOKEN", "label": "Token personal de GitHub",
               "help_url": "https://github.com/settings/tokens", "required": true}],
  "context_hints": "repositorios de código, commits, issues, pull requests, GitHub"
}
```

UI (`McpPanel` gana la pestaña/sección "Directorio", grid de tarjetas por
categoría — mismo lenguaje visual que el resto de Ajustes): tarjeta con
título + descripción + botón **Conectar** → panel con los campos de secreto
YA descritos (con el enlace "¿dónde consigo el token?") y el comando VISIBLE
(nunca se oculta qué se va a ejecutar — es código externo, el usuario lo ve
antes de aceptar) → guardar = `POST /api/mcp/servers` (fontanería C1 intacta)
→ **Probar automático** al conectar (descubre las tools y muestra "N
herramientas disponibles"). Total: 1 clic + pegar un token.

### Nivel 2 — «¿No está en la lista?» — búsqueda del registro oficial

- Backend NUEVO: `GET /api/mcp/directory/search?q=` — proxy fino contra
  `registry.modelcontextprotocol.io/v0/servers?search=` (server-side: sin
  CORS, con caché de 15 min en memoria, timeout corto, fail-soft si no hay
  red). El mapeo entrada→`MCPServerConfig` es DETERMINISTA (código, no LLM):
  `packages[npm,runtimeHint=npx]` → stdio `npx -y <identifier>`;
  `remotes[streamable-http]` → http; `environmentVariables`/`headers` con
  `isSecret` → campos de secreto del formulario, con sus descripciones.
- Reglas de honestidad/seguridad en la UI de resultados: procedencia SIEMPRE
  visible (repo, editor del name reverse-DNS), badge "comunitario — revisa la
  fuente" para todo lo que no sea del publisher oficial del servicio, y el
  comando/URL exacto a la vista antes de conectar. Entradas sin package npm
  ni remote streamable-http → se muestran como "no conectable automáticamente"
  con el enlace al repo (nunca adivinar un comando).

---

## 3. Diseño — Pieza B: /comando (`/github …`)

Determinista, 0 LLM, resuelto ANTES del clasificador — en los MISMOS dos
puntos de precheck donde ya viven `quick_answers` (PU4) y `quick_memory`
(PU10): `orchestrator.handle_stream` y el pipeline del TIE (la lección de
PU4: el orquestador tiene su propio precheck previo, engancharse solo en el
TIE no basta).

- Parser: el mensaje empieza por `/<slug>` y `<slug>` es un servidor MCP
  conectado y habilitado → se retira el prefijo y el turno sigue su camino
  normal con **pin de tools**: `Intent.requires_tools` incluye SIEMPRE
  `mcp_<slug>` y el catálogo del toolloop lo antepone (cabecera "el usuario
  pidió explícitamente usar este servicio"). No salta el gate ni el permiso
  — `/github` expresa INTENCIÓN de herramienta, no autorización (la
  autorización sigue siendo del ApprovalGate/`mcp.use`, A3b intacta).
- `/github` a secas (sin texto) → respuesta determinista con las acciones
  del servidor (de la caché de tools de C1), sin LLM.
- `/algo` que no existe → mensaje honesto con los slugs conectados.
- Frontend: autocompletado al teclear "/" en el composer del chat (lista de
  `getMcpServers()` — ya existe el endpoint), mismo patrón visual que los
  chips de ejemplo del mini-chat de memoria.

---

## 4. Diseño — Pieza C: uso por CONTEXTO (el caso Nausika)

"Ruta naval de Barcelona a Mallorca" → Aithera usa `mcp_nausika` sin que
nadie escriba /nausika. Tres capas — una ya existe, dos son el trabajo real
de C1b:

1. **(YA, gratis desde C1)** El planner y el toolloop ven `mcp_nausika` en
   `tie_catalog()` con la descripción del servidor y la de CADA tool que el
   servidor declara — la selección semántica natural del modelo. Por eso el
   campo `description` de C1 se diseñó "para ti y para el modelo", y el
   catálogo curado trae `context_hints` buenos de fábrica.
2. **(EL GAP REAL, detectado al auditar C1)** `tie/intents.py`: la lista de
   `requires_tools` que el CLASIFICADOR puede asignar es un TECHO (hallazgo
   PU8 — lo que no está en su lista no llega al camino directo). Hoy esa
   lista es estática de tools nativas → **hay que inyectar dinámicamente los
   `mcp_*` conectados en el prompt del clasificador**, una línea por
   servidor: `mcp_nausika: navegación a vela/motor, rutas navales, mareas`.
   Sin esto, la petición de Nausika clasificaría hacia `search`/`browser`
   aunque el MCP esté conectado. Es un cambio pequeño y el corazón del
   enrutado por contexto.
3. `tie/capabilities_map.py` (R6): sección nueva "Servicios conectados
   (MCP)" generada del store — el chat sabe DECIR "puedo consultar tu MCP de
   Nausika" y lo ofrece cuando encaja.

El flujo Nausika completo queda: clasificador (capa 2) o planner (capa 1)
eligen `mcp_nausika` → gate/`mcp.use` (C1) → la tool del servidor calcula la
ruta → la observación vuelve saneada como `<datos>` → el responder del TIE
redacta la respuesta elaborada con los datos reales de Nausika — exactamente
"los procesos que ya hace Nausika" con la voz de Aithera.

---

## 5. Alcance de la sesión C1b (propuesta)

1. `mcpCatalog.json` curado (20-30 entradas verificadas contra el registro
   oficial/paquetes npm reales) + sección "Directorio" en `McpPanel` con
   Conectar 1-clic + Probar automático.
2. `GET /api/mcp/directory/search` (proxy + mapeo determinista + caché).
3. Parser `/comando` en los 2 prechecks + autocompletado del composer.
4. Inyección dinámica de `mcp_*` en el clasificador + sección MCP en
   `capabilities_map`.
5. Tests: mapeo registro→config con respuestas REALES grabadas (fixtures),
   parser /comando (positivos + los negativos de siempre), clasificador con
   un MCP fake conectado eligiéndolo por contexto, capabilities_map.
   Verificación en vivo: conectar GitHub desde el directorio y pedirle algo
   por contexto.

Fuera de alcance (dicho explícito): OAuth de servidores remotos (los que lo
exijan se conectan con token pegado; el flujo OAuth navegador es sesión
aparte si algún servidor clave lo necesita), y C2 (Aithera como SERVIDOR
MCP) que sigue siendo su propia sesión.

---

## 6. Cierre — qué se construyó de verdad (2026-08-08)

Lo entregado sigue el diseño de arriba punto por punto. Lo que MERECE
anotarse porque no estaba escrito o cambió al tocar el código real:

**Un hallazgo con consecuencia.** El mapa de capacidades (R6) mide 1449
caracteres de un tope de 1500. La línea de servicios MCP (~145) no cabía, y
la primera versión la RESERVABA dentro del presupuesto: verificado que eso
expulsaba en silencio la categoría "organizar tu trabajo" — el mismo modo de
fallo que PU8 documentó, esta vez causado por mí. Corregido a **aditiva**
(con tope propio de 400): lo que el usuario conecta se SUMA a lo que Aithera
ya sabía hacer, nunca lo sustituye. Un test lo fija comparando línea a línea
que el mapa base sobrevive intacto.

**El catálogo curado tiene 14 entradas, no 25** — y las 14 están
verificadas: cada paquete npm consultado contra `registry.npmjs.org` (existe
y no está deprecado) y cada URL remota probada con un `initialize` real (las
5 responden 401 = viven y piden credenciales). Se descartaron a propósito
`server-github`, `server-slack`, `server-postgres` y `server-brave-search`
oficiales (DEPRECADOS en npm) y los `filesystem`/`memory` oficiales (Aithera
ya tiene los suyos; duplicarlos confunde al planificador). Catorce entradas
que funcionan valen más que veinticinco a medias.

**El `/comando` no autoriza, y hay un test que lo dice.** Fija QUÉ
herramienta usar; `mcp.use` y el ApprovalGate siguen exactamente igual. El
pin además SUBE el intent a EXECUTE si quedó en camino corto — sin eso, el
comando se aceptaría y el servicio no se usaría (el camino corto no tiene
herramientas).

**Cableado, no solo lógica.** Dos veces en este proyecto (S9b, S9c) la
lógica era correcta y estaba desconectada; aquí hay un test que ejercita
`tie.handle_stream` REAL y comprueba que el prefijo se retira antes de
clasificar. Su mutación (desconectar el parseo del pipeline) lo tumba.

**Invalidación de caché.** El mapa de capacidades cachea 1 hora: sin
invalidar, conectar GitHub y preguntar "¿qué sabes hacer?" no lo mencionaría
hasta una hora después. Los endpoints de alta/baja tiran las dos cachés.

**Tests**: `test_mcp_directorio.py` (24) — mapeo con respuestas REALES del
registro grabadas como fixture (npm+npx, remoto streamable-http, pypi sin
`runtimeHint`, y una entrada solo-Docker que se marca no conectable con
motivo), el atajo con sus negativos, y el enrutado por contexto con el
clasificador real. **5 mutaciones** confirmadas y restauradas byte a byte.
Regresión: 270 passed + 4 xfailed en el subconjunto TIE/orquestador/MCP (el
único fallo, `test_action_intent.py::test_el_detector_cubre_todas_las_
acciones_del_catalogo`, es PREEXISTENTE y ajeno — sus archivos están
intactos en este árbol, ya venía documentado del cierre de LC3).

**Pendiente de probar en vivo** (nada de esto es verificable sin la app
corriendo): conectar GitHub desde el directorio con un token real y ver sus
herramientas; escribir `/` en el chat y ver el autocompletado; y el caso
Nausika de verdad — un servicio de dominio conectado y una pregunta de ese
dominio SIN nombrarlo, para confirmar que el clasificador lo elige.

---

## 7. C1c — «Autorizar» sin tokens + pestaña propia (2026-08-08)

Petición del usuario al ver C1b, con capturas de cómo lo hace Claude: *"que
se puedan conectar múltiples MCP de forma directa, con redirección a la url
que toca, con el authorize directo en la web del producto sin tantas
complejidades de buscar tokens"*, más sacar MCP de «Conexiones» a su propia
pestaña entre IA y Permisos, buscador arriba, y descripciones que entienda
alguien que no sabe qué es ese MCP.

**El login de un clic — `app/mcp/oauth.py`.** No se reimplementa el
protocolo: el SDK oficial ya trae el baile completo (descubrimiento del
recurso protegido RFC 9728 → metadatos del servidor de autorización RFC 8414
→ **registro dinámico de cliente** RFC 7591, que es lo que evita tener que
dar de alta una app en cada servicio → PKCE → intercambio → refresco). Lo
que se aporta son las tres piezas que el SDK deja abiertas porque dependen
de dónde corre el cliente: **dónde se guardan** los tokens (cifrados con
DPAPI en la tabla Config, como el resto de secretos), **cómo se abre el
navegador** (el SDK asume una CLI; aquí se CAPTURA la URL y la abre el
frontend) y **cómo vuelve el código** (el `redirect_uri` es un endpoint de
la propia API). El puente entre las dos últimas es un `asyncio.Event` por
flujo — no un `Future`, que se ata a un event loop al construirse y aquí el
arranque y la espera son dos peticiones HTTP distintas.

**Verificado EN VIVO contra los servicios reales**: se probó el flujo
completo (sin autorizar nada — eso es del usuario) contra 23 servidores
remotos. **16 devolvieron una URL de «Authorize» de su propio dominio**:
Linear, Notion, Asana, Atlassian, Intercom, Sentry, Vercel, Netlify, Neon,
Stripe, PayPal, Square, Canva, Webflow, Wix y Zapier. **GitHub NO**: su
servidor no admite registro dinámico (404 en el `registration_endpoint`), así
que se queda con token — y el catálogo lo dice con esas palabras en vez de
fingir que se puede. Box, Monday, Prisma, Cloudflare-docs y Globalping
tampoco completaron el descubrimiento y quedan fuera del catálogo.

**Catálogo a 27 entradas**, todas verificadas: las 16 de OAuth por el flujo
real de arriba, y los paquetes npm contra `registry.npmjs.org`. Cada entrada
declara `auth: oauth | token | none`, y la UI lo enseña como una etiqueta
("1 clic" / "pide clave" / "sin cuenta") para que se sepa antes de pulsar.
Las descripciones se reescribieron para alguien que no sabe qué es ese
servicio ("el sitio donde aterrizan los errores de tus aplicaciones cuando
fallan en producción" en vez de "Sentry MCP server").

**La pestaña.** «Servicios» sale de Conexiones y se coloca entre «IA y
Modelos» y «Permisos». De arriba abajo: qué es esto en dos frases sin jerga
→ **el buscador** (filtra el catálogo al teclear y, si no encuentra,
consulta el registro público) → lo que ya tienes conectado → el catálogo por
categorías. El alta manual queda al final, para un servidor propio.

Tests: `test_mcp_oauth.py` (18 — el token cifrado en reposo y que la API no
lo devuelve, el puente navegador↔callback llamando al handler REAL del SDK,
un `state` desconocido que se rechaza, dos flujos concurrentes sin mezclarse,
la autorización que se va al borrar el servidor, que solo `auth="oauth"`
arma el flujo, y la coherencia del catálogo — 27 entradas, cada tipo de auth
declarando lo suyo, descripciones de verdad). **3 mutaciones** confirmadas y
restauradas byte a byte. Regresión: 123 passed + 4 xfailed; `tsc` limpio y
`vite build` completo; +19 claves i18n ×4 (paridad 1429).

**Pendiente en vivo**: pulsar «Conectar» en Notion o Linear y completar el
«Authorize» de verdad en el navegador — el descubrimiento y la URL están
probados contra los servidores reales, pero el viaje de vuelta (callback →
token → herramientas descubiertas) solo se cierra con una cuenta real.
