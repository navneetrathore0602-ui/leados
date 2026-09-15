from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class EnrichmentProvider(ABC):
    """
    Abstract base class for all LeadOS business enrichment providers.
    """

    @abstractmethod
    def can_enrich(self, business: Any) -> bool:
        """
        Check if provider can attempt enrichment for this business instance.
        """
        pass

    @abstractmethod
    def enrich(self, business: Any) -> Dict[str, Any]:
        """
        Execute business profile enrichment.
        Must return standardized dictionary structure with field-level provenance.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Health status check of provider.
        """
        pass
