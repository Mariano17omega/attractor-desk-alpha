"""
Custom action node - handles user-defined quick actions.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import (
    CUSTOM_QUICK_ACTION_ARTIFACT_CONTENT_PROMPT,
    CUSTOM_QUICK_ACTION_ARTIFACT_PROMPT_PREFIX,
    CUSTOM_QUICK_ACTION_CONVERSATION_CONTEXT,
    REFLECTIONS_QUICK_ACTION_PROMPT,
)
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, is_artifact_markdown_content
from core.utils.messages import format_messages
from core.store import get_store
from core.types import (
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    CustomQuickAction,
    Reflections,
)


async def custom_action(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Execute a custom quick action defined by the user.
    """
    if not state.custom_quick_action_id:
        raise ValueError("No custom quick action ID provided")
    
    # Get model configuration
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    user_id = configurable.get("user_id", "default")
    assistant_id = configurable.get("assistant_id", "default")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.5,
        streaming=False,
    )
    
    # Get custom action from store
    store = get_store()
    custom_actions = store.get(["custom_actions", user_id], "actions")
    
    if not custom_actions or not custom_actions.value:
        raise ValueError("No custom actions found")
    
    action_data = custom_actions.value.get(state.custom_quick_action_id)
    if not action_data:
        raise ValueError(f"Custom action not found: {state.custom_quick_action_id}")
    
    custom_action = CustomQuickAction(**action_data)
    
    # Get current artifact
    if not state.artifact or not state.artifact.contents:
        raise ValueError("No artifact for custom action")
    
    current_content = get_artifact_content(state.artifact)
    
    if is_artifact_markdown_content(current_content):
        artifact_text = current_content.full_markdown
    else:
        artifact_text = current_content.code
    
    # Build prompt
    formatted_prompt = f"<custom-instructions>\n{custom_action.prompt}\n</custom-instructions>"
    
    # Add reflections if requested
    if custom_action.include_reflections:
        memories = store.get(["memories", assistant_id], "reflection")
        if memories and memories.value:
            reflections_str = get_formatted_reflections(Reflections(**memories.value))
            formatted_prompt += f"\n\n{REFLECTIONS_QUICK_ACTION_PROMPT.format(reflections=reflections_str)}"
    
    # Add prefix if requested
    if custom_action.include_prefix:
        formatted_prompt = f"{CUSTOM_QUICK_ACTION_ARTIFACT_PROMPT_PREFIX}\n\n{formatted_prompt}"
    
    # Add conversation context if requested
    if custom_action.include_recent_history:
        messages = state.internal_messages if state.internal_messages else state.messages
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        conversation = format_messages(recent_messages)
        formatted_prompt += f"\n\n{CUSTOM_QUICK_ACTION_CONVERSATION_CONTEXT.format(conversation=conversation)}"
    
    # Add artifact content
    formatted_prompt += f"\n\n{CUSTOM_QUICK_ACTION_ARTIFACT_CONTENT_PROMPT.format(artifactContent=artifact_text)}"
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "user", "content": formatted_prompt},
    ])
    
    new_content_text = response.content if isinstance(response.content, str) else str(response.content)
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    
    if is_artifact_markdown_content(current_content):
        new_content = ArtifactMarkdownV3(
            index=new_index,
            type="text",
            title=current_content.title,
            full_markdown=new_content_text,
        )
    else:
        new_content = ArtifactCodeV3(
            index=new_index,
            type="code",
            title=current_content.title,
            language=current_content.language,
            code=new_content_text,
        )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
