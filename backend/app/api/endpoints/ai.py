# AI API Endpoints
from fastapi import APIRouter

from app.ai.ai_manager import ai_manager
from app.db.schemas import AIStatusResponse

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Get AI system status."""
    status = await ai_manager.health_check()
    return status


@router.get("/providers")
async def get_providers():
    """Get available AI providers."""
    return {
        "providers": ai_manager.get_available_providers(),
        "current": ai_manager.current_provider_name
    }


@router.post("/providers/{provider_name}")
async def set_provider(provider_name: str, model: str = None):
    """Set the active AI provider."""
    success = ai_manager.set_provider(provider_name, model)
    if not success:
        return {"error": f"Provider '{provider_name}' not available"}
    return {"message": f"Provider set to {provider_name}"}
