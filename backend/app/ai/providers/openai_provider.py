# OpenAI AI Provider
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key=api_key, model=model)
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def get_default_model(self) -> str:
        return "gpt-4"

    @property
    def provider_name(self) -> str:
        return "openai"

    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using OpenAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system_prompt),
            "max_tokens": 4096
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "response": data["choices"][0]["message"]["content"],
                    "model": self.model,
                    "provider": self.provider_name,
                    "tokens": data.get("usage", {}).get("total_tokens", 0)
                }
        except Exception as e:
            return {
                "response": f"Error connecting to OpenAI: {str(e)}",
                "model": self.model,
                "provider": self.provider_name,
                "error": True
            }

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Generate response using OpenAI, yielding incremental text chunks via SSE."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system_prompt),
            "max_tokens": 4096,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        chunk = delta.get("content")
                        if chunk:
                            yield chunk
        except Exception as e:
            yield f"[Error conectando con OpenAI: {str(e)}]"

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except:
            return False
