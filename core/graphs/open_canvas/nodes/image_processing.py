"""
Image processing node - handles requests involving images.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.llm import get_chat_model


async def image_processing(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Handle image processing requests using a specialized model.
    """
    # Get model configuration
    configurable = config.get("configurable", {})
    # Use image_model if configured, otherwise fallback to default model
    model_name = configurable.get("image_model") or configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.5,
        streaming=True,
        api_key=api_key,
    )
    
    # System prompt for image analysis
    system_prompt = (
        "You are an AI assistant specialized in analyzing and interacting with images. "
        "Answer the user's request based on the images provided in the conversation. "
        "Be concise and helpful."
    )

    # Get messages
    messages = state.internal_messages if state.internal_messages else state.messages
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *[{"role": m.type, "content": m.content} for m in messages],
    ])
    
    return {
        "messages": [response],
        "internal_messages": [response],
    }
