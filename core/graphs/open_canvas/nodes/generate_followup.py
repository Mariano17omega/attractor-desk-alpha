"""
Generate followup node - creates a followup message after artifact generation.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import FOLLOWUP_ARTIFACT_PROMPT
from core.graphs.open_canvas.nodes.node_utils import (
    get_model_from_config,
    get_reflections_from_store,
    get_messages,
)
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.utils.messages import format_messages


async def generate_followup(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Generate a followup message after generating or updating an artifact.
    """
    # Get model using shared utility (with temperature 0.7 and max_tokens 250)
    model = get_model_from_config(
        config, temperature=0.7, streaming=False, max_tokens=250
    )

    # Get reflections using shared utility (content only)
    reflections_str = get_reflections_from_store(config, only_content=True)

    # Get artifact content
    if state.artifact and state.artifact.contents:
        current_content = get_artifact_content(state.artifact)
        if is_artifact_markdown_content(current_content):
            artifact_text = current_content.full_markdown
        else:
            artifact_text = current_content.code
    else:
        artifact_text = "No artifacts generated yet."

    # Get conversation using shared utility
    messages = get_messages(state)
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
