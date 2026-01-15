import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import RunnableConfig

from core.graphs.open_canvas.nodes.image_processing import image_processing
from core.graphs.open_canvas.state import OpenCanvasState


@pytest.mark.asyncio
async def test_image_processing_uses_configured_model() -> None:
    # Setup
    state = OpenCanvasState(messages=[HumanMessage(content="Analyze this image")])
    config = RunnableConfig(
        configurable={
            "image_model": "custom-vision-model",
            "model": "default-model",
        }
    )
    
    # Mock LLM
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = AIMessage(content="Image analyzed")
    
    with patch("core.graphs.open_canvas.nodes.image_processing.get_chat_model") as mock_get_model:
        mock_get_model.return_value = mock_model
        
        # Execute
        result = await image_processing(state, config)
        
        # Verify get_chat_model called with correct model
        mock_get_model.assert_called_with(
            model="custom-vision-model",
            temperature=0.5,
            streaming=True,
            api_key=None,
        )
        
        # Verify ainvoke called with system prompt
        call_args = mock_model.ainvoke.call_args[0][0]
        assert call_args[0]["role"] == "system"
        assert "image" in call_args[0]["content"].lower()
        
        # Verify result
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Image analyzed"


@pytest.mark.asyncio
async def test_image_processing_fallbacks_to_default_model() -> None:
    # Setup
    state = OpenCanvasState(messages=[HumanMessage(content="Analyze this image")])
    config = RunnableConfig(
        configurable={
            "model": "default-model",
        }
    )
    
    # Mock LLM
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = AIMessage(content="Default analyzed")
    
    with patch("core.graphs.open_canvas.nodes.image_processing.get_chat_model") as mock_get_model:
        mock_get_model.return_value = mock_model
        
        # Execute
        await image_processing(state, config)
        
        # Verify get_chat_model called with default model
        mock_get_model.assert_called_with(
            model="default-model",
            temperature=0.5,
            streaming=True,
            api_key=None,
        )
