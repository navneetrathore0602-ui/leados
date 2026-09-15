import random
from datetime import datetime, timezone
from typing import Dict, Any
from app.enrichment.base import EnrichmentProvider

class MockEnrichmentProvider(EnrichmentProvider):
    """
    Mock enrichment provider for deterministic testing of enrichment,
    field provenance, social profile discovery, and batch enrichment.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def can_enrich(self, business: Any) -> bool:
        return True

    def health_check(self) -> bool:
        return True

    def enrich(self, business: Any) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        b_id = str(getattr(business, "id", "12345"))
        b_name = getattr(business, "name", "Test Business") or "Test Business"

        # Deterministic seed based on business id/name
        seed_val = self.seed + sum(ord(c) for c in b_name)
        rng = random.Random(seed_val)

        domain_slug = b_name.lower().replace(" ", "").replace("&", "and")
        site_url = getattr(business, "website", None) or f"https://www.{domain_slug}.example.com"

        phone_val = f"+91 98200 {rng.randint(10000, 99999)}"
        email_val = f"contact@{domain_slug}.example.com"
        wa_val = f"https://wa.me/9198200{rng.randint(10000, 99999)}"

        socials = [
            {
                "platform": "instagram",
                "profile_url": f"https://www.instagram.com/{domain_slug}_official/",
                "username": f"{domain_slug}_official",
                "source": "mock_website_social_link",
                "source_url": f"{site_url}/contact",
                "confidence": 0.95,
                "discovered_at": now_iso
            },
            {
                "platform": "facebook",
                "profile_url": f"https://www.facebook.com/{domain_slug}/",
                "username": domain_slug,
                "source": "mock_website_social_link",
                "source_url": site_url,
                "confidence": 0.92,
                "discovered_at": now_iso
            },
            {
                "platform": "linkedin",
                "profile_url": f"https://www.linkedin.com/company/{domain_slug}/",
                "username": domain_slug,
                "source": "mock_website_social_link",
                "source_url": f"{site_url}/about",
                "confidence": 0.90,
                "discovered_at": now_iso
            }
        ]

        services = [
            {"name": "Custom Product Installation", "source": "mock_services_page", "confidence": 0.85},
            {"name": "24/7 Customer Support", "source": "mock_services_page", "confidence": 0.85},
            {"name": "Wholesale Direct Supply", "source": "mock_services_page", "confidence": 0.85}
        ]

        candidates = [
            {
                "field_name": "phone",
                "value": f"+91 98201 {rng.randint(10000, 99999)}",
                "normalized_value": f"9198201{rng.randint(10000, 99999)}",
                "source": "secondary_contact_page",
                "source_url": f"{site_url}/contact",
                "confidence": 0.75,
                "status": "conflicting"
            }
        ]

        return {
            "website": {
                "value": site_url,
                "source": "mock_enrichment_provider",
                "source_url": site_url,
                "confidence": 0.95,
                "discovered_at": now_iso
            },
            "phone": {
                "value": phone_val,
                "normalized_value": phone_val.replace(" ", "").replace("+", ""),
                "source": "mock_enrichment_provider",
                "source_url": f"{site_url}/contact",
                "confidence": 0.92,
                "discovered_at": now_iso
            },
            "email": {
                "value": email_val,
                "normalized_value": email_val.lower(),
                "source": "mock_enrichment_provider",
                "source_url": f"{site_url}/contact",
                "confidence": 0.90,
                "verification_status": "syntax_valid",
                "discovered_at": now_iso
            },
            "whatsapp": {
                "value": wa_val,
                "source": "mock_enrichment_provider",
                "source_url": site_url,
                "confidence": 0.90,
                "discovered_at": now_iso
            },
            "social_profiles": socials,
            "description": {
                "value": f"{b_name} is a premier verified business providing top-tier products and services.",
                "source": "mock_meta_description",
                "source_url": site_url,
                "confidence": 0.95,
                "discovered_at": now_iso
            },
            "services": services,
            "opening_hours": {
                "value": "Mon - Sat: 9:00 AM - 8:00 PM",
                "source": "mock_footer_hours",
                "confidence": 0.90
            },
            "candidate_fields": candidates
        }
