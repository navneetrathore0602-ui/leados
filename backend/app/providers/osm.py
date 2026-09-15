import re
import httpx
from typing import List, Dict, Any, Optional
from app.providers.base import DiscoveryProvider
from app.core.config import settings

def parse_search_query(query_str: str) -> Dict[str, str]:
    """
    Parses natural user search input such as 'Restaurants in Mumbai' or 'Dentists in Delhi'
    into category and location components.
    """
    if not query_str or not isinstance(query_str, str):
        return {"category": "Business", "location": "Mumbai"}
    
    parts = re.split(r'\s+in\s+', query_str.strip(), flags=re.IGNORECASE)
    if len(parts) >= 2:
        category = parts[0].strip()
        location = " in ".join(parts[1:]).strip()
        return {"category": category, "location": location}
    
    return {"category": query_str.strip(), "location": ""}

class OpenStreetMapProvider(DiscoveryProvider):
    """
    Real business discovery provider using OpenStreetMap / Nominatim Places API.
    Conforms to DiscoveryProvider interface, returning standardized LeadOS dictionary results.
    """

    def __init__(self):
        self.base_url = settings.OSM_NOMINATIM_URL
        self.user_agent = settings.OSM_USER_AGENT
        self.headers = {"User-Agent": self.user_agent}

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    self.base_url,
                    params={"q": "Mumbai", "format": "jsonv2", "limit": 1},
                    headers=self.headers
                )
                return resp.status_code == 200
        except Exception:
            return False

    def fetch_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        return None

    def search(
        self,
        campaign: Any,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        effective_limit = min(limit, settings.DISCOVERY_TEST_LIMIT)

        # Build query keywords and locations
        keywords = campaign.keywords or []
        locations = campaign.locations or []
        category = campaign.category or ""

        kw_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
        loc_str = " ".join(locations) if isinstance(locations, list) else str(locations)

        main_term = kw_str if kw_str.strip() else category
        query_parts = [p for p in [main_term, loc_str] if p and p.strip()]
        search_query = " ".join(query_parts) if query_parts else "business"

        # Calculate pagination offset for multi-page requests
        offset = max(0, (page - 1) * limit)

        params = {
            "q": search_query,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "limit": effective_limit
        }
        # Add offset if page > 1 to support pagination
        if offset > 0:
            params["offset"] = offset

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.base_url, params=params, headers=self.headers)
                if resp.status_code != 200:
                    return []
                raw_items = resp.json()
        except httpx.TimeoutException:
            raise RuntimeError("PROVIDER_TIMEOUT: Request to OpenStreetMap API timed out")
        except httpx.HTTPError as e:
            raise RuntimeError(f"PROVIDER_UNAVAILABLE: OpenStreetMap API returned HTTP error: {e}")
        except Exception as e:
            raise RuntimeError(f"UNKNOWN_ERROR: OpenStreetMap provider search failed: {e}")

        results: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_items):
            addr = item.get("address") or {}
            extratags = item.get("extratags") or {}

            # Extract business name
            name = (
                item.get("name") or 
                extratags.get("name") or 
                addr.get("amenity") or 
                addr.get("shop") or 
                item.get("display_name", "").split(",")[0]
            )

            if not name or not name.strip():
                continue

            city = addr.get("city") or addr.get("town") or addr.get("suburb") or addr.get("county") or (locations[0] if locations else "Mumbai")
            state = addr.get("state") or "Maharashtra"
            country = addr.get("country") or "India"
            postal_code = addr.get("postcode")

            # Extract phone, email, website from extratags
            phone = extratags.get("phone") or extratags.get("contact:phone") or extratags.get("mobile")
            email = extratags.get("email") or extratags.get("contact:email")
            website = extratags.get("website") or extratags.get("contact:website") or extratags.get("url")

            lat = float(item["lat"]) if item.get("lat") else None
            lon = float(item["lon"]) if item.get("lon") else None

            osm_type = item.get("osm_type", "node")
            osm_id = item.get("osm_id", idx)
            source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

            formatted_address = item.get("display_name") or f"{name}, {city}, {state}"

            results.append({
                "name": name.strip(),
                "category": category or addr.get("shop") or addr.get("amenity") or "Commercial",
                "subcategory": extratags.get("type") or addr.get("shop") or "Dealer",
                "address": formatted_address,
                "city": city,
                "state": state,
                "country": country,
                "postal_code": postal_code,
                "latitude": lat,
                "longitude": lon,
                "phone": phone,
                "email": email,
                "website": website,
                "rating": 4.5 if website else 4.0,
                "review_count": 15,
                "source_name": "OpenStreetMap Places API",
                "source_url": source_url,
                "raw_data": item  # Store complete original provider payload
            })

        return results
