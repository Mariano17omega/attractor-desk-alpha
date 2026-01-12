"""
Generate artifact node - creates new artifacts based on user request.
"""

from typing import Any, Literal, Union
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig
from pydantic import BaseModel, Field

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import NEW_ARTIFACT_PROMPT
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.store import get_store
from core.types import (
    ArtifactV3,
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    ProgrammingLanguageOptions,
    Reflections,
)


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
    
    # Get reflections
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(Reflections(**memories.value))
    
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
    
    # Get messages
    messages = state.internal_messages if state.internal_messages else state.messages
    
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
            title=args.get("title", "Untitled"),
            language=language,
            code=args.get("artifact", ""),
        )
    else:
        content = ArtifactMarkdownV3(
            index=1,
            type="text",
            title=args.get("title", "Untitled"),
            full_markdown=args.get("artifact", ""),
        )
    
    # Create new artifact
    new_artifact = ArtifactV3(
        current_index=1,
        contents=[content],
    )
    
    print(f"[DEBUG] Generated artifact: type={artifact_type}, title={args.get('title', 'Untitled')}")
    print(f"[DEBUG] Artifact content preview: {args.get('artifact', '')[:100]}...")
    
    return {"artifact": new_artifact}
