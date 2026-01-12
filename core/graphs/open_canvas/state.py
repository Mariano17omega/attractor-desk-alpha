"""
State definition for Open Canvas graph.
Matches the original TypeScript OpenCanvasGraphAnnotation.
"""

from typing import Annotated, Any, Optional, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from core.types import (
    ArtifactLengthOptions,
    ArtifactV3,
    CodeHighlight,
    LanguageOptions,
    ProgrammingLanguageOptions,
    ReadingLevelOptions,
    SearchResult,
    TextHighlight,
)
from core.constants import OC_SUMMARIZED_MESSAGE_KEY


def is_summary_message(msg: Any) -> bool:
    """Check if a message is a summary message."""
    if not isinstance(msg, dict) and not hasattr(msg, "additional_kwargs"):
        return False
    
    additional_kwargs = (
        msg.get("additional_kwargs", {}) 
        if isinstance(msg, dict) 
        else getattr(msg, "additional_kwargs", {})
    )
    
    if additional_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True:
        return True
    
    # Also check kwargs for serialized messages
    kwargs = msg.get("kwargs", {}) if isinstance(msg, dict) else getattr(msg, "kwargs", {})
    if kwargs.get("additional_kwargs", {}).get(OC_SUMMARIZED_MESSAGE_KEY) is True:
        return True
    
    return False


def internal_messages_reducer(
    state: Sequence[BaseMessage],
    update: Sequence[BaseMessage],
) -> list[BaseMessage]:
    """
    Reducer for _messages that handles summary messages specially.
    
    If the latest message is a summary, clear existing state.
    """
    if not update:
        return list(state)
    
    latest_msg = update[-1] if isinstance(update, (list, tuple)) else update
    
    if is_summary_message(latest_msg):
        # Clear existing messages when receiving a summary
        return add_messages([], update)
    
    return add_messages(state, update)


class OpenCanvasState(BaseModel):
    """
    State for the Open Canvas graph.
    
    This matches the TypeScript OpenCanvasGraphAnnotation.
    """
    
    # Messages visible to the user
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    
    # Internal messages (may include summaries, hidden messages)
    internal_messages: Annotated[list[BaseMessage], internal_messages_reducer] = Field(
        default_factory=list
    )
    
    # Highlighted code in artifact
    highlighted_code: Optional[CodeHighlight] = Field(
        default=None,
        alias="highlightedCode"
    )
    
    # Highlighted text in artifact
    highlighted_text: Optional[TextHighlight] = Field(
        default=None,
        alias="highlightedText"
    )
    
    # Current artifact
    artifact: Optional[ArtifactV3] = None
    
    # Next node to route to
    next: Optional[str] = None

    # Session title updates
    session_title: Optional[str] = None
    
    # Text artifact modification options
    language: Optional[LanguageOptions] = None
    artifact_length: Optional[ArtifactLengthOptions] = Field(
        default=None,
        alias="artifactLength"
    )
    regenerate_with_emojis: Optional[bool] = Field(
        default=None,
        alias="regenerateWithEmojis"
    )
    reading_level: Optional[ReadingLevelOptions] = Field(
        default=None,
        alias="readingLevel"
    )
    
    # Code artifact modification options
    add_comments: Optional[bool] = Field(default=None, alias="addComments")
    add_logs: Optional[bool] = Field(default=None, alias="addLogs")
    port_language: Optional[ProgrammingLanguageOptions] = Field(
        default=None,
        alias="portLanguage"
    )
    fix_bugs: Optional[bool] = Field(default=None, alias="fixBugs")
    
    # Custom quick action
    custom_quick_action_id: Optional[str] = Field(
        default=None,
        alias="customQuickActionId"
    )
    
    # Web search
    web_search_enabled: Optional[bool] = Field(
        default=None,
        alias="webSearchEnabled"
    )
    web_search_results: Optional[list[SearchResult]] = Field(
        default=None,
        alias="webSearchResults"
    )

    # RAG state
    rag_enabled: Optional[bool] = None
    rag_scope: Optional[str] = None
    rag_query: Optional[str] = None
    rag_queries: Optional[list[str]] = None
    rag_should_retrieve: Optional[bool] = None
    rag_candidates: Optional[list[dict]] = None
    rag_context: Optional[str] = None
    rag_citations: Optional[list[dict]] = None
    rag_grounded: Optional[bool] = None
    rag_retrieval_debug: Optional[dict] = None
    rag_selected_chunk_ids: Optional[list[str]] = None
    
    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


# Type alias for return type
OpenCanvasReturnType = dict[str, Any]
