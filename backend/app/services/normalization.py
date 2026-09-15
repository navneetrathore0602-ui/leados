import re
from urllib.parse import urlparse

LEGAL_SUFFIXES_REGEX = re.compile(
    r'\b(pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|inc\.?|llp\.?|corp\.?|corporation|co\.?|company)\b',
    re.IGNORECASE
)

def normalize_business_name(name: str) -> str:
    if not name:
        return ""
    cleaned = name.lower()
    # Strip legal entity suffix
    cleaned = LEGAL_SUFFIXES_REGEX.sub('', cleaned)
    # Replace symbols and punctuation with space
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    # Collapse multiple spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned

def normalize_website(url: str) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    if not u.startswith(('http://', 'https://')):
        u = 'http://' + u
    try:
        parsed = urlparse(u)
        hostname = parsed.hostname or ""
        if hostname.startswith("www."):
            hostname = hostname[4:]
        path = parsed.path.rstrip('/')
        return f"{hostname}{path}"
    except Exception:
        # Fallback simple regex cleanup
        u = re.sub(r'^https?://', '', u)
        u = re.sub(r'^www\.', '', u)
        return u.rstrip('/')

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    # Retain digits only for matching
    digits = re.sub(r'\D', '', phone)
    # Strip leading zeros or country codes if necessary, or return clean digits
    return digits


def normalize_business_records(businesses: list, db=None) -> int:
    """
    Normalizes names, websites, and contacts across a list of business models.
    """
    count = 0
    for b in businesses:
        if b.name and not b.normalized_name:
            b.normalized_name = normalize_business_name(b.name)
        if b.website:
            b.website = b.website.strip()
        for c in (b.contacts or []):
            if c.value and not c.normalized_value:
                if c.type in ["phone", "mobile"]:
                    c.normalized_value = normalize_phone(c.value)
                elif c.type == "email":
                    c.normalized_value = c.value.strip().lower()
        count += 1
    if db:
        db.commit()
    return count

