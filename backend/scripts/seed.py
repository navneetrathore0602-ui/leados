import os
import sys
import uuid
from datetime import datetime, timezone

# Add backend root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import Business, BusinessLocation, BusinessContact, SourceRecord

SAMPLE_BUSINESSES = [
    {
        "name": "Apex Plumbing Solutions",
        "normalized_name": "apex plumbing solutions",
        "category": "Home Services",
        "subcategory": "Plumbing",
        "description": "24/7 emergency commercial and residential plumbing services specializing in pipe repair and leak detection.",
        "website": "https://www.apexplumbing.example.com",
        "rating": 4.8,
        "review_count": 142,
        "employee_count_estimate": 15,
        "lead_score": 92,
        "verification_score": 95,
        "status": "qualified",
        "location": {
            "address": "742 Evergreen Terrace",
            "locality": "Downtown",
            "city": "Springfield",
            "state": "IL",
            "country": "USA",
            "postal_code": "62701",
            "latitude": 39.7817,
            "longitude": -89.6501
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 234-5678", "normalized_value": "+15552345678", "is_verified": True, "confidence": 98.0, "source": "Google Maps"},
            {"type": "email", "value": "contact@apexplumbing.example.com", "normalized_value": "contact@apexplumbing.example.com", "is_verified": True, "confidence": 90.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/apex-plumbing", "confidence": 95.0}
    },
    {
        "name": "Summit Cloud Technologies",
        "normalized_name": "summit cloud technologies",
        "category": "Technology",
        "subcategory": "Cloud Infrastructure",
        "description": "Enterprise cloud migration, DevOps automation, and AWS/Azure managed infrastructure services.",
        "website": "https://www.summitcloud.example.io",
        "rating": 4.9,
        "review_count": 89,
        "employee_count_estimate": 45,
        "lead_score": 88,
        "verification_score": 92,
        "status": "new",
        "location": {
            "address": "100 Innovation Way, Suite 400",
            "locality": "Tech District",
            "city": "Austin",
            "state": "TX",
            "country": "USA",
            "postal_code": "78701",
            "latitude": 30.2672,
            "longitude": -97.7431
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 876-5432", "normalized_value": "+15558765432", "is_verified": True, "confidence": 95.0, "source": "Google Maps"},
            {"type": "email", "value": "sales@summitcloud.example.io", "normalized_value": "sales@summitcloud.example.io", "is_verified": True, "confidence": 94.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/summit-cloud", "confidence": 98.0}
    },
    {
        "name": "Vanguard Law Group",
        "normalized_name": "vanguard law group",
        "category": "Legal",
        "subcategory": "Corporate Law",
        "description": "Full-service corporate law firm specializing in M&A, intellectual property, and venture financing.",
        "website": "https://www.vanguardlaw.example.com",
        "rating": 4.7,
        "review_count": 56,
        "employee_count_estimate": 20,
        "lead_score": 78,
        "verification_score": 88,
        "status": "contacted",
        "location": {
            "address": "500 Financial Plaza, 12th Floor",
            "locality": "Financial District",
            "city": "Chicago",
            "state": "IL",
            "country": "USA",
            "postal_code": "60603",
            "latitude": 41.881832,
            "longitude": -87.623177
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 345-6789", "normalized_value": "+15553456789", "is_verified": True, "confidence": 92.0, "source": "Google Maps"},
            {"type": "email", "value": "info@vanguardlaw.example.com", "normalized_value": "info@vanguardlaw.example.com", "is_verified": False, "confidence": 75.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "YellowPages", "source_url": "https://yellowpages.example.com/vanguard-law", "confidence": 85.0}
    },
    {
        "name": "Solaris Energy Co",
        "normalized_name": "solaris energy co",
        "category": "Clean Energy",
        "subcategory": "Solar Installation",
        "description": "Turnkey residential and commercial solar panel installation and battery storage solutions.",
        "website": "https://www.solarisenergy.example.com",
        "rating": 4.6,
        "review_count": 210,
        "employee_count_estimate": 60,
        "lead_score": 85,
        "verification_score": 90,
        "status": "qualified",
        "location": {
            "address": "1200 Sunbelt Blvd",
            "locality": "Industrial Park",
            "city": "Phoenix",
            "state": "AZ",
            "country": "USA",
            "postal_code": "85001",
            "latitude": 33.448377,
            "longitude": -112.074037
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 987-6543", "normalized_value": "+15559876543", "is_verified": True, "confidence": 97.0, "source": "Google Maps"},
            {"type": "email", "value": "quotes@solarisenergy.example.com", "normalized_value": "quotes@solarisenergy.example.com", "is_verified": True, "confidence": 91.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/solaris-energy", "confidence": 94.0}
    },
    {
        "name": "Metro Dental Care",
        "normalized_name": "metro dental care",
        "category": "Healthcare",
        "subcategory": "Dentistry",
        "description": "Comprehensive family and cosmetic dentistry, teeth whitening, and oral surgery.",
        "website": "https://www.metrodental.example.com",
        "rating": 4.5,
        "review_count": 180,
        "employee_count_estimate": 12,
        "lead_score": 64,
        "verification_score": 82,
        "status": "new",
        "location": {
            "address": "45 Medical Center Drive",
            "locality": "Midtown",
            "city": "Atlanta",
            "state": "GA",
            "country": "USA",
            "postal_code": "30308",
            "latitude": 33.7490,
            "longitude": -84.3880
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 456-7890", "normalized_value": "+15554567890", "is_verified": True, "confidence": 96.0, "source": "Google Maps"},
            {"type": "email", "value": "appointments@metrodental.example.com", "normalized_value": "appointments@metrodental.example.com", "is_verified": True, "confidence": 88.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/metro-dental", "confidence": 90.0}
    },
    {
        "name": "Quantum CyberSecurity",
        "normalized_name": "quantum cybersecurity",
        "category": "Technology",
        "subcategory": "Cybersecurity",
        "description": "Managed threat detection, SOC-as-a-service, penetration testing, and compliance audits.",
        "website": "https://www.quantumcyber.example.io",
        "rating": 4.9,
        "review_count": 73,
        "employee_count_estimate": 30,
        "lead_score": 96,
        "verification_score": 98,
        "status": "qualified",
        "location": {
            "address": "88 Cyber Way, Suite 300",
            "locality": "Seaport",
            "city": "Boston",
            "state": "MA",
            "country": "USA",
            "postal_code": "02210",
            "latitude": 42.3601,
            "longitude": -71.0589
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 654-3210", "normalized_value": "+15556543210", "is_verified": True, "confidence": 99.0, "source": "Google Maps"},
            {"type": "email", "value": "security@quantumcyber.example.io", "normalized_value": "security@quantumcyber.example.io", "is_verified": True, "confidence": 96.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/quantum-cyber", "confidence": 99.0}
    },
    {
        "name": "Beacon Marketing Agency",
        "normalized_name": "beacon marketing agency",
        "category": "Marketing",
        "subcategory": "Digital Advertising",
        "description": "Performance marketing, SEO optimization, content creation, and social media ad campaigns.",
        "website": "https://www.beaconmarketing.example.com",
        "rating": 4.3,
        "review_count": 48,
        "employee_count_estimate": 18,
        "lead_score": 58,
        "verification_score": 75,
        "status": "new",
        "location": {
            "address": "312 Creative Ave",
            "locality": "SoHo",
            "city": "New York",
            "state": "NY",
            "country": "USA",
            "postal_code": "10012",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 789-0123", "normalized_value": "+15557890123", "is_verified": False, "confidence": 70.0, "source": "Google Maps"},
            {"type": "email", "value": "hello@beaconmarketing.example.com", "normalized_value": "hello@beaconmarketing.example.com", "is_verified": True, "confidence": 85.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Clutch.co", "source_url": "https://clutch.example.com/beacon-marketing", "confidence": 80.0}
    },
    {
        "name": "Horizon Logistics Solutions",
        "normalized_name": "horizon logistics solutions",
        "category": "Logistics",
        "subcategory": "Freight & Warehousing",
        "description": "Third-party warehousing, cold chain storage, and freight distribution across North America.",
        "website": "https://www.horizonlogistics.example.com",
        "rating": 4.4,
        "review_count": 94,
        "employee_count_estimate": 110,
        "lead_score": 74,
        "verification_score": 86,
        "status": "contacted",
        "location": {
            "address": "5500 Cargo Way",
            "locality": "Port Area",
            "city": "Seattle",
            "state": "WA",
            "country": "USA",
            "postal_code": "98134",
            "latitude": 47.6062,
            "longitude": -122.3321
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 321-0987", "normalized_value": "+15553210987", "is_verified": True, "confidence": 91.0, "source": "Google Maps"},
            {"type": "email", "value": "dispatch@horizonlogistics.example.com", "normalized_value": "dispatch@horizonlogistics.example.com", "is_verified": True, "confidence": 89.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/horizon-logistics", "confidence": 92.0}
    },
    {
        "name": "Pinnacle Financial Services",
        "normalized_name": "pinnacle financial services",
        "category": "Finance",
        "subcategory": "Wealth Management",
        "description": "Personalized retirement planning, wealth management, tax optimization, and estate strategies.",
        "website": "https://www.pinnaclefinance.example.com",
        "rating": 4.8,
        "review_count": 115,
        "employee_count_estimate": 25,
        "lead_score": 82,
        "verification_score": 94,
        "status": "qualified",
        "location": {
            "address": "900 Wall Street Blvd, Ste 1500",
            "locality": "Downtown",
            "city": "Denver",
            "state": "CO",
            "country": "USA",
            "postal_code": "80202",
            "latitude": 39.7392,
            "longitude": -104.9903
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 210-9876", "normalized_value": "+15552109876", "is_verified": True, "confidence": 97.0, "source": "Google Maps"},
            {"type": "email", "value": "advisors@pinnaclefinance.example.com", "normalized_value": "advisors@pinnaclefinance.example.com", "is_verified": True, "confidence": 93.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/pinnacle-finance", "confidence": 96.0}
    },
    {
        "name": "Veritas Health Systems",
        "normalized_name": "veritas health systems",
        "category": "Healthcare",
        "subcategory": "Urgent Care",
        "description": "Walk-in urgent care clinic providing X-rays, lab testing, pediatric care, and occupational medicine.",
        "website": "https://www.veritashealth.example.com",
        "rating": 4.1,
        "review_count": 165,
        "employee_count_estimate": 35,
        "lead_score": 48,
        "verification_score": 70,
        "status": "new",
        "location": {
            "address": "220 Oak Ridge Lane",
            "locality": "Suburbs",
            "city": "Columbus",
            "state": "OH",
            "country": "USA",
            "postal_code": "43215",
            "latitude": 39.9612,
            "longitude": -82.9988
        },
        "contacts": [
            {"type": "phone", "value": "+1 (555) 543-2109", "normalized_value": "+15555432109", "is_verified": True, "confidence": 88.0, "source": "Google Maps"},
            {"type": "email", "value": "care@veritashealth.example.com", "normalized_value": "care@veritashealth.example.com", "is_verified": False, "confidence": 65.0, "source": "Website Scraper"}
        ],
        "source": {"source_name": "Google Maps", "source_url": "https://maps.example.com/place/veritas-health", "confidence": 87.0}
    }
]

def seed_db():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    added_count = 0
    updated_count = 0

    try:
        for b_data in SAMPLE_BUSINESSES:
            existing = db.query(Business).filter(Business.normalized_name == b_data["normalized_name"]).first()
            if existing:
                # Update scores/status if needed to ensure idempotency
                existing.lead_score = b_data["lead_score"]
                existing.verification_score = b_data["verification_score"]
                existing.status = b_data["status"]
                updated_count += 1
                continue

            business_id = uuid.uuid4()
            business = Business(
                id=business_id,
                name=b_data["name"],
                normalized_name=b_data["normalized_name"],
                category=b_data["category"],
                subcategory=b_data["subcategory"],
                description=b_data["description"],
                website=b_data["website"],
                rating=b_data["rating"],
                review_count=b_data["review_count"],
                employee_count_estimate=b_data["employee_count_estimate"],
                lead_score=b_data["lead_score"],
                verification_score=b_data["verification_score"],
                status=b_data["status"],
                first_seen_at=now,
                last_verified_at=now,
                created_at=now,
                updated_at=now
            )
            db.add(business)

            loc_data = b_data["location"]
            location = BusinessLocation(
                id=uuid.uuid4(),
                business_id=business_id,
                address=loc_data["address"],
                locality=loc_data["locality"],
                city=loc_data["city"],
                state=loc_data["state"],
                country=loc_data["country"],
                postal_code=loc_data["postal_code"],
                latitude=loc_data["latitude"],
                longitude=loc_data["longitude"],
                created_at=now
            )
            db.add(location)

            for c_data in b_data["contacts"]:
                contact = BusinessContact(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    type=c_data["type"],
                    value=c_data["value"],
                    normalized_value=c_data["normalized_value"],
                    is_verified=c_data["is_verified"],
                    confidence=c_data["confidence"],
                    source=c_data["source"],
                    first_seen_at=now,
                    last_verified_at=now
                )
                db.add(contact)

            src_data = b_data["source"]
            source_rec = SourceRecord(
                id=uuid.uuid4(),
                business_id=business_id,
                source_name=src_data["source_name"],
                source_url=src_data["source_url"],
                raw_data={"seeded": True, "category": b_data["category"]},
                discovered_at=now,
                confidence=src_data["confidence"]
            )
            db.add(source_rec)
            added_count += 1

        db.commit()
        print(f"Seed completed successfully! Added {added_count} new businesses, updated {updated_count} existing businesses.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
