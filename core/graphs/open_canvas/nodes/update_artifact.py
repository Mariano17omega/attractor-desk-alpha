"""
Update artifact node - handles highlighted code updates.
"""

from typing import Optional
from langgraph.config import RunnableConfig
from pydantic import BaseModel, Field

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_code_content
from core.store import get_store
from core.types import ArtifactCodeV3, Reflections


class UpdateArtifactSchema(BaseModel):
    """Schema for the update_artifact tool."""
    
    replacement_content: str = Field(
        description="The content to replace the highlighted text with. Do not include the surrounding code."
    )


async def update_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Update a specific highlighted portion of the artifact.
    Uses tool calling to ensure clean output.
    """
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact to update")
    
    if not state.highlighted_code:
        raise ValueError("No highlighted code selection")
    
    # Get model configuration
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.5,
        streaming=False,
    )
    
    # Get current artifact content
    current_content = get_artifact_content(state.artifact)
    
    if not is_artifact_code_content(current_content):
        raise ValueError("Update artifact only works with code artifacts")
    
    code = current_content.code
    start_idx = state.highlighted_code.start_char_index
    end_idx = state.highlighted_code.end_char_index
    
    # Extract highlighted portion
    before_highlight = code[:start_idx]
    highlighted_text = code[start_idx:end_idx]
    after_highlight = code[end_idx:]
    
    # Get reflections
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(Reflections(**memories.value))
    
    # Build prompt
    formatted_prompt = UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT.format(
        beforeHighlight=before_highlight[-200:] if len(before_highlight) > 200 else before_highlight,
        highlightedText=highlighted_text,
        afterHighlight=after_highlight[:200] if len(after_highlight) > 200 else after_highlight,
        reflections=reflections_str,
    )
    

    # Bind tool for structured output
    model_with_tool = model.bind_tools(
        [
            {
                "name": "update_artifact",
                "description": "Update the highlighted text.",
                "schema": UpdateArtifactSchema,
            }
        ],
        tool_choice="update_artifact",
    )
    
    # Get user message
    messages = state.internal_messages if state.internal_messages else state.messages
    recent_message = messages[-1] if messages else None
    
    if not recent_message:
        raise ValueError("No message to process")
    
    # Invoke model
    response = await model_with_tool.ainvoke([
        {"role": "system", "content": formatted_prompt},
        {"role": "user", "content": str(recent_message.content)},
    ])
    
    # Extract tool call
    if not response.tool_calls:
        print("[WARN] No tool call in update_artifact, falling back to content")
        updated_text = response.content if isinstance(response.content, str) else str(response.content)
    else:
        tool_call = response.tool_calls[0]
        args = tool_call["args"]
        updated_text = args.get("replacement_content", "")
    
    # Reconstruct full code
    new_code = before_highlight + updated_text + after_highlight
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    new_content = ArtifactCodeV3(
        index=new_index,
        type="code",
        title=current_content.title,
        language=current_content.language,
        code=new_code,
    )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
