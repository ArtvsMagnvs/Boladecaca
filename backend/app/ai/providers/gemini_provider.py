# Google Gemini AI Provider
#
# La API de Gemini no es compatible con el formato de OpenAI (usa
# "contents"/"parts" en vez de "messages", y la key va en la query string en
# vez de en un header Authorization), asi que tiene su propia implementacion
# en vez de heredar de OpenAICompatibleProvider.
import json
import httpx
from typing import Dict, Any, List, Optional, AsyncIterator
from .base import BaseAIProvider, IMAGE_MIME_DEFAULT, normalize_history, normalize_images


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

    def _build_payload(self, prompt: str, system_prompt: Optional[str],
                       history: Optional[List[Dict[str, Any]]] = None,
                       images: Optional[List[str]] = None) -> Dict[str, Any]:
        """[R6.5a] Gemini es el que mas se aleja del resto: no usa "messages"
        sino "contents", el texto va envuelto en "parts", y al asistente lo
        llama "model" en vez de "assistant" — mandarle "assistant" es un 400.
        El system tampoco va en el array: es "systemInstruction".

        [B·WEB-2] Las imagenes son otro "part" del MISMO turno del usuario:
        `inline_data` con mime_type + base64. Van ANTES del texto a proposito —
        la propia doc de Gemini recomienda imagen-primero cuando la pregunta se
        refiere a ella, que es justo nuestro caso ("mira esta captura y...")."""
        contents = [
            {"role": ("model" if m["role"] == "assistant" else "user"),
             "parts": [{"text": m["content"]}]}
            for m in normalize_history(history)
        ]
        parts: List[Dict[str, Any]] = [
            {"inline_data": {"mime_type": IMAGE_MIME_DEFAULT, "data": img}}
            for img in normalize_images(images)
        ]
        parts.append({"text": prompt})
        contents.append({"role": "user", "parts": parts})
        payload: Dict[str, Any] = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        return payload

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       messages: Optional[List[Dict[str, Any]]] = None,
                       images: Optional[List[str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            response = await client.post(url, json=self._build_payload(prompt, system_prompt, messages, images), timeout=180.0)
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

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                              messages: Optional[List[Dict[str, Any]]] = None) -> AsyncIterator[str]:
        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            async with client.stream("POST", url, json=self._build_payload(prompt, system_prompt, messages), timeout=180.0) as response:
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
