"""
Rewrite artifact node - modifies existing artifacts based on user request.
"""

from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import UPDATE_ENTIRE_ARTIFACT_PROMPT, OPTIONALLY_UPDATE_META_PROMPT
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.store import get_store
from core.types import (
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    ProgrammingLanguageOptions,
    Reflections,
)


async def rewrite_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Rewrite an existing artifact based on user request.
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
    
    if is_artifact_markdown_content(current_content):
        artifact_text = current_content.full_markdown
        artifact_type = "text"
    else:
        artifact_text = current_content.code
        artifact_type = "code"
    
    # Get reflections
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(Reflections(**memories.value))
    
    # Build prompt (keeping same type for now)
    update_meta = OPTIONALLY_UPDATE_META_PROMPT.format(
        artifactType=artifact_type,
        artifactTitle=f"Current title: {current_content.title}",
    )
    
    formatted_prompt = UPDATE_ENTIRE_ARTIFACT_PROMPT.format(
        artifactContent=artifact_text,
        reflections=reflections_str,
        updateMetaPrompt=update_meta,
    )
    
    # Get messages
    messages = state.internal_messages if state.internal_messages else state.messages
    recent_message = messages[-1] if messages else None
    
    if not recent_message:
        raise ValueError("No message to process")
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "system", "content": formatted_prompt},
        {"role": "user", "content": str(recent_message.content)},
    ])
    
    new_content_text = response.content if isinstance(response.content, str) else str(response.content)
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    
    if artifact_type == "code":
        new_content = ArtifactCodeV3(
            index=new_index,
            type="code",
            title=current_content.title,
            language=current_content.language if hasattr(current_content, "language") else ProgrammingLanguageOptions.OTHER,
            code=new_content_text,
        )
    else:
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
