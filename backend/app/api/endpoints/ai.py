# AI API Endpoints - Fase 2: Sistema de IA multi-proveedor
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.ai_manager import ai_manager
from app.ai.catalog import PROVIDER_CATALOG
from app.db.schemas import (
    AIStatusResponse,
    AIProviderConfigCreate,
    AIProviderConfigUpdate,
    AIProviderConfigResponse,
    AITestConnectionResponse,
)

router = APIRouter(prefix="/ai", tags=["AI"])


# ==================== Estado / legado (Fase <2, se mantiene por compatibilidad) ====================

@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Get AI system status."""
    status = await ai_manager.health_check()
    return status


@router.get("/providers")
async def get_providers():
    """Get available (instantiated) AI providers."""
    return {
        "providers": ai_manager.get_available_providers(),
        "current": ai_manager.current_provider_name
    }


@router.post("/providers/{provider_name}")
async def set_provider_legacy(provider_name: str, model: Optional[str] = None):
    """Set the active AI provider (forma simple, sin API key - usa la ya configurada)."""
    success = ai_manager.set_provider(provider_name, model)
    if not success:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not configured yet")
    return {"message": f"Provider set to {provider_name}"}


# ==================== Fase 2: Configuracion -> Modelos IA ====================

@router.get("/catalog")
def get_catalog():
    """Catalogo estatico de proveedores y modelos preconfigurados, para poblar la UI."""
    return PROVIDER_CATALOG


@router.get("/configured", response_model=List[AIProviderConfigResponse])
def get_configured_providers():
    """
    Lista unificada: todos los proveedores del catalogo, indicando para cada uno
    si el usuario ya lo configuro, que modelo tiene, si esta activo, etc.
    """
    return ai_manager.list_configured()


@router.post("/configured", response_model=AIProviderConfigResponse, status_code=201)
def add_provider(config: AIProviderConfigCreate):
    """
    Anadir (o actualizar) un proveedor. La API key se guarda localmente en la
    base de datos del usuario y nunca se incrusta en el codigo ni se envia a
    terceros distintos del propio proveedor de IA.
    """
    if config.provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Proveedor desconocido: {config.provider}")

    ok = ai_manager.add_or_update_provider(
        provider_name=config.provider,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="No se pudo guardar el proveedor")

    return next(c for c in ai_manager.list_configured() if c["provider"] == config.provider)


@router.put("/configured/{provider_name}", response_model=AIProviderConfigResponse)
def update_provider(provider_name: str, update: AIProviderConfigUpdate):
    """Actualizar el modelo, la API key o el base_url de un proveedor ya configurado."""
    if provider_name not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Proveedor desconocido: {provider_name}")

    ok = ai_manager.add_or_update_provider(
        provider_name=provider_name,
        model=update.model,
        api_key=update.api_key,
        base_url=update.base_url,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el proveedor")

    return next(c for c in ai_manager.list_configured() if c["provider"] == provider_name)


@router.delete("/configured/{provider_name}")
def delete_provider(provider_name: str):
    """Eliminar un proveedor configurado. Ollama no se puede eliminar (es el fallback local)."""
    ok = ai_manager.remove_provider(provider_name)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="No se pudo eliminar (Ollama no se puede eliminar, o el proveedor no estaba configurado)",
        )
    return {"message": f"Provider '{provider_name}' eliminado"}


@router.post("/configured/{provider_name}/activate", response_model=AIStatusResponse)
async def activate_provider(provider_name: str, model: Optional[str] = None):
    """Activar un proveedor ya configurado como el proveedor actual del sistema."""
    ok = ai_manager.set_provider(provider_name, model)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' no esta configurado")
    return await ai_manager.health_check()


class TestConnectionRequest(BaseModel):
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.post("/configured/{provider_name}/test", response_model=AITestConnectionResponse)
async def test_provider_connection(provider_name: str, body: TestConnectionRequest = TestConnectionRequest()):
    """
    Probar conexion. Si se envian model/api_key/base_url en el body se prueban
    esos valores sin guardarlos (util antes de pulsar "Guardar"); si no, se
    prueba el proveedor ya guardado.
    """
    if provider_name not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Proveedor desconocido: {provider_name}")

    healthy = await ai_manager.test_provider(
        provider_name,
        model=body.model,
        api_key=body.api_key,
        base_url=body.base_url,
    )
    return AITestConnectionResponse(
        provider=provider_name,
        healthy=healthy,
        message="Conexion correcta" if healthy else "No se pudo conectar (revisa la API key o el servicio)",
    )


@router.get("/ollama/models")
async def get_ollama_models():
    """Autodeteccion de modelos instalados localmente en Ollama."""
    models = await ai_manager.list_ollama_models()
    return {"models": models}
