# Anthropic AI Provider
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key=api_key, model=model)
        self.api_url = "https://api.anthropic.com/v1/messages"

    def get_default_model(self) -> str:
        return "claude-sonnet-4-6"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _build_payload(self, prompt: str, system_prompt: Optional[str], stream: bool) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream
        }
        if system_prompt:
            payload["system"] = system_prompt
        return payload

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Anthropic Claude."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        payload = self._build_payload(prompt, system_prompt, stream=False)

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
                    "response": data["content"][0]["text"],
                    "model": self.model,
                    "provider": self.provider_name,
                    "tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                }
        except Exception as e:
            return {
                "response": f"Error connecting to Anthropic: {str(e)}",
                "model": self.model,
                "provider": self.provider_name,
                "error": True
            }

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Generate response using Anthropic Claude, yielding incremental text chunks via SSE."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        payload = self._build_payload(prompt, system_prompt, stream=True)

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if data.get("type") == "content_block_delta":
                            chunk = data.get("delta", {}).get("text", "")
                            if chunk:
                                yield chunk
                        elif data.get("type") == "message_stop":
                            break
        except Exception as e:
            yield f"[Error conectando con Anthropic: {str(e)}]"

    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        if not self.api_key:
            return False
        return True
