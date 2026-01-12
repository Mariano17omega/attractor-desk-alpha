"""Tests for RAG nodes and Open Canvas state utilities."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from core.constants import OC_SUMMARIZED_MESSAGE_KEY
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.graphs.open_canvas.state import (
    OpenCanvasState,
    internal_messages_reducer,
    is_summary_message,
)
from core.graphs.rag.nodes import decide_retrieve, rewrite_query, select_scope, _last_user_message


def test_is_summary_message_detects_flags() -> None:
    msg = HumanMessage(content="summary", additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True})
    assert is_summary_message(msg) is True

    serialized = {"kwargs": {"additional_kwargs": {OC_SUMMARIZED_MESSAGE_KEY: True}}}
    assert is_summary_message(serialized) is True

    assert is_summary_message({"content": "nope"}) is False


def test_internal_messages_reducer_clears_on_summary() -> None:
    state = [HumanMessage(content="hello")]
    summary = HumanMessage(
        content="summary",
        additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
    )

    result = internal_messages_reducer(state, [summary])

    assert len(result) == 1
    assert result[0].content == "summary"


def test_decide_retrieve_requires_min_length() -> None:
    state = OpenCanvasState(messages=[AIMessage(content="hi"), HumanMessage(content="hi")])
    result = decide_retrieve(state, {"configurable": {"rag_enabled": True}})

    assert result["rag_should_retrieve"] is False
    assert result["rag_query"] is None


def test_decide_retrieve_returns_last_user_query() -> None:
    messages = [
        HumanMessage(content="first"),
        AIMessage(content="ok"),
        HumanMessage(content="Find the doc"),
    ]
    state = OpenCanvasState(messages=messages)
    result = decide_retrieve(state, {"configurable": {"rag_enabled": True}})

    assert result["rag_should_retrieve"] is True
    assert result["rag_query"] == "Find the doc"

    assert _last_user_message(messages) == "Find the doc"


def test_select_scope_falls_back_to_workspace_without_session() -> None:
    state = OpenCanvasState()

    result = select_scope(state, {"configurable": {"rag_scope": "session"}})
    assert result["rag_scope"] == "workspace"

    result = select_scope(
        state,
        {"configurable": {"rag_scope": "session", "session_id": "s1"}},
    )
    assert result["rag_scope"] == "session"


def test_rewrite_query_adds_simplified_version() -> None:
    state = OpenCanvasState(rag_should_retrieve=True, rag_query="Hello, World!")
    result = rewrite_query(state, {"configurable": {"rag_enable_query_rewrite": True}})

    assert result["rag_queries"] == ["Hello, World!", "hello world"]


def test_build_rag_prompt_combines_context_and_grounding() -> None:
    state = OpenCanvasState(
        rag_should_retrieve=True,
        rag_context="Context chunk",
        rag_grounded=False,
    )
    prompt = build_rag_prompt(state)

    assert "Use the following retrieved context" in prompt
    assert "Context chunk" in prompt
    assert "Grounding check" in prompt

    empty_prompt = build_rag_prompt(OpenCanvasState(rag_should_retrieve=False))
    assert empty_prompt == ""
