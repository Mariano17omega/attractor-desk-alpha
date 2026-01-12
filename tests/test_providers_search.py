"""Tests for search provider helpers."""

from __future__ import annotations

from core.providers.search import SearchProvider, SearchResult


class DummyProvider(SearchProvider):
    """Minimal provider for testing."""

    @property
    def is_available(self) -> bool:
        return True

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                url="https://example.com",
                title="Example",
                content=f"Result for {query}",
            )
        ]


def test_search_result_to_dict() -> None:
    result = SearchResult(url="u", title="t", content="c", author="a")
    data = result.to_dict()

    assert data["url"] == "u"
    assert data["title"] == "t"
    assert data["content"] == "c"
    assert data["author"] == "a"
    assert data["publishedDate"] == ""


def test_search_sync_uses_asyncio_run() -> None:
    provider = DummyProvider()
    results = provider.search_sync("query", num_results=1)

    assert len(results) == 1
    assert results[0].title == "Example"
