"""
FireCrawl web scraping provider.
Optional - fails gracefully if API key is not configured.
"""

from dataclasses import dataclass
from typing import Optional

from core.config import get_firecrawl_api_key, is_firecrawl_enabled


@dataclass
class ScrapedPage:
    """Result from a web page scrape."""
    url: str
    title: str
    content: str
    markdown: str
    html: Optional[str] = None
    metadata: Optional[dict] = None


class FireCrawlProvider:
    """
    Web scraping provider using FireCrawl.
    
    Requires FIRECRAWL_API_KEY in API_KEY.txt.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._app = None
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the API key."""
        if self._api_key:
            return self._api_key
        return get_firecrawl_api_key()
    
    @property
    def is_available(self) -> bool:
        """Check if FireCrawl is configured."""
        return self.api_key is not None
    
    def _get_app(self):
        """Get or create the FireCrawl app."""
        if self._app is None:
            if not self.is_available:
                raise ValueError(
                    "FireCrawl API key not configured. "
                    "Add FIRECRAWL_API_KEY to API_KEY.txt to enable web scraping."
                )
            
            try:
                from firecrawl import FirecrawlApp
                self._app = FirecrawlApp(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "firecrawl-py package not installed. "
                    "Install with: pip install firecrawl-py"
                )
        
        return self._app
    
    def scrape_url(self, url: str) -> Optional[ScrapedPage]:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped page content, or None on failure
        """
        if not self.is_available:
            print("Warning: FireCrawl not available, returning None")
            return None
        
        try:
            app = self._get_app()
            
            result = app.scrape_url(
                url,
                params={
                    "formats": ["markdown", "html"],
                }
            )
            
            if not result:
                return None
            
            return ScrapedPage(
                url=url,
                title=result.get("metadata", {}).get("title", ""),
                content=result.get("markdown", ""),
                markdown=result.get("markdown", ""),
                html=result.get("html"),
                metadata=result.get("metadata"),
            )
            
        except Exception as e:
            print(f"FireCrawl scrape error: {e}")
            return None
    
    def scrape_urls(self, urls: list[str]) -> list[ScrapedPage]:
        """
        Scrape content from multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped pages (excludes failures)
        """
        results = []
        for url in urls:
            page = self.scrape_url(url)
            if page:
                results.append(page)
        return results


# Singleton instance for convenience
_default_provider: Optional[FireCrawlProvider] = None


def get_firecrawl_provider() -> FireCrawlProvider:
    """Get the default FireCrawl provider instance."""
    global _default_provider
    if _default_provider is None:
        _default_provider = FireCrawlProvider()
    return _default_provider
