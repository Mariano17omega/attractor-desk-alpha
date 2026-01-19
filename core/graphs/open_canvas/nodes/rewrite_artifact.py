"""
Rewrite artifact node - modifies existing artifacts based on user request.
"""

import logging
from typing import Any, Optional, Literal
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.config import RunnableConfig
from pydantic import BaseModel, Field

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import UPDATE_ENTIRE_ARTIFACT_PROMPT, OPTIONALLY_UPDATE_META_PROMPT
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.graphs.open_canvas.nodes.node_utils import (
    get_model_from_config,
    get_reflections_from_store,
    get_messages,
)
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.types import (
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    ProgrammingLanguageOptions,
)

logger = logging.getLogger(__name__)


class RewriteArtifactSchema(BaseModel):
    """Schema for the rewrite_artifact tool."""
    
    artifact: str = Field(
        description="The new content of the artifact. This should be the COMPLETE updated content."
    )
    title: Optional[str] = Field(
        default=None,
        description="The logical title for the artifact (2-5 words). Only provide if the title should change."
    )
    type: Literal["text", "code"] = Field(
        default="text",
        description="The type of artifact: 'text' for writing, 'code' for code."
    )
    language: str = Field(
        default="other",
        description="Programming language if type is 'code'."
    )


async def rewrite_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Rewrite an existing artifact based on user request.
    Uses tool calling to ensure clean output.
    """
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact to rewrite")

    # Get model using shared utility
    model = get_model_from_config(config, temperature=0.5, streaming=False)

    # Get current artifact content
    current_content = get_artifact_content(state.artifact)

    # Determine type
    if is_artifact_markdown_content(current_content):
        artifact_text = current_content.full_markdown
        artifact_type = "text"
        current_lang = "other"
    else:
        artifact_text = current_content.code
        artifact_type = "code"
        current_lang = current_content.language.value

    # Get reflections using shared utility
    reflections_str = get_reflections_from_store(config)
    
    # Build prompt
    update_meta = OPTIONALLY_UPDATE_META_PROMPT.format(
        artifactType=artifact_type,
        artifactTitle=f"Current title: {current_content.title}",
    )
    
    formatted_prompt = UPDATE_ENTIRE_ARTIFACT_PROMPT.format(
        artifactContent=artifact_text,
        reflections=reflections_str,
        updateMetaPrompt=update_meta,
    )
    formatted_prompt += build_rag_prompt(state)
    
    # Bind tool for structured output
    model_with_tool = model.bind_tools(
        [
            {
                "name": "rewrite_artifact",
                "description": "Rewrite the artifact content.",
                "schema": RewriteArtifactSchema,
            }
        ],
        tool_choice="rewrite_artifact",
    )
    
    # Get messages using shared utility
    messages = get_messages(state)
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
        # Fallback if model refuses to call tool (rare with tool_choice forced)
        # But for 'rewrite', it implies the model might have just chatted.
        logger.warning("No tool call in rewrite_artifact, falling back to content")
        # In this fallback, we risk dirty content, but it's better than crashing.
        new_content_text = response.content if isinstance(response.content, str) else str(response.content)
        new_type = artifact_type
        new_title = current_content.title
        new_lang = current_lang
    else:
        tool_call = response.tool_calls[0]
        args = tool_call["args"]
        new_content_text = args.get("artifact", "")
        new_type = args.get("type", artifact_type)
        new_title = args.get("title") or current_content.title
        new_lang = args.get("language", "other")

    # Clean up any XML tags the LLM might have included from the prompt
    import re
    # Remove <artifact> and </artifact> tags
    new_content_text = re.sub(r'</?artifact>', '', new_content_text)
    # Strip leading/trailing whitespace that might result
    new_content_text = new_content_text.strip()
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    
    if new_type == "code":
        try:
            language_enum = ProgrammingLanguageOptions(new_lang.lower())
        except ValueError:
            language_enum = ProgrammingLanguageOptions.OTHER
            
        new_content = ArtifactCodeV3(
            index=new_index,
            type="code",
            title=new_title,
            language=language_enum,
            code=new_content_text,
        )
    else:
        new_content = ArtifactMarkdownV3(
            index=new_index,
            type="text",
            title=new_title,
            full_markdown=new_content_text,
        )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
