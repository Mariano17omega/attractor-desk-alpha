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
from core.graphs.open_canvas.nodes.node_utils import (
    get_model_from_config,
    get_reflections_from_store,
)
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.types import ArtifactMarkdownV3


async def rewrite_artifact_theme(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Rewrite a text artifact based on theme options.
    """
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact to rewrite")

    # Get model using shared utility
    model = get_model_from_config(config, temperature=0.5, streaming=False)

    # Get current artifact content
    current_content = get_artifact_content(state.artifact)

    if not is_artifact_markdown_content(current_content):
        # This node is for text artifacts only
        return {}

    artifact_text = current_content.full_markdown

    # Get reflections using shared utility
    reflections_str = get_reflections_from_store(config)
    
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
