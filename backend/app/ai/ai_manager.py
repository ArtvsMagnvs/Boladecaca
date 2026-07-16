# AI Manager - Centralized AI service management (Fase 2 - Sistema de IA)
#
# A partir de la Fase 2, la fuente de verdad de "que proveedores existen, con
# que modelo y cual esta activo" es la tabla ai_provider_configs en la base
# de datos (gestionable desde Configuracion -> Modelos IA), no las variables
# de entorno. Las variables de entorno solo se usan como arranque inicial en
# una instalacion nueva (primera vez que no hay ninguna fila en la tabla), y
# ese arranque inicial se persiste en la base de datos para que las siguientes
# veces ya vengan de ahi.
#
# V0.3 - Fallback automatico MiniMax -> Ollama:
# El proveedor primario configurado por el usuario (por defecto MiniMax con
# su API key hardcodeada y modelo M2.7-highspeed) es el que se intenta
# primero. Si falla por error de red, 5xx, 401/403 (key invalida) o timeout,
# el manager cambia transparentemente a Ollama (que corre en local sin
# internet) para que el usuario nunca vea un chat roto. Cada 60 segundos se
# reintenta el proveedor primario para volver a el en cuanto sea posible.
from typing import Optional, Dict, Any, AsyncIterator, List
import os
import time

from .providers.base import BaseAIProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider
from .providers.minimax_provider import MinimaxProvider, MINIMAX_HARDCODED_KEY
from .providers.deepseek_provider import DeepSeekProvider
from .providers.openrouter_provider import OpenRouterProvider
from .providers.grok_provider import GrokProvider
from .catalog import PROVIDER_CATALOG, get_provider_info, list_provider_names

from app.db.database import SessionLocal
from app.db.models import AIProviderConfig
# V0.8 (hardening): las API keys se guardan CIFRADAS en reposo (DPAPI). Se
# cifran al persistir y se descifran solo al instanciar el proveedor.
from app.core import secrets


def _enc(v: Optional[str]) -> Optional[str]:
    """Cifra una api_key para guardarla; conserva None/'' (ej. Ollama)."""
    return secrets.encrypt(v) if v else v


def _dec(v: Optional[str]) -> Optional[str]:
    """Descifra una api_key guardada; conserva None/'' y tolera texto plano legado."""
    return secrets.decrypt(v) if v else v


# Proveedores que no requieren API key (hoy solo Ollama, local).
NO_KEY_PROVIDERS = {"ollama"}

# Fabrica: nombre de proveedor -> clase que lo implementa.
PROVIDER_CLASSES = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "minimax": MinimaxProvider,
    "deepseek": DeepSeekProvider,
    "openrouter": OpenRouterProvider,
    "grok": GrokProvider,
}

# Fallback por defecto cuando el proveedor primario falla: Ollama local,
# que no depende de internet. Constante a nivel de modulo para que cualquier
# parte del codigo pueda referirse a la misma politica.
DEFAULT_FALLBACK_PROVIDER = "ollama"

# Tiempo entre reintentos del proveedor primario (en segundos). Mientras
# este timer no haya expirado, seguimos usando el fallback sin reintentar.
FALLBACK_RETRY_INTERVAL_S = 60.0


def _instantiate_provider(provider_name: str, model: Optional[str], api_key: Optional[str], base_url: Optional[str]) -> Optional[BaseAIProvider]:
    """Build a provider instance from its name + stored config. Returns None for unknown providers."""
    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class:
        return None

    catalog_info = get_provider_info(provider_name)
    resolved_model = model or catalog_info.get("default_model") or None

    if provider_name == "ollama":
        return OllamaProvider(
            base_url=base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=resolved_model or "llama3",
        )

    # All other providers take (api_key, model[, base_url for OpenAI-compatible ones]).
    kwargs: Dict[str, Any] = {"api_key": api_key, "model": resolved_model}
    if base_url and hasattr(provider_class, "api_url"):
        kwargs["base_url"] = base_url
    try:
        return provider_class(**kwargs)
    except TypeError:
        # GeminiProvider/AnthropicProvider don't accept base_url.
        kwargs.pop("base_url", None)
        return provider_class(**kwargs)


def _resolve_minimax_key() -> Optional[str]:
    """Resuelve la API key de MiniMax con la cadena de prioridad correcta:
    1. Variable de entorno MINIMAX_API_KEY (si esta definida y no vacia)
    2. Constante hardcodeada en minimax_provider.py (la del usuario)

    Asi, si el usuario quiere sobrescribir la hardcoded por una nueva desde
    .env, puede hacerlo; si no, usamos la hardcoded que ya esta probada.
    """
    env_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if env_key:
        return env_key
    if MINIMAX_HARDCODED_KEY and MINIMAX_HARDCODED_KEY.strip():
        return MINIMAX_HARDCODED_KEY.strip()
    return None


class AIManager:
    """Manages AI providers, chat interactions and automatic fallback."""

    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.current_provider: Optional[BaseAIProvider] = None
        self.current_provider_name: str = "ollama"

        # Cache de health_check: la pantalla de Dashboard llamaba a /ai/status
        # (que dispara una llamada de red REAL al proveedor externo activo,
        # con hasta 10s de timeout) cada vez que se abria esa pantalla. Esto
        # congelaba la interfaz visiblemente en cada clic. Con una cache de
        # 30s, abrir/cerrar Dashboard varias veces seguidas no repite la
        # llamada externa cada vez.
        self._health_cache: Dict[str, tuple] = {}  # provider_name -> (timestamp, healthy)

        # Estado de fallback: cuando el proveedor primario falla, guardamos
        # un timestamp "no reintentar hasta" para no martillear al proveedor
        # caido. Tambien recordamos si estamos en modo fallback para que la
        # UI pueda avisar al usuario.
        self._fallback_until: float = 0.0
        self._fallback_active: bool = False
        self._primary_provider_name: Optional[str] = None
        self._health_cache_ttl = 30.0

        self._initialize_providers()

    # ------------------------------------------------------------------
    # Carga inicial
    # ------------------------------------------------------------------

    def _initialize_providers(self):
        """Load configured providers from the database (Fase 2), bootstrapping from env vars on first run.

        V0.3 - Migracion suave de MiniMax: si la fila existente tiene un
        modelo antiguo (cualquiera que no sea M2.7 / M2.7-highspeed / M2.5 /
        M2.1), lo actualizamos a "MiniMax-M2.7-highspeed" que es el modelo
        por defecto recomendado. Esto evita que un usuario con una BD de
        V0.2 siga intentando usar un modelo inexistente y reciba siempre
        400 Bad Request sin entender por que."""
        db = SessionLocal()
        try:
            rows = db.query(AIProviderConfig).all()

            if not rows:
                self._bootstrap_from_env(db)
                rows = db.query(AIProviderConfig).all()

            # Migracion V0.3: actualizar modelos MiniMax obsoletos a highspeed.
            minimax_valid_models = {
                "MiniMax-M2.7",
                "MiniMax-M2.7-highspeed",
                "MiniMax-M2.5",
                "MiniMax-M2.1",
            }
            minimax_updated = False
            for row in rows:
                if row.provider == "minimax" and row.model not in minimax_valid_models:
                    row.model = "MiniMax-M2.7-highspeed"
                    minimax_updated = True
            if minimax_updated:
                db.commit()

            active_name = None
            for row in rows:
                instance = _instantiate_provider(row.provider, row.model, _dec(row.api_key), row.base_url)
                if instance:
                    self.providers[row.provider] = instance
                    if row.is_active:
                        active_name = row.provider

            # Ollama siempre disponible como fallback local, incluso sin fila en BD.
            if "ollama" not in self.providers:
                self.providers["ollama"] = _instantiate_provider("ollama", None, None, None)

            self.current_provider_name = active_name or DEFAULT_FALLBACK_PROVIDER
            self.current_provider = self.providers.get(self.current_provider_name) or self.providers[DEFAULT_FALLBACK_PROVIDER]
            # Recordamos el proveedor primario (el "verdadero" preferido) para
            # poder volver a el tras un fallback.
            self._primary_provider_name = self.current_provider_name
        finally:
            db.close()

    def _bootstrap_from_env(self, db):
        """First-run only: migrate legacy .env-based config (Fase <2) into the DB.

        V0.3: MiniMax SIEMPRE se siembra (con env var o hardcoded key), porque
        es el proveedor primario que el usuario quiere usar por defecto. Si
        no hay ninguna fila activa despues del seed, se marca MiniMax como
        activo. Ollama se siembra tambien (sin api_key) para garantizar que
        el fallback local existe desde el primer arranque.
        """
        seeds: List[tuple] = [
            ("ollama", os.getenv("OLLAMA_MODEL", "llama3"), None, os.getenv("OLLAMA_BASE_URL")),
        ]
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            seeds.append(("openai", os.getenv("OPENAI_MODEL") or None, openai_key, None))
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            seeds.append(("anthropic", os.getenv("ANTHROPIC_MODEL") or None, anthropic_key, None))
        # FIX V0.3: Minimax se siembra SIEMPRE usando la cadena de prioridad
        # env var -> hardcoded. Antes solo se sembraba si MINIMAX_API_KEY
        # estaba en el .env, lo que dejaba al usuario sin poder usar el
        # proveedor aunque la hardcoded key existiera.
        minimax_key = _resolve_minimax_key()
        if minimax_key:
            seeds.append((
                "minimax",
                os.getenv("MINIMAX_MODEL", "MiniMax-M2.7-highspeed"),
                minimax_key,
                None,
            ))
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            seeds.append(("deepseek", os.getenv("DEEPSEEK_MODEL") or None, deepseek_key, None))
        grok_key = os.getenv("GROK_API_KEY", "")
        if grok_key:
            seeds.append(("grok", os.getenv("GROK_MODEL") or None, grok_key, None))
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key:
            seeds.append(("gemini", os.getenv("GEMINI_MODEL") or None, gemini_key, None))

        # FIX V0.3: si AI_PROVIDER no esta definido, por defecto usamos
        # MiniMax (que es lo que el usuario quiere). Si AI_PROVIDER=ollama
        # o cualquier otro, respetamos la eleccion explicita.
        default_provider = os.getenv("AI_PROVIDER", "").strip().lower()
        if not default_provider:
            default_provider = "minimax" if any(p == "minimax" for p, *_ in seeds) else "ollama"

        for provider, model, api_key, base_url in seeds:
            row = AIProviderConfig(
                provider=provider,
                model=model,
                api_key=_enc(api_key),  # cifrada en reposo
                base_url=base_url,
                is_active=(provider == default_provider),
            )
            db.add(row)
        db.commit()

    # ------------------------------------------------------------------
    # Fallback automatico MiniMax -> Ollama
    # ------------------------------------------------------------------

    def _is_fallback_blocked(self) -> bool:
        """Devuelve True si estamos dentro del periodo "no reintentar el primario".
        Asi evitamos martillear a un proveedor caido (ej. sin internet) cada
        vez que el usuario envia un mensaje."""
        return time.monotonic() < self._fallback_until

    def _activate_fallback(self, reason: str, log_func=None):
        """Cambia al proveedor fallback (Ollama) y bloquea reintentos del
        primario durante FALLBACK_RETRY_INTERVAL_S segundos.

        Args:
            reason: texto corto explicando por que se activo el fallback
                (para logs y para mostrarlo en la UI).
            log_func: callable opcional para emitir logs (se inyecta para
                no acoplar AIManager al modulo de logging_config).
        """
        fallback = self.providers.get(DEFAULT_FALLBACK_PROVIDER)
        if not fallback or self.current_provider_name == DEFAULT_FALLBACK_PROVIDER:
            # Ya estamos en fallback o no hay fallback disponible: no hacemos nada.
            self._fallback_active = True
            return

        primary = self.current_provider_name
        self.current_provider = fallback
        self.current_provider_name = DEFAULT_FALLBACK_PROVIDER
        self._fallback_active = True
        self._fallback_until = time.monotonic() + FALLBACK_RETRY_INTERVAL_S
        # Invalidamos la cache de salud del primario para forzar un recheck
        # en el proximo intento de "volver al primario".
        self._health_cache.pop(primary, None)

        msg = (
            f"Fallback automatico activado: {primary} -> {DEFAULT_FALLBACK_PROVIDER}. "
            f"Motivo: {reason}. Reintento del primario en {FALLBACK_RETRY_INTERVAL_S:.0f}s."
        )
        if log_func:
            log_func(msg)
        else:
            print(f"[AIManager] {msg}")

    async def _try_restore_primary(self) -> bool:
        """Si ha pasado el tiempo de bloqueo del fallback y el primario
        responde OK al health check, vuelve a el. Devuelve True si se
        restauro, False en caso contrario.

        Version async (V0.3): antes era sync y usaba asyncio.run() dentro,
        lo que provocaba un RuntimeWarning porque el health_check ya es
        coroutine. Ahora se llama con await desde los callers async.
        """
        if not self._fallback_active:
            return True  # Ya estamos en el primario.
        if self._is_fallback_blocked():
            return False
        if not self._primary_provider_name:
            return False
        primary_instance = self.providers.get(self._primary_provider_name)
        if not primary_instance:
            self._fallback_active = False
            return False

        # Intentamos un health check en el primario (con cache de 30s).
        cache_key = self._primary_provider_name
        cached = self._health_cache.get(cache_key)
        now = time.monotonic()
        if cached and (now - cached[0]) < self._health_cache_ttl:
            healthy = cached[1]
        else:
            try:
                healthy = await primary_instance.health_check()
            except Exception:
                healthy = False
            self._health_cache[cache_key] = (now, healthy)

        if healthy:
            self.current_provider = primary_instance
            self.current_provider_name = self._primary_provider_name
            self._fallback_active = False
            return True
        # Sigue caido: ampliamos el bloqueo otro ciclo.
        self._fallback_until = time.monotonic() + FALLBACK_RETRY_INTERVAL_S
        return False

    def _is_transient_error(self, exc: Exception) -> bool:
        """Clasifica un error como "transitorio" (justifica fallback) o
        "permanente" (no tiene sentido cambiar de proveedor).

        Transitorios: cualquier excepcion de red / HTTP / timeout / DNS.
        NO transitorios: p.ej. ValueError por mensaje vacio (no deberian
        llegar aqui, pero por si acaso)."""
        # httpx es el cliente HTTP que usan todos los providers OpenAI-compatibles.
        try:
            import httpx
            if isinstance(exc, (httpx.HTTPError, httpx.RequestError, httpx.TimeoutException)):
                return True
        except ImportError:
            pass
        # Errores genericos de conexion siguen considerandose transitorios.
        name = type(exc).__name__
        transient_names = (
            "ConnectError", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
            "PoolTimeout", "NetworkError", "RemoteProtocolError",
            "HTTPStatusError", "TransportError",
        )
        return name in transient_names

    # ------------------------------------------------------------------
    # Gestion de proveedores (Configuracion -> Modelos IA)
    # ------------------------------------------------------------------

    def list_configured(self) -> List[Dict[str, Any]]:
        """Return one entry per catalog provider, merged with whatever the user has configured in the DB."""
        db = SessionLocal()
        try:
            rows = {row.provider: row for row in db.query(AIProviderConfig).all()}
        finally:
            db.close()

        result = []
        for provider_name in list_provider_names():
            info = get_provider_info(provider_name)
            row = rows.get(provider_name)
            is_configured = row is not None or provider_name in NO_KEY_PROVIDERS
            has_key = bool(row and row.api_key)
            _plain_key = _dec(row.api_key) if has_key else ""  # solo para el preview
            result.append({
                "provider": provider_name,
                "label": info["label"],
                "model": (row.model if row else None) or info.get("default_model"),
                "base_url": row.base_url if row else None,
                "has_api_key": has_key,
                "api_key_preview": ("..." + _plain_key[-4:]) if _plain_key and len(_plain_key) >= 4 else None,
                "is_active": provider_name == self.current_provider_name,
                "is_configured": is_configured,
                "requires_key": info.get("requires_key", True),
                "available_models": info.get("models", []),
            })
        return result

    def add_or_update_provider(self, provider_name: str, model: Optional[str] = None,
                                 api_key: Optional[str] = None, base_url: Optional[str] = None) -> bool:
        """Add a new provider config, or update an existing one. API keys are stored locally only."""
        if provider_name not in PROVIDER_CLASSES:
            return False

        db = SessionLocal()
        try:
            row = db.query(AIProviderConfig).filter(AIProviderConfig.provider == provider_name).first()
            if row:
                if model is not None:
                    row.model = model
                if api_key is not None:
                    row.api_key = _enc(api_key)  # cifrada en reposo
                if base_url is not None:
                    row.base_url = base_url
            else:
                catalog_info = get_provider_info(provider_name)
                row = AIProviderConfig(
                    provider=provider_name,
                    model=model or catalog_info.get("default_model"),
                    api_key=_enc(api_key),  # cifrada en reposo
                    base_url=base_url,
                    is_active=False,
                )
                db.add(row)
            db.commit()

            instance = _instantiate_provider(provider_name, row.model, _dec(row.api_key), row.base_url)
            if instance:
                self.providers[provider_name] = instance
                self._health_cache.pop(provider_name, None)
                # Si el usuario actualizo el primario y estamos en fallback,
                # reseteamos el bloqueo para que el proximo ciclo lo reintente.
                if self._fallback_active and self._primary_provider_name == provider_name:
                    self._fallback_until = 0.0
            return True
        finally:
            db.close()

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a configured provider. Falls back to Ollama if it was the active one."""
        if provider_name == "ollama":
            return False  # Ollama es el fallback local, no se elimina.

        db = SessionLocal()
        try:
            row = db.query(AIProviderConfig).filter(AIProviderConfig.provider == provider_name).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
        finally:
            db.close()

        self.providers.pop(provider_name, None)
        if self.current_provider_name == provider_name:
            self.set_provider("ollama")
        return True

    def set_provider(self, provider_name: str, model: Optional[str] = None) -> bool:
        """Switch to a different AI provider and persist it as the active one."""
        if provider_name not in self.providers:
            return False

        self.current_provider = self.providers[provider_name]
        self.current_provider_name = provider_name
        self._health_cache.pop(provider_name, None)
        # Al cambiar manualmente el proveedor, reseteamos el estado de fallback
        # para que el nuevo activo sea el primario a partir de ahora.
        self._primary_provider_name = provider_name
        self._fallback_active = False
        self._fallback_until = 0.0

        if model:
            self.current_provider.model = model

        db = SessionLocal()
        try:
            db.query(AIProviderConfig).update({AIProviderConfig.is_active: False})
            row = db.query(AIProviderConfig).filter(AIProviderConfig.provider == provider_name).first()
            if row:
                row.is_active = True
                if model:
                    row.model = model
            else:
                row = AIProviderConfig(provider=provider_name, model=model, is_active=True)
                db.add(row)
            db.commit()
        finally:
            db.close()

        return True

    async def test_provider(self, provider_name: str, model: Optional[str] = None,
                              api_key: Optional[str] = None, base_url: Optional[str] = None) -> bool:
        """
        Probar conexion. Si se pasa una api_key/base_url nuevas (el usuario esta
        probando credenciales que todavia no ha guardado), se usan esas. Si no
        se pasan, se reutiliza la api_key/base_url ya guardada para ese
        proveedor.
        """
        existing = self.providers.get(provider_name)

        effective_api_key = api_key if api_key else (getattr(existing, "api_key", None) if existing else None)
        effective_model = model or (getattr(existing, "model", None) if existing else None)

        instance = _instantiate_provider(provider_name, effective_model, effective_api_key, base_url)
        if not instance:
            instance = existing

        if not instance:
            return False
        return await instance.health_check()

    async def list_ollama_models(self) -> List[str]:
        """Auto-deteccion de modelos instalados localmente en Ollama."""
        ollama = self.providers.get("ollama")
        if not isinstance(ollama, OllamaProvider):
            return []
        try:
            # V0.9 A2a: reutiliza el cliente httpx persistente del proveedor ollama
            # (en vez de abrir uno nuevo por llamada); timeout por-request.
            client = ollama._get_client()
            response = await client.get(f"{ollama.base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            return []

    async def aclose(self) -> None:
        """V0.9 (A2a, doc 12 A2): cierra los httpx.AsyncClient persistentes de
        TODOS los proveedores (llamado en el shutdown del lifespan). Fail-soft."""
        for provider in list(self.providers.values()):
            try:
                await provider.aclose()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Chat (con fallback automatico integrado)
    # ------------------------------------------------------------------

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message and get a complete (non-streaming) response.

        Si el proveedor primario falla por un error transitorio (sin internet,
        timeout, 5xx, 401) y hay un fallback configurado, se reintenta
        automaticamente con el fallback y se devuelve su respuesta.
        """
        # Si estabamos en fallback pero ya toca reintentar el primario,
        # comprobamos si esta sano y volvemos a el antes del chat.
        if self._fallback_active:
            await self._try_restore_primary()

        try:
            if not self.current_provider:
                return {"response": "No AI provider configured", "error": True}

            result = await self.current_provider.generate(message, system_prompt)
            if result.get("error"):
                # El provider devolvio un error encapsulado: activamos fallback
                # salvo que ya estemos en el.
                if self.current_provider_name != DEFAULT_FALLBACK_PROVIDER:
                    self._activate_fallback(
                        f"el proveedor respondio con error: {result.get('response', '')[:120]}"
                    )
                    # Reintentamos UNA vez con el fallback.
                    fallback = self.providers.get(DEFAULT_FALLBACK_PROVIDER)
                    if fallback:
                        fb_result = await fallback.generate(message, system_prompt)
                        if not fb_result.get("error"):
                            fb_result["served_by"] = DEFAULT_FALLBACK_PROVIDER
                            fb_result["primary_unavailable"] = self._primary_provider_name
                            return fb_result
                # O seguimos en el primario y devolvemos su error, o el fallback
                # tampoco respondio. Devolvemos lo que tengamos.
            return result
        except Exception as e:
            # Excepcion real (timeout, network, etc.): activamos fallback.
            if self.current_provider_name != DEFAULT_FALLBACK_PROVIDER and self._is_transient_error(e):
                self._activate_fallback(f"excepcion transitoria: {type(e).__name__}: {e}")
                fallback = self.providers.get(DEFAULT_FALLBACK_PROVIDER)
                if fallback:
                    try:
                        fb_result = await fallback.generate(message, system_prompt)
                        fb_result["served_by"] = DEFAULT_FALLBACK_PROVIDER
                        fb_result["primary_unavailable"] = self._primary_provider_name
                        return fb_result
                    except Exception:
                        pass
            return {
                "response": f"Error connecting to {self.current_provider_name}: {str(e)}",
                "model": getattr(self.current_provider, "model", None),
                "provider": self.current_provider_name,
                "error": True,
            }

    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """
        Send a chat message and stream the response as incremental text chunks.

        V0.3 - Fallback automatico integrado:
        Si el proveedor primario falla con un error transitorio, hace un
        fallback transparente a Ollama en mitad del stream. Tambien aplica
        la red de seguridad universal previa (si el proveedor primario no
        emite NINGUN chunk en streaming, intenta una llamada normal).
        """
        # Si estabamos en fallback pero ya toca reintentar el primario,
        # comprobamos si esta sano y volvemos a el antes del stream.
        if self._fallback_active:
            await self._try_restore_primary()

        if not self.current_provider:
            yield "No hay un proveedor de IA configurado."
            return

        primary_name = self.current_provider_name
        got_any_chunk = False
        try:
            async for chunk in self.current_provider.generate_stream(message, system_prompt):
                got_any_chunk = True
                yield chunk
        except Exception as e:
            # El provider lanzo una excepcion real (no devolvio error encapsulado).
            if self.current_provider_name != DEFAULT_FALLBACK_PROVIDER and self._is_transient_error(e):
                self._activate_fallback(f"stream interrumpido: {type(e).__name__}: {e}")
                # Avisamos al usuario de que estamos usando el fallback y seguimos.
                yield f"\n\n[Conectando con fallback local: {DEFAULT_FALLBACK_PROVIDER}...] \n\n"
                fallback = self.providers.get(DEFAULT_FALLBACK_PROVIDER)
                if fallback:
                    try:
                        async for chunk in fallback.generate_stream(message, system_prompt):
                            got_any_chunk = True
                            yield chunk
                    except Exception as e2:
                        yield f"\n[Error tambien en fallback ({DEFAULT_FALLBACK_PROVIDER}): {e2}]"
            else:
                yield f"[Error conectando con {self.current_provider_name}: {str(e)}]"

        # Red de seguridad: si el primario (o el fallback) no emitio ningun
        # chunk, intentamos una llamada no-streaming.
        if not got_any_chunk:
            try:
                fallback = await self.current_provider.generate(message, system_prompt)
                text = fallback.get("response", "")
                if text:
                    yield text
                else:
                    yield (
                        "(El proveedor no devolvio ninguna respuesta. "
                        "Revisa el modelo configurado o prueba la conexion.)"
                    )
            except Exception as e:
                # Ultimo recurso: fallback automatico si no estamos ya en el.
                if self.current_provider_name != DEFAULT_FALLBACK_PROVIDER and self._is_transient_error(e):
                    self._activate_fallback(f"fallo no-streaming: {type(e).__name__}: {e}")
                    fb = self.providers.get(DEFAULT_FALLBACK_PROVIDER)
                    if fb:
                        try:
                            fb_resp = await fb.generate(message, system_prompt)
                            text = fb_resp.get("response", "")
                            if text:
                                yield f"\n\n[Fallback activo: {DEFAULT_FALLBACK_PROVIDER}]\n\n{text}"
                                return
                        except Exception:
                            pass
                yield f"\n[Error: ninguna respuesta del proveedor {self.current_provider_name}]"

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the current AI provider.

        Usa una cache de 30s por proveedor para no repetir una llamada de red
        real al proveedor externo cada vez que el usuario abre el Dashboard.

        V0.3: incluye informacion de fallback para que la UI pueda avisar al
        usuario ("IA: MiniMax (fallback: Ollama)").
        """
        if not self.current_provider:
            return {
                "provider": None,
                "model": None,
                "healthy": False,
                "fallback_active": False,
                "primary_provider": None,
            }

        cache_key = self.current_provider_name
        cached = self._health_cache.get(cache_key)
        now = time.monotonic()
        if cached and (now - cached[0]) < self._health_cache_ttl:
            healthy = cached[1]
        else:
            try:
                healthy = await self.current_provider.health_check()
            except Exception:
                healthy = False
            self._health_cache[cache_key] = (now, healthy)

        return {
            "provider": self.current_provider_name,
            "model": self.current_provider.model,
            "healthy": healthy,
            "fallback_active": self._fallback_active,
            "primary_provider": self._primary_provider_name,
        }

    def get_available_providers(self) -> list:
        """Get list of available (instantiated) provider names."""
        return list(self.providers.keys())


# Global AI manager instance
ai_manager = AIManager()
