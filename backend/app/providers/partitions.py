import re
from typing import List

# Sub-location partitions for major metro cities in India
METRO_SUB_LOCATIONS = {
    "mumbai": [
        "Andheri", "Goregaon", "Malad", "Borivali", "Vile Parle", "Powai",
        "Bhandup", "Mulund", "Thane", "Navi Mumbai", "Bandra", "Worli",
        "Dadar", "Kurla", "Ghatkopar", "Kandivali", "Lower Parel"
    ],
    "delhi": [
        "Connaught Place", "Nehru Place", "South Extension", "Dwarka",
        "Rohini", "Lajpat Nagar", "Karol Bagh", "Okhla", "Janakpuri",
        "Pitampura", "Chandni Chowk", "Mayur Vihar", "Noida", "Gurgaon"
    ],
    "bangalore": [
        "Indiranagar", "Koramangala", "HSR Layout", "Whitefield",
        "Jayanagar", "JP Nagar", "Hebbal", "Yelahanka", "Marathahalli",
        "Electronic City", "Rajajinagar", "Malleshwaram", "Banashankari"
    ],
    "pune": [
        "Kothrud", "Viman Nagar", "Hinjawadi", "Baner", "Aundh",
        "Wakad", "Hadapsar", "Pimpri", "Chinchwad", "Camp", "Shivajinagar"
    ],
    "hyderabad": [
        "Hitec City", "Gachibowli", "Jubilee Hills", "Banjara Hills",
        "Madhapur", "Kukatpally", "Secunderabad", "Ameerpet", "Kondapur"
    ],
    "chennai": [
        "T Nagar", "Anna Nagar", "Velachery", "Adyar", "Nungambakkam",
        "OMR", "Porur", "Mylapore", "Tambaram", "Guindy"
    ],
    "kolkata": [
        "Salt Lake", "New Town", "Park Street", "Bhowanipore",
        "Ballygunge", "Howrah", "Dum Dum", "Behala", "Jadavpur"
    ],
    "kishangarh": [
        "RIICO Industrial Area", "Madanganj", "Silora", "Ajmer Road",
        "Makrana Road", "Marble City", "Industrial Area", "Harmada Road",
        "Naya Nagar", "Pasand Nagar", "Bypass", "Industrial Estate",
        "Stone Market", "Granite Market", "RICCO Phase 1", "RICCO Phase 2",
        "RICCO Phase 3", "RICCO Phase 4", "Tehsil", "Surajpole"
    ],
    "ajmer": [
        "Kishangarh", "Madanganj", "RIICO Industrial Area", "Silora",
        "Makhupura", "Pushkar Road", "Nasirabad Road", "Jaipur Road"
    ]
}

# Generic directional / area partitions for any other location worldwide
GENERIC_PARTITIONS = [
    "North", "South", "East", "West", "Central",
    "Industrial Area", "Market", "City Center"
]

def generate_location_partitions(category: str, location: str) -> List[str]:
    """
    Dynamically generates geographic search query partitions and relevant category variations
    for a given business category and location.
    """
    clean_cat = (category or "business").strip()
    clean_loc = (location or "city").strip()

    primary_query = f"{clean_cat} {clean_loc}".strip()
    partitions = [primary_query]

    # Normalize location name to check metro mappings
    loc_key = re.sub(r"[^\w\s]", "", clean_loc.lower()).strip()
    cat_key = re.sub(r"[^\w\s]", "", clean_cat.lower()).strip()
    
    sub_areas = None
    for k in METRO_SUB_LOCATIONS:
        if k in loc_key:
            sub_areas = METRO_SUB_LOCATIONS[k]
            break

    # Industry Category variations for thorough discovery
    cat_variations = []
    if "marble" in cat_key or "granite" in cat_key or "stone" in cat_key:
        cat_variations = [
            "Granite Dealers", "Marble Manufacturers", "Marble Exporters",
            "Marble Factory", "Stone Suppliers", "Marble Gangsaw"
        ]
    elif "restaurant" in cat_key or "food" in cat_key:
        cat_variations = ["Cafes", "Dining", "Bistros", "Bakeries"]
    elif "hotel" in cat_key or "resort" in cat_key:
        cat_variations = ["Resorts", "Lodging", "Guest House", "Homestays"]

    for var in cat_variations:
        var_query = f"{var} {clean_loc}".strip()
        if var_query not in partitions:
            partitions.append(var_query)

    if sub_areas:
        for area in sub_areas:
            partitions.append(f"{clean_cat} {area} {clean_loc}")
            for var in cat_variations[:2]:
                partitions.append(f"{var} {area} {clean_loc}")
    else:
        for area in GENERIC_PARTITIONS:
            partitions.append(f"{clean_cat} {clean_loc} {area}")
            for var in cat_variations[:2]:
                partitions.append(f"{var} {clean_loc} {area}")

    return partitions
