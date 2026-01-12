"""External providers package for Open Canvas."""

from core.providers.search import SearchProvider, SearchResult
from core.providers.exa_search import ExaSearchProvider
from core.providers.firecrawl import FireCrawlProvider

__all__ = [
    "SearchProvider",
    "SearchResult",
    "ExaSearchProvider",
    "FireCrawlProvider",
]
