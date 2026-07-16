# Google Gemini AI Provider
#
# La API de Gemini no es compatible con el formato de OpenAI (usa
# "contents"/"parts" en vez de "messages", y la key va en la query string en
# vez de en un header Authorization), asi que tiene su propia implementacion
# en vez de heredar de OpenAICompatibleProvider.
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Google Gemini (Generative Language API) provider."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key=api_key, model=model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def get_default_model(self) -> str:
        return "gemini-pro"

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _build_payload(self, prompt: str, system_prompt: Optional[str]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        return payload

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            response = await client.post(url, json=self._build_payload(prompt, system_prompt), timeout=180.0)
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return {
                "response": text,
                "model": self.model,
                "provider": self.provider_name,
                "tokens": usage.get("totalTokenCount", 0),
            }
        except Exception as e:
            return {
                "response": f"Error connecting to Gemini: {str(e)}",
                "model": self.model,
                "provider": self.provider_name,
                "error": True,
            }

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            async with client.stream("POST", url, json=self._build_payload(prompt, system_prompt), timeout=180.0) as response:
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
                    try:
                        chunk = data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        chunk = ""
                    if chunk:
                        yield chunk
        except Exception as e:
            yield f"[Error conectando con Gemini: {str(e)}]"

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            response = await client.get(f"{self.base_url}?key={self.api_key}", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
