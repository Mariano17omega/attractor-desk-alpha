"""Tests for reflect_node in the Open Canvas graph."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import HumanMessage, AIMessage

from core.graphs.open_canvas.graph import reflect_node
from core.graphs.open_canvas.state import OpenCanvasState
from core.store.memory_store import reset_store, get_store
from core.types import ArtifactV3, ArtifactMarkdownV3, ArtifactCodeV3


@pytest.fixture(autouse=True)
def reset_global_store():
    """Reset the global store before each test."""
    reset_store()
    yield
    reset_store()


def _make_state(
    messages=None,
    artifact=None,
) -> OpenCanvasState:
    """Create a minimal OpenCanvasState for testing."""
    return OpenCanvasState(
        messages=messages or [],
        internal_messages=messages or [],
        artifact=artifact,
    )


def _make_config(assistant_id="test-assistant"):
    """Create a minimal RunnableConfig for testing."""
    return {
        "configurable": {
            "assistant_id": assistant_id,
            "model": "openai/gpt-4o-mini",
            "api_key": "test-key",
        }
    }


@pytest.mark.asyncio
async def test_reflect_node_skips_when_no_messages():
    """Test that reflect_node returns empty when there are no messages."""
    state = _make_state(messages=[])
    config = _make_config()
    
    result = await reflect_node(state, config)
    
    assert result == {}


@pytest.mark.asyncio
async def test_reflect_node_calls_model_and_stores_reflections():
    """Test that reflect_node invokes the model and persists reflections."""
    messages = [
        HumanMessage(content="Write me a poem about cats"),
        AIMessage(content="Here's a poem about cats..."),
    ]
    state = _make_state(messages=messages)
    config = _make_config()
    
    # Mock the model response with tool calls
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {
            "name": "generate_reflections",
            "args": {
                "style_rules": ["User prefers creative writing", "User likes poems"],
                "content": ["User has interest in cats"],
            },
        }
    ]
    
    mock_model = MagicMock()
    mock_model.bind_tools = MagicMock(return_value=mock_model)
    mock_model.ainvoke = AsyncMock(return_value=mock_response)
    
    with patch("core.graphs.open_canvas.graph.get_chat_model", return_value=mock_model):
        result = await reflect_node(state, config)
    
    assert result == {}
    
    # Check that reflections were stored
    store = get_store()
    memories = store.get(["memories", "test-assistant"], "reflection")
    assert memories is not None
    assert memories.value["styleRules"] == ["User prefers creative writing", "User likes poems"]
    assert memories.value["content"] == ["User has interest in cats"]


@pytest.mark.asyncio
async def test_reflect_node_includes_artifact_context():
    """Test that reflect_node includes artifact content in the prompt."""
    messages = [
        HumanMessage(content="Update the artifact"),
        AIMessage(content="Done!"),
    ]
    artifact = ArtifactV3(
        currentIndex=0,
        contents=[
            ArtifactMarkdownV3(
                index=0,
                type="text",
                title="Test Doc",
                fullMarkdown="# Hello World\n\nThis is a test document.",
            )
        ],
    )
    state = _make_state(messages=messages, artifact=artifact)
    config = _make_config()
    
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {
            "name": "generate_reflections",
            "args": {
                "style_rules": [],
                "content": [],
            },
        }
    ]
    
    mock_model = MagicMock()
    mock_model.bind_tools = MagicMock(return_value=mock_model)
    mock_model.ainvoke = AsyncMock(return_value=mock_response)
    
    with patch("core.graphs.open_canvas.graph.get_chat_model", return_value=mock_model):
        await reflect_node(state, config)
    
    # Verify the model was called with artifact context
    call_args = mock_model.ainvoke.call_args[0][0]
    system_prompt = call_args[0]["content"]
    assert "Hello World" in system_prompt


@pytest.mark.asyncio
async def test_reflect_node_uses_existing_reflections():
    """Test that reflect_node includes existing reflections in the prompt."""
    messages = [
        HumanMessage(content="Write something"),
        AIMessage(content="Here you go!"),
    ]
    state = _make_state(messages=messages)
    config = _make_config()
    
    # Pre-populate store with existing reflections
    store = get_store()
    store.put(
        ["memories", "test-assistant"],
        "reflection",
        {
            "styleRules": ["Existing style rule"],
            "content": ["Existing fact about user"],
        },
    )
    
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {
            "name": "generate_reflections",
            "args": {
                "style_rules": ["Updated style rule"],
                "content": ["Updated fact"],
            },
        }
    ]
    
    mock_model = MagicMock()
    mock_model.bind_tools = MagicMock(return_value=mock_model)
    mock_model.ainvoke = AsyncMock(return_value=mock_response)
    
    with patch("core.graphs.open_canvas.graph.get_chat_model", return_value=mock_model):
        await reflect_node(state, config)
    
    # Verify the model was called with existing reflections context
    call_args = mock_model.ainvoke.call_args[0][0]
    system_prompt = call_args[0]["content"]
    assert "Existing style rule" in system_prompt
    
    # Verify new reflections replaced old ones
    memories = store.get(["memories", "test-assistant"], "reflection")
    assert memories.value["styleRules"] == ["Updated style rule"]


@pytest.mark.asyncio
async def test_reflect_node_handles_model_failure_gracefully():
    """Test that reflect_node handles model errors without crashing."""
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
    ]
    state = _make_state(messages=messages)
    config = _make_config()
    
    mock_model = MagicMock()
    mock_model.bind_tools = MagicMock(return_value=mock_model)
    mock_model.ainvoke = AsyncMock(side_effect=Exception("Model error"))
    
    with patch("core.graphs.open_canvas.graph.get_chat_model", return_value=mock_model):
        result = await reflect_node(state, config)
    
    # Should return empty without raising
    assert result == {}
    
    # Store should not have been updated
    store = get_store()
    memories = store.get(["memories", "test-assistant"], "reflection")
    assert memories is None
