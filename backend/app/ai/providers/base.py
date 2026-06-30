# Base AI Provider Interface
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator


class BaseAIProvider(ABC):
    """Base class for all AI providers."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.get_default_model()

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
