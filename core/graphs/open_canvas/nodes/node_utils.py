"""Shared utilities for graph nodes to reduce code duplication.

This module provides common functions used across multiple graph nodes:
- Model initialization from config
- Reflection retrieval from store
- Message extraction from state

These utilities consolidate ~10 lines of duplicated code per node.
"""

from typing import Optional

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig

from core.llm import get_chat_model
from core.store import get_store
from core.utils.reflections import get_formatted_reflections
from core.types import Reflections
from core.graphs.open_canvas.state import OpenCanvasState


def get_model_from_config(
    config: RunnableConfig,
    temperature: float = 0.5,
    streaming: bool = False,
    max_tokens: Optional[int] = None,
):
    """Extract model configuration and initialize chat model.

    Args:
        config: LangGraph runnable configuration
        temperature: Model temperature (default 0.5)
        streaming: Enable streaming mode (default False)
        max_tokens: Optional max tokens limit

    Returns:
        Initialized chat model instance
    """
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")

    return get_chat_model(
        model=model_name,
        temperature=temperature,
        streaming=streaming,
        max_tokens=max_tokens,
        api_key=api_key,
    )


def get_reflections_from_store(
    config: RunnableConfig,
    only_content: bool = False,
) -> str:
    """Retrieve and format reflections from LangGraph store.

    Args:
        config: LangGraph runnable configuration
        only_content: If True, return only content (no style rules)

    Returns:
        Formatted reflections string or default message if none found
    """
    store = get_store()
    configurable = config.get("configurable", {})
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")

    if not memories or not memories.value:
        return "No reflections found."

    return get_formatted_reflections(
        Reflections(**memories.value),
        only_content=only_content,
    )


def get_messages(state: OpenCanvasState) -> list[BaseMessage]:
    """Get messages from state, preferring internal_messages.

    Args:
        state: The current graph state

    Returns:
        List of messages (internal_messages if available, otherwise messages)
    """
    return state.internal_messages if state.internal_messages else state.messages
