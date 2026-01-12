"""
Rewrite code artifact theme node - code modifications like comments, logs, port language.
"""

from langgraph.config import RunnableConfig

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.graphs.open_canvas.prompts import (
    ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT,
    ADD_LOGS_TO_CODE_ARTIFACT_PROMPT,
    FIX_BUGS_CODE_ARTIFACT_PROMPT,
    PORT_LANGUAGE_CODE_ARTIFACT_PROMPT,
)
from core.llm import get_chat_model
from core.utils.artifacts import get_artifact_content, is_artifact_code_content
from core.types import ArtifactCodeV3, ProgrammingLanguageOptions


async def rewrite_code_artifact_theme(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> OpenCanvasReturnType:
    """
    Rewrite a code artifact based on theme options.
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
    
    if not is_artifact_code_content(current_content):
        # This node is for code artifacts only
        return {}
    
    artifact_code = current_content.code
    current_language = current_content.language
    
    # Determine which modification to apply
    prompt = None
    new_language = current_language
    
    if state.add_comments:
        prompt = ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT.format(
            artifactContent=artifact_code,
        )
    elif state.add_logs:
        prompt = ADD_LOGS_TO_CODE_ARTIFACT_PROMPT.format(
            artifactContent=artifact_code,
        )
    elif state.fix_bugs:
        prompt = FIX_BUGS_CODE_ARTIFACT_PROMPT.format(
            artifactContent=artifact_code,
        )
    elif state.port_language:
        new_language = state.port_language
        prompt = PORT_LANGUAGE_CODE_ARTIFACT_PROMPT.format(
            newLanguage=state.port_language.value,
            artifactContent=artifact_code,
        )
    
    if not prompt:
        return {}
    
    # Invoke model
    response = await model.ainvoke([
        {"role": "user", "content": prompt},
    ])
    
    new_code = response.content if isinstance(response.content, str) else str(response.content)
    
    # Create new artifact content
    new_index = len(state.artifact.contents) + 1
    new_content = ArtifactCodeV3(
        index=new_index,
        type="code",
        title=current_content.title,
        language=new_language,
        code=new_code,
    )
    
    # Update artifact
    updated_artifact = state.artifact.model_copy(deep=True)
    updated_artifact.contents.append(new_content)
    updated_artifact.current_index = new_index
    
    return {"artifact": updated_artifact}
