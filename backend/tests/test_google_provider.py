import sys
import os
import uuid
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.google_places import GooglePlacesDiscoveryProvider
from app.providers.partitions import generate_location_partitions
from app.providers.registry import get_provider, list_providers


class DummyCampaign:
    def __init__(self, keywords=None, locations=None, category=None):
        self.id = uuid.uuid4()
        self.keywords = keywords or ["Restaurants"]
        self.locations = locations or ["Mumbai"]
        self.category = category or "Hospitality"
        self.target_leads = 10


def test_partition_generator():
    partitions = generate_location_partitions("Marble Dealers", "Mumbai")
    assert len(partitions) >= 10
    assert partitions[0] == "Marble Dealers Mumbai"
    assert any("Andheri" in p for p in partitions)
    assert any("Goregaon" in p for p in partitions)


def test_google_provider_registry():
    provider = get_provider("google")
    assert isinstance(provider, GooglePlacesDiscoveryProvider)
    
    provider_places = get_provider("google_places")
    assert isinstance(provider_places, GooglePlacesDiscoveryProvider)

    providers = list_providers()
    provider_ids = [p["id"] for p in providers]
    assert "google" in provider_ids


def test_google_provider_health_check():
    with patch("app.providers.google_places.settings.GOOGLE_MAPS_API_KEY", "test_fake_key"):
        provider = GooglePlacesDiscoveryProvider()
        assert provider.health_check() is True

    with patch("app.providers.google_places.settings.GOOGLE_MAPS_API_KEY", ""):
        provider = GooglePlacesDiscoveryProvider()
        assert provider.health_check() is False


def test_google_provider_search_success_v1_new():
    mock_google_response = {
        "places": [
            {
                "id": "ChIJN1t_t_xT5zsR0Wp_mock_id",
                "displayName": {
                    "text": "Bastian Mumbai",
                    "languageCode": "en"
                },
                "formattedAddress": "Linking Road, Bandra West, Mumbai, Maharashtra 400050, India",
                "location": {
                    "latitude": 19.0600,
                    "longitude": 72.8300
                },
                "rating": 4.5,
                "userRatingCount": 1250,
                "nationalPhoneNumber": "022 2642 0000",
                "websiteUri": "https://www.bastianmumbai.com",
                "googleMapsUri": "https://maps.google.com/?cid=12345",
                "types": ["restaurant", "food", "point_of_interest"]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_google_response

    with patch("app.providers.google_places.settings.GOOGLE_MAPS_API_KEY", "valid_fake_key"):
        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            provider = GooglePlacesDiscoveryProvider()
            campaign = DummyCampaign(keywords=["Restaurants"], locations=["Mumbai"])
            results = provider.search(campaign, page=1, limit=10)

            mock_post.assert_called()
            first_call_args = mock_post.call_args_list[0]
            _, kwargs = first_call_args
            headers = kwargs.get("headers", {})
            json_body = kwargs.get("json", {})
            
            assert headers.get("X-Goog-Api-Key") == "valid_fake_key"
            assert "places.displayName" in headers.get("X-Goog-FieldMask", "")
            assert "Restaurants Mumbai" in json_body.get("textQuery", "")

            assert len(results) == 1
            item = results[0]
            assert item["name"] == "Bastian Mumbai"
            assert item["city"] == "Mumbai"
            assert item["phone"] == "022 2642 0000"
            assert item["website"] == "https://www.bastianmumbai.com"
            assert item["rating"] == 4.5
            assert item["review_count"] == 1250
            assert item["source_name"] == "Google Places API"
            assert item["source_url"] == "https://maps.google.com/?cid=12345"


def test_google_provider_quota_error_propagation_v1_new():
    mock_google_response = {
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota).",
            "status": "RESOURCE_EXHAUSTED"
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = mock_google_response

    with patch("app.providers.google_places.settings.GOOGLE_MAPS_API_KEY", "valid_fake_key"):
        with patch("httpx.Client.post", return_value=mock_resp):
            provider = GooglePlacesDiscoveryProvider()
            campaign = DummyCampaign()
            with pytest.raises(RuntimeError) as exc_info:
                provider.search(campaign, page=1, limit=10)
            assert "GOOGLE_QUOTA_EXCEEDED" in str(exc_info.value)
