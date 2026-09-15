from typing import Dict
from pydantic import BaseModel

class LeadStatsResponse(BaseModel):
    total_businesses: int
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    verified_contacts: int
    businesses_by_category: Dict[str, int]
    businesses_by_city: Dict[str, int]
