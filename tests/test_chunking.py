"""Tests for Markdown chunking utilities."""

from core.utils.chunking import chunk_markdown


def test_chunk_markdown_splits_by_headers() -> None:
    markdown = "# Intro\nHello world.\n\n## Details\nMore text here."
    chunks = chunk_markdown(markdown, chunk_size_chars=200, chunk_overlap_chars=20)
    assert [chunk.section_title for chunk in chunks] == ["Intro", "Details"]
    assert "Hello world." in chunks[0].text
    assert "More text here." in chunks[1].text


def test_chunk_markdown_overlap_fallback() -> None:
    markdown = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_markdown(markdown, chunk_size_chars=10, chunk_overlap_chars=3)
    assert [chunk.section_title for chunk in chunks] == [None, None, None, None]
    assert len(chunks) == 4
    assert chunks[0].text[-3:] == chunks[1].text[:3]
    assert chunks[1].text[-3:] == chunks[2].text[:3]
    assert chunks[2].text[-3:] == chunks[3].text[:3]
