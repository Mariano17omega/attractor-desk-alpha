"""
Update highlighted text node - handles text artifact highlighted updates.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.store import get_store
from core.types import ArtifactMarkdownV3, Reflections


async def update_highlighted_text(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Update a specific highlighted portion of a text artifact.
    """
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact to update")
    
    if not state.highlighted_text:
        raise ValueError("No highlighted text selection")
    
    # Get model configuration
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.5,
        streaming=False,
        api_key=api_key,
    )
    
    # Get current artifact content
    current_content = get_artifact_content(state.artifact)
    
    if not is_artifact_markdown_content(current_content):
        raise ValueError("Update highlighted text only works with text artifacts")
    
    full_markdown = current_content.full_markdown
    selected_text = state.highlighted_text.selected_text
    markdown_block = state.highlighted_text.markdown_block
    
    # Use markdown_block to disambiguate duplicate occurrences of selected_text.
    # First find the block, then locate selected_text within that block context.
    block_start = full_markdown.find(markdown_block)
    if block_start == -1:
        # Fallback: if block not found, try direct search (legacy behavior)
        text_start = full_markdown.find(selected_text)
        if text_start == -1:
            raise ValueError("Selected text not found in artifact")
    else:
        # Find selected_text within the markdown_block
        offset_in_block = markdown_block.find(selected_text)
        if offset_in_block == -1:
            raise ValueError("Selected text not found within markdown block")
        text_start = block_start + offset_in_block
    
    text_end = text_start + len(selected_text)
    
    before_highlight = full_markdown[:text_start]
    after_highlight = full_markdown[text_end:]
    
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
        highlightedText=selected_text,
        afterHighlight=after_highlight[:200] if len(after_highlight) > 200 else after_highlight,
        reflections=reflections_str,
    )
    
    # Get user message
    messages = state.internal_messages if state.internal_messages else state.messages
    recent_message = messages[-1] if messages else None
    
    if not recent_message:
        raise ValueError("No message to process")
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "system", "content": formatted_prompt},
        {"role": "user", "content": str(recent_message.content)},
    ])
    
    updated_text = response.content if isinstance(response.content, str) else str(response.content)
    
    # Reconstruct full markdown
    new_markdown = before_highlight + updated_text + after_highlight
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    new_content = ArtifactMarkdownV3(
        index=new_index,
        type="text",
        title=current_content.title,
        full_markdown=new_markdown,
    )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
