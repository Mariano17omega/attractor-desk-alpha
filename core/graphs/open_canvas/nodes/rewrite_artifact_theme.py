"""
Rewrite artifact theme node - text modifications like language, reading level, emojis.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import (
    CHANGE_ARTIFACT_LANGUAGE_PROMPT,
    CHANGE_ARTIFACT_READING_LEVEL_PROMPT,
    CHANGE_ARTIFACT_LENGTH_PROMPT,
    ADD_EMOJIS_TO_ARTIFACT_PROMPT,
    CHANGE_ARTIFACT_TO_PIRATE_PROMPT,
)
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.store import get_store
from core.types import ArtifactMarkdownV3, Reflections


async def rewrite_artifact_theme(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Rewrite a text artifact based on theme options.
    """
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact to rewrite")
    
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
    
    if not is_artifact_markdown_content(current_content):
        # This node is for text artifacts only
        return {}
    
    artifact_text = current_content.full_markdown
    
    # Get reflections
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(Reflections(**memories.value))
    
    # Determine which modification to apply
    prompt = None
    
    if state.language:
        prompt = CHANGE_ARTIFACT_LANGUAGE_PROMPT.format(
            newLanguage=state.language.value,
            artifactContent=artifact_text,
            reflections=reflections_str,
        )
    elif state.reading_level:
        if state.reading_level.value == "pirate":
            prompt = CHANGE_ARTIFACT_TO_PIRATE_PROMPT.format(
                artifactContent=artifact_text,
                reflections=reflections_str,
            )
        else:
            prompt = CHANGE_ARTIFACT_READING_LEVEL_PROMPT.format(
                newReadingLevel=state.reading_level.value,
                artifactContent=artifact_text,
                reflections=reflections_str,
            )
    elif state.artifact_length:
        prompt = CHANGE_ARTIFACT_LENGTH_PROMPT.format(
            newLength=state.artifact_length.value,
            artifactContent=artifact_text,
            reflections=reflections_str,
        )
    elif state.regenerate_with_emojis:
        prompt = ADD_EMOJIS_TO_ARTIFACT_PROMPT.format(
            artifactContent=artifact_text,
            reflections=reflections_str,
        )
    
    if not prompt:
        return {}
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "user", "content": prompt},
    ])
    
    new_content_text = response.content if isinstance(response.content, str) else str(response.content)
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    new_content = ArtifactMarkdownV3(
        index=new_index,
        type="text",
        title=current_content.title,
        full_markdown=new_content_text,
    )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
