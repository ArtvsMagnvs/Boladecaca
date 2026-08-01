# app/tie/action_intent.py — detector DETERMINISTA de "esto es una acción sobre
# Aithera" (2026-07-25, tras el fallo real: crear milestone+agente acabó en el
# camino conversacional y el modelo FINGIÓ haberlo hecho).
#
# EL FALLO QUE CIERRA (log real del usuario):
#     17:35:20 classify LLM: 5781ms modelo='llama3'
#     17:35:20 [intents] sin JSON parseable, fallback conversational
# Una petición de ACCIÓN ("crea una milestone MVP y un agente Investigador")
# dependía de que un LLM local produjera JSON válido. Al fallar, el fail-safe
# "conversational" (correcto para charla) tiraba la intención de acción a la
# basura: el turno acababa en chat SIN herramientas y el modelo respondía como
# si lo hubiera hecho. Dos mentiras seguidas.
#
# EL ARREGLO, Y POR QUÉ ES GLOBAL (no un parche):
#   1. Los VERBOS de acción y los SUSTANTIVOS de dominio se listan una vez y
#      cubren TODAS las acciones del catálogo de `aithera_tool` (proyectos,
#      hitos, tareas, agentes, reglas, recordatorios, idioma, modelo) — y las
#      futuras que usen los mismos sustantivos. `assert_covers_catalog()` lo
#      verifica CONTRA el catálogo real, así que una acción nueva sin cobertura
#      rompe un test en vez de fallar en silencio en producción.
#   2. No sustituye al clasificador ni al TIE: es una RED DE SEGURIDAD. Corrige
#      dos casos concretos y acotados (ver `intents.classify`):
#        · el LLM falló (sin JSON / error / excepción) → antes: charla. Ahora:
#          acción, con las herramientas puestas.
#        · el LLM dijo "conversational" pero el mensaje es claramente una orden
#          de actuar → se corrige el tipo (los modelos pequeños confunden
#          "créame X" con charla). El resto del intent del LLM se respeta.
#      Todo lo demás (planner, grafo, MEL, orquestador, multi-objetivo) sigue
#      exactamente igual: la versatilidad del chat no se toca.
from __future__ import annotations

import unicodedata
from typing import Optional

from app.tie.contracts import Intent, IntentType


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# Verbos que expresan "hazlo" (es/en/fr/pt). Se comparan por PREFIJO para cubrir
# conjugaciones ("crea", "crear", "créame", "crealo", "creas"…).
_ACTION_VERB_STEMS = (
    # crear / añadir
    "crea", "crear", "cree", "creame", "genera", "generar", "anade", "anadir",
    "agrega", "agregar", "monta", "montar", "haz", "hazme", "pon", "ponme", "poner",
    "create", "add", "make", "generate", "set", "setup",
    "ajoute", "ajouter", "cree", "creer", "genere", "mets", "mettre",
    "cria", "criar", "adiciona", "adicionar", "gera", "poe", "por",
    # borrar / archivar
    "borra", "borrar", "elimina", "eliminar", "quita", "quitar", "archiva", "archivar",
    "delete", "remove", "archive", "supprime", "supprimer", "apaga", "apagar", "remove",
    # modificar / mover / renombrar
    "cambia", "cambiar", "modifica", "modificar", "edita", "editar", "actualiza",
    "actualizar", "renombra", "renombrar", "mueve", "mover", "asigna", "asignar",
    "change", "modify", "edit", "update", "rename", "move", "assign",
    "modifie", "modifier", "renomme", "deplace", "assigne",
    "muda", "mudar", "altera", "atualiza", "renomeia", "move", "atribui",
    # abrir / ejecutar / activar
    "abre", "abrir", "ejecuta", "ejecutar", "lanza", "lanzar", "activa", "activar",
    "desactiva", "desactivar", "cierra", "cerrar", "completa", "completar",
    "open", "run", "execute", "launch", "start", "enable", "disable", "close", "complete",
    "ouvre", "ouvrir", "execute", "lance", "active", "desactive", "ferme",
    "abre", "abrir", "executa", "lanca", "ativa", "desativa", "fecha",
)

# Sustantivos de DOMINIO de la app. Cada uno mapea a la familia de acciones del
# catálogo de `aithera_tool` que lo gobierna (ver `assert_covers_catalog`).
_DOMAIN_NOUNS: dict[str, tuple[str, ...]] = {
    "project": ("proyecto", "proyectos", "project", "projects", "projet", "projets", "projeto", "projetos"),
    "milestone": ("milestone", "milestones", "hito", "hitos", "jalon", "marco"),
    "task": ("tarea", "tareas", "task", "tasks", "tache", "taches", "tarefa", "tarefas"),
    "agent": ("agente", "agentes", "agent", "agents"),
    "rule": ("regla", "reglas", "rule", "rules", "automatizacion", "automatizaciones",
             "automation", "regle", "regles", "regra", "regras",
             "recordatorio", "recordatorios", "reminder", "reminders", "cron",
             "autorespuesta", "auto-respuesta", "respuesta automatica"),
    "language": ("idioma", "idiomas", "language", "langue", "lingua",
                 "espanol", "ingles", "frances", "portugues",
                 "english", "spanish", "french", "portuguese"),
    "model": ("modelo", "modelos", "model", "models", "modele", "modelo"),
}

# Qué acciones del catálogo cubre cada sustantivo (para el test de cobertura).
_NOUN_TO_ACTIONS: dict[str, tuple[str, ...]] = {
    "project": ("list_projects", "project_status", "create_project"),
    "milestone": ("create_milestone",),
    "task": ("create_task", "update_task"),
    # [2026-08-02] `update_agent`/`delete_agent` (nuevas) van aquí: "cambia las
    # skills del agente X" o "borra el agente Y" son órdenes sobre el MISMO
    # sustantivo de dominio que ya cubría crear/listar.
    "agent": ("create_agent", "assign_tools", "list_agents", "run_agent_task",
              "update_agent", "delete_agent"),
    "rule": ("create_rule", "create_cron_job", "list_rules", "toggle_rule",
             "create_auto_reply_rule"),
    "language": ("set_language",),
    "model": ("set_chat_model",),
}

_MAX_WORDS = 60   # una orden puede ser larga ("crea X y además Y con Z…")


def _domains(norm: str) -> list[str]:
    return [dom for dom, words in _DOMAIN_NOUNS.items()
            if any(w in norm for w in words)]


def _has_action_verb(norm: str) -> bool:
    words = [w.strip(".,;:!?¡¿()[]{}\"'…") for w in norm.split()]
    for w in words:
        if w in _ACTION_VERB_STEMS:
            return True
        # Prefijo, para cubrir conjugaciones y pronombres enclíticos sin listar
        # cada forma: "creame", "crearlo", "ponle", "activalo", "asignale",
        # "creado"… Se admiten stems de 3+ letras ("pon", "haz") porque el
        # detector YA exige además un sustantivo de dominio, así que un "pon" en
        # otro contexto no dispara nada.
        if any(w.startswith(stem) and len(w) - len(stem) <= 4
               for stem in _ACTION_VERB_STEMS if len(stem) >= 3):
            return True
    return False


def looks_like_action(text: str) -> bool:
    """True si el mensaje pide ACTUAR sobre Aithera (verbo de acción + sustantivo
    de dominio). Determinista, sin LLM. Conservador: sin las DOS señales, False."""
    norm = _norm(text)
    if not norm or len(norm.split()) > _MAX_WORDS:
        return False
    return bool(_domains(norm)) and _has_action_verb(norm)


def action_intent(text: str) -> Optional[Intent]:
    """Intent de ACCIÓN listo para el camino de acción directa del TIE (toolloop
    con la tool `aithera`), o None si el mensaje no es una orden de actuar.

    `requires_planning=False` a propósito: crear/abrir/cambiar cosas de la app es
    una secuencia mecánica de llamadas a `aithera_tool`, no un plan que revisar
    (mismo criterio que `Intent.is_direct_action`). Si de verdad hiciera falta
    plan (varios entregables dependientes), el clasificador LLM lo marcará
    cuando funcione — este detector solo actúa cuando el LLM NO ha podido."""
    if not looks_like_action(text):
        return None
    return Intent(
        type=IntentType.EXECUTE,
        goal=text.strip()[:200],
        domain=_domains(_norm(text)),
        confidence=1.0,                 # el detector es determinista
        requires_planning=False,
        requires_tools=["aithera"],
        requires_memory=False,
        model_capability="agentic",
        raw_text=text.strip(),
    )


# ===========================================================================
# [NEW-7, doc 34] Segundo detector: "esto pide LEER EL MUNDO", no solo Aithera
# ===========================================================================
# EL FALLO QUE CIERRA (verificación en vivo del usuario, 2026-07-28):
#     "Lista los archivos de la carpeta Aithera, dime cuántos .py hay en
#      backend/app/tie, y léeme las primeras líneas de pipeline.py"
#   → [intents] sin JSON parseable, fallback conversational
#   → camino corto (CERO herramientas) → el modelo INVENTÓ el listado, inventó
#     el número de archivos e inventó el contenido de `pipeline.py` (imports
#     que no existen en el archivo real).
#
# Es EXACTAMENTE el mismo fallo que cerró `action_intent()` el 25-jul, pero un
# escalón más afuera: aquel rescataba las órdenes sobre la PROPIA Aithera
# (proyectos, tareas, agentes); una petición de leer archivos, buscar en la web
# o mirar el correo seguía cayendo al fail-safe "conversational" cuando el
# clasificador fallaba su JSON (~40% de las veces con `llama3`, medido). Y el
# camino corto no tiene NINGUNA herramienta: cualquier respuesta con datos
# concretos ahí es falsa por construcción.
#
# MISMA DISCIPLINA que el detector de arriba: dos señales obligatorias (verbo
# de lectura/acción + objeto del mundo), 0 LLM, y ante la duda None — un falso
# negativo solo cuesta lo de siempre; un falso positivo mandaría una charla al
# bucle de herramientas. Por eso "¿qué es un archivo .py?" NO dispara (no hay
# verbo de acción) y "léeme el archivo X" SÍ.

# Verbos de LEER/BUSCAR el mundo exterior, en DOS niveles — la diferencia
# importa para no arrastrar charla al bucle de herramientas:
#
#   FUERTES: solo tienen sentido sobre algo real y concreto. "Lee", "lista",
#   "abre", "descarga", "navega" piden un objeto que existe.
#   DÉBILES: genéricos, valen igual para una pregunta conceptual. "Dime qué
#   archivos suele tener un proyecto FastAPI" es charla, no una lectura.
#
# Regla: verbo FUERTE + objeto del mundo dispara. Verbo DÉBIL solo dispara si
# además hay una RUTA o EXTENSIÓN concreta ("dime cuántos .py hay en
# backend/app/tie" sí; "dime qué archivos hacen falta" no).
_READ_VERB_STEMS = (
    "lee", "leer", "leeme", "leelo", "lea", "leyendo",
    "lista", "listar", "listame", "enumera", "enumerar",
    "busca", "buscar", "buscame", "localiza", "localizar",
    "revisa", "revisar", "consulta", "consultar",
    "analiza", "analizar", "resume", "resumir", "resumeme",
    "extrae", "extraer", "descarga", "descargar",
    "navega", "navegar", "visita", "visitar", "abre", "abrir", "abreme",
    "read", "list", "search", "review", "analyze", "analyse",
    "summarize", "summarise", "extract", "download", "browse", "visit",
    "fetch", "open", "enumerate",
    "lis", "lire", "cherche", "chercher", "telecharge", "ouvre", "ouvrir",
    "parcours", "resume",
    "ler", "leia", "procura", "procurar", "baixa", "baixar", "abrir",
)

_WEAK_READ_VERB_STEMS = (
    "muestra", "mostrar", "muestrame", "ensename", "ensena", "dime", "dame",
    "encuentra", "encontrar", "mira", "mirar", "comprueba", "comprobar",
    "verifica", "verificar", "cuenta", "contar", "cuantos", "cuantas",
    "show", "tell", "give", "find", "look", "check", "verify", "count",
    "how many",
    "montre", "montrer", "trouve", "verifie", "compte", "combien",
    "mostra", "mostrar", "encontra", "conta", "quantos",
)

# Objetos del MUNDO por familia de herramienta. Cada familia mapea al `tool_id`
# real del ToolManager, para que el intent que se devuelve sea ejecutable.
_WORLD_OBJECTS: dict[str, tuple[str, ...]] = {
    "filesystem": (
        "archivo", "archivos", "fichero", "ficheros", "carpeta", "carpetas",
        "directorio", "directorios", "ruta", "rutas",
        "file", "files", "folder", "folders", "directory", "directories", "path",
        "dossier", "dossiers", "repertoire", "fichier", "fichiers",
        "pasta", "pastas", "arquivo", "arquivos", "diretorio",
    ),
    "document": (
        "documento", "documentos", "pdf", "docx", "xlsx", "word", "excel",
        "hoja de calculo", "hoja", "document", "documents", "spreadsheet",
        "gdd", "informe", "memoria", "manual", "planilha",
    ),
    "search": (
        "internet", "web", "google", "online", "en la red", "en red",
        "noticias", "news", "buscador",
    ),
    "browser": ("navegador", "navegando", "url", "http://", "https://", "www.", "browser"),
    "email": (
        "correo", "correos", "email", "emails", "e-mail", "bandeja", "inbox",
        "mail", "gmail", "courriel", "correio",
    ),
    "calendar": (
        "calendario", "agenda", "evento", "eventos", "reunion", "reuniones",
        "calendar", "meeting", "meetings", "event", "events", "compromisso",
    ),
}

# Extensiones que delatan un archivo CONCRETO del sistema del usuario. Su sola
# presencia (con un verbo de lectura) ya es señal suficiente: nadie escribe
# "pipeline.py" en una charla trivial.
_FILE_EXTENSIONS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".csv",
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".html", ".css", ".yml",
    ".yaml", ".sql", ".log", ".ini", ".cfg", ".toml", ".sh", ".bat", ".ps1",
)


def _matches_stems(norm: str, stems: tuple[str, ...]) -> bool:
    words = [w.strip(".,;:!?¡¿()[]{}\"'…") for w in norm.split()]
    for w in words:
        if w in stems:
            return True
        # Prefijo, para conjugaciones y enclíticos ("leerlo", "listame",
        # "abrelo"). Mínimo 4 letras: con 3 un "le"/"ver" cualquiera colaría.
        if any(w.startswith(stem) and len(w) - len(stem) <= 4
               for stem in stems if len(stem) >= 4):
            return True
    # Las locuciones de dos palabras ("how many", "combien de") se buscan enteras.
    return any(" " in stem and stem in norm for stem in stems)


def _has_strong_read_verb(norm: str) -> bool:
    return _matches_stems(norm, _READ_VERB_STEMS)


def _has_weak_read_verb(norm: str) -> bool:
    return _matches_stems(norm, _WEAK_READ_VERB_STEMS)


def _looks_like_path(raw: str) -> bool:
    """¿Hay un archivo o ruta CONCRETA en el texto? Un nombre con extensión
    conocida, o un token con separador de ruta entre letras (`app/tie`,
    `C:\\Users\\...`). No basta con una barra suelta ni con una fecha."""
    low = (raw or "").lower()
    if any(ext in low for ext in _FILE_EXTENSIONS):
        return True
    for tok in low.split():
        tok = tok.strip(".,;:!?¡¿()[]{}\"'…")
        if len(tok) < 4:
            continue
        for sep in ("/", "\\"):
            if sep in tok:
                izq, _, der = tok.partition(sep)
                if izq[-1:].isalnum() and der[:1].isalnum():
                    return True
    return False


def _world_tools(norm: str) -> list[str]:
    return [fam for fam, words in _WORLD_OBJECTS.items()
            if any(w in norm for w in words)]


def looks_like_world_read(text: str) -> bool:
    """True si el mensaje pide LEER/BUSCAR algo del mundo real (archivos, web,
    correo, agenda) — es decir, algo que el camino corto NO puede responder sin
    inventárselo. Determinista y conservador (ver la nota de los dos niveles de
    verbo): un verbo genérico exige además una ruta o extensión concreta."""
    raw = (text or "").strip()
    norm = _norm(raw)
    if not norm or len(norm.split()) > _MAX_WORDS:
        return False
    concreto = _looks_like_path(raw)
    if _has_strong_read_verb(norm):
        return bool(_world_tools(norm)) or concreto
    if _has_weak_read_verb(norm):
        return concreto      # sin un archivo/ruta real, un "dime…" es charla
    return False


def world_intent(text: str) -> Optional[Intent]:
    """Intent de LECTURA DEL MUNDO listo para el camino de acción directa
    (toolloop con las herramientas detectadas), o None.

    Igual que `action_intent()`: solo actúa cuando el clasificador LLM NO ha
    podido, y con `requires_planning=False` — leer un archivo o buscar algo es
    una secuencia mecánica, no un plan. Lo importante no es acertar QUÉ
    herramienta exacta hace falta (el bucle de tool-use elige del catálogo),
    sino no acabar en el camino SIN herramientas, que es donde se fabrica."""
    if not looks_like_world_read(text):
        return None
    raw = (text or "").strip()
    tools = _world_tools(_norm(raw))
    if not tools:
        tools = ["filesystem"]      # se llegó aquí por una ruta/extensión concreta
    if "document" in tools and "filesystem" not in tools:
        tools.append("filesystem")  # leer un documento suele exigir localizarlo
    navega = bool({"browser", "search"} & set(tools))
    return Intent(
        type=IntentType.EXECUTE,
        goal=raw[:200],
        confidence=1.0,                 # el detector es determinista
        requires_planning=False,
        requires_tools=tools,
        requires_browser=navega,
        requires_memory=False,
        model_capability="agentic",
        raw_text=raw,
    )


# ===========================================================================
# [NEW-7b, doc 34] "guárdame un resumen" — la mitad de PERSISTIR de una tarea
# ===========================================================================
# EL FALLO QUE CIERRA (verificación en vivo, 2026-07-28, consecuencia directa
# de `world_intent()` arriba): "Investiga qué es FastAPI y guárdame un resumen
# de tres líneas" — Aithera investigó bien, pero respondió "no tengo
# herramienta de escritura de ficheros disponible en este paso (solo búsqueda
# web y navegador)". `world_intent()` detecta el LADO DE LECTURA del mensaje
# ("investiga" → search/browser) pero no el lado de ESCRITURA ("guárdame") —
# así que el intent llega al camino directo sin `filesystem`, y el bucle de
# tool-use no tiene con qué cumplir la mitad de la orden. Es el mismo patrón
# de fondo que S5 (NEW-1, la tubería entre pasos): la herramienta que hacía
# falta EXISTE, pero nadie se la puso en la mano al paso que la necesitaba.
#
# EL ARREGLO ES DELIBERADAMENTE UNIVERSAL: no es un parche de `world_intent()`
# — `ensure_persistence_tool()` se aplica al FINAL de `intents.classify()`
# (`intents.py`), sobre CUALQUIER intent que salga de ahí, venga del LLM
# (clasificación exitosa) o de un rescate determinista. Así cubre tanto "el
# clasificador funcionó pero se olvidó de `filesystem`" (probable, ningún LLM
# es perfecto) como "el rescate determinista no lo detectó".
_SAVE_VERB_STEMS = (
    "guarda", "guardame", "guardalo", "guardalos", "guardar", "guarde",
    "anota", "anotame", "anotalo", "apunta", "apuntame", "apuntalo",
    "save", "keep",
    "garde", "sauvegarde", "sauvegarder", "note",
    "salva", "salve",
)

# Modismos donde el verbo NO tiene nada que ver con persistir un dato: "guarda
# silencio" no pide escribir un archivo. Si el objeto inmediato tras el verbo
# es uno de estos, no cuenta — evita el falso positivo más obvio del español.
_SAVE_IDIOM_GUARDS = (
    "silencio", "las formas", "la calma", "la compostura", "las distancias",
    "la distancia", "el secreto", "la linea", "cama",
)


def _wants_to_persist(text: str) -> bool:
    """¿El mensaje pide GUARDAR/ANOTAR algo (un resumen, una nota, un
    resultado)? Determinista. Conservador: exige el verbo Y descarta los
    modismos conocidos que no hablan de guardar un dato."""
    norm = _norm(text)
    if not _matches_stems(norm, _SAVE_VERB_STEMS):
        return False
    return not any(idiom in norm for idiom in _SAVE_IDIOM_GUARDS)


def ensure_persistence_tool(intent: Optional[Intent], text: str) -> Optional[Intent]:
    """Si el intent YA implica hacer algo (no es charla) y el mensaje pide
    guardar/anotar, `filesystem` se añade a `requires_tools` — sin ella el
    camino directo/corto no tiene con qué cumplir esa mitad del encargo.

    No CREA intents por su cuenta (a diferencia de `action_intent`/
    `world_intent`): solo completa uno que ya existe. `None` o conversational
    pasan intactos — "guarda silencio" en mitad de una charla no debe convertir
    una respuesta trivial en una misión con herramientas."""
    if intent is None or intent.type == IntentType.CONVERSATIONAL:
        return intent
    if "filesystem" in (intent.requires_tools or []):
        return intent
    fuente = text or intent.raw_text or ""
    if _wants_to_persist(fuente):
        intent.requires_tools = list(intent.requires_tools or []) + ["filesystem"]
    return intent


# [2026-08-02] Acciones del catálogo que NO son órdenes del usuario y por tanto
# NO se mapean a ningún sustantivo de dominio.
#
# `ask_user` la decide el MODELO en mitad de una misión cuando le falta un dato;
# el usuario nunca la pide por su nombre. Meterla en un sustantivo sería peor
# que dejarla fuera: cualquier mensaje que contuviera "pregunta" pasaría a
# rescatarse como intent de acción, que es justo el falso positivo que este
# detector existe para evitar. Se excluye A PROPÓSITO y por escrito — el test de
# cobertura sigue vigilando todo lo demás.
_NOT_USER_INVOKED: set = {"ask_user"}


def assert_covers_catalog(catalog_action_ids: set) -> set:
    """Devuelve las acciones del catálogo de `aithera_tool` que NINGÚN sustantivo
    de dominio cubre. Vacío = cobertura total. Lo usa un test: si mañana se añade
    una acción nueva a la tool y nadie la mapea aquí, el test falla — así el
    detector no se queda obsoleto en silencio (que es como nacen los parches)."""
    cubiertas = {a for acts in _NOUN_TO_ACTIONS.values() for a in acts}
    return set(catalog_action_ids) - cubiertas - _NOT_USER_INVOKED
