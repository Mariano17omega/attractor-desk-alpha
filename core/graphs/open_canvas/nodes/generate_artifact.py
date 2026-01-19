"""
Generate artifact node - creates new artifacts based on user request.
"""

import logging
from typing import Any, Literal, Union
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig
from pydantic import BaseModel, Field

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import NEW_ARTIFACT_PROMPT
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.graphs.open_canvas.nodes.node_utils import (
    get_model_from_config,
    get_reflections_from_store,
    get_messages,
)
from core.types import (
    ArtifactV3,
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    ProgrammingLanguageOptions,
)

logger = logging.getLogger(__name__)


class ArtifactToolSchema(BaseModel):
    """Schema for the generate_artifact tool."""
    
    artifact: str = Field(
        description="The full content of the artifact to generate."
    )
    title: str = Field(
        description="A short title for the artifact (2-5 words)."
    )
    type: Literal["text", "code"] = Field(
        description="The type of artifact: 'text' for writing, 'code' for code."
    )
    language: str = Field(
        default="other",
        description="Programming language if type is 'code'."
    )


async def generate_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Generate a new artifact based on the user's query.
    """
    # Get model using shared utility
    model = get_model_from_config(config, temperature=0.5, streaming=False)

    # Get reflections using shared utility
    reflections_str = get_reflections_from_store(config)

    # Build prompt
    formatted_prompt = NEW_ARTIFACT_PROMPT.format(
        reflections=reflections_str,
        disableChainOfThought="",  # Not using chain of thought
    )
    formatted_prompt += build_rag_prompt(state)

    # Bind tool
    model_with_tool = model.bind_tools(
        [
            {
                "name": "generate_artifact",
                "description": "Generate a new artifact based on the user's request.",
                "schema": ArtifactToolSchema,
            }
        ],
        tool_choice="generate_artifact",
    )

    # Get messages using shared utility
    messages = get_messages(state)
    
    # Invoke model
    response = await model_with_tool.ainvoke([
        {"role": "system", "content": formatted_prompt},
        *[{"role": m.type, "content": m.content} for m in messages],
    ])
    
    # Extract tool call
    if not response.tool_calls:
        raise ValueError("No tool call returned from model")
    
    tool_call = response.tool_calls[0]
    args = tool_call["args"]
    
    # Create artifact content
    artifact_type = args.get("type", "text")
    artifact_title = args.get("title", "Untitled")
    artifact_preview = args.get("artifact", "")[:100]
    
    if artifact_type == "code":
        # Map language string to enum
        lang_str = args.get("language", "other").lower()
        try:
            language = ProgrammingLanguageOptions(lang_str)
        except ValueError:
            language = ProgrammingLanguageOptions.OTHER
        
        content = ArtifactCodeV3(
            index=1,
            type="code",
            title=artifact_title,
            language=language,
            code=args.get("artifact", ""),
        )
    else:
        content = ArtifactMarkdownV3(
            index=1,
            type="text",
            title=artifact_title,
            full_markdown=args.get("artifact", ""),
        )
    
    # Create new artifact
    new_artifact = ArtifactV3(
        current_index=1,
        contents=[content],
    )
    
    logger.debug("Generated artifact: type=%s, title=%s", artifact_type, artifact_title)
    logger.debug("Artifact content preview: %s...", artifact_preview)

    return {"artifact": new_artifact}
