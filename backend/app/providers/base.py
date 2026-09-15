from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class DiscoveryProvider(ABC):
    """
    Abstract Base Class for LeadOS Discovery Providers.
    All providers (Mock, Google Maps, Directories) must implement this interface
    and return standardized discovery result dictionaries.
    """

    @abstractmethod
    def search(
        self,
        campaign: Any,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Execute search query based on campaign criteria.
        Returns a list of normalized raw business dictionary results.
        """
        pass

    @abstractmethod
    def fetch_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch extended details for a specific record if supported by provider.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify provider availability and operational status.
        """
        pass
