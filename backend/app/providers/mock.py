import random
import hashlib
from typing import List, Dict, Any, Optional
from app.providers.base import DiscoveryProvider

MARBLE_PREFIXES = [
    "ABC", "Royal", "Mumbai", "Apex", "Shree", "Imperial", "Everest", 
    "Titanium", "Vanguard", "Lotus", "Sunlight", "Crown", "Star", "Golden",
    "Mahalaxmi", "Venkateshwara", "Galaxy", "Crystal", "Diamond", "Reliance"
]

MARBLE_SUFFIXES = [
    "Marble Studio", "Stone House", "Premium Marble", "Granite & Marble",
    "Marble World", "Stone Trading Co", "Marble Gallery", "Stone Solutions",
    "Marble Crafts", "Granite Depot", "Stones & Tiles", "Marble Emporium",
    "Natural Stone Hub", "Marble Mart", "Stone Industry"
]

STREET_NAMES = [
    "Link Road", "S.V. Road", "LBS Marg", "Station Road", "Gokhale Road",
    "MIDC Industrial Area", "Palm Beach Road", "Western Express Highway",
    "Eastern Express Highway", "Main Market Yard"
]

class MockDiscoveryProvider(DiscoveryProvider):
    """
    Mock discovery provider for deterministic testing of campaign discovery,
    normalization, deduplication, and job execution without external network calls.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def health_check(self) -> bool:
        return True

    def fetch_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        return None

    def search(
        self,
        campaign: Any,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        target_total = campaign.target_leads or 100
        keywords = campaign.keywords or ["Marble Dealer", "Granite"]
        locations = campaign.locations or ["Mumbai", "Thane", "Navi Mumbai"]
        category = campaign.category or "Marble & Granite"

        # Calculate requested slice
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, target_total)

        if start_idx >= target_total:
            return []

        results: List[Dict[str, Any]] = []

        for idx in range(start_idx, end_idx):
            # Deterministic generator based on index
            rng = random.Random(self.seed + idx)

            # 15% chance of generating a duplicate record of index (idx - 3) to test deduplication
            if idx > 3 and rng.random() < 0.15:
                dup_idx = idx - 3
                dup_rng = random.Random(self.seed + dup_idx)
                prefix = dup_rng.choice(MARBLE_PREFIXES)
                suffix = dup_rng.choice(MARBLE_SUFFIXES)
                city = dup_rng.choice(locations)
                b_name = f"{prefix} {suffix}"
                phone = f"+91 98200 {dup_idx:05d}"
                domain_slug = b_name.lower().replace(" ", "").replace("&", "and")
                website = f"https://www.{domain_slug}.example.in"
            else:
                prefix = rng.choice(MARBLE_PREFIXES)
                suffix = rng.choice(MARBLE_SUFFIXES)
                city = rng.choice(locations)
                b_name = f"{prefix} {suffix}"
                phone = f"+91 98200 {idx:05d}"
                domain_slug = b_name.lower().replace(" ", "").replace("&", "and")
                website = f"https://www.{domain_slug}.example.in"

            # Optional missing fields for testing filters
            has_website = rng.random() > 0.1  # 90% have website
            has_phone = rng.random() > 0.05    # 95% have phone
            has_email = rng.random() > 0.2  # 80% have email

            email = f"info@{domain_slug}.example.in" if has_email else None
            rating = round(rng.uniform(3.5, 5.0), 1)
            review_count = rng.randint(5, 150)
            street = rng.choice(STREET_NAMES)
            building = rng.randint(1, 200)

            subcategory = rng.choice(keywords) if keywords else "Marble Dealer"

            raw_item = {
                "name": b_name,
                "category": category,
                "subcategory": subcategory,
                "address": f"Plot {building}, {street}, Near Railway Station",
                "city": city,
                "state": "Maharashtra",
                "country": "India",
                "postal_code": f"4000{rng.randint(10, 99)}",
                "latitude": round(19.0760 + rng.uniform(-0.1, 0.1), 6),
                "longitude": round(72.8777 + rng.uniform(-0.1, 0.1), 6),
                "phone": phone if has_phone else None,
                "email": email,
                "website": website if has_website else None,
                "rating": rating,
                "review_count": review_count,
                "source_name": "Mock Discovery Provider",
                "source_url": f"https://mock.provider.example/place/{domain_slug}-{idx}",
                "raw_data": {
                    "mock_idx": idx,
                    "generated_for_campaign": str(campaign.id),
                    "seed": self.seed
                }
            }

            results.append(raw_item)

        return results
