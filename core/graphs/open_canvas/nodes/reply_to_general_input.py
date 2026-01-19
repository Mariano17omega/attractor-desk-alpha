"""
Reply to general input node - handles non-artifact responses.
"""

from langchain_core.messages import AIMessage
from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import CURRENT_ARTIFACT_PROMPT, NO_ARTIFACT_PROMPT
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.graphs.open_canvas.nodes.node_utils import (
    get_model_from_config,
    get_reflections_from_store,
    get_messages,
)
from core.utils.artifacts import get_artifact_content, format_artifact_content_with_template


async def reply_to_general_input(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Generate responses to questions. Does not generate artifacts.

    If a recovery message is set (from artifact dispatch validation failure),
    returns that message directly without invoking the LLM.
    """
    # Check for recovery message from artifact dispatch
    if state.artifact_action_recovery_message:
        recovery_response = AIMessage(content=state.artifact_action_recovery_message)
        return {
            "messages": [recovery_response],
            "internal_messages": [recovery_response],
        }

    # Get model using shared utility (with streaming enabled)
    model = get_model_from_config(config, temperature=0.5, streaming=True)

    # Get reflections using shared utility
    reflections_str = get_reflections_from_store(config)

    # Get artifact context
    if state.artifact and state.artifact.contents:
        current_content = get_artifact_content(state.artifact)
        artifact_prompt = format_artifact_content_with_template(
            CURRENT_ARTIFACT_PROMPT,
            current_content,
        )
    else:
        artifact_prompt = NO_ARTIFACT_PROMPT
    rag_prompt = build_rag_prompt(state)

    # Build prompt
    prompt = f"""You are an AI assistant tasked with responding to the users question.

The user has generated artifacts in the past. Use the following artifacts as context when responding to the users question.

You also have the following reflections on style guidelines and general memories/facts about the user to use when generating your response.
<reflections>
{reflections_str}
</reflections>

{artifact_prompt}"""
    prompt += rag_prompt

    # Get messages using shared utility
    messages = get_messages(state)
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "system", "content": prompt},
        *[{"role": m.type, "content": m.content} for m in messages],
    ])
    
    return {
        "messages": [response],
        "internal_messages": [response],
    }
