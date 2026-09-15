from datetime import datetime, timezone
from typing import Dict, Any, List, Type
from app.providers.base import DiscoveryProvider
from app.providers.mock import MockDiscoveryProvider
from app.providers.osm import OpenStreetMapProvider
from app.providers.google_places import GooglePlacesDiscoveryProvider

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "google": {
        "name": "Google Places API (Official)",
        "class": GooglePlacesDiscoveryProvider,
        "enabled": True
    },
    "google_places": {
        "name": "Google Places API (Official)",
        "class": GooglePlacesDiscoveryProvider,
        "enabled": True
    },
    "osm": {
        "name": "OpenStreetMap Places API (Real)",
        "class": OpenStreetMapProvider,
        "enabled": True
    },
    "openstreetmap": {
        "name": "OpenStreetMap Places API (Real)",
        "class": OpenStreetMapProvider,
        "enabled": True
    },
    "mock": {
        "name": "Mock Discovery Provider (Development)",
        "class": MockDiscoveryProvider,
        "enabled": True
    }
}

def get_provider(provider_name: str = "mock") -> DiscoveryProvider:
    name_clean = (provider_name or "mock").lower()
    provider_info = PROVIDERS.get(name_clean)
    if not provider_info or not provider_info["enabled"]:
        # Default fallback to mock
        return MockDiscoveryProvider()
    
    cls: Type[DiscoveryProvider] = provider_info["class"]
    return cls()

def list_providers() -> List[Dict[str, Any]]:
    # Return unique providers (skip duplicate aliases like openstreetmap if osm is present)
    seen = set()
    result = []
    for key, pinfo in PROVIDERS.items():
        if pinfo["class"] not in seen:
            seen.add(pinfo["class"])
            result.append({
                "id": key,
                "name": pinfo["name"],
                "enabled": pinfo["enabled"]
            })
    return result

def get_providers_health() -> List[Dict[str, Any]]:
    health_list: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    seen_classes = set()

    for key, pinfo in PROVIDERS.items():
        if pinfo["class"] in seen_classes:
            continue
        seen_classes.add(pinfo["class"])

        err = None
        healthy = False
        try:
            instance = pinfo["class"]()
            healthy = instance.health_check()
        except Exception as e:
            err = str(e)
            healthy = False

        health_list.append({
            "provider": key,
            "name": pinfo["name"],
            "enabled": pinfo["enabled"],
            "healthy": healthy,
            "last_checked": now,
            "error": err
        })

    return health_list
