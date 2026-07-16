# Base AI Provider Interface
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator

import httpx


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
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response from the AI (non-streaming).

        Returns:
            Dict with keys: 'response' (str), 'model' (str), 'tokens' (int, optional)
        """
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """
        Generate a response from the AI as a stream of text chunks.

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
