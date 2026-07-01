# Shared base for providers that expose an OpenAI-compatible Chat Completions API.
#
# OpenAI, DeepSeek, OpenRouter and Grok (xAI) all accept the same request shape
# (POST {"model", "messages": [...], "stream": bool}) and the same streaming SSE
# format ("data: {...}" chunks with choices[0].delta.content). Implementing this
# once here avoids repeating the same request/parsing logic per provider, which
# was exactly the kind of duplication flagged in the Fase 0 audit.
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class OpenAICompatibleProvider(BaseAIProvider):
    """Base class for OpenAI-compatible Chat Completions providers."""

    api_url: str = ""
    default_model_name: str = ""
    provider_id: str = "openai-compatible"
    extra_headers: Dict[str, str] = {}
    # Algunos proveedores OpenAI-compatibles no usan "max_tokens" o tienen un
    # tope distinto a los 4096 por defecto (ej. MiniMax exige el nombre de
    # campo "max_completion_tokens" con un maximo documentado de 2048; pedir
    # 4096 ahi devuelve 400 Bad Request aunque la API key y el modelo sean
    # correctos - exactamente el bug detectado con MiniMax).
    max_tokens_param: str = "max_tokens"
    max_tokens_value: int = 4096

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        if base_url:
            self.api_url = base_url
        super().__init__(api_key=api_key, model=model)

    def get_default_model(self) -> str:
        return self.default_model_name

    @property
    def provider_name(self) -> str:
        return self.provider_id

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _build_messages(self, prompt: str, system_prompt: Optional[str]):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system_prompt),
            self.max_tokens_param: self.max_tokens_value,
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(self.api_url, json=payload, headers=self._headers())
                response.raise_for_status()
                data = response.json()
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "model": self.model,
                    "provider": self.provider_name,
                    "tokens": data.get("usage", {}).get("total_tokens", 0),
                }
        except Exception as e:
            return {
                "response": f"Error connecting to {self.provider_name}: {str(e)}",
                "model": self.model,
                "provider": self.provider_name,
                "error": True,
            }

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system_prompt),
            self.max_tokens_param: self.max_tokens_value,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=self._headers()) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]" or not data_str:
                            if data_str == "[DONE]":
                                break
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
            yield f"[Error conectando con {self.provider_name}: {str(e)}]"

    async def health_check(self) -> bool:
        """
        Probar conexion: la mayoria de estas APIs no exponen un endpoint de salud
        dedicado, asi que se hace una llamada minima real (max_tokens=1).

        ANTES esto aceptaba cualquier status_code que no fuera 401/403/5xx como
        "sano" - lo que significaba que un 404 (endpoint mal escrito o dominio
        equivocado) o un 400 (modelo invalido) se reportaban como "Conexion
        correcta". Asi fallo MiniMax: el endpoint antiguo respondia con un
        error que no era 401/403/5xx, "Probar conexion" decia que todo iba
        bien, pero el chat real nunca encontraba una respuesta valida.

        Ahora se exige HTTP 200 exacto, y ademas se revisa el cuerpo por si el
        proveedor reporta un error de aplicacion DENTRO de una respuesta 200
        (ej. el campo "base_resp" que usa MiniMax, o un campo "error" generico
        que devuelven algunos gateways/proxies OpenAI-compatibles).
        """
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "ping"}],
                        self.max_tokens_param: 1,
                    },
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    return False
                try:
                    data = response.json()
                except Exception:
                    return True  # 200 sin cuerpo JSON parseable: se da por bueno.
                if isinstance(data, dict):
                    if data.get("error"):
                        return False
                    base_resp = data.get("base_resp")
                    if isinstance(base_resp, dict) and base_resp.get("status_code", 0) != 0:
                        return False
                return True
        except Exception:
            return False
