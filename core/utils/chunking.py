"""Chunking utilities for local RAG."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional


_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")


@dataclass(frozen=True)
class Chunk:
    """Chunked text with optional section title."""

    text: str
    section_title: Optional[str]


def chunk_markdown(
    markdown: str,
    chunk_size_chars: int = 1200,
    chunk_overlap_chars: int = 150,
) -> list[Chunk]:
    sections = _split_markdown_sections(markdown)
    chunks: list[Chunk] = []
    for section_title, section_text in sections:
        if not section_text and section_title:
            section_text = section_title
        for chunk_text in _split_with_overlap(
            section_text,
            chunk_size_chars=chunk_size_chars,
            chunk_overlap_chars=chunk_overlap_chars,
        ):
            chunks.append(Chunk(text=chunk_text, section_title=section_title))
    return chunks


def _split_markdown_sections(markdown: str) -> list[tuple[Optional[str], str]]:
    lines = markdown.splitlines()
    sections: list[tuple[Optional[str], str]] = []
    current_title: Optional[str] = None
    current_lines: list[str] = []
    for line in lines:
        match = _HEADER_RE.match(line)
        if match:
            if current_title is not None or current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None or current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    if not sections:
        return [(None, markdown.strip())]
    return sections


def _split_with_overlap(
    text: str,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
) -> Iterable[str]:
    text = text.strip()
    if not text:
        return []
    if chunk_size_chars <= 0:
        return [text]
    overlap = max(0, min(chunk_overlap_chars, chunk_size_chars - 1))
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + chunk_size_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - overlap
    return chunks
