# Ollama AI Provider
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """Ollama local AI provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        super().__init__(model=model)
        self.base_url = base_url.rstrip("/")

    def get_default_model(self) -> str:
        return "llama3"

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Ollama."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                return {
                    "response": data.get("response", ""),
                    "model": self.model,
                    "provider": self.provider_name
                }
        except Exception as e:
            return {
                "response": f"Error connecting to Ollama: {str(e)}",
                "model": self.model,
                "provider": self.provider_name,
                "error": True
            }

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Generate response using Ollama, yielding incremental text chunks."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
        except Exception as e:
            yield f"[Error conectando con Ollama: {str(e)}]"

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False
