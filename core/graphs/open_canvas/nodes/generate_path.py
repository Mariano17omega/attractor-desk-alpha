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
    
    This matches the TypeScript implementation which:
    1. First checks for explicit state flags (highlighted_code, etc.)
    2. Falls through to LLM-based routing with ONLY 2 options
    """
    messages = state.internal_messages if state.internal_messages else state.messages
    
    # Check for direct routing based on explicit state flags
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
    
    # For all other cases, use LLM-based routing with constrained options
    # This matches the TypeScript dynamic-determine-path.ts behavior
    return await _dynamic_determine_path(state, messages, config)


async def _dynamic_determine_path(
    state: OpenCanvasState,
    messages: list[BaseMessage],
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Use LLM to dynamically determine the routing path.
    
    CRITICAL: This matches TypeScript by limiting route options to ONLY 2:
    - replyToGeneralInput: for general questions not requiring artifact changes
    - rewriteArtifact/generateArtifact: for any artifact-related action
    """
    from typing import Literal
    from pydantic import BaseModel, Field
    
    # Get model from config or use default
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    model = get_chat_model(
        model=model_name,
        temperature=0,
        streaming=False,
        api_key=api_key,
    )
    
    # Determine artifact route based on presence (matches TypeScript exactly)
    has_artifact = state.artifact is not None and len(state.artifact.contents) > 0
    artifact_route = "rewriteArtifact" if has_artifact else "generateArtifact"
    
    # Build prompt based on artifact presence
    if has_artifact:
        # custom override to fix routing bias
        artifact_options = """
- 'rewriteArtifact': The user has requested a change to the artifact. This includes editing text, modifying paragraphs, fixing code, changing styles, appending new content, or ANY modification to the existing content. Use this for requests like "add x", "change y", "fix z", "make it better", etc.
- 'replyToGeneralInput': The user submitted a general input which does not require making an update to the artifact. This is for questions unrelated to the artifact or simple greetings.
"""
        current_artifact = get_artifact_content(state.artifact)
        current_artifact_prompt = CURRENT_ARTIFACT_PROMPT.format(
            artifact=format_artifact_content(current_artifact, shorten_content=True)
        )
    else:
        artifact_options = ROUTE_QUERY_OPTIONS_NO_ARTIFACTS
        current_artifact_prompt = NO_ARTIFACT_PROMPT
    
    # Format recent messages (match TypeScript: last 3 messages)
    recent_messages = messages[-3:] if len(messages) > 3 else messages
    recent_messages_str = format_messages(recent_messages)
    
    # Build prompt (matches TypeScript ROUTE_QUERY_PROMPT usage)
    prompt = ROUTE_QUERY_PROMPT.format(
        artifactOptions=artifact_options,
        recentMessages=recent_messages_str,
        currentArtifactPrompt=current_artifact_prompt,
    )
    
    # Create STRICT routing schema with only 2 options (matches TypeScript exactly)
    # TypeScript: z.enum(["replyToGeneralInput", artifactRoute])
    valid_routes = ("replyToGeneralInput", artifact_route)
    
    class RouteDecision(BaseModel):
        """The routing decision - limited to 2 options."""
        route: Literal["replyToGeneralInput", "rewriteArtifact", "generateArtifact"] = Field(
            description=f"The route to take: '{valid_routes[0]}' or '{valid_routes[1]}'"
        )
    
    # Get routing decision using tool calling (matches TypeScript bindTools pattern)
    model_with_output = model.with_structured_output(RouteDecision, name="route_query")
    
    # Get the last user message text
    last_msg_content = recent_messages[-1].content if recent_messages else "No recent messages"
    if not isinstance(last_msg_content, str):
        last_msg_content = str(last_msg_content)

    result = await model_with_output.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"The user passed the following message:\n<user-message>\n{last_msg_content}\n</user-message>\n\nBased on the entire conversation history, where should this be routed?"}
    ])
    
    # Parse the output
    if isinstance(result, BaseMessage) and hasattr(result, "tool_calls") and result.tool_calls:
        # Extract args from the first tool call
        args = result.tool_calls[0]["args"]
        # Validate with Pydantic model
        decision = RouteDecision(**args)
        route = decision.route
    elif hasattr(result, "route"):
        # Handle case where with_structured_output works as expected (future proofing)
        route = result.route
    else:
        route = "replyToGeneralInput"
    
    # Validate route is one of the 2 allowed options
    if route not in valid_routes:
        # Default to artifact action if we have an artifact and the route is invalid
        # This matches the TypeScript bias towards artifact actions
        route = artifact_route if has_artifact else "replyToGeneralInput"
    
    # print(f"[DEBUG] route: {route}")
    
    return {"next": route}
