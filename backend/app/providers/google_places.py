import re
import logging
import httpx
from typing import List, Dict, Any, Optional
from app.providers.base import DiscoveryProvider
from app.providers.partitions import generate_location_partitions
from app.core.config import settings

logger = logging.getLogger(__name__)

class GooglePlacesDiscoveryProvider(DiscoveryProvider):
    """
    Official Google Places API (New) Discovery Provider for LeadOS.
    Executes real business discovery via POST https://places.googleapis.com/v1/places:searchText.
    Supports dynamic geographic partitioning when limit > 60, deduplicating strictly by Google Place ID.
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.search_url = settings.GOOGLE_PLACES_NEW_URL
        self.details_url = settings.GOOGLE_PLACE_DETAILS_NEW_URL

    def health_check(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fetch_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not record_id:
            return None

        url = f"{self.details_url}/{record_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,nationalPhoneNumber,internationalPhoneNumber,websiteUri,rating,userRatingCount,location,googleMapsUri"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    def search(
        self,
        campaign: Any,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        if page > 1:
            return []

        if not self.api_key or not self.api_key.strip():
            raise RuntimeError("GOOGLE_API_KEY_MISSING: GOOGLE_MAPS_API_KEY is not configured in backend environment")

        effective_limit = min(limit, settings.DISCOVERY_TEST_LIMIT)

        # Extract search parameters
        keywords = campaign.keywords or []
        locations = campaign.locations or []
        category = campaign.category or ""

        kw_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
        loc_str = " ".join(locations) if isinstance(locations, list) else str(locations)

        main_term = kw_str if kw_str.strip() else (category or "business")
        main_loc = loc_str if loc_str.strip() else "Mumbai"

        # Generate sub-location partitions
        query_partitions = generate_location_partitions(category=main_term, location=main_loc)

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.location,places.googleMapsUri,places.primaryTypeDisplayName,places.types,nextPageToken"
        }

        raw_results: List[Dict[str, Any]] = []
        seen_place_ids = set()
        max_partition_queries = max(12, (effective_limit // 15) + 10)

        try:
            with httpx.Client(timeout=15.0) as client:
                for q_idx, search_query in enumerate(query_partitions[:max_partition_queries], 1):
                    page_token: Optional[str] = None
                    
                    while len(raw_results) < effective_limit:
                        pageSize = min(effective_limit - len(raw_results), 20)
                        payload: Dict[str, Any] = {
                            "textQuery": search_query,
                            "pageSize": pageSize
                        }
                        if page_token:
                            payload["pageToken"] = page_token

                        resp = client.post(self.search_url, headers=headers, json=payload)
                        
                        if resp.status_code != 200:
                            body = {}
                            try:
                                body = resp.json()
                            except Exception:
                                pass
                            
                            err_info = body.get("error", {})
                            err_status = err_info.get("status", "HTTP_ERROR")
                            err_msg = err_info.get("message") or f"Google Places API (New) returned HTTP status {resp.status_code}"

                            if err_status in ("PERMISSION_DENIED", "UNAUTHENTICATED"):
                                raise RuntimeError(f"GOOGLE_API_DENIED: {err_msg}")
                            elif err_status in ("RESOURCE_EXHAUSTED", "OVER_QUERY_LIMIT"):
                                raise RuntimeError(f"GOOGLE_QUOTA_EXCEEDED: {err_msg}")
                            elif err_status == "INVALID_ARGUMENT":
                                raise RuntimeError(f"GOOGLE_INVALID_REQUEST: {err_msg}")
                            else:
                                raise RuntimeError(f"GOOGLE_HTTP_ERROR: HTTP {resp.status_code} ({err_status}) - {err_msg}")
                        
                        body = resp.json()
                        page_items = body.get("places", [])
                        if not page_items:
                            break
                        
                        # Deduplicate by Google Place ID
                        q_added = 0
                        for item in page_items:
                            pid = item.get("id")
                            if pid and pid in seen_place_ids:
                                continue
                            if pid:
                                seen_place_ids.add(pid)
                            raw_results.append(item)
                            q_added += 1
                            if len(raw_results) >= effective_limit:
                                break

                        logger.info(f"Query {q_idx} ('{search_query}'): +{q_added} new items (Total unique: {len(raw_results)})")

                        page_token = body.get("nextPageToken")
                        if not page_token or len(raw_results) >= effective_limit:
                            break

                    if len(raw_results) >= effective_limit:
                        break

        except httpx.TimeoutException:
            raise RuntimeError("GOOGLE_TIMEOUT: Request to Google Places API (New) timed out")
        except httpx.HTTPError as e:
            if not isinstance(e, RuntimeError):
                raise RuntimeError(f"GOOGLE_UNAVAILABLE: Google Places API (New) HTTP connection error: {e}")
            raise e

        results: List[Dict[str, Any]] = []

        for item in raw_results[:effective_limit]:
            display_obj = item.get("displayName", {})
            name = (display_obj.get("text") if isinstance(display_obj, dict) else str(display_obj or "")).strip()
            if not name:
                continue

            place_id = item.get("id")
            formatted_address = item.get("formattedAddress", "")
            
            # Location parsing
            location_obj = item.get("location", {})
            lat = float(location_obj["latitude"]) if "latitude" in location_obj else None
            lon = float(location_obj["longitude"]) if "longitude" in location_obj else None

            # Category / Types
            primary_disp = item.get("primaryTypeDisplayName", {})
            primary_cat = primary_disp.get("text") if isinstance(primary_disp, dict) else None
            types = item.get("types", [])
            primary_type = primary_cat or (types[0].replace("_", " ").title() if types else (category or "Business"))

            # Extract city / state / country from formatted address
            city = locations[0].split(",")[0].strip() if locations else "Kishangarh"
            state = "Rajasthan" if "rajasthan" in (loc_str + formatted_address).lower() else "Maharashtra"
            country = "India"

            if formatted_address:
                addr_parts = [p.strip() for p in formatted_address.split(",")]
                matched_city = None
                if locations:
                    for loc in locations:
                        loc_clean = loc.split(",")[0].strip()
                        if any(loc_clean.lower() in p.lower() for p in addr_parts):
                            matched_city = loc_clean
                            break
                if matched_city:
                    city = matched_city
                elif len(addr_parts) >= 3:
                    city = addr_parts[-3]
                elif len(addr_parts) == 2:
                    city = addr_parts[0]

            rating = float(item.get("rating")) if item.get("rating") is not None else None
            review_count = int(item.get("userRatingCount")) if item.get("userRatingCount") is not None else 0
            
            phone = item.get("nationalPhoneNumber") or item.get("internationalPhoneNumber")
            website = item.get("websiteUri")

            google_maps_url = item.get("googleMapsUri") or (f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else f"https://www.google.com/maps/search/?api=1&query={httpx.URL(main_term)}")

            results.append({
                "name": name,
                "category": primary_type,
                "subcategory": category or primary_type,
                "address": formatted_address,
                "city": city,
                "state": state,
                "country": country,
                "postal_code": None,
                "latitude": lat,
                "longitude": lon,
                "phone": phone,
                "email": None,
                "website": website,
                "rating": rating,
                "review_count": review_count,
                "source_name": "Google Places API",
                "source_id": place_id,
                "source_url": google_maps_url,
                "raw_data": item
            })

        return results
