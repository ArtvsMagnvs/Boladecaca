# app/tie/webflows.py — C·WEB-4 (doc 32, BLOQUE C): los CASOS DE USO reales
# sobre el bucle agentic de navegación.
#
# QUÉ ES: C·WEB-3 construyó el motor (observar → elegir por índice → actuar).
# Esto son los cinco flujos concretos que el usuario pidió —compra, cita previa,
# descarga, buscar dónde se genera una API key, y research en un foro—, cada uno
# con SU frontera de seguridad. No hay un bucle nuevo: un playbook es DATO que
# moldea el bucle que ya existe.
#
# POR QUÉ DATO Y NO CÓDIGO: si cada caso fuese una rama del bucle, añadir el
# sexto exigiría tocar el motor que usan los cinco anteriores. Así, un caso nuevo
# es una entrada más en `PLAYBOOKS` y su prueba; el bucle no se entera.
#
# LA DECISIÓN DE DISEÑO IMPORTANTE — parada dura, no otro gate. El bucle ya sabe
# abrir un ApprovalGate ante un paso que compromete (C·WEB-3 paso 4). Aquí NO se
# reusa eso para el paso final de estos flujos, y el motivo es concreto: con el
# perfil Autónomo un gate se AUTO-APRUEBA (regla de A3b, con rastro pero sin
# preguntar). Un gate sobre «Pagar» significaría entonces que Aithera paga sola —
# justo lo contrario de lo que el encargo dice («el usuario paga»). Por eso el
# límite de estos flujos es una PARADA: no se puede conceder, no la levanta
# ningún permiso, y el flujo termina ahí contando hasta dónde llegó. Misma
# categoría que «no se escribe en un campo de contraseña».
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def normaliza(texto: str) -> str:
    """Minúsculas SIN acentos.

    Vive aquí (y `webloop` la importa) para que no haya dos copias que puedan
    divergir. Sin esto, «Código de seguridad» o «Contraseña» —como lo escribe
    literalmente cualquier web española— no casarían con los catálogos, y ese
    fallo se descubrió de verdad al probar C·WEB-3. Los propios catálogos se
    normalizan al construirse: una entrada nueva escrita con tilde no puede
    abrir un agujero en silencio."""
    base = unicodedata.normalize("NFD", (texto or "").strip().lower())
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> List[str]:
    return [p for p in re.split(r"[^a-z0-9]+", normaliza(texto)) if p]


def _contiene_frase(texto: str, frase: str) -> bool:
    """¿Aparece `frase` como PALABRAS completas dentro de `texto`?

    Por qué no un `in` a secas: «compra» es subcadena de «comprando», así que
    detectar el flujo por subcadena convertiría «seguir comprando» en una orden
    de compra. La lección es la misma que dejó el arreglo de `search_skills`
    (2026-08-02): con términos cortos, subcadena es ruido."""
    ancho = " " + " ".join(_palabras(texto)) + " "
    return f" {' '.join(_palabras(frase))} " in ancho


def marcador_en(texto: str, patron: str) -> bool:
    """¿Está `patron` (ya normalizado) en `texto`? Subcadena, SALVO para los
    términos de una sola palabra de ≤3 letras, que exigen palabra completa.

    HALLAZGO REAL de los tests de C·WEB-4, y es un fallo de C·WEB-3: con
    subcadena a secas, «pin» casa dentro de «o-pin-iones», así que escribir
    «opiniones» en el buscador de un foro se rechazaba con «no relleno
    contraseñas». Lo mismo le pasaba a «cvv» dentro de cualquier palabra que lo
    contuviera. Con palabra completa, «CVV», «CVV:» y «cvv-input» siguen
    casando (se parte por todo lo que no sea alfanumérico), que son las formas
    en las que una web real etiqueta ese campo."""
    if not patron:
        return False
    if len(patron) <= 3 and " " not in patron:
        return patron in set(_palabras(texto))
    return patron in normaliza(texto)


# ---------------------------------------------------------------------------
# El contrato de un playbook
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Playbook:
    """Un caso de uso. Todo lo que lo distingue es DATO.

    `triggers`   qué frases del objetivo lo activan (palabras completas).
    `guidance`   bloque que se añade al prompt del bucle: cómo se hace ESTE flujo.
    `hard_stops` textos de elemento ante los que el flujo TERMINA (ver cabecera:
                 parada, no gate — no se puede conceder ni con Autónomo). Se
                 comparan por SUBCADENA a propósito: aquí el error barato es
                 parar de más, y el caro es pulsar de más.
    `read_only`  el flujo no escribe (salvo en un buscador) ni pulsa nada que
                 comprometa: research no deja huella a nombre del usuario.
    """
    name: str
    triggers: Tuple[str, ...]
    guidance: str
    stop_answer: str
    hard_stops: Tuple[str, ...] = ()
    read_only: bool = False
    closing_note: str = ""
    suggested_steps: int = 0        # 0 = el del bucle


def _pb(name, triggers, guidance, stop_answer, hard_stops=(), **kw) -> Playbook:
    return Playbook(
        name=name,
        triggers=tuple(normaliza(t) for t in triggers),
        guidance=guidance.strip(),
        stop_answer=stop_answer.strip(),
        hard_stops=tuple(normaliza(h) for h in hard_stops),
        **kw,
    )


# ---------------------------------------------------------------------------
# Los cinco casos (doc 32 §C·WEB-4)
# ---------------------------------------------------------------------------
COMPRA = _pb(
    "compra",
    triggers=("carrito", "cesta", "carro de la compra", "comprar", "comprame",
              "compra", "pedido", "encargar", "cart", "basket", "add to cart"),
    guidance="""FLUJO: COMPRA EN UNA TIENDA ONLINE.
Tu tarea llega HASTA EL CARRITO, ni un paso más:
- Busca cada producto por el buscador de la tienda, no por el menú.
- Comprueba que el resultado es el producto pedido (nombre y formato) antes de
  añadirlo; si hay varios parecidos, elige el que más se ajuste y dilo al final.
- Ajusta la cantidad si el usuario la ha indicado.
- Cuando todo esté en el carrito, responde "done" enumerando QUÉ has añadido.
NO pulses pagar, tramitar el pedido ni finalizar la compra: eso lo hace el
usuario. Si la tienda pide iniciar sesión, para y dilo.""",
    stop_answer="He dejado el carrito preparado. El pago lo haces tú: no toco "
                "ni el botón de pagar ni ningún medio de pago.",
    hard_stops=("pagar", "pago", "checkout", "tramitar pedido", "realizar pedido",
                "finalizar pedido", "confirmar pedido", "finalizar compra",
                "tramitar compra", "comprar ahora", "buy now", "place order",
                "proceder al pago", "ir a pagar", "complete purchase"),
    closing_note="Revisa el carrito antes de pagar: los precios y la "
                 "disponibilidad los pone la tienda, no yo.",
)

CITA = _pb(
    "cita",
    triggers=("cita", "cita previa", "citas", "reservar", "reserva", "agendar",
              "pedir hora", "turno", "appointment", "book a", "booking"),
    guidance="""FLUJO: PEDIR CITA / RESERVA.
Tu tarea llega HASTA LA PANTALLA DE CONFIRMACIÓN, sin confirmar:
- Sigue el formulario paso a paso; en cada pantalla rellena solo lo que el
  usuario te ha dado y pulsa "siguiente"/"continuar".
- Si un campo pide un dato personal que no tienes (DNI, teléfono, número de
  historia), NO te lo inventes: para y pide al usuario ese dato concreto.
- Elige el hueco que encaje con lo pedido (fecha/hora); si no hay, dilo.
- Al llegar al resumen previo a confirmar, responde "done" describiendo la cita
  exacta (sitio, día, hora) para que el usuario dé el último clic.""",
    stop_answer="He llegado al último paso con todo relleno. La confirmación la "
                "das tú: una cita reservada compromete tu nombre y tu tiempo.",
    hard_stops=("confirmar", "confirm", "reservar ahora", "book now",
                "finalizar reserva", "finalizar cita", "solicitar cita",
                "enviar solicitud", "firmar"),
    closing_note="No he confirmado nada: hasta que pulses tú, no hay cita.",
)

DESCARGA = _pb(
    "descarga",
    triggers=("descarga", "descargar", "descargame", "bajar", "bajate",
              "download", "instalador", "iso", "torrent"),
    guidance="""FLUJO: LOCALIZAR UNA DESCARGA.
Tu tarea es ENCONTRAR EL ENLACE REAL, no descargar ni instalar:
- Navega hasta la página del archivo y localiza el enlace de descarga directo.
- Cuidado con los botones "Download" falsos de la publicidad: el bueno suele
  estar junto al nombre del archivo, su tamaño o su versión.
- Responde "done" con la URL directa COMPLETA y, si la ves, el tamaño y la
  versión. Aithera se encargará después de descargarla.
NO pulses "instalar" ni "ejecutar" NUNCA, ni abras lo descargado.""",
    stop_answer="He parado antes de instalar o ejecutar nada. Localizo la "
                "descarga; abrirla o no es decisión tuya.",
    hard_stops=("instalar", "install", "ejecutar", "run now", "abrir con",
                "open with", "instalar ahora"),
    closing_note="",
)

API_KEY = _pb(
    "api_key",
    triggers=("api key", "api keys", "apikey", "clave api", "clave de api",
              "token de api", "credenciales de la api", "secret key"),
    guidance="""FLUJO: LOCALIZAR DÓNDE SE GENERA UNA CLAVE DE API.
Tu tarea es ENSEÑARLE EL CAMINO al usuario, no crear la clave:
- Ve a la documentación o a la consola del proveedor y localiza la pantalla
  exacta donde se generan las claves.
- Responde "done" con la URL de esa pantalla y los pasos concretos que le
  quedan al usuario, más el plan gratuito o el coste si aparece en la página.
NUNCA inicies sesión, NUNCA generes una clave y NUNCA copies el valor de una
clave que veas en pantalla: eso es del usuario y solo suyo.""",
    stop_answer="Aquí es donde se genera la clave. El registro, el inicio de "
                "sesión y la creación de la clave los haces tú: yo no manejo "
                "tus credenciales.",
    hard_stops=("iniciar sesion", "log in", "login", "sign in", "acceder",
                "continuar con google", "continue with google", "sign up",
                "registrarse", "crear cuenta", "create new secret key",
                "generar clave", "generate key", "create api key",
                "nueva clave", "create key"),
    closing_note="No he generado ninguna clave ni he copiado ningún valor.",
)

FORO = _pb(
    "foro",
    triggers=("foro", "foros", "hilo", "hilos", "reddit", "subreddit", "forum",
              "stackoverflow", "stack overflow", "que opina la gente",
              "que dice la gente", "opiniones en"),
    guidance="""FLUJO: RESEARCH EN UN FORO.
Tu tarea es LEER Y SINTETIZAR, sin participar:
- Busca el tema con el buscador del propio foro.
- Entra en los hilos que de verdad traten el tema; si uno no aporta, vuelve
  atrás en vez de seguir bajando.
- Baja dentro del hilo para leer las respuestas, no solo el primer mensaje: la
  respuesta buena suele estar a mitad.
- Ve quedándote con lo esencial de cada hilo y responde "done" con una síntesis
  que distinga lo que varias personas repiten de lo que dice uno solo, citando
  el título de los hilos de donde sale cada cosa.
NO respondas, no votes, no te suscribas y no publiques nada.""",
    stop_answer="Solo leo: no respondo, no voto y no publico nada a tu nombre.",
    hard_stops=("responder", "reply", "publicar", "post reply", "comentar",
                "votar", "upvote", "downvote", "suscribirse", "seguir tema",
                "unirse", "join"),
    read_only=True,
    closing_note="Es lo que dice la gente en un foro, no una fuente "
                 "verificada: contrástalo antes de darlo por bueno.",
    suggested_steps=35,
)

# El ORDEN importa: gana el primero que case. Se ordenan de más específico a más
# genérico, y la FRONTERA DE SEGURIDAD por delante — «busca en el foro el enlace
# de descarga» activa `descarga` (que avisa de la fuente) en vez de `foro`,
# porque perder el aviso es peor que perder el modo solo-lectura.
PLAYBOOKS: Tuple[Playbook, ...] = (API_KEY, DESCARGA, FORO, CITA, COMPRA)
_POR_NOMBRE: Dict[str, Playbook] = {p.name: p for p in PLAYBOOKS}


def get(name: Optional[str]) -> Optional[Playbook]:
    return _POR_NOMBRE.get((name or "").strip().lower()) if name else None


def detect(goal: str) -> Optional[str]:
    """Qué flujo es este objetivo, o None si no es ninguno de los cinco.

    Determinista y conservador: hace falta una frase del catálogo como palabras
    completas. Ante la duda NO se activa ningún playbook — el bucle genérico de
    C·WEB-3 sigue funcionando igual de bien, así que un falso negativo solo
    cuesta orientación, mientras que un falso positivo pondría fronteras que no
    tocan (por ejemplo, parar en «Confirmar» en una tarea que sí debía enviarse).
    """
    if not goal:
        return None
    for pb in PLAYBOOKS:
        if any(_contiene_frase(goal, t) for t in pb.triggers):
            return pb.name
    return None


def is_hard_stop(playbook: Optional[str], texto: str) -> bool:
    """¿Pulsar esto cruza la frontera de ESTE flujo?

    A diferencia de `webloop.is_sensitive_element` (que abre un gate y puede
    concederse), esto TERMINA el flujo y no lo levanta ningún permiso."""
    pb = get(playbook)
    if pb is None:
        return False
    if not normaliza(texto):
        return False
    return any(marcador_en(texto, h) for h in pb.hard_stops)


_BUSCADOR = ("buscar", "busqueda", "buscador", "search", "consulta", "filtrar",
             "filter", "encontrar", "find", "query", "q")


def is_search_field(texto: str) -> bool:
    """¿Es la caja de búsqueda del sitio?

    Se usa SOLO en modo solo-lectura, para dejar buscar sin dejar escribir en
    ningún otro sitio. Los términos de ≤3 letras (`q`) exigen palabra completa:
    por subcadena, «q» aparece en casi cualquier etiqueta y el modo dejaría de
    servir para nada."""
    if not normaliza(texto):
        return False
    return any(marcador_en(texto, t) for t in _BUSCADOR)


# ---------------------------------------------------------------------------
# Fuentes de descarga poco fiables
# ---------------------------------------------------------------------------
# No es una lista negra de dominios (imposible de mantener y siempre desfasada):
# son las SEÑALES de una descarga que conviene mirar dos veces. El aviso nunca
# bloquea — informa. Bloquear por heurística cerraría descargas legítimas.
_SENALES_RIESGO: Tuple[Tuple[str, str], ...] = (
    ("crack", "el sitio distribuye software crackeado"),
    ("keygen", "el sitio distribuye generadores de claves"),
    ("warez", "es un sitio de warez"),
    ("torrent", "viene de una red de torrents"),
    ("nulled", "es software 'nulled'"),
    ("repack", "es un repack de terceros, no el instalador original"),
    ("unlocked", "es una distribución no oficial"),
    ("skidrow", "viene de un grupo de pirateo"),
    ("fitgirl", "es un repack de terceros"),
)
_EXTENSIONES_EJECUTABLES = (".exe", ".msi", ".bat", ".cmd", ".scr", ".ps1",
                            ".apk", ".dmg", ".pkg", ".jar", ".vbs")


def download_source_warning(url: str) -> str:
    """Aviso honesto sobre de dónde sale un archivo. "" si no hay nada que decir.

    POLÍTICA (doc 32 C·WEB-4): Aithera puede localizar y descargar, pero NUNCA
    ejecuta lo descargado ni da por segura una fuente. El usuario decide con la
    información delante."""
    low = normaliza(url)
    if not low:
        return ""
    motivos = [m for s, m in _SENALES_RIESGO if s in low]
    ejecutable = any(low.split("?")[0].endswith(e) for e in _EXTENSIONES_EJECUTABLES)
    if not motivos and not ejecutable:
        return ""
    partes = []
    if motivos:
        partes.append("Cuidado con esta fuente: " + "; ".join(motivos))
    if ejecutable:
        partes.append("Es un archivo EJECUTABLE")
    return ("⚠ " + ". ".join(partes)
            + ". No lo abro ni lo ejecuto: analízalo con tu antivirus y ábrelo tú "
              "si te fías.")


_RE_URL = re.compile(r"https?://[^\s<>\"')\]]+")


def urls_in(texto: str) -> List[str]:
    """URLs mencionadas en un texto, sin repetir y conservando el orden."""
    vistas: List[str] = []
    for u in _RE_URL.findall(texto or ""):
        u = u.rstrip(".,;:)")
        if u not in vistas:
            vistas.append(u)
    return vistas


# ---------------------------------------------------------------------------
# Secretos que nunca deben acabar en un log
# ---------------------------------------------------------------------------
# Se aplica SIEMPRE, con playbook o sin él: la respuesta del bucle acaba en la
# traza de la misión, en la telemetría y en la memoria. Si el usuario ya tenía
# la sesión abierta y su clave estaba en pantalla, el modelo puede repetirla sin
# malicia — y quedaría escrita para siempre en tres sitios distintos.
_RE_JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{4,}")
_RE_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}")
_RE_PREFIJADO = re.compile(
    r"\b(?:sk-ant-|sk-|sk_live_|pk_live_|rk_live_|ghp_|gho_|ghu_|ghs_|"
    r"github_pat_|xoxb-|xoxp-|xoxa-|hf_|gsk_|AKIA|ASIA|AIza)[A-Za-z0-9_\-]{8,}"
)
_RE_LARGO = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")
OCULTO = "«clave oculta»"


def _es_alta_entropia(cadena: str) -> bool:
    """Mayúsculas Y minúsculas Y dígitos. Es lo que separa una clave de un hash
    de git (40 hex en minúscula, que SÍ es legítimo mencionar) o de un
    identificador largo de una URL."""
    return (any(c.isupper() for c in cadena)
            and any(c.islower() for c in cadena)
            and any(c.isdigit() for c in cadena))


def redact_secrets(texto: str) -> str:
    """Tapa lo que parece una credencial. Conservador: solo formas reconocibles
    o cadenas largas de alta entropía — un identificador normal de una URL, un
    SHA de git o un código de producto se dejan intactos."""
    if not texto:
        return texto
    fuera = _RE_JWT.sub(OCULTO, texto)
    fuera = _RE_BEARER.sub(f"Bearer {OCULTO}", fuera)
    fuera = _RE_PREFIJADO.sub(OCULTO, fuera)
    return _RE_LARGO.sub(
        lambda m: OCULTO if _es_alta_entropia(m.group(0)) else m.group(0), fuera)


# ---------------------------------------------------------------------------
# Cierre del flujo
# ---------------------------------------------------------------------------
def handoff(playbook: Optional[str], answer: str) -> Optional[Dict[str, object]]:
    """Qué tiene que hacer el bucle GENERAL después de este flujo, si algo.

    El caso real es la descarga: este flujo LOCALIZA el enlace y ahí termina su
    competencia; bajarlo es de `download_tool`. Devolverlo explícito evita que
    el bucle de fuera tenga que adivinarlo — y evita que `browser_tool` tenga
    que importar un interno del TIE para calcularlo (doc 16)."""
    if get(playbook) is None or (playbook or "") != "descarga":
        return None
    enlaces = urls_in(answer or "")
    if not enlaces:
        return None
    return {
        "tool": "download", "action": "download_url",
        "params": {"url": enlaces[0]},
        "note": ("bájala con download.download_url; NUNCA la ejecutes ni la "
                 "instales tú"),
    }


def finish(playbook: Optional[str], answer: str) -> Tuple[str, List[str]]:
    """Post-proceso determinista de la respuesta final: (respuesta, notas).

    Las notas NO son limitaciones (eso es «lo que no pude hacer»): son lo que el
    usuario tiene que saber para decidir — de dónde sale un archivo, que nadie
    ha confirmado nada todavía, que un foro no es una fuente verificada."""
    limpio = redact_secrets(answer or "")
    notas: List[str] = []
    if limpio != (answer or ""):
        notas.append("He ocultado lo que parecía una credencial: las claves no "
                     "se guardan en el historial de una misión.")

    pb = get(playbook)
    if pb is None:
        return limpio, notas

    if pb.name == "descarga":
        for u in urls_in(limpio):
            aviso = download_source_warning(u)
            if aviso and aviso not in notas:
                notas.append(aviso)
    if pb.closing_note and pb.closing_note not in notas:
        notas.append(pb.closing_note)
    return limpio, notas
