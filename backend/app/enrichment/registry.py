from typing import Dict, Any, List, Type
from app.enrichment.base import EnrichmentProvider
from app.enrichment.website import WebsiteEnrichmentProvider
from app.enrichment.mock import MockEnrichmentProvider

ENRICHMENT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "website": {
        "name": "Website HTML Scraper & Contact Extractor",
        "class": WebsiteEnrichmentProvider,
        "enabled": True
    },
    "mock": {
        "name": "Mock Enrichment Provider (Development)",
        "class": MockEnrichmentProvider,
        "enabled": True
    }
}

def get_enrichment_provider(provider_name: str = "website") -> EnrichmentProvider:
    name_clean = (provider_name or "website").lower()
    info = ENRICHMENT_PROVIDERS.get(name_clean)
    if not info or not info["enabled"]:
        return MockEnrichmentProvider()
    cls: Type[EnrichmentProvider] = info["class"]
    return cls()

def list_enrichment_providers() -> List[Dict[str, Any]]:
    result = []
    for key, info in ENRICHMENT_PROVIDERS.items():
        result.append({
            "id": key,
            "name": info["name"],
            "enabled": info["enabled"]
        })
    return result
