"""
Abstract search provider interface.
All search implementations must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """Result from a web search."""
    url: str
    title: str
    content: str
    author: str = ""
    published_date: str = ""
    image: Optional[str] = None
    favicon: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "publishedDate": self.published_date,
            "image": self.image,
            "favicon": self.favicon,
        }


class SearchProvider(ABC):
    """Abstract base class for search providers."""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[SearchResult]:
        """
        Execute a search query.
        
        Args:
            query: Search query string
            num_results: Maximum results to return
            
        Returns:
            List of search results
        """
        pass
    
    def search_sync(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[SearchResult]:
        """
        Synchronous search (default implementation uses asyncio).
        
        Args:
            query: Search query string
            num_results: Maximum results to return
            
        Returns:
            List of search results
        """
        import asyncio
        return asyncio.run(self.search(query, num_results))
