import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

from app.providers.base import DiscoveryProvider
from app.enrichment.base import EnrichmentProvider
from app.core.config import settings
from app.services.normalization import normalize_phone, normalize_website

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
EMAIL_FIND_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_TEXT_REGEX = re.compile(r'(?:\+?\d{1,4}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}')

SOCIAL_PATTERNS = {
    "instagram": re.compile(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.-]+)/?'),
    "facebook": re.compile(r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9_.-]+)/?'),
    "linkedin": re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in|school|showcase)/([a-zA-Z0-9_.-]+)/?'),
    "youtube": re.compile(r'https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)?([a-zA-Z0-9_.-]+)/?'),
    "x": re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_.-]+)/?')
}

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "igshid", "fbclid", "ref", "s", "t", "rc"}
GENERIC_SOCIAL_PATHS = {"share", "sharer", "intent", "p", "posts", "reel", "reels", "stories", "dialog", "home", "search", "explore", "privacy", "terms", "policy", "login", "signup"}


def is_plausible_phone(raw_str: str, context_text: str = "") -> bool:
    """
    Validation function to reject false-positive phone numbers (software versions, floating point decimals,
    dates, standalone postal codes) while accepting plausible international and local phone numbers.
    """
    if not raw_str or not isinstance(raw_str, str):
        return False

    cleaned = raw_str.strip()

    # Reject floating point decimals or software version numbers (e.g. 5.6666666666666 or Python 3.12.1)
    if "." in cleaned:
        parts = cleaned.split(".")
        # If any segment after the dot has > 4 digits or non-digits, it's a float/version, not phone punctuation
        for p in parts[1:]:
            if len(p) > 4 or not p.isdigit():
                return False
        # If there are more than 3 dots, it's not a phone number
        if len(parts) > 4:
            return False

    # Extract pure digits
    digits = re.sub(r'\D', '', cleaned)
    digit_count = len(digits)

    # Standard E.164 length check (7 to 15 digits)
    if digit_count < 7 or digit_count > 15:
        return False

    # Reject standalone 4-digit years (e.g., 1999, 2024, 2025, 2026)
    if re.match(r'^(19|20)\d{2}$', digits):
        return False

    # Reject repeating single digits (e.g. 0000000000 or 1111111111)
    if len(set(digits)) == 1:
        return False

    # Reject standalone 5/6 digit postal codes unless telephone context or explicit phone syntax (+ or parentheses) is present
    phone_context_keywords = ["phone", "tel", "call", "mobile", "contact", "fax", "cell", "telephone", "ph", "whatsapp"]
    has_phone_context = any(kw in context_text.lower() for kw in phone_context_keywords)
    has_phone_syntax = any(char in cleaned for char in ['+', '(', ')'])

    if (digit_count in (5, 6)) and not (has_phone_context or has_phone_syntax):
        return False

    return True


def validate_email_syntax(email_str: str) -> Optional[str]:
    """
    Validates email syntax and returns canonical lowercase email or None if invalid.
    Separates EMAIL_FOUND from EMAIL_SYNTAX_VALID.
    """
    if not email_str or not isinstance(email_str, str):
        return None
    cleaned = email_str.strip()
    if ".." in cleaned or cleaned.startswith(".") or cleaned.endswith("."):
        return None
    if EMAIL_REGEX.match(cleaned):
        return cleaned.lower()
    return None


def normalize_social_url(url: str, platform: str) -> Optional[Dict[str, str]]:
    """
    Canonicalizes social profile URLs by stripping tracking query params (utm_*, igshid, fbclid, ref)
    and rejecting generic share/intent/sharer URLs.
    """
    if not url or not isinstance(url, str):
        return None

    try:
        parsed = urllib.parse.urlparse(url)
        # Parse query params and strip tracking params
        query_dict = urllib.parse.parse_qs(parsed.query)
        clean_query = {k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS}
        new_query = urllib.parse.urlencode(clean_query, doseq=True)

        path_parts = [p for p in parsed.path.split('/') if p]
        if not path_parts:
            return None

        first_part = path_parts[0].lower()
        if first_part in GENERIC_SOCIAL_PATHS:
            return None

        username = None
        if platform in ("instagram", "facebook", "x", "twitter"):
            username = path_parts[0]
            if username.startswith("@"):
                username = username[1:]
        elif platform == "linkedin":
            if len(path_parts) >= 2 and path_parts[0].lower() in ("company", "in", "school", "showcase"):
                username = path_parts[1]
            else:
                username = path_parts[0]
        elif platform == "youtube":
            username = path_parts[0]
            if username.startswith("@"):
                username = username[1:]

        if not username or username.lower() in GENERIC_SOCIAL_PATHS:
            return None

        clean_path = f"/{'/'.join(path_parts)}"
        canonical_url = urllib.parse.urlunparse((
            parsed.scheme or "https",
            parsed.netloc.lower(),
            clean_path,
            "",
            new_query,
            ""
        ))

        return {
            "platform": platform,
            "profile_url": canonical_url,
            "username": username
        }
    except Exception:
        return None


class WebsiteEnrichmentProvider(EnrichmentProvider):
    """
    Public business website enrichment provider.
    Inspects publicly accessible pages (/, /contact, /about, /services)
    extracting business contacts, social profiles, metadata, and field provenance with page-level telemetry.
    """

    def can_enrich(self, business: Any) -> bool:
        return True

    def health_check(self) -> bool:
        return True

    def _discover_website_candidate(self, business: Any) -> Optional[Dict[str, Any]]:
        """
        Attempt to identify official business website for businesses without a website.
        """
        b_name = getattr(business, "name", "") or ""
        norm_name = getattr(business, "normalized_name", "") or b_name.lower()
        
        if not norm_name or len(norm_name.strip()) < 3:
            return None

        slug = re.sub(r'[^a-z0-9]', '', norm_name)
        if not slug:
            return None

        candidate_domains = [
            f"https://www.{slug}.com",
            f"https://www.{slug}.in",
            f"https://www.{slug}.co.in"
        ]

        headers = {"User-Agent": settings.OSM_USER_AGENT}
        for candidate_url in candidate_domains:
            try:
                with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                    resp = client.get(candidate_url, headers=headers)
                    if resp.status_code == 200:
                        confidence = 0.88 if f"{slug}.com" in candidate_url or f"{slug}.in" in candidate_url else 0.75
                        return {
                            "value": candidate_url,
                            "source": "website_discovery_service",
                            "source_url": candidate_url,
                            "confidence": confidence
                        }
            except Exception:
                continue

        return None

    def _fetch_page_with_telemetry(self, url: str) -> Dict[str, Any]:
        """
        Fetches an HTTP page with page-level telemetry (duration_ms, http_status, failure_category, response_bytes)
        and bounded exponential backoff retries.
        """
        headers = {"User-Agent": settings.OSM_USER_AGENT}
        max_retries = int(getattr(settings, "ENRICHMENT_MAX_RETRIES", 2))
        backoff_sec = float(getattr(settings, "ENRICHMENT_RETRY_BACKOFF_SECONDS", 1.0))
        max_duration = float(settings.ENRICHMENT_MAX_DURATION_SECONDS)
        max_redirects = settings.ENRICHMENT_MAX_REDIRECTS

        telemetry = {
            "url": url,
            "http_status": None,
            "duration_ms": 0.0,
            "failure_category": None,
            "response_bytes": 0,
            "attempts": 0,
            "content": None
        }

        for attempt in range(max_retries + 1):
            telemetry["attempts"] = attempt + 1
            start_time = time.perf_counter()
            try:
                with httpx.Client(
                    timeout=max_duration,
                    follow_redirects=True,
                    max_redirects=max_redirects
                ) as client:
                    resp = client.get(url, headers=headers)
                    dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    telemetry["duration_ms"] = dur_ms
                    telemetry["http_status"] = resp.status_code
                    telemetry["response_bytes"] = len(resp.content)

                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "")
                        if "text/html" in content_type or "application/xhtml" in content_type or resp.text.startswith("<"):
                            telemetry["content"] = resp.text[:settings.ENRICHMENT_MAX_RESPONSE_SIZE]
                            telemetry["failure_category"] = None
                            return telemetry
                        else:
                            telemetry["failure_category"] = "INVALID_CONTENT_TYPE"
                            return telemetry
                    elif 400 <= resp.status_code < 500:
                        telemetry["failure_category"] = "HTTP_4XX"
                        return telemetry
                    elif 500 <= resp.status_code < 600:
                        telemetry["failure_category"] = "HTTP_5XX"
            except httpx.TimeoutException:
                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                telemetry["duration_ms"] = dur_ms
                telemetry["failure_category"] = "TIMEOUT"
            except httpx.TooManyRedirects:
                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                telemetry["duration_ms"] = dur_ms
                telemetry["failure_category"] = "TOO_MANY_REDIRECTS"
            except Exception:
                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                telemetry["duration_ms"] = dur_ms
                telemetry["failure_category"] = "CONNECTION_ERROR"

            if attempt < max_retries and telemetry["failure_category"] in ("HTTP_5XX", "TIMEOUT", "CONNECTION_ERROR"):
                time.sleep(backoff_sec * (2 ** attempt))

        return telemetry

    def enrich(self, business: Any) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()

        site_url = getattr(business, "website", None)
        discovered_site = None

        if not site_url or not site_url.strip():
            disc_res = self._discover_website_candidate(business)
            if disc_res:
                site_url = disc_res["value"]
                discovered_site = disc_res

        if not site_url or not site_url.strip():
            return {
                "website": None,
                "phone": None,
                "email": None,
                "whatsapp": None,
                "social_profiles": [],
                "description": None,
                "services": [],
                "opening_hours": None,
                "candidate_fields": [],
                "reachability_state": "UNREACHABLE",
                "pages_attempted": 0,
                "pages_successful": 0,
                "pages_failed": 0,
                "total_http_requests": 0,
                "telemetry_logs": [],
                "page_durations_ms": []
            }

        if not site_url.startswith("http://") and not site_url.startswith("https://"):
            site_url = f"https://{site_url}"

        parsed_base = urllib.parse.urlparse(site_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"

        target_paths = ["", "/contact", "/about", "/services"]
        max_pages = settings.ENRICHMENT_MAX_PAGES_PER_BUSINESS

        html_pages: List[Dict[str, str]] = []
        telemetry_logs: List[Dict[str, Any]] = []
        page_durations: List[float] = []

        total_requests = 0
        pages_successful = 0
        pages_failed = 0
        root_success = False

        for idx, path in enumerate(target_paths):
            if len(html_pages) >= max_pages:
                break
            page_url = f"{base_domain}{path}" if path else base_domain
            
            telemetry = self._fetch_page_with_telemetry(page_url)
            total_requests += telemetry["attempts"]
            page_durations.append(telemetry["duration_ms"])
            
            log_entry = {
                "url": page_url,
                "http_status": telemetry["http_status"],
                "duration_ms": telemetry["duration_ms"],
                "failure_category": telemetry["failure_category"],
                "response_bytes": telemetry["response_bytes"],
                "attempts": telemetry["attempts"]
            }
            telemetry_logs.append(log_entry)

            if telemetry["content"]:
                html_pages.append({"url": page_url, "html": telemetry["content"]})
                pages_successful += 1
                if idx == 0:
                    root_success = True
            else:
                pages_failed += 1

        # Determine Reachability State
        if root_success:
            reachability_state = "SUCCESS"
        elif pages_successful > 0:
            reachability_state = "PARTIAL"
        elif any(t["failure_category"] in ("HTTP_4XX", "HTTP_5XX") for t in telemetry_logs):
            reachability_state = "FAILED"
        else:
            reachability_state = "UNREACHABLE"

        website_prov = discovered_site or {
            "value": site_url,
            "source": "business_website",
            "source_url": site_url,
            "confidence": 0.98,
            "discovered_at": now_iso
        }

        if not html_pages:
            return {
                "website": website_prov,
                "phone": None,
                "email": None,
                "whatsapp": None,
                "social_profiles": [],
                "description": None,
                "services": [],
                "opening_hours": None,
                "candidate_fields": [],
                "reachability_state": reachability_state,
                "pages_attempted": len(telemetry_logs),
                "pages_successful": 0,
                "pages_failed": pages_failed,
                "total_http_requests": total_requests,
                "telemetry_logs": telemetry_logs,
                "page_durations_ms": page_durations
            }

        extracted_phones: List[Dict[str, Any]] = []
        extracted_emails: List[Dict[str, Any]] = []
        extracted_whatsapp: Optional[Dict[str, Any]] = None
        extracted_socials: List[Dict[str, Any]] = []
        extracted_description: Optional[Dict[str, Any]] = None
        extracted_services: List[Dict[str, Any]] = []
        extracted_hours: Optional[Dict[str, Any]] = None
        candidates: List[Dict[str, Any]] = []

        seen_social_urls = set()
        seen_emails = set()
        seen_phones = set()

        for page in html_pages:
            page_url = page["url"]
            soup = BeautifulSoup(page["html"], "html.parser")

            # 1. Extract Meta Description
            if not extracted_description:
                meta_desc = (
                    soup.find("meta", attrs={"name": "description"}) or
                    soup.find("meta", attrs={"property": "og:description"})
                )
                if meta_desc and meta_desc.get("content"):
                    desc_text = meta_desc["content"].strip()
                    if len(desc_text) > 10:
                        extracted_description = {
                            "value": desc_text[:500],
                            "source": "website_meta_description",
                            "source_url": page_url,
                            "confidence": 0.92,
                            "discovered_at": now_iso
                        }

            # 2. Extract Anchor Links (tel:, mailto:, wa.me, socials)
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full_href = urllib.parse.urljoin(page_url, href)

                # tel: links
                if href.startswith("tel:"):
                    raw_ph = href.replace("tel:", "").strip()
                    if is_plausible_phone(raw_ph, context_text=f"tel:{raw_ph}"):
                        norm_ph = normalize_phone(raw_ph)
                        if norm_ph and norm_ph not in seen_phones:
                            seen_phones.add(norm_ph)
                            extracted_phones.append({
                                "value": raw_ph,
                                "normalized_value": norm_ph,
                                "source": "website_contact_link",
                                "source_url": page_url,
                                "confidence": 0.95,
                                "discovered_at": now_iso
                            })

                # mailto: links
                elif href.startswith("mailto:"):
                    raw_em = href.replace("mailto:", "").split("?")[0].strip()
                    valid_em = validate_email_syntax(raw_em)
                    if valid_em and valid_em not in seen_emails:
                        seen_emails.add(valid_em)
                        extracted_emails.append({
                            "value": raw_em,
                            "normalized_value": valid_em,
                            "source": "website_mailto_link",
                            "source_url": page_url,
                            "confidence": 0.95,
                            "verification_status": "syntax_valid",
                            "discovered_at": now_iso
                        })

                # WhatsApp links
                elif "wa.me/" in href or "api.whatsapp.com/send" in href:
                    if not extracted_whatsapp:
                        extracted_whatsapp = {
                            "value": full_href,
                            "source": "website_whatsapp_link",
                            "source_url": page_url,
                            "confidence": 0.92,
                            "discovered_at": now_iso
                        }

                # Social links
                for platform, pat in SOCIAL_PATTERNS.items():
                    m = pat.match(full_href)
                    if m:
                        canon_social = normalize_social_url(full_href, platform)
                        if canon_social and canon_social["profile_url"] not in seen_social_urls:
                            seen_social_urls.add(canon_social["profile_url"])
                            extracted_socials.append({
                                "platform": canon_social["platform"],
                                "profile_url": canon_social["profile_url"],
                                "username": canon_social["username"],
                                "source": "website_social_link",
                                "source_url": page_url,
                                "confidence": 0.92,
                                "discovered_at": now_iso
                            })

            # 3. Extract Text Emails and Phones via Regex with strict precision checks
            page_text = soup.get_text(separator=" ")
            
            for em in EMAIL_FIND_REGEX.findall(page_text):
                valid_em = validate_email_syntax(em)
                if valid_em:
                    # Exclude common image/script/asset artifacts
                    if not any(valid_em.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".js", ".css", ".webp", ".png@2x"]):
                        if valid_em not in seen_emails:
                            seen_emails.add(valid_em)
                            extracted_emails.append({
                                "value": em,
                                "normalized_value": valid_em,
                                "source": "website_text_regex",
                                "source_url": page_url,
                                "confidence": 0.88,
                                "verification_status": "syntax_valid",
                                "discovered_at": now_iso
                            })

            for ph in PHONE_TEXT_REGEX.findall(page_text):
                ph_str = ph.strip()
                if is_plausible_phone(ph_str, context_text=page_text[:200]):
                    norm_ph = normalize_phone(ph_str)
                    if norm_ph and len(norm_ph) >= 7 and norm_ph not in seen_phones:
                        seen_phones.add(norm_ph)
                        extracted_phones.append({
                            "value": ph_str,
                            "normalized_value": norm_ph,
                            "source": "website_text_regex",
                            "source_url": page_url,
                            "confidence": 0.82,
                            "discovered_at": now_iso
                        })

            # 4. Services Extraction
            if "/services" in page_url or "services" in page_url.lower():
                service_tags = soup.find_all(["h2", "h3", "h4", "li"])
                for tag in service_tags:
                    stext = tag.get_text().strip()
                    if 3 < len(stext) < 60 and not any(s["name"] == stext for s in extracted_services):
                        extracted_services.append({
                            "name": stext,
                            "source": "website_services_page",
                            "source_url": page_url,
                            "confidence": 0.85
                        })
                        if len(extracted_services) >= 10:
                            break

        primary_phone = extracted_phones[0] if extracted_phones else None
        if len(extracted_phones) > 1:
            for extra_ph in extracted_phones[1:]:
                candidates.append({
                    "field_name": "phone",
                    "value": extra_ph["value"],
                    "normalized_value": extra_ph["normalized_value"],
                    "source": extra_ph["source"],
                    "source_url": extra_ph["source_url"],
                    "confidence": extra_ph["confidence"],
                    "status": "conflicting" if primary_phone and extra_ph["normalized_value"] != primary_phone["normalized_value"] else "candidate"
                })

        primary_email = extracted_emails[0] if extracted_emails else None
        if len(extracted_emails) > 1:
            for extra_em in extracted_emails[1:]:
                candidates.append({
                    "field_name": "email",
                    "value": extra_em["value"],
                    "normalized_value": extra_em["normalized_value"],
                    "source": extra_em["source"],
                    "source_url": extra_em["source_url"],
                    "confidence": extra_em["confidence"],
                    "status": "candidate"
                })

        return {
            "website": website_prov,
            "phone": primary_phone,
            "email": primary_email,
            "whatsapp": extracted_whatsapp,
            "social_profiles": extracted_socials,
            "description": extracted_description,
            "services": extracted_services,
            "opening_hours": extracted_hours,
            "candidate_fields": candidates,
            "reachability_state": reachability_state,
            "pages_attempted": len(telemetry_logs),
            "pages_successful": pages_successful,
            "pages_failed": pages_failed,
            "total_http_requests": total_requests,
            "telemetry_logs": telemetry_logs,
            "page_durations_ms": page_durations
        }

