from typing import Optional
from pydantic import BaseModel

class ProviderHealthInfo(BaseModel):
    provider: str
    name: str
    enabled: bool
    healthy: bool
    last_checked: str
    error: Optional[str] = None
