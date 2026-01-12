"""
Generate path node - routes to the appropriate node based on user input.
"""

from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import (
    ROUTE_QUERY_PROMPT,
    ROUTE_QUERY_OPTIONS_HAS_ARTIFACTS,
    ROUTE_QUERY_OPTIONS_NO_ARTIFACTS,
    CURRENT_ARTIFACT_PROMPT,
    NO_ARTIFACT_PROMPT,
)
from core.llm import get_chat_model
from core.utils.artifacts import get_artifact_content, format_artifact_content
from core.utils.messages import format_messages


async def generate_path(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Routes to the proper node in the graph based on the user's query.
    """
    messages = state.internal_messages if state.internal_messages else state.messages
    
    # Check for direct routing based on state
    if state.highlighted_code:
        return {"next": "updateArtifact"}
    
    if state.highlighted_text:
        return {"next": "updateHighlightedText"}
    
    if state.language or state.artifact_length or state.regenerate_with_emojis or state.reading_level:
        return {"next": "rewriteArtifactTheme"}
    
    if state.add_comments or state.add_logs or state.port_language or state.fix_bugs:
        return {"next": "rewriteCodeArtifactTheme"}
    
    if state.custom_quick_action_id:
        return {"next": "customAction"}
    
    if state.web_search_enabled:
        return {"next": "webSearch"}
    
    # Get the last user message for heuristic checks
    last_message = messages[-1] if messages else None
    last_message_content = ""
    if last_message:
        last_message_content = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
        last_message_content = last_message_content.lower()
    
    # Heuristic: check for obvious artifact generation requests
    has_artifact = state.artifact is not None and len(state.artifact.contents) > 0
    
    artifact_keywords = [
        "write", "create", "generate", "make", "compose", "draft",
        "poem", "story", "email", "letter", "essay", "article",
        "code", "script", "function", "class", "program",
        "build", "implement", "design", "develop",
    ]
    
    generation_patterns = [
        "write me", "create a", "generate a", "make a", "compose a",
        "write a", "can you write", "please write", "i need",
        "help me write", "draft a", "build a", "implement a",
    ]
    
    # Check for artifact generation patterns
    is_generation_request = any(pattern in last_message_content for pattern in generation_patterns)
    has_artifact_keyword = any(keyword in last_message_content for keyword in artifact_keywords)
    
    print(f"[DEBUG] Routing - Message: '{last_message_content[:100]}...'")
    print(f"[DEBUG] Routing - has_artifact: {has_artifact}, is_generation: {is_generation_request}, has_keyword: {has_artifact_keyword}")
    
    if not has_artifact and (is_generation_request or has_artifact_keyword):
        # No artifact exists and user is asking for something to be created
        print("[DEBUG] Routing -> generateArtifact (heuristic)")
        return {"next": "generateArtifact"}
    
    if has_artifact and is_generation_request:
        # Artifact exists but user wants something new or modified
        print("[DEBUG] Routing -> rewriteArtifact (heuristic)")
        return {"next": "rewriteArtifact"}
    
    # Fallback to LLM-based routing for ambiguous cases
    print("[DEBUG] Routing -> LLM fallback")
    return await _dynamic_determine_path(state, messages, config)


async def _dynamic_determine_path(
    state: OpenCanvasState,
    messages: list[BaseMessage],
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Use LLM to dynamically determine the routing path.
    """
    # Get model from config or use default
    model_name = config.get("configurable", {}).get("model", "anthropic/claude-3.5-sonnet")
    model = get_chat_model(model=model_name, temperature=0, streaming=False)
    
    # Determine routing options based on artifact presence
    has_artifact = state.artifact is not None and len(state.artifact.contents) > 0
    
    if has_artifact:
        artifact_options = ROUTE_QUERY_OPTIONS_HAS_ARTIFACTS
        current_artifact = get_artifact_content(state.artifact)
        current_artifact_prompt = CURRENT_ARTIFACT_PROMPT.format(
            artifact=format_artifact_content(current_artifact, shorten_content=True)
        )
    else:
        artifact_options = ROUTE_QUERY_OPTIONS_NO_ARTIFACTS
        current_artifact_prompt = NO_ARTIFACT_PROMPT
    
    # Format recent messages
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    recent_messages_str = format_messages(recent_messages)
    
    # Build prompt
    prompt = ROUTE_QUERY_PROMPT.format(
        artifactOptions=artifact_options,
        recentMessages=recent_messages_str,
        currentArtifactPrompt=current_artifact_prompt,
    )
    
    # Create routing schema
    from pydantic import BaseModel, Field
    
    class RouteDecision(BaseModel):
        """The routing decision."""
        route: str = Field(
            description="The route to take: 'generateArtifact', 'rewriteArtifact', or 'replyToGeneralInput'"
        )
    
    # Get routing decision
    model_with_output = model.with_structured_output(RouteDecision, name="route_decision")
    
    result = await model_with_output.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Based on my last message, where should you route?"},
    ])
    
    route = result.route if hasattr(result, "route") else "replyToGeneralInput"
    
    # Validate route
    valid_routes = [
        "generateArtifact",
        "rewriteArtifact", 
        "replyToGeneralInput",
        "updateArtifact",
        "rewriteArtifactTheme",
        "rewriteCodeArtifactTheme",
        "customAction",
        "updateHighlightedText",
        "webSearch",
    ]
    
    if route not in valid_routes:
        route = "replyToGeneralInput"
    
    return {"next": route}
