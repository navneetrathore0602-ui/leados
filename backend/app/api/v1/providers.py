from typing import List
from fastapi import APIRouter
from app.schemas.provider import ProviderHealthInfo
from app.providers.registry import get_providers_health

router = APIRouter()

@router.get("", response_model=List[ProviderHealthInfo])
@router.get("/", response_model=List[ProviderHealthInfo])
def get_providers():
    """
    Get registered discovery providers status and health check.
    """
    return get_providers_health()
