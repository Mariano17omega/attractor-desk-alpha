"""
Exa search provider implementation.
Optional - fails gracefully if API key is not configured.
"""

from typing import Optional

from core.config import get_exa_api_key, is_web_search_enabled
from core.providers.search import SearchProvider, SearchResult


class ExaSearchProvider(SearchProvider):
    """
    Search provider using Exa.ai semantic search.
    
    Requires EXA_API_KEY in API_KEY.txt.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client = None
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the API key."""
        if self._api_key:
            return self._api_key
        return get_exa_api_key()
    
    @property
    def is_available(self) -> bool:
        """Check if Exa is configured."""
        return self.api_key is not None
    
    def _get_client(self):
        """Get or create the Exa client."""
        if self._client is None:
            if not self.is_available:
                raise ValueError(
                    "Exa API key not configured. "
                    "Add EXA_API_KEY to API_KEY.txt to enable web search."
                )
            
            try:
                from exa_py import Exa
                self._client = Exa(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "exa-py package not installed. "
                    "Install with: pip install exa-py"
                )
        
        return self._client
    
    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[SearchResult]:
        """
        Execute a semantic search using Exa.
        
        Args:
            query: Search query string
            num_results: Maximum results to return
            
        Returns:
            List of search results
        """
        if not self.is_available:
            print("Warning: Exa search not available, returning empty results")
            return []
        
        try:
            client = self._get_client()
            
            # Use search_and_contents to get full content
            response = client.search_and_contents(
                query,
                num_results=num_results,
                text=True,
            )
            
            results = []
            for result in response.results:
                results.append(SearchResult(
                    url=result.url,
                    title=result.title or "",
                    content=result.text or "",
                    author=getattr(result, "author", "") or "",
                    published_date=getattr(result, "published_date", "") or "",
                    image=getattr(result, "image", None),
                    favicon=getattr(result, "favicon", None),
                ))
            
            return results
            
        except Exception as e:
            print(f"Exa search error: {e}")
            return []
    
    def search_sync(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[SearchResult]:
        """
        Synchronous Exa search.
        
        The Exa client is synchronous, so we override the default async implementation.
        """
        if not self.is_available:
            print("Warning: Exa search not available, returning empty results")
            return []
        
        try:
            client = self._get_client()
            
            response = client.search_and_contents(
                query,
                num_results=num_results,
                text=True,
            )
            
            results = []
            for result in response.results:
                results.append(SearchResult(
                    url=result.url,
                    title=result.title or "",
                    content=result.text or "",
                    author=getattr(result, "author", "") or "",
                    published_date=getattr(result, "published_date", "") or "",
                    image=getattr(result, "image", None),
                    favicon=getattr(result, "favicon", None),
                ))
            
            return results
            
        except Exception as e:
            print(f"Exa search error: {e}")
            return []


# Singleton instance for convenience
_default_provider: Optional[ExaSearchProvider] = None


def get_exa_provider() -> ExaSearchProvider:
    """Get the default Exa provider instance."""
    global _default_provider
    if _default_provider is None:
        _default_provider = ExaSearchProvider()
    return _default_provider
