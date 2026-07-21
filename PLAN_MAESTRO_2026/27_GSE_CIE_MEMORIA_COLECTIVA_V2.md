# 27 — GLOBAL SKILL ENGINE + COLLECTIVE INTELLIGENCE ENGINE
## Aithera Fase 2.0+ · El salto de memoria personal a inteligencia colectiva

> **Estado**: DISEÑO MAESTRO (V2.0+, aún no en desarrollo). Extiende y da cuerpo
> a las reservas RFC-003/004/005 del `08_MOS_ARQUITECTURA_COMPLETA.md`.
> **Origen**: petición del usuario (2026-07-20) — diseñar la memoria colectiva
> mundial de Aithera desde cero, con investigación del estado del arte y
> libertad para innovar más allá de lo que existe.
> **Redactado como comité**: CTO (25 años), Principal Architect, experto en
> IA/multiagente, experto en sistemas de memoria globales, ingeniero de memorias
> compartidas con IA, Staff de rendimiento, especialista UX, experto en
> ciberseguridad, experto en ciberseguridad contra IA avanzada, e inversor VC.

---

## 0. RESUMEN EJECUTIVO (para leer en 2 minutos)

Aithera hoy es un asistente **personal**: cada instalación aprende de SU usuario
(el MOS — Memory Operating System — con sus 5 capas de memoria y el Local
Learning Loop). Este documento diseña el siguiente salto: que **millones de
instancias de Aithera en el mundo aprendan las unas de las otras sin que ningún
dato personal salga jamás de ningún ordenador**.

Se construye sobre dos motores nuevos, ya reservados en la arquitectura del MOS:

- **GSE — Global Skill Engine** (RFC-004): la red mundial de conocimiento
  TÉCNICO reutilizable. Skills, workflows y patrones versionados que cualquier
  Aithera puede publicar, descubrir y adoptar. **Nunca** contiene conversaciones,
  emails ni nada identificable — solo el "cómo se hace" destilado, anonimizado.
- **CIE — Collective Intelligence Engine** (RFC-005): el cerebro que observa la
  red entera, detecta que miles de instancias resuelven lo mismo de formas
  distintas, y **sintetiza conocimiento nuevo que ninguna instancia tenía**.
  No almacena: analiza y propone. Los Guardians validan; las instancias adoptan.

**La tesis central, y lo que lo hace distinto de todo lo que existe**: no se
comparte *información*, se comparte *capacidad probada*. El valor de una skill en
la red no lo decide cuánta gente la tiene (eso se falsifica), sino **cuánto
mejora los resultados reales medidos** de quien la usa (eso no se falsifica). Es
una memoria colectiva basada en **prueba-de-utilidad**, no en votos ni en
popularidad.

**Recomendación de infraestructura (§7)**: topología **federada híbrida** — un
servicio de coordinación fino y barato (el "Nexus") que NUNCA ve datos crudos,
más los nodos Aithera que guardan todo lo privado en local. Empieza con un VPS
de 5-20 €/mes + almacenamiento content-addressed (Cloudflare R2). Escala a
millones sin rediseño porque el contenido es inmutable, firmado y cacheable en
CDN.

**Veredicto del comité (§13)**: técnicamente factible por fases, con un foso
defensivo real (efecto red + datos de utilidad imposibles de falsificar) y un
riesgo dominante claro (envenenamiento de la memoria colectiva por IA
adversaria) que el diseño ataca en 5 capas. Recomendación: construir, pero
**solo después de que el LLL/LSL local (V1.1) esté maduro** — la red amplifica
lo local, y amplificar algo inmaduro es amplificar ruido.

---

## 1. INVESTIGACIÓN DEL ESTADO DEL ARTE (lo que ya existe, y por qué no basta)

Se revisaron los papers más relevantes de 2025-2026. Resumen honesto de qué
aportan y dónde se quedan cortos para el caso de Aithera.

### 1.1 Memoria compartida multi-usuario en agentes LLM
**"Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic
Access Control"** (arXiv 2505.18279, 2025). Propone dos niveles de memoria —
privada (visible solo a su originador) y compartida (fragmentos selectivamente
compartidos) — con control de acceso dinámico, adherencia demostrable a
políticas asimétricas y variables en el tiempo, y auditabilidad total de las
operaciones de memoria.
→ **Qué tomamos**: el modelo de dos niveles y la auditabilidad total. La idea de
políticas de acceso demostrables.
→ **Dónde se queda corto**: comparte *fragmentos de memoria* (que pueden
contener datos), asume un almacén compartido central, y no resuelve el problema
adversario a escala mundial abierta. Nosotros compartimos **skills destiladas**,
no fragmentos, y la topología es federada, no central.

### 1.2 Memoria en sistemas multi-agente e inteligencia colectiva
**"Memory in LLM-based Multi-agent Systems: Mechanisms, Challenges, and
Collective Intelligence"** (survey, 2025). Formaliza la transición de la
cognición individual a la colectiva: la memoria compartida convierte el
conocimiento individual en una base de conocimiento de equipo, permitiendo lograr
juntos lo que ninguno lograría solo ("lifelong team learning", "hive mind" que
trasciende las instancias individuales).
→ **Qué tomamos**: el marco conceptual del "aprendizaje de equipo de por vida" y
la meta de que la red produzca conocimiento emergente. Es exactamente el CIE.
→ **Dónde se queda corto**: es un survey de sistemas cerrados (un equipo de
agentes coordinados), no una red abierta de millones de asistentes de personas
distintas que no se conocen ni se fían entre sí.

### 1.3 Aprendizaje federado y destilación de conocimiento con privacidad
**Federated Distillation / PrivateKT / Selective Knowledge Sharing** (Nature
Communications 2023-2024; surveys arXiv 2024-2025). El paradigma clave: en vez de
mover datos crudos a un servidor central, se transfiere **conocimiento** (no
parámetros ni datos). La privacidad diferencial inyecta ruido estadístico en las
contribuciones; el consenso por mayoría genera pseudo-etiquetas sin exponer los
datos de origen.
→ **Qué tomamos**: EL principio rector — *knowledge, not data, flows*. La
privacidad diferencial en el borde. El consenso como mecanismo de agregación.
→ **Dónde innovamos**: el consenso por mayoría es falsificable (crea 1000
instancias falsas y ganas la votación). Nosotros sustituimos "mayoría" por
"utilidad medida" (§4.3, prueba-de-utilidad).

### 1.4 Sincronización distribuida sin autoridad central
**CRDTs (Conflict-free Replicated Data Types) + vector clocks**. Estructuras de
datos que convergen a un estado consistente entre réplicas sin bloqueo ni
coordinación central ("strong eventual consistency"). Usadas en producción por
Redis, Riak, SoundCloud, Facebook a escala de decenas de millones de usuarios.
Las basadas en operaciones necesitan "reliable causal broadcast" (infraestructura
no trivial); las basadas en estado son más simples de desplegar.
→ **Qué tomamos**: convergencia sin autoridad central. Vector clocks para rastrear
causalidad (¡el contrato `LocalSkill` YA tiene `derived_from`/`superseded_by`!).
→ **Dónde innovamos**: un **CRDT semántico** cuyo merge no es "el último gana"
sino "la evidencia más fuerte gana" (§4.4). Es un CRDT específico del dominio.

### 1.5 El vector de ataque dominante: envenenamiento de memoria colectiva
**Memory Poisoning / MINJA / PoisonedRAG / Confundo / Cordon-MAS / SMSR**
(arXiv 2025-2026). Hallazgo demoledor: la memoria persistente COMPARTIDA es una
vulnerabilidad crítica. MINJA logra >95% de éxito inyectando instrucciones
maliciosas solo con consultas. PoisonedRAG dirige las respuestas inyectando
pocos textos. Confundo genera veneno que sobrevive al preprocesado, reranking y
paráfrasis. **Y lo más importante: las defensas basadas en detección (un
clasificador que filtra el veneno) son frágiles frente a un atacante adaptativo
que optimiza el veneno para evadir al detector.** Las líneas que sí funcionan:
control de flujo de información (Cordon-MAS), defensas certificadas (SMSR),
procedencia obligatoria.
→ **Consecuencia de diseño**: NO confiamos en un detector. La seguridad es
multicapa, con procedencia criptográfica, prueba-de-utilidad (el veneno no puede
falsificar buenos resultados reales), quórum de Guardians independientes,
cuarentena con instancias "canario", y control de flujo por construcción (§8).

**Conclusión de la investigación**: el estado del arte tiene todas las piezas
sueltas (dos niveles de memoria, destilación federada, privacidad diferencial,
CRDTs, defensas contra veneno) pero **nadie las ha combinado para una red abierta
y mundial de asistentes personales**. Eso es lo que se diseña aquí, y es
genuinamente nuevo.

---

## 2. LOS TRES PRINCIPIOS INVIOLABLES

Todo lo que sigue se subordina a estos tres principios. Si algo los contradice,
está mal diseñado.

1. **Autosuficiencia (P05 del MOS)**: Aithera sin red es un asistente completo.
   La red solo AMPLIFICA. Jamás es prerrequisito. Si el Nexus mundial cae, cada
   Aithera sigue funcionando al 100% para su usuario. Esto no es solo robustez:
   es la garantía de que el usuario nunca es rehén de la red.

2. **Knowledge, not data (privacidad por topología, no por promesa)**: lo único
   que sale de un ordenador hacia la red es una `PortableSkill` — una capacidad
   técnica destilada, sin una sola letra de contenido personal. No es una política
   que se pueda saltar: es topología. El módulo de red (`app/network/`) NO tiene
   ningún símbolo importable que devuelva contenido de `mem_personal`. Aunque el
   código de red fuera malicioso, no podría filtrar datos privados porque no
   existe la función que se los daría.

3. **La red propone, el usuario decide, la utilidad manda**: el CIE nunca impone.
   Propone skills; los Guardians validan que no sean veneno; el usuario final
   decide si su Aithera las adopta (y con qué autonomía). Y el ranking de todo lo
   colectivo se decide por utilidad medida, no por votos ni por antigüedad ni por
   quién lo publicó.

---

## 3. ARQUITECTURA GENERAL — LOS CINCO ANILLOS

```
┌──────────────────────────────────────────────────────────────────────┐
│  ANILLO 5 — CIE (Collective Intelligence Engine)                       │
│  Observa la red entera. Detecta patrones. SINTETIZA skills nuevas.     │
│  No almacena. Propone. (El "sueño colectivo", §5)                      │
├──────────────────────────────────────────────────────────────────────┤
│  ANILLO 4 — Guardians (RFC-003)  ·  sistema inmune de la red           │
│  Validan cada contribución: veneno, duplicados, fugas, contradicciones.│
│  N independientes por aprobación. No trabajan para ningún usuario.     │
├──────────────────────────────────────────────────────────────────────┤
│  ANILLO 3 — GSN (Global Skill Network)  ·  el substrato compartido     │
│  Registro firmado + almacén content-addressed de PortableSkills.       │
│  Inmutable, verificable, cacheable. El "Nexus" lo coordina (§7).       │
├──────────────────────────────────────────────────────────────────────┤
│  ANILLO 2 — GSE (Global Skill Engine)  ·  el motor LOCAL de cada nodo  │
│  Publica/descubre/adopta skills. Traduce entre LocalSkill y            │
│  PortableSkill. Firma con la clave del nodo. Aplica DP en el borde.    │
├──────────────────────────────────────────────────────────────────────┤
│  ANILLO 1 — MOS + LSL/LLL (lo que YA existe, V0.85→V1.1)               │
│  La memoria personal de 5 capas. El aprendizaje local. Intocable:      │
│  la red se conecta AQUÍ por una sola puerta (ISkillStore.export).      │
└──────────────────────────────────────────────────────────────────────┘

         Private Memory (mem_personal, mem_conversational)
                    ▲  NUNCA cruza hacia arriba
         ═══════════╪═══════════ FRONTERA DE PRIVACIDAD (topológica) ═══════
                    │  solo PortableSkill firmada + DP-noised cruza
                    ▼
         GSE → GSN → Guardians → CIE
```

**Nomenclatura (para zanjar la ambigüedad GSE vs GSN)**:
- **GSN** = Global Skill *Network*: el substrato de datos compartido (el
  registro + el almacén). Es "la red" como sustantivo pasivo.
- **GSE** = Global Skill *Engine*: el motor local en cada Aithera que HABLA con
  la GSN. Es "el motor" como sujeto activo. Uno por instalación.
- El usuario los usó como sinónimos; aquí se separan porque son cosas distintas:
  la red (compartida, una) y el motor (local, uno por nodo).

### 3.1 Direccionalidad de imports (la frontera de privacidad, hecha código)

Regla dura, heredada del RFC-001 y ampliada:

```
app/memory/        ← Private Memory. NO importa nada de app/network/
app/network/       ← GSE, cliente GSN, Guardians. Importa SOLO:
                       - ISkillStore.export_anonymized() → PortableSkill
                       - Los contratos públicos (PortableSkill, SkillProof…)
                     NUNCA importa mem_personal, chat_service, email_tool…
```

Un test de fronteras (`test_network_boundaries.py`, extensión del
`test_module_boundaries.py` que ya existe) lo vigila: si alguien en `app/network/`
importa un símbolo que da acceso a datos personales, el test falla en CI. La
privacidad no depende de que nadie se equivoque; depende de que el compilador y
los tests lo impidan.

---

## 4. GSE + GSN — EL MOTOR DE SKILLS GLOBALES (RFC-004, desarrollado)

### 4.1 Qué viaja: `PortableSkill` (el único tipo que cruza la frontera)

```python
@dataclass(frozen=True)
class PortableSkill:
    # — identidad content-addressed —
    cid: str                    # SHA-256 del contenido canónico. ES el id. Inmutable.
    name: str                   # legible, no único (varias versiones comparten name)
    version: str                # semver "1.4.2"

    # — el conocimiento (runtime-agnóstico, sin datos personales) —
    definition: dict            # prompt/workflow/patrón. Validado sin texto libre personal.
    capability: str             # ∈ MEL_CAPABILITIES (chat/classify/reason/code/…)
    domain: list[str]           # ["email","calendar","code",…] — para descubrimiento

    # — linaje (los vector clocks del CRDT semántico) —
    derived_from: list[str]     # cids de skills origen (fusión/especialización)
    supersedes: Optional[str]   # cid de la versión que reemplaza
    author_pubkey: str          # clave pública Ed25519 del nodo que la publicó (pseudónimo)

    # — evidencia (lo que decide su ranking, §4.3) —
    proof: "SkillProof"         # utilidad medida, DP-noised, k-anonimizada

    # — procedencia y firma (seguridad, §8) —
    signature: str              # firma Ed25519 del autor sobre (cid + proof_hash)
    published_at: str           # ISO-8601 UTC
    status: str                 # proposed | quarantined | published | deprecated | archived
```

**Regla de oro del `PrivacyFilter`**: `definition` se valida contra un esquema
que PROHÍBE texto libre potencialmente personal. Una skill de email dice "usa la
plantilla de agradecimiento formal cuando el remitente sea un cliente
recurrente", nunca "responde a juan@empresa.com que sí a la reunión del martes".
El filtro es parte del contrato de export, no un paso opcional (RFC-001).

### 4.2 `SkillProof` — la evidencia (privacidad diferencial en el borde)

Lo verdaderamente novedoso: una skill no viaja con datos, viaja con la **prueba
estadística y anonimizada de que funciona**.

```python
@dataclass(frozen=True)
class SkillProof:
    sample_size: int            # nº de ejecuciones que respaldan la prueba (k-anon: ≥ k)
    success_rate: float         # ratio de éxito medido (validación por nodo, doc 14 §3.4.7)
    outcome_delta: float        # mejora medida vs no usar la skill (estimado-vs-real, WPMS)
    dp_epsilon: float           # presupuesto de privacidad diferencial aplicado al agregado
    contexts: list[str]         # etiquetas de contexto anonimizadas (no contenido)
    measured_over_days: int
```

- La prueba se calcula **en local**, a partir de la telemetría que el Learner
  (doc 15) YA recoge: estimado-vs-real, tasa de éxito, bloqueos. El nodo aplica
  **ruido de privacidad diferencial** (`dp_epsilon`) al agregado ANTES de que
  salga, y solo publica si `sample_size ≥ k` (k-anonimato: nunca una prueba
  basada en una sola ejecución, que podría ser identificable).
- Nada de la prueba permite reconstruir una interacción concreta. Es
  estadística agregada y ruidosa por diseño.

### 4.3 Consenso por PRUEBA-DE-UTILIDAD (la innovación central)

**El problema del estado del arte**: si el ranking colectivo se decide por
mayoría/popularidad, un atacante crea 10.000 instancias falsas (ataque Sybil) y
promociona su skill-veneno. Los votos son gratis de falsificar.

**Nuestra solución**: el ranking de una skill lo decide su `outcome_delta`
agregado sobre la red — **la mejora real medida en los resultados de quien la
usa**. Y eso NO es gratis de falsificar: para simular buenos resultados reales,
un atacante tendría que ejecutar misiones reales que de verdad salgan bien, lo
cual... es contribuir de verdad. La utilidad es un trabajo honesto por
construcción.

```
ranking(skill) = f(
    outcome_delta_agregado,     # peso dominante: ¿mejora los resultados de VERDAD?
    diversidad_de_contextos,    # ¿funciona en muchos contextos o solo en uno?
    reputación_del_publicador,  # §4.5, ponderada, nunca dominante
    antigüedad_validada,        # tiempo en PUBLISHED sin ser refutada
    penalización_por_refutación # si otros nodos miden que EMPEORA, cae rápido
)
```

Un nodo que adopta una skill y mide que le va PEOR contribuye una refutación
(también DP-noised). Suficientes refutaciones independientes → la skill baja de
ranking o pasa a `deprecated`. **La red se autocorrige por evidencia, no por
moderación manual.**

### 4.4 CRDT semántico — convergencia sin autoridad central

Las skills evolucionan en muchos nodos a la vez. Cuando dos nodos publican
versiones divergentes de la misma skill (mismo `name`, linaje que se bifurca), la
red debe converger sin un árbitro central. Los CRDTs clásicos resuelven "el
último escritor gana" o uniones de conjuntos; ninguno sirve para conocimiento
(la versión más nueva no es necesariamente la mejor).

**Innovación — merge por evidencia dominante**:
```
merge(skill_A, skill_B):
    si A.supersedes == B.cid → A gana (linaje explícito)
    si no, comparar A.proof.outcome_delta vs B.proof.outcome_delta:
        si uno domina claramente (Δ > umbral con sus intervalos de confianza) → gana
        si empatan estadísticamente → se conservan AMBAS como branches A/B,
            y la red las prueba en paralelo (los nodos adoptan una u otra y
            miden); el branch perdedor pasa a deprecated cuando la evidencia
            se separe.
```

Esto converge (strong eventual consistency) porque el orden de aplicación de
merges no cambia el resultado: el ganador es una función de la evidencia, no del
orden de llegada. Los `derived_from`/`supersedes` son los vector clocks que
rastrean la causalidad. **Es un CRDT específico del dominio del conocimiento —
no existe en la literatura, y es correcto por la misma razón que los CRDTs
clásicos: la operación de merge es conmutativa, asociativa e idempotente sobre
la evidencia.**

### 4.5 Reputación como utilidad acumulada (no como stake ni PoW)

Cada nodo (identificado por su clave pública pseudónima) acumula reputación
cuando las skills que publica resultan útiles PARA OTROS (medido). No hay
criptomoneda, no hay proof-of-work (derroche energético), no hay stake
(plutocracia). La reputación es **utilidad histórica probada**, y solo pondera
—nunca domina— el ranking y el peso del voto Guardian. Un nodo nuevo empieza con
reputación neutra y la gana contribuyendo cosas que funcionan.

### 4.6 Ciclo de vida de una skill en la red

```
LOCAL (LSL)  →  el LLL destila una skill que funciona para el usuario
     │  el usuario (o su política de autonomía) autoriza compartirla
     ▼
PROPOSED     →  GSE la convierte a PortableSkill (PrivacyFilter + DP + firma)
     │           y la publica en la GSN
     ▼
QUARANTINED  →  entra en cuarentena: instancias "canario" voluntarias la
     │           ejecutan en sandbox y miden; los Guardians la analizan
     ▼  (quórum de N Guardians independientes + sin refutaciones canario)
PUBLISHED    →  visible y adoptable por toda la red. Rankeada por utilidad.
     │
     ▼  (refutaciones acumuladas, o versión mejor la supersede)
DEPRECATED   →  sigue existiendo (linaje) pero no se recomienda
     ▼
ARCHIVED     →  fuera del índice activo, nunca borrada (auditoría e historia)
```

Nada se borra jamás (auditabilidad total, del paper 1.1). El "olvido" es salir
del índice activo, no la destrucción.

---

## 5. CIE — COLLECTIVE INTELLIGENCE ENGINE (RFC-005, desarrollado)

El CIE es lo que separa una "biblioteca compartida de skills" (útil pero
mundano) de una **inteligencia colectiva** (nuevo). No almacena; observa y
sintetiza.

### 5.1 Los tres modos del CIE

**Modo 1 — Convergencia (detección de lo mismo resuelto distinto)**
El CIE detecta clusters de skills que atacan el mismo problema con enfoques
distintos (p.ej. 40.000 instancias resuelven "resumir un hilo de email largo" de
9 formas). Compara estadísticamente sus `outcome_delta`. Si una domina, la
promociona como recomendación. Si varias empatan por contexto, las etiqueta como
"mejor según contexto X/Y". Esto es agregación inteligente — potente, pero aún
no emergente.

**Modo 2 — Síntesis (el "Sueño Colectivo" — la idea genuinamente nueva)**
Periódicamente y offline, el CIE toma clusters de skills relacionadas de muchos
nodos y **sintetiza una skill de orden superior que ninguna instancia tenía**.
Ejemplo: 12.000 nodos tienen skills sueltas para "detectar reunión en un email",
"comprobar conflictos de calendario" y "redactar propuesta de reagendado"; el CIE
las compone en una skill nueva "gestión autónoma de reagendado de reuniones" que
nadie había ensamblado, la marca `PROPOSED`, y la manda a cuarentena para que
Guardians y canarios la validen. **La red produce conocimiento que ningún nodo
creó.** Esto es inteligencia colectiva real, no un caché compartido. Es el
equivalente a que un equipo de investigación descubra algo que ningún miembro
sabía por separado.

**Modo 3 — Anticipación (patrones emergentes)**
El CIE detecta tendencias en el agregado anonimizado (p.ej. "en las últimas 2
semanas, 200.000 nodos empezaron a fallar en la misma tarea" → probablemente una
API externa cambió). Propone una skill de mitigación antes de que el problema se
generalice. Es el sistema nervioso de la red avisando de un cambio en el mundo.

### 5.2 El CIE nunca decide

Regla dura: el CIE **propone**, los Guardians **validan**, las instancias
**adoptan** (según su política de autonomía del usuario). El CIE no tiene
autoridad para insertar nada directamente en ningún nodo. Su salida siempre es
un `PROPOSED` que pasa por cuarentena. Esto es lo que impide que el CIE —el
componente más potente— sea también el punto único de fallo o de captura.

### 5.3 El CIE es el LLL a escala de red

Punto de elegancia arquitectónica: el CIE usa **los mismos algoritmos** que el
Local Learning Loop (doc 09/15) que ya corre en cada Aithera para aprender de su
usuario. El LLL detecta tareas repetidas y destila una skill local; el CIE
detecta tareas repetidas EN LA RED y destila una skill global. Mismo motor,
distinta escala de entrada. Esto significa que gran parte del CIE ya estará
escrita y probada (como LLL) antes de que empiece la V2.0 — se reutiliza, no se
reinventa.

---

## 6. CÓMO CONECTA CON AITHERA — TODOS LOS COMPONENTES

La regla es que la red se enchufa por **una sola puerta** y no toca nada más.
Aquí, componente por componente, qué cambia (poco) y qué no cambia (casi todo).

| Componente Aithera | Cómo conecta con GSE/CIE | Qué cambia |
|---|---|---|
| **MOS · ISkillStore** | La ÚNICA puerta. Gana `export_anonymized()` → PortableSkill y `import_skill(PortableSkill)`. | Método nuevo con default; contrato congelado se extiende, no se rompe. |
| **MOS · Private Memory** | NO conecta. Aislamiento topológico (§3.1). | Nada. Ni un símbolo importable. |
| **LSL/LLL (doc 09/15)** | Origen de las skills que se publican y destino de las que se adoptan. El LLL local y el CIE global comparten algoritmos. | El LLL gana un hook "esta skill es candidata a publicar" (opt-in del usuario). |
| **TIE (Task Intelligence Engine)** | Al planificar, el `router`/`enricher` puede consultar la GSN por una skill publicada para el objetivo, además de las locales. | El planner gana una fuente más de skills; la elección sigue siendo por utilidad. |
| **MEL (Model Execution Layer)** | Las skills son runtime/modelo-agnósticas (`capability`, no nombre de modelo). El MEL las ejecuta igual que una skill local. | Nada: una skill importada es una skill. |
| **Automation Engine** | Una skill global puede convertirse en una automatización local (con la política de permisos del usuario). | El AE gana skills globales como fuente de acciones. |
| **ApprovalGate / Permisos (A3b)** | Nuevo permiso `network.publish` y `network.adopt` en el catálogo (fail-closed: por defecto NO se publica ni se adopta sin permiso). | +2 permisos, grupo "Red colectiva". Frontend ya renderiza grupos dinámicos. |
| **Gateway multi-canal** | Sin cambios. La red no es un canal de mensajes; es una fuente de conocimiento. | Nada. |
| **Guardians** | Corren como `GuardianRuntime(AgentRuntime)` — reutilizan el contrato de runtime de doc 10, con un MemoryRouter capado (solo GSN/CIE). | Runtime nuevo, contrato existente. |
| **UI (Hub/Settings)** | Panel "Red colectiva": on/off, qué se comparte, skills adoptadas, "lo que la red te ha enseñado" (con undo, como el perfil). | Sección nueva en Ajustes; tarjeta opcional en el Hub. |

**El punto clave de la conexión**: para el 100% del código existente de Aithera,
una skill de la red es indistinguible de una skill local. La red no introduce un
concepto nuevo en el corazón del sistema; introduce una **fuente nueva** de un
concepto que ya existe (skills). Por eso el acoplamiento es mínimo y el riesgo de
regresión es bajo.

---

## 7. INFRAESTRUCTURA — CÓMO CONECTAR EL MUNDO (la pregunta del usuario)

El usuario preguntó explícitamente: VPS / web / servidor dedicado / otros —
propón y recomienda. Aquí el análisis completo, como CTO.

### 7.1 Las tres topologías posibles

**Opción A — Servidor central en la nube** (un VPS/servicio gestionado que
guarda todo).
- ✅ Simplísimo de construir y operar.
- ❌ Punto único de confianza: TÚ hospedas el conocimiento de todos → responsable
  legal, objetivo de ataque, y contradice el principio de privacidad (aunque
  solo guardes skills, centralizas). ❌ El coste crece linealmente con usuarios.
  ❌ Si cae, la red entera cae (aunque los nodos sigan por autosuficiencia).
- **Veredicto**: NO. Centralizar mata la tesis de privacidad y crea un pasivo.

**Opción B — Pura P2P** (libp2p/DHT, sin ningún servidor).
- ✅ Cero coste de servidor, máxima descentralización, sin punto único.
- ❌ NAT traversal, descubrimiento de nodos, disponibilidad (los ordenadores
  personales se apagan), y coordinación del quórum de Guardians son *muy* duros.
  ❌ UX mala: si los nodos que tienen la skill que necesitas están offline, no la
  obtienes. ❌ Para un dev en solitario, operar esto bien es prohibitivo.
- **Veredicto**: NO al principio. Es el ideal teórico pero el infierno operativo.
  Se deja como horizonte V3.0 (§11).

**Opción C — Federada híbrida (RECOMENDADA)** — el "Nexus".
Un servicio de coordinación FINO y BARATO que hace de relay + registro + índice,
pero que **no tiene autoridad sobre el contenido y nunca ve datos crudos**. Los
nodos guardan todo lo privado en local; el Nexus solo mueve PortableSkills
firmadas y content-addressed. Es el término medio entre A (central, malo para
privacidad) y B (P2P, malo para operar).

### 7.2 Por qué la federada híbrida es la correcta (y por qué no traiciona la privacidad)

La clave está en que el Nexus maneja **contenido inmutable, firmado y
direccionado por su hash (content-addressed, estilo CID de IPFS)**. Esto
significa:
- El Nexus **no puede manipular** una skill sin que su hash cambie y la firma deje
  de validar. Cualquier nodo detecta la manipulación al instante.
- El Nexus **no ve datos personales** porque lo único que le llega es
  PortableSkill (que por construcción no los contiene).
- El Nexus es **reemplazable**: si mañana no te fías de tu proveedor, levantas
  otro Nexus y los nodos apuntan ahí; el contenido es el mismo (mismos hashes).
  No hay lock-in.
- El Nexus es **cacheable**: las skills publicadas son públicas e inmutables →
  una CDN (Cloudflare) las sirve globalmente casi gratis. La lectura, que es el
  99% del tráfico, ni toca tu servidor.

En resumen: el Nexus es un cartero que lleva sobres lacrados y sellados que no
puede abrir ni falsificar. Coordina sin controlar.

### 7.3 Recomendación concreta de stack (para empezar hoy, escalar a millones)

**Fase de arranque (0 → 10.000 nodos) — coste ~5-20 €/mes:**
- **Nexus API**: FastAPI (el MISMO stack que Aithera — cero tecnología nueva que
  aprender), en un VPS pequeño (Hetzner CX22 ~4 €/mes, o Fly.io con free tier).
- **Almacén content-addressed**: Cloudflare R2 (S3-compatible, **sin cargos de
  egreso** — clave: las descargas de skills no te cuestan) o Backblaze B2.
  Cada skill se guarda bajo su CID (SHA-256). Inmutable por diseño.
- **Registro firmado**: PostgreSQL (ya lo usa Aithera) con la tabla de skills:
  cid, name, version, proof, signature, status, ranking. Índice para
  descubrimiento.
- **CDN**: Cloudflare delante de R2. Las skills públicas se cachean globalmente;
  la latencia de descubrimiento es de CDN, no de tu VPS.
- **Identidad de nodo**: cada Aithera genera un par de claves Ed25519 en el
  primer arranque (guardado con DPAPI, como los secretos actuales). La clave
  pública ES la identidad pseudónima. Sin cuentas, sin contraseñas, sin email.
  Las contribuciones se firman; el Nexus verifica firmas.

**Fase de escala (10.000 → millones) — el diseño ya lo aguanta:**
- El Nexus API es **stateless** (toda la verdad está en Postgres + R2) → se
  escala horizontalmente detrás de un balanceador. Cloudflare absorbe el tráfico
  de lectura. Postgres se replica (read replicas) para el descubrimiento.
- Los Guardians corren como procesos separados (los puede correr una fundación,
  voluntarios de alta reputación, o tú al principio). Coordinan vía el relay del
  Nexus.
- Costes que crecen sublinealmente: la lectura la paga la CDN (barata y global);
  la escritura (publicar skills) es infrecuente comparada con la lectura y va al
  VPS/Postgres.

**Estimación de coste honesta (VC lens)**: con 100.000 nodos activos, el coste de
infra del Nexus está en el orden de **cientos de €/mes**, no miles, porque el
90% del tráfico es lectura cacheada de artefactos inmutables. Es uno de los
pocos modelos de red social/conocimiento cuyo coste marginal por usuario tiende a
cero. Esto es una ventaja de negocio enorme (§13).

### 7.4 Diagrama de despliegue

```
    [Aithera nodo · Madrid] ─┐
    [Aithera nodo · Tokio ] ─┤   firma Ed25519 + PortableSkill
    [Aithera nodo · Lima  ] ─┤        (nunca datos crudos)
              ...            │
                             ▼
              ┌──────────────────────────────┐
              │  Cloudflare CDN (lectura)     │  ← 99% del tráfico, cacheado
              └───────────────┬──────────────┘
                              ▼
              ┌──────────────────────────────┐
              │  NEXUS (FastAPI, stateless)   │  ← relay + verificación de firmas
              │  - registro firmado (índice)  │
              │  - coordinación de Guardians  │
              └──────┬───────────────┬────────┘
                     ▼               ▼
         ┌────────────────┐  ┌──────────────────┐
         │ PostgreSQL     │  │ Cloudflare R2     │
         │ (registro,     │  │ (skills por CID,  │
         │  ranking,proof)│  │  inmutables)      │
         └────────────────┘  └──────────────────┘
                     ▲
         ┌───────────┴───────────┐
         │  Guardians (N indep.)  │  ← validan cuarentena; sin datos privados
         │  + Canarios voluntarios│
         └───────────────────────┘
```

---

## 8. SEGURIDAD — LA DEFENSA CONTRA IA ADVERSARIA (5 capas)

El comité incluyó a propósito un experto en ciberseguridad **contra los modelos
más avanzados de IA**. Es la sección más importante, porque la investigación
(§1.5) es clara: una memoria colectiva abierta es el objetivo soñado de un
atacante con IA, y las defensas de un solo detector son frágiles. Por eso la
defensa es en profundidad, con 5 capas independientes que un atacante tendría que
romper TODAS a la vez.

**Capa 1 — Procedencia criptográfica (no anónima, pseudónima y firmada)**
Toda PortableSkill va firmada con la clave del nodo. No hay contribuciones
anónimas sin firma. Un atacante puede crear identidades, pero cada una arrastra
su historial: reputación, ratio de refutación, patrón de contribución. La
procedencia es la base sobre la que actúan las demás capas.

**Capa 2 — Prueba-de-utilidad (el veneno no puede fingir buenos resultados)**
Esta es la defensa estructural más potente, y es original. Como el ranking se
decide por `outcome_delta` medido en ejecuciones reales, una skill-veneno tendría
que producir mejoras reales medibles para escalar — y si las produce, no es
veneno, es útil. El atacante no puede votar su veneno a la cima porque no hay
votos; solo hay resultados. Para falsificar resultados a escala tendría que
operar una flota de nodos ejecutando misiones reales exitosas, que es
económicamente absurdo y, de hecho, es contribuir.

**Capa 3 — Cuarentena con canarios (sandbox antes del mundo)**
Ninguna skill llega a PUBLISHED sin pasar por QUARANTINED: instancias "canario"
voluntarias la ejecutan **en sandbox aislado** y miden su efecto real y su
comportamiento (¿intenta exfiltrar? ¿ejecuta acciones fuera de su capacidad
declarada? ¿su `outcome_delta` real coincide con el que declaró?). Una skill cuya
utilidad declarada no se reproduce en los canarios se rechaza. Esto ataca
directamente a Confundo (veneno que sobrevive al preprocesado): aquí no hay que
detectar el veneno leyéndolo, se detecta **ejecutándolo en un entorno seguro y
midiendo que hace daño o miente**.

**Capa 4 — Quórum de Guardians independientes (control de flujo de información)**
N Guardians (RFC-003) independientes deben aprobar por consenso. Son agentes con
un MemoryRouter capado (solo ven GSN/CIE, nunca datos privados — inyección de
dependencias). Aplican el enfoque de Cordon-MAS (control de flujo): una skill no
puede referenciar ni activar capacidades que no declaró; el flujo de información
está acotado por construcción. N independientes significa que capturar la red
exige capturar N Guardians a la vez, no uno.

**Capa 5 — Detección de anomalías + refutación distribuida (autocorrección)**
Aun si algo pasa las 4 capas, la red lo caza a posteriori: nodos que adoptan la
skill y miden peores resultados contribuyen refutaciones (DP-noised). Un patrón
de refutación estadísticamente significativo degrada la skill automáticamente y
marca a su publicador. Detección de anomalías sobre patrones de contribución
(un nodo que publica 500 skills en una hora, o cuyas skills siempre son
refutadas) dispara cuarentena reforzada. La red tiene un sistema inmune que
aprende de las infecciones.

**Modelado de amenazas explícito (qué NO protege esto, honestidad)**:
- No protege contra un usuario que *decide* adoptar una skill que a él le va bien
  pero es éticamente cuestionable — eso es decisión del usuario, no de la red.
- No es inmune a un atacante estado-nación con recursos ilimitados que opere una
  flota real y paciente durante meses; ninguna red abierta lo es. Lo eleva de
  "trivial" (MINJA 95% en RAG normal) a "económicamente ruinoso y lento".
- La privacidad diferencial protege el agregado, no garantiza cero fuga bajo
  ataques de correlación sofisticados con datos externos; por eso además está el
  k-anonimato y la frontera topológica.

**Auditabilidad total (del paper 1.1)**: cada operación de la red (publicar,
adoptar, refutar, aprobar Guardian, deprecar) queda en un log firmado e inmutable.
Cualquiera puede auditar por qué una skill está donde está. La transparencia es
una defensa: el veneno prefiere la oscuridad.

---

## 9. UX — CÓMO LO VIVE EL USUARIO (el especialista en UX)

La red debe ser **invisible cuando funciona y transparente cuando importa**. El
usuario medio no debería tener que entender CRDTs ni privacidad diferencial para
beneficiarse.

- **Onboarding (opt-in explícito, nunca por defecto)**: al activar Aithera, la
  red colectiva está APAGADA. Una tarjeta la explica en una frase — "Aithera
  puede aprender trucos de otras Aitheras del mundo, sin que nada tuyo salga
  nunca de aquí" — con un interruptor. Fail-closed: sin decir que sí, no se
  publica ni se adopta nada.
- **Los dos permisos** (`network.adopt`, `network.publish`) son independientes:
  puedes recibir sin dar, o dar sin recibir, o ambos. Muchos usuarios querrán
  "aprender de la red pero no compartir": es una posición legítima y por defecto.
- **"Lo que la red te ha enseñado"**: un panel (como el perfil destilado que ya
  existe) lista las skills que Aithera adoptó de la red, cuánto le han ayudado
  (outcome real), y un botón para olvidar cualquiera. Transparencia con undo.
- **Cero fricción en el uso**: cuando Aithera usa una skill de la red, funciona
  igual que una local; opcionalmente una etiqueta discreta ("aprendida de la
  red") si el usuario quiere saberlo. Nunca un popup interrumpiendo.
- **Contribución con dignidad**: cuando una skill que TÚ publicaste ayuda a otros,
  Aithera te lo dice ("una skill que compartiste ha ayudado a 3.400 personas esta
  semana"). Es el refuerzo que sostiene el bien común sin gamificación barata.

---

## 10. PLAN DE DESARROLLO POR SESIONES (modelo + esfuerzo por sesión)

Cada sesión con su modelo recomendado y nivel de esfuerzo. Criterio de asignación
(como los bloques anteriores del proyecto):
- **Fable 5 / Max**: contratos congelados, seguridad, criptografía, algoritmos de
  consenso — donde un error se propaga a toda la red y no se puede deshacer.
- **Opus / Alto**: arquitectura de módulos, el CIE, integración con el MOS.
- **Sonnet / Medio**: infraestructura Nexus (CRUD + firmas), UI, adaptadores,
  tests de contrato — trabajo acotado y bien especificado.

> **Prerrequisito duro de todo el bloque**: la V1.1 (LSL completa + LLL + Learning
> System del doc 15) debe estar CERRADA y madura. La red amplifica lo local;
> amplificar algo inmaduro amplifica ruido. No empezar la V2.0 antes.

### BLOQUE G — Fundamentos (la frontera y los contratos)

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **G1** | Contratos CONGELADOS: `PortableSkill`, `SkillProof`, `PrivacyFilter`, la extensión `ISkillStore.export_anonymized()`/`import_skill()`. Paquete `app/network/` con la direccionalidad de imports + `test_network_boundaries.py`. Nada de red todavía: solo la frontera, blindada. | **Fable 5** | **Max** |
| **G2** | Identidad de nodo: par de claves Ed25519, firma/verificación de PortableSkill, almacenamiento con DPAPI. `sign()`/`verify()` con sus tests. El `cid` content-addressed (SHA-256 canónico). | **Fable 5** | **Max** |
| **G3** | `PrivacyFilter` + privacidad diferencial en el borde: el esquema que prohíbe texto libre personal, el ruido DP sobre `SkillProof`, el k-anonimato (no publicar con `sample_size < k`). Tests adversarios: intentar colar datos personales y verificar que el filtro los corta. | **Fable 5** | **Max** |

### BLOQUE N — El Nexus (la infraestructura de coordinación)

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **N1** | Nexus API (FastAPI, repo aparte o `nexus/`): endpoints publish/discover/fetch/refute. Registro Postgres + almacén R2 content-addressed. Verificación de firma en el borde (rechaza lo no firmado). Stateless. | **Sonnet** | **Medio** |
| **N2** | Descubrimiento + ranking: consulta por dominio/capacidad, ordenación por prueba-de-utilidad, CDN-cacheable. Rate limiting por clave pública. | **Sonnet** | **Medio** |
| **N3** | Cliente GSE en Aithera (`app/network/gse.py`): publicar (opt-in), descubrir, adoptar (import_skill), refutar. Integración con el permiso `network.*` (A3b). Todo fail-closed. | **Opus** | **Alto** |

### BLOQUE C — CRDT semántico + consenso de utilidad

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **C1** | El CRDT semántico: `merge()` por evidencia dominante, branches A/B en empate, convergencia probada con tests de conmutatividad/idempotencia. Vector clocks sobre `derived_from`/`supersedes`. | **Fable 5** | **Max** |
| **C2** | Prueba-de-utilidad: agregación de `outcome_delta` DP-noised, penalización por refutación, reputación como utilidad acumulada. Resistencia a Sybil verificada con simulación. | **Fable 5** | **Max** |

### BLOQUE S — Seguridad (Guardians + cuarentena + defensa en profundidad)

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **S1** | `GuardianRuntime(AgentRuntime)` con MemoryRouter capado (solo GSN/CIE). Las 4 validaciones: veneno, duplicados, fugas, contradicciones. Control de flujo estilo Cordon-MAS (una skill no activa capacidades no declaradas). | **Fable 5** | **Max** |
| **S2** | Cuarentena + canarios: sandbox de ejecución aislado, medición de `outcome_delta` real vs declarado, rechazo si mienten. Quórum de N Guardians. | **Fable 5** | **Max** |
| **S3** | Detección de anomalías + refutación distribuida + auditoría inmutable (log firmado de toda operación de red). Simulación de ataque MINJA/PoisonedRAG y verificación de que las 5 capas lo paran. | **Fable 5** | **Max** |

### BLOQUE I — CIE (Collective Intelligence Engine)

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **I1** | CIE Modo 1 (Convergencia): detección de clusters, comparación estadística, recomendación por contexto. Reutiliza los algoritmos del LLL (doc 15) a escala de red. | **Opus** | **Alto** |
| **I2** | CIE Modo 2 (Síntesis / "Sueño Colectivo"): composición de skills de orden superior a partir de clusters, generación de `PROPOSED`, entrada a cuarentena. La pieza genuinamente nueva. | **Fable 5** | **Max** |
| **I3** | CIE Modo 3 (Anticipación): detección de tendencias en el agregado (fallos masivos correlacionados → skill de mitigación). Ventana temporal, umbrales, propuesta proactiva. | **Opus** | **Alto** |

### BLOQUE U — UX + integración + cierre

| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **U1** | Panel "Red colectiva" en Ajustes: on/off, permisos independientes adopt/publish, "lo que la red te ha enseñado" con undo, contribución con dignidad. | **Sonnet** | **Medio** |
| **U2** | Integración TIE/AE: el planner descubre skills de red como una fuente más; el AE puede volverlas automatizaciones (con permisos). Sin regresión en el camino local. | **Opus** | **Alto** |
| **U3** | Suite de contratos de red (patrón `test_product_contracts`): "nada personal sale nunca", "una skill-veneno no llega a PUBLISHED", "la red caída no afecta al nodo", "adoptar es reversible". Verificación en vivo contra un Nexus de staging. | **Fable 5** | **Max** |

**Total**: ~17 sesiones en 5 bloques. Orden recomendado: G → N → C → S → I → U,
con S (seguridad) pudiendo solaparse con C porque comparten el concepto de
prueba-de-utilidad. Ninguna sesión de red toca el código privado del MOS más
allá de la puerta única `ISkillStore` (G1).

---

## 11. HORIZONTE V3.0+ (documentado para no perderlo, NO en alcance)

- **Descentralización del Nexus (P2P real)**: cuando la red sea grande y madura,
  migrar el Nexus de "un servicio coordinador" a una DHT (libp2p) donde los
  propios nodos de alta reputación hacen de relay. El diseño content-addressed +
  firmado ya lo permite (el contenido no depende de dónde viva). Es un cambio de
  transporte, no de arquitectura.
- **Colectivos privados / federados por organización**: una empresa levanta su
  propio Nexus privado; sus Aitheras comparten skills internas sin salir a la red
  pública. Mismo protocolo, otro Nexus. (Vía de monetización, §13.)
- **Interoperabilidad con otros asistentes**: la GSN es un protocolo abierto (no
  exclusivo de Aithera, RFC-004). Otros asistentes que implementen el contrato
  PortableSkill + firma + prueba-de-utilidad pueden participar. La red vale más
  cuanto más diversa.
- **Skills multi-modales**: hoy el diseño es de skills técnicas (texto/workflow).
  El horizonte incluye skills de voz, de visión, de control de escritorio.

---

## 12. RIESGOS Y MITIGACIONES (tabla honesta)

| Riesgo | Severidad | Mitigación en el diseño |
|---|---|---|
| Envenenamiento por IA adversaria | CRÍTICA | 5 capas (§8); prueba-de-utilidad hace el ataque económicamente ruinoso |
| Fuga de datos personales a la red | CRÍTICA | Frontera topológica (§3.1) + PrivacyFilter + DP + k-anon; imposible por construcción, no por promesa |
| Ataque Sybil (flota de nodos falsos) | ALTA | Consenso por utilidad medida, no por votos; los nodos falsos no pueden falsificar resultados reales |
| Cold-start (red vacía = sin valor) | ALTA | Autosuficiencia: Aithera es completa sin red; la red es bonus. Se puede sembrar con skills curadas iniciales |
| Coste de infra descontrolado | MEDIA | Content-addressed + CDN → coste marginal por usuario → 0 (§7.3) |
| Captura del Nexus (proveedor malicioso) | MEDIA | Content-addressed + firmas: el Nexus no puede manipular; es reemplazable sin lock-in |
| Regulatorio (GDPR y equivalentes) | MEDIA | No se mueven datos personales NUNCA → fuera del alcance de la mayoría de la regulación de datos; auditabilidad total |
| Deriva de calidad (la red se llena de ruido) | MEDIA | Lifecycle de skills (deprecate por refutación) + Guardians + ranking por utilidad |
| Dependencia de un CIE central | MEDIA | El CIE propone, nunca decide; los nodos son autosuficientes; el CIE es auditable y reemplazable |

---

## 13. VEREDICTO DEL COMITÉ

**El CTO (25 años)**: Es construible, por fases, con el stack que ya domináis
(FastAPI/Postgres). La decisión de acoplar la red por una sola puerta
(`ISkillStore`) es lo que lo hace viable para un equipo pequeño: el 95% de
Aithera no se entera de que existe la red. El prerrequisito de madurar la V1.1
antes no es negociable. Construir, sí; con disciplina de fases, también.

**El Principal Architect**: La elegancia está en la reutilización — el CIE es el
LLL a escala, los Guardians son AgentRuntimes, las skills de red son skills. No
se inventa un sistema paralelo; se extiende el existente. El CRDT semántico y la
prueba-de-utilidad son las dos piezas realmente nuevas, y ambas son correctas por
las mismas razones que sus ancestros clásicos.

**El experto en IA/multiagente**: El "Sueño Colectivo" (CIE Modo 2) es lo que
convierte esto de un caché compartido en inteligencia colectiva real. Es
ambicioso y es la joya del diseño. También es lo más difícil y lo que dejaría
para el final (I2), tras haber probado que la agregación simple (I1) funciona.

**El experto en memorias globales**: La topología content-addressed + federada
híbrida es la decisión correcta y no obvia. Resuelve el trilema
privacidad/operabilidad/coste que hunde a la mayoría de intentos de memoria
colectiva. El Nexus-como-cartero-de-sobres-lacrados es un buen modelo mental.

**El ingeniero de memorias compartidas con IA**: La prueba-de-utilidad como
consenso es la mejor idea del documento. Resuelve de un plumazo Sybil y buena
parte del envenenamiento, porque ancla el valor en algo que no se puede
falsificar sin hacer el trabajo de verdad. Lo firmaría en un paper.

**El Staff de rendimiento**: El 99% del tráfico es lectura de artefactos
inmutables → CDN. Es de las pocas redes cuyo coste no explota con la escala. La
escritura y el consenso son los caminos calientes a vigilar, pero son
infrecuentes. Aprobado desde rendimiento.

**El especialista en UX**: Opt-in, permisos independientes, "lo que la red te ha
enseñado" con undo, y contribución con dignidad. La regla "invisible cuando
funciona, transparente cuando importa" es la correcta. Mi única exigencia:
jamás un popup de red interrumpiendo una conversación.

**El experto en ciberseguridad**: La defensa en profundidad de 5 capas es seria y
la honestidad sobre lo que NO protege (estado-nación paciente) es lo que hace
creíble el resto. La auditabilidad total como defensa es acertada.

**El experto en ciberseguridad contra IA avanzada**: La investigación es clara —
un detector solo es frágil (§1.5). Que la defensa NO dependa de leer y detectar
el veneno, sino de ejecutarlo en sandbox y medir que hace daño o miente (capa 3),
es lo que le da robustez frente a atacantes adaptativos como Confundo. La
prueba-de-utilidad es, además, una defensa de seguridad disfrazada de mecanismo
de ranking. Bien pensado.

**El inversor VC**: El foso es doble y real — **efecto red** (más nodos → mejores
skills → más valor de unirse) y **datos de utilidad imposibles de falsificar**
(el activo que ningún competidor puede copiar sin la red). El coste marginal por
usuario tiende a cero, lo cual es oro. El protocolo abierto (no exclusivo de
Aithera) parece regalar el foso, pero en realidad lo agranda: la red vale más
cuanto más grande, y quien la arranca y coordina (el Nexus de referencia, los
Guardians de referencia, la marca) captura el valor aunque el protocolo sea
abierto — el modelo Ethereum/Linux, no el modelo jardín cerrado. Monetización
clara: Nexus gestionado, colectivos privados de empresa, Guardians premium.
Riesgo dominante: cold-start y confianza. **Inversión: sí, por fases, condicionada
a que el producto personal (V1.x) ya tenga tracción — la red es el segundo acto,
no el primero.**

**Veredicto unánime**: Diseño sólido, innovador donde debe (prueba-de-utilidad,
CRDT semántico, Sueño Colectivo) y conservador donde debe (federada híbrida sobre
stack conocido, acoplamiento por una puerta). **Construir en V2.0+, tras madurar
V1.1, en el orden de bloques G→N→C→S→I→U.** Es el segundo acto de Aithera, y es
un acto que casi nadie más está en posición de escribir.

---

## Fuentes de la investigación

- [Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control (arXiv 2505.18279)](https://arxiv.org/abs/2505.18279)
- [Memory in LLM-based Multi-agent Systems: Mechanisms, Challenges, and Collective Intelligence (survey)](https://www.researchgate.net/publication/398392208_Memory_in_LLM-based_Multi-agent_Systems_Mechanisms_Challenges_and_Collective_Intelligence)
- [Selective knowledge sharing for privacy-preserving federated distillation without a good teacher (Nature Communications)](https://www.nature.com/articles/s41467-023-44383-9)
- [Differentially private knowledge transfer for federated learning (Nature Communications)](https://www.nature.com/articles/s41467-023-38794-x)
- [Knowledge Distillation in Federated Learning: a Survey (arXiv 2406.10861)](https://arxiv.org/pdf/2406.10861)
- [Conflict-free replicated data type (CRDT) — Wikipedia](https://en.wikipedia.org/wiki/Conflict-free_replicated_data_type)
- [CRDTs solve distributed data consistency challenges (Ably)](https://ably.com/blog/crdts-distributed-data-consistency-challenges)
- [Memory Poisoning Attack and Defense on Memory Based LLM-Agents (arXiv 2601.05504)](https://arxiv.org/html/2601.05504v2)
- [Cordon-MAS: Defending RAG against Knowledge Poisoning via Information-Flow Control (arXiv 2605.26754)](https://arxiv.org/pdf/2605.26754)
- [SMSR: Certified Defence Against Runtime Memory Poisoning in Persistent LLM Agent Systems (arXiv 2606.12703)](https://arxiv.org/html/2606.12703)

---
*Documento de diseño maestro. V2.0+ (no en desarrollo). Extiende RFC-003/004/005
del doc 08. Prerrequisito: V1.1 (LSL/LLL) cerrada. Redactado 2026-07-20.*
