from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "LeadOS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "leados_dev_secret_key_8f9a2b4c6e1d"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    DATABASE_URL: str = "sqlite:///./leados.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    LEADOS_ADMIN_EMAIL: Optional[str] = None
    LEADOS_ADMIN_PASSWORD: Optional[str] = None

    DISCOVERY_TEST_LIMIT: int = 10000

    OSM_NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
    OSM_USER_AGENT: str = "LeadOS/3.0"

    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GOOGLE_PLACES_NEW_URL: str = "https://places.googleapis.com/v1/places:searchText"
    GOOGLE_PLACE_DETAILS_NEW_URL: str = "https://places.googleapis.com/v1/places"
    GOOGLE_PLACES_URL: str = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    GOOGLE_PLACE_DETAILS_URL: str = "https://maps.googleapis.com/maps/api/place/details/json"

    ENRICHMENT_MAX_PAGES_PER_BUSINESS: int = 4
    ENRICHMENT_MAX_DURATION_SECONDS: int = 15
    ENRICHMENT_MAX_RESPONSE_SIZE: int = 1048576  # 1MB max per page
    ENRICHMENT_MAX_REDIRECTS: int = 3
    ENRICHMENT_MAX_RETRIES: int = 2
    ENRICHMENT_RETRY_BACKOFF_SECONDS: float = 1.0
    ENRICHMENT_MAX_CONCURRENCY: int = 5
    ENRICHMENT_DOMAIN_DELAY_SECONDS: float = 1.0

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.DATABASE_URL

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

