"""
Reply to general input node - handles non-artifact responses.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import CURRENT_ARTIFACT_PROMPT, NO_ARTIFACT_PROMPT
from core.graphs.open_canvas.nodes.rag_utils import build_rag_prompt
from core.llm import get_chat_model
from core.utils.reflections import get_formatted_reflections
from core.utils.artifacts import get_artifact_content, format_artifact_content_with_template
from core.store import get_store
from core.types import Reflections


async def reply_to_general_input(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Generate responses to questions. Does not generate artifacts.
    """
    # Get model configuration
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    
    model = get_chat_model(
        model=model_name,
        temperature=0.5,
        streaming=True,
        api_key=api_key,
    )
    
    # Get reflections
    store = get_store()
    assistant_id = configurable.get("assistant_id", "default")
    memories = store.get(["memories", assistant_id], "reflection")
    
    reflections_str = "No reflections found."
    if memories and memories.value:
        reflections_str = get_formatted_reflections(Reflections(**memories.value))
    
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

    # Get messages
    messages = state.internal_messages if state.internal_messages else state.messages
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "system", "content": prompt},
        *[{"role": m.type, "content": m.content} for m in messages],
    ])
    
    return {
        "messages": [response],
        "internal_messages": [response],
    }
