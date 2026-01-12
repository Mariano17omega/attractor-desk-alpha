"""Tests for core utility helpers."""

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3, ProgrammingLanguageOptions
from core.utils.artifacts import (
    format_artifact_content,
    format_artifact_content_with_template,
    get_artifact_content,
    is_artifact_code_content,
    is_artifact_markdown_content,
)
from core.utils.messages import format_messages, get_string_from_content
from core.utils.reflections import format_reflections, get_formatted_reflections


def test_format_messages_handles_complex_content() -> None:
    messages = [
        SystemMessage(content="System context"),
        HumanMessage(content=[{"text": "Hello"}, {"text": "World"}, {"other": "skip"}]),
        AIMessage(content="Done"),
    ]

    formatted = format_messages(messages)

    assert '<system index="0">' in formatted
    assert '<human index="1">' in formatted
    assert "Hello\nWorld" in formatted
    assert '<ai index="2">' in formatted


def test_get_string_from_content_handles_list() -> None:
    content = [{"text": "Alpha"}, {"text": "Beta"}, {"other": "ignored"}]
    assert get_string_from_content(content) == "Alpha\nBeta"


def test_format_reflections_handles_flags_and_strings() -> None:
    reflections = SimpleNamespace(
        style_rules='["Be concise", "Use bullets"]',
        content='["Prefers Python", "Likes summaries"]',
    )
    output = format_reflections(reflections)

    assert "Be concise" in output
    assert "Prefers Python" in output

    with pytest.raises(ValueError):
        format_reflections(reflections, only_style=True, only_content=True)


def test_format_reflections_handles_invalid_json() -> None:
    reflections = SimpleNamespace(style_rules="not-json", content="[]")
    output = format_reflections(reflections, only_style=True)

    assert "No style guidelines found." in output


def test_get_formatted_reflections_handles_none() -> None:
    assert get_formatted_reflections(None) == "No reflections found."


def test_artifact_content_helpers_handle_fallback_and_formatting() -> None:
    markdown = ArtifactMarkdownV3(index=1, title="Doc", full_markdown="Hello")
    code = ArtifactCodeV3(
        index=2,
        title="Code",
        language=ProgrammingLanguageOptions.PYTHON,
        code="print('ok')",
    )
    artifact = ArtifactV3(current_index=3, contents=[markdown, code])

    content = get_artifact_content(artifact)
    assert content == code

    assert is_artifact_code_content(code) is True
    assert is_artifact_markdown_content(markdown) is True
    assert is_artifact_code_content({"type": "text"}) is False

    long_code = ArtifactCodeV3(
        index=3,
        title="Long",
        language=ProgrammingLanguageOptions.PYTHON,
        code="a" * 600,
    )
    formatted = format_artifact_content(long_code, shorten_content=True)
    artifact_text = formatted.split("Content: ")[1]
    assert len(artifact_text) == 500

    template = "Here is the artifact:\n{artifact}\nThanks"
    templated = format_artifact_content_with_template(template, markdown)
    assert templated.startswith("Here is the artifact:")


def test_get_artifact_content_requires_artifact() -> None:
    with pytest.raises(ValueError):
        get_artifact_content(None)
