# AI Manager - Centralized AI service management
from typing import Optional, Dict, Any, AsyncIterator
import os

from .providers.base import BaseAIProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider


class AIManager:
    """Manages AI providers and chat interactions."""

    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.current_provider: Optional[BaseAIProvider] = None
        self.current_provider_name: str = "ollama"
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available AI providers."""
        # Ollama (local)
        self.providers["ollama"] = OllamaProvider(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3")
        )

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self.providers["openai"] = OpenAIProvider(
                api_key=openai_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4")
            )

        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            self.providers["anthropic"] = AnthropicProvider(
                api_key=anthropic_key,
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            )

        # Set default provider
        default_provider = os.getenv("AI_PROVIDER", "ollama")
        if default_provider in self.providers:
            self.current_provider = self.providers[default_provider]
            self.current_provider_name = default_provider

    def set_provider(self, provider_name: str, model: Optional[str] = None) -> bool:
        """Switch to a different AI provider."""
        if provider_name not in self.providers:
            return False

        self.current_provider = self.providers[provider_name]
        self.current_provider_name = provider_name

        if model:
            self.current_provider.model = model

        return True

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message and get a complete (non-streaming) response."""
        if not self.current_provider:
            return {
                "response": "No AI provider configured",
                "error": True
            }

        return await self.current_provider.generate(message, system_prompt)

    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Send a chat message and stream the response as incremental text chunks."""
        if not self.current_provider:
            yield "No hay un proveedor de IA configurado."
            return

        async for chunk in self.current_provider.generate_stream(message, system_prompt):
            yield chunk

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the current AI provider."""
        if not self.current_provider:
            return {
                "provider": None,
                "model": None,
                "healthy": False
            }

        healthy = await self.current_provider.health_check()

        return {
            "provider": self.current_provider_name,
            "model": self.current_provider.model,
            "healthy": healthy
        }

    def get_available_providers(self) -> list:
        """Get list of available provider names."""
        return list(self.providers.keys())


# Global AI manager instance
ai_manager = AIManager()
