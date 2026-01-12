"""
Generate followup node - creates a followup message after artifact generation.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import FOLLOWUP_ARTIFACT_PROMPT
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.utils.messages import format_messages
from core.store import get_store
from core.types import Reflections


async def generate_followup(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Generate a followup message after generating or updating an artifact.
    """
    # Get model configuration
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.7,
        max_tokens=250,
        streaming=False,
        api_key=api_key,
    )
    
    # Get reflections (content only)
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(
            Reflections(**memories.value),
            only_content=True,
        )
    
    # Get artifact content
    if state.artifact and state.artifact.contents:
        current_content = get_artifact_content(state.artifact)
        if is_artifact_markdown_content(current_content):
            artifact_text = current_content.full_markdown
        else:
            artifact_text = current_content.code
    else:
        artifact_text = "No artifacts generated yet."
    
    # Get conversation
    messages = state.internal_messages if state.internal_messages else state.messages
    conversation = format_messages(messages)
    
    # Build prompt
    formatted_prompt = FOLLOWUP_ARTIFACT_PROMPT.format(
        artifactContent=artifact_text,
        reflections=reflections_str,
        conversation=conversation,
    )
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "user", "content": formatted_prompt},
    ])
    
    return {
        "messages": [response],
        "internal_messages": [response],
    }
