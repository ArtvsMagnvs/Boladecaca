# Base AI Provider Interface
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator, List

import httpx


# ---------------------------------------------------------------------------
# Historial de conversacion (R6.5a) — el canal que faltaba
# ---------------------------------------------------------------------------
# EL CONTRATO, en una linea: `messages` son los turnos ANTERIORES; el turno
# ACTUAL sigue viajando en `prompt`, y el system en `system_prompt`.
#
# Por que asi y no metiendo todo en `messages`: mantiene `prompt` con el mismo
# significado que ha tenido siempre (cero regresion para los ~15 call-sites que
# ya existen), y deja el system aparte — que es lo que Anthropic y Gemini
# necesitan de todas formas, porque en sus APIs NO va dentro del array.
#
# Formato canonico: [{"role": "user"|"assistant", "content": "..."}]. Cada
# proveedor lo traduce a lo suyo (Gemini usa "model" en vez de "assistant";
# Ollama necesita otro endpoint; Claude Code no tiene API de mensajes y lo
# aplana). Un proveedor que ignore el parametro sigue funcionando igual: por eso
# es opcional en toda la jerarquia.
VALID_ROLES = ("user", "assistant")


def normalize_history(messages: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Sanea el historial ANTES de que lo vea ningun proveedor.

    Es una frontera de confianza: estos turnos vienen de la BD y acabaran en el
    payload de una API externa. Se descartan los que no tienen contenido, se
    normalizan los roles, y se IGNORAN los `system` (el system prompt tiene su
    propio parametro — colar uno aqui podria pisar las instrucciones reales).

    Nunca lanza: ante una entrada rara devuelve lo que si es utilizable. Un
    historial mal formado no puede tumbar una respuesta."""
    if not messages:
        return []
    out: List[Dict[str, str]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        role = str(m.get("role") or "").strip().lower()
        if role == "system":
            continue          # el system va por `system_prompt`, no por aqui
        if role not in VALID_ROLES:
            role = "user"     # ante la duda, el rol menos privilegiado
        out.append({"role": role, "content": content})
    return out


# ---------------------------------------------------------------------------
# Imagenes (B·WEB-2, doc 32) — el canal multimodal
# ---------------------------------------------------------------------------
# EL CONTRATO: `images` son imagenes en base64 SIN el prefijo `data:`, en el
# orden en que el modelo debe verlas. Van SIEMPRE con el turno actual (el de
# `prompt`) — que es el caso de uso real: "mira ESTA captura y dime donde esta
# el boton". Adjuntar imagenes a turnos pasados es innecesario y multiplicaria
# el coste de cada llamada.
#
# Solo lo implementan los proveedores REALMENTE multimodales (ver
# `mel/catalog.py::supports_vision`). Los demas ni siquiera reciben el
# parametro: el MEL no les envia peticiones de vision, y si por lo que fuera
# llegara una, el registry lanza en vez de degradar en silencio — un modelo que
# no ve la imagen respondería igual, inventandose lo que "ve".
IMAGE_MIME_DEFAULT = "image/png"


def normalize_images(images: Optional[List[str]]) -> List[str]:
    """Sanea la lista de imagenes ANTES de que la vea ningun proveedor.

    Acepta tanto base64 puro como un data-URI completo
    (`data:image/png;base64,iVBOR...`) y devuelve SIEMPRE base64 puro — asi
    cada proveedor lo envuelve en su formato sin tener que adivinar. Descarta
    entradas vacias o que no sean texto. Nunca lanza."""
    if not images:
        return []
    out: List[str] = []
    for img in images:
        if not isinstance(img, str):
            continue
        dato = img.strip()
        if not dato:
            continue
        if dato.startswith("data:"):
            _, _, dato = dato.partition(",")
            dato = dato.strip()
        if dato:
            out.append(dato)
    return out


class BaseAIProvider(ABC):
    """Base class for all AI providers."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.get_default_model()
        # V0.9 (A2a, doc 12 A2): un unico httpx.AsyncClient POR PROVEEDOR, creado
        # lazy y reutilizado entre requests (mantiene vivas las conexiones TLS en
        # vez de rehacer el handshake en cada chat — antes se abria un
        # `async with httpx.AsyncClient(...)` por llamada, +100-300ms en el
        # primer chunk). Se cierra en shutdown via AIManager.aclose(). El timeout
        # sigue siendo POR REQUEST (se pasa en cada .post/.stream), no del cliente.
        self._http: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Cliente HTTP compartido del proveedor (lazy). Si se cerro (shutdown)
        se recrea, para que el proveedor siga siendo utilizable si el proceso
        vuelve a necesitarlo."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient()
        return self._http

    def with_model(self, model: str) -> "BaseAIProvider":
        """[V1.0 multi-modelo] Vista de ESTE proveedor apuntando a otro de sus
        modelos, compartiendo credenciales y el cliente httpx persistente.

        Por qué: un proveedor = una API key, pero MUCHOS modelos (los 4 de Claude
        Code, los GPT-*, los Qwen, los locales de Ollama…). El MEL necesita poder
        elegir `code -> opus` y `chat -> haiku` dentro del MISMO proveedor. En vez
        de añadir un parámetro por-llamada a `generate()` en los 11 proveedores,
        se clona la instancia cambiando solo el modelo: sin handshake TLS extra,
        sin reinstanciar nada, y sin tocar el contrato de la clase.

        Devuelve `self` si ya apunta a ese modelo (caso común, coste cero)."""
        if not model or model == self.model:
            return self
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)   # comparte _http, api_key, base_url…
        clone.model = model
        return clone

    async def aclose(self) -> None:
        """Cierra el cliente compartido (llamado por AIManager.aclose() en el
        shutdown del lifespan). Fail-soft: nunca lanza."""
        try:
            if self._http is not None and not self._http.is_closed:
                await self._http.aclose()
        except Exception:
            pass
        finally:
            self._http = None

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model for this provider."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       messages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a response from the AI (non-streaming).

        `messages` [R6.5a]: turnos ANTERIORES de la conversacion, formato
        canonico [{"role": "user"|"assistant", "content": str}]. El turno actual
        va en `prompt` y el system en `system_prompt` (ver `normalize_history`).
        Opcional en toda la jerarquia: un proveedor que lo ignore sigue siendo
        valido y se comporta como siempre.

        `images` [B·WEB-2]: NO va en esta firma a proposito. Solo lo aceptan los
        proveedores REALMENTE multimodales (Gemini, Anthropic, los compatibles
        con OpenAI y Ollama con un modelo VL), cada uno anadiendolo a su propia
        `generate`. Ponerlo aqui obligaria a los que no ven a aceptarlo y
        ignorarlo en silencio — y una imagen ignorada en silencio es justo lo
        que produce una respuesta inventada. Que el resto lance `TypeError` es
        el comportamiento QUERIDO: el registry lo convierte en un fallo claro.

        Returns:
            Dict with keys: 'response' (str), 'model' (str), 'tokens' (int, optional)
        """
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                              messages: Optional[List[Dict[str, Any]]] = None) -> AsyncIterator[str]:
        """
        Generate a response from the AI as a stream of text chunks.

        `messages`: igual que en `generate`.

        Yields:
            str: incremental text chunks as they arrive from the provider.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is accessible."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
