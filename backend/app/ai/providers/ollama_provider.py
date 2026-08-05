# Ollama AI Provider
import json
import httpx
from typing import Dict, Any, List, Optional, AsyncIterator
from .base import BaseAIProvider, normalize_history, normalize_images


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

    # `with_model()` lo hereda de BaseAIProvider (V1.0): los modelos locales
    # (Qwen, Ornith, DeepSeek…) comparten runtime, así que son un proveedor con
    # varios modelos — el clon reusa el mismo cliente httpx.

    def _endpoint_and_payload(self, prompt: str, system_prompt: Optional[str],
                              history: Optional[List[Dict[str, Any]]], stream: bool,
                              images: Optional[List[str]] = None):
        """[R6.5a] Ollama tiene DOS APIs y solo una admite conversacion:
          - `/api/generate`: un prompt suelto + system. Es la que se ha usado
            siempre y NO puede llevar historial.
          - `/api/chat`: array de mensajes, como OpenAI.

        Sin historial se sigue usando `/api/generate` con el MISMO payload de
        siempre — cero regresion, byte a byte. Solo se cambia de endpoint cuando
        de verdad hay turnos previos que enviar. Ojo: las dos APIs devuelven el
        texto en sitios distintos (`response` vs `message.content`), y de eso se
        encarga `_extract_chunk`."""
        turnos = normalize_history(history)
        # [B·WEB-2] Ollama es el mas comodo de los cuatro formatos: `images` es
        # una lista de base64 PUROS (sin data-URI) que va DENTRO del propio
        # payload — en `/api/generate` al nivel de arriba, y en `/api/chat`
        # dentro del mensaje del usuario. Sin imagenes, todo queda byte a byte
        # como siempre.
        imgs = normalize_images(images)
        if not turnos:
            payload = {"model": self.model, "prompt": prompt, "stream": stream}
            if system_prompt:
                payload["system"] = system_prompt
            if imgs:
                payload["images"] = imgs
            return f"{self.base_url}/api/generate", payload, False

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(turnos)
        turno_actual: Dict[str, Any] = {"role": "user", "content": prompt}
        if imgs:
            turno_actual["images"] = imgs
        messages.append(turno_actual)
        return f"{self.base_url}/api/chat", {
            "model": self.model, "messages": messages, "stream": stream,
        }, True

    @staticmethod
    def _extract_chunk(data: Dict[str, Any], es_chat: bool) -> str:
        """El texto de una respuesta, venga del endpoint que venga."""
        if es_chat:
            return (data.get("message") or {}).get("content", "")
        return data.get("response", "")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       messages: Optional[List[Dict[str, Any]]] = None,
                       images: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate response using Ollama."""
        url, payload, es_chat = self._endpoint_and_payload(prompt, system_prompt, messages,
                                                           stream=False, images=images)

        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            response = await client.post(url, json=payload, timeout=180.0)
            response.raise_for_status()
            data = response.json()

            return {
                "response": self._extract_chunk(data, es_chat),
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

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                              messages: Optional[List[Dict[str, Any]]] = None) -> AsyncIterator[str]:
        """Generate response using Ollama, yielding incremental text chunks."""
        url, payload, es_chat = self._endpoint_and_payload(prompt, system_prompt, messages, stream=True)

        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            async with client.stream("POST", url, json=payload, timeout=180.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = self._extract_chunk(data, es_chat)
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except Exception as e:
            yield f"[Error conectando con Ollama: {str(e)}]"

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            client = self._get_client()  # V0.9 A2a: cliente persistente por proveedor
            response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
