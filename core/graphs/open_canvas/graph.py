"""
Open Canvas main graph definition.
This is the primary graph that handles all conversation and artifact generation.
"""

from datetime import datetime
import logging
from typing import Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.config import RunnableConfig
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from core.constants import CHARACTER_MAX, OC_SUMMARIZED_MESSAGE_KEY
from core.graphs.open_canvas.nodes import (
    generate_path,
    reply_to_general_input,
    clean_state,
    image_processing,
)
from core.graphs.open_canvas.artifact_ops import artifact_ops_graph
from core.graphs.open_canvas.prompts import (
    WEB_SEARCH_CLASSIFIER_PROMPT,
    WEB_SEARCH_QUERY_PROMPT,
    SUMMARIZER_PROMPT,
    SUMMARY_MESSAGE_TEMPLATE,
    TITLE_SYSTEM_PROMPT,
    TITLE_USER_PROMPT,
    REFLECT_SYSTEM_PROMPT,
    REFLECT_USER_PROMPT,
)
from core.store import get_store
from core.types import Reflections
from core.utils.reflections import get_formatted_reflections
from core.graphs.open_canvas.state import OpenCanvasState, is_summary_message
from core.graphs.rag.graph import graph as rag_graph
from core.llm import get_chat_model
from core.persistence import Database, SessionRepository
from core.providers.exa_search import ExaSearchProvider
from core.providers.search import SearchResult as ProviderSearchResult
from core.types import ExaMetadata, SearchResult as WebSearchResult
from core.utils.artifacts import get_artifact_content, is_artifact_code_content, is_artifact_markdown_content
from core.utils.messages import create_ai_message_from_web_results, format_messages, get_string_from_content

logger = logging.getLogger(__name__)


def route_node(state: OpenCanvasState) -> str:
    """Route based on the 'next' field in state."""
    if not state.next:
        raise ValueError("'next' state field not set.")
    return state.next


def simple_token_calculator(state: OpenCanvasState) -> Literal["summarizer", "__end__"]:
    """Check if messages exceed token limit and need summarization."""
    messages = state.internal_messages if state.internal_messages else state.messages
    
    total_chars = 0
    for msg in messages:
        content = msg.content
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total_chars += len(part["text"])
    
    if total_chars > CHARACTER_MAX:
        return "summarizer"
    return END


def conditionally_generate_title(
    state: OpenCanvasState,
) -> Literal["generateTitle", "summarizer", "__end__"]:
    """
    Conditionally route to generateTitle if this is the first human-AI exchange.
    """
    messages = state.messages if state.messages else []
    
    if len(messages) > 2:
        # Not the first exchange, check for summarization
        return simple_token_calculator(state)
    
    return "generateTitle"


def _last_user_message(messages: list[BaseMessage]) -> Optional[BaseMessage]:
    for message in reversed(messages):
        if getattr(message, "type", "") != "human":
            continue
        if is_summary_message(message):
            continue
        return message
    return None


def _to_web_search_results(
    results: list[ProviderSearchResult],
) -> list[WebSearchResult]:
    converted: list[WebSearchResult] = []
    for result in results:
        metadata = ExaMetadata(
            id=result.url or "",
            url=result.url,
            title=result.title or "",
            author=result.author or "",
            published_date=result.published_date or "",
            image=result.image,
            favicon=result.favicon,
        )
        converted.append(
            WebSearchResult(
                page_content=result.content or "",
                metadata=metadata,
            )
        )
    return converted


async def summarizer_node(
    state: OpenCanvasState,
    config: RunnableConfig,
):
    """Summarize internal messages when over the character budget."""
    messages = state.internal_messages if state.internal_messages else state.messages
    if not messages:
        return {}

    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    model = get_chat_model(
        model=model_name,
        temperature=0,
        streaming=False,
        api_key=api_key,
    )

    formatted_messages = format_messages(messages)
    response = await model.ainvoke([
        {"role": "system", "content": SUMMARIZER_PROMPT},
        {"role": "user", "content": f"Here are the messages to summarize:\n{formatted_messages}"},
    ])

    summary_content = response.content
    if isinstance(summary_content, list):
        summary_content = get_string_from_content(summary_content)
    elif not isinstance(summary_content, str):
        summary_content = str(summary_content)
    summary_message = HumanMessage(
        content=SUMMARY_MESSAGE_TEMPLATE.format(summary=summary_content),
        additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
    )

    logger.debug("Summary generated (%s chars).", len(summary_content))

    return {"internal_messages": [summary_message]}


async def generate_title_node(
    state: OpenCanvasState,
    config: RunnableConfig,
):
    """Generate and persist a concise session title after the first exchange."""
    if len(state.messages) > 2:
        return {}

    configurable = config.get("configurable", {})
    session_id = configurable.get("session_id")
    if not session_id:
        return {}

    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    model = get_chat_model(
        model=model_name,
        temperature=0,
        streaming=False,
        api_key=api_key,
    )

    class TitleOutput(BaseModel):
        """Generated session title."""
        title: str = Field(description="The generated title for the conversation.")

    model_with_tool = model.bind_tools(
        [
            {
                "name": "generate_title",
                "description": "Generate a concise title for the conversation.",
                "schema": TitleOutput,
            }
        ],
        tool_choice="generate_title",
    )

    conversation = format_messages(state.messages)
    artifact_context = "No artifact was generated during this conversation."
    if state.artifact and state.artifact.contents:
        current_content = get_artifact_content(state.artifact)
        if is_artifact_markdown_content(current_content):
            artifact_text = current_content.full_markdown
        elif is_artifact_code_content(current_content):
            artifact_text = current_content.code
        else:
            artifact_text = ""
        if artifact_text:
            artifact_context = (
                "An artifact was generated during this conversation:\n\n"
                f"{artifact_text}"
            )

    formatted_user_prompt = TITLE_USER_PROMPT.format(
        conversation=conversation,
        artifact_context=artifact_context,
    )

    response = await model_with_tool.ainvoke([
        {"role": "system", "content": TITLE_SYSTEM_PROMPT},
        {"role": "user", "content": formatted_user_prompt},
    ])

    title = None
    if response.tool_calls:
        args = response.tool_calls[0].get("args") or {}
        title = args.get("title")

    if not title:
        logger.debug("Title generation skipped: no tool call returned.")
        return {}

    # Get database from config or create a new instance (fallback for backwards compatibility)
    db = configurable.get("database") or Database()
    repo = SessionRepository(db)
    session = repo.get_by_id(session_id)
    if not session:
        return {}

    title = title.strip()
    if not title:
        return {}

    if session.title != title:
        session.title = title
        session.updated_at = datetime.now()
        repo.update(session)
        logger.debug("Session title updated: %s", title)

    return {"session_title": title}


async def web_search_node(
    state: OpenCanvasState,
    config: RunnableConfig,
):
    """Web search flow: classify, generate query, search, and store results."""
    if not state.web_search_enabled:
        return {"web_search_results": []}

    messages = state.internal_messages if state.internal_messages else state.messages
    last_user_message = _last_user_message(messages)
    if not last_user_message:
        logger.debug("Web search skipped: no user message.")
        return {"web_search_results": []}

    user_message = get_string_from_content(last_user_message.content).strip()
    if not user_message:
        logger.debug("Web search skipped: empty user message.")
        return {"web_search_results": []}

    configurable = config.get("configurable", {})
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    model = get_chat_model(
        model=model_name,
        temperature=0,
        streaming=False,
        api_key=api_key,
    )

    class WebSearchDecision(BaseModel):
        """Classification for web search."""
        should_search: bool = Field(
            description="Whether or not to search the web based on the user's latest message."
        )

    classifier = model.with_structured_output(WebSearchDecision, name="classify_message")
    classifier_prompt = WEB_SEARCH_CLASSIFIER_PROMPT.format(message=user_message)

    should_search = False
    try:
        result = await classifier.ainvoke([{"role": "user", "content": classifier_prompt}])
        if getattr(result, "tool_calls", None):
            args = result.tool_calls[0].get("args") or {}
            should_search = bool(
                args.get("should_search", args.get("shouldSearch", False))
            )
        elif hasattr(result, "should_search"):
            should_search = bool(result.should_search)
    except Exception as exc:
        logger.warning("Web search classification failed: %s", exc)

    if not should_search:
        logger.debug("Web search not required for this message.")
        return {"web_search_results": []}

    additional_context = f"The current date is {datetime.now().strftime('%B %d, %Y %H:%M')}"
    formatted_messages = format_messages(messages)
    query_prompt = WEB_SEARCH_QUERY_PROMPT.format(
        conversation=formatted_messages,
        additional_context=additional_context,
    )
    query_response = await model.ainvoke([{"role": "user", "content": query_prompt}])
    query_content = query_response.content
    if isinstance(query_content, list):
        query_content = get_string_from_content(query_content)
    elif not isinstance(query_content, str):
        query_content = str(query_content)
    query = query_content.strip()
    if not query:
        logger.debug("Web search skipped: query generation failed.")
        return {"web_search_results": []}

    provider_name = configurable.get("web_search_provider", "exa") or "exa"
    num_results = int(configurable.get("web_search_num_results", 5))
    results: list[ProviderSearchResult] = []

    if provider_name == "exa":
        provider = ExaSearchProvider(api_key=configurable.get("exa_api_key"))
        try:
            results = provider.search_sync(query, num_results=num_results)
        except Exception as exc:
            logger.warning("Exa search failed: %s", exc)
    else:
        logger.warning("Web search provider not supported: %s", provider_name)

    converted_results = _to_web_search_results(results)
    logger.debug("Web search results: %s", len(converted_results))
    return {"web_search_results": converted_results}


async def route_post_web_search(state: OpenCanvasState):
    """Route after web search completes, using the stored intended route."""
    # Use the stored intended route, or fall back to replyToGeneralInput
    intended_route = state.post_web_search_route or "replyToGeneralInput"
    
    result = {
        "next": intended_route,
        "web_search_enabled": False,
        "post_web_search_route": None,  # Clear after use
    }
    
    # Add web search results as context message if available
    if state.web_search_results:
        result["internal_messages"] = [
            create_ai_message_from_web_results(state.web_search_results)
        ]
    
    return result


async def reflect_node(
    state: OpenCanvasState,
    config: RunnableConfig,
):
    """
    Reflect on the conversation and artifact to generate/update user reflections.
    
    Reflections consist of:
    - Style Guidelines: General style rules for generating content
    - Content: Memories, facts, and insights about the user
    
    These are persisted to the store and used by other nodes to personalize responses.
    """
    configurable = config.get("configurable", {})
    assistant_id = configurable.get("assistant_id", "default")
    model_name = configurable.get("model", "anthropic/claude-3.5-sonnet")
    api_key = configurable.get("api_key")
    
    # Get existing reflections from store
    store = get_store()
    memories = store.get(["memories", assistant_id], "reflection")
    
    existing_reflections = "No existing reflections."
    if memories and memories.value:
        existing_reflections = get_formatted_reflections(Reflections(**memories.value))
    
    # Get artifact context
    artifact_context = "No artifact was generated during this conversation."
    if state.artifact and state.artifact.contents:
        current_content = get_artifact_content(state.artifact)
        if is_artifact_markdown_content(current_content):
            artifact_context = current_content.full_markdown
        elif is_artifact_code_content(current_content):
            artifact_context = current_content.code
    
    # Format conversation
    messages = state.internal_messages if state.internal_messages else state.messages
    if not messages:
        logger.debug("Reflection skipped: no messages.")
        return {}
    
    conversation = format_messages(messages)
    
    # Build prompts
    system_prompt = REFLECT_SYSTEM_PROMPT.format(
        artifact=artifact_context,
        reflections=existing_reflections,
    )
    user_prompt = REFLECT_USER_PROMPT.format(conversation=conversation)
    
    # Define the reflections output schema
    class ReflectionsOutput(BaseModel):
        """Generated reflections about the user."""
        style_rules: list[str] = Field(
            default_factory=list,
            description="Style guidelines for generating content for this user.",
        )
        content: list[str] = Field(
            default_factory=list,
            description="Memories, facts, and insights about the user.",
        )
    
    # Get model with structured output
    model = get_chat_model(
        model=model_name,
        temperature=0,
        streaming=False,
        api_key=api_key,
    )
    
    model_with_tool = model.bind_tools(
        [
            {
                "name": "generate_reflections",
                "description": "Generate the new, full list of reflections about the user.",
                "schema": ReflectionsOutput,
            }
        ],
        tool_choice="generate_reflections",
    )
    
    try:
        response = await model_with_tool.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        
        # Extract reflections from tool call
        if response.tool_calls:
            args = response.tool_calls[0].get("args") or {}
            new_reflections = {
                "styleRules": args.get("style_rules", []),
                "content": args.get("content", []),
            }
            
            # Persist to store
            store.put(["memories", assistant_id], "reflection", new_reflections)
            logger.debug(
                "Reflections updated: %d style rules, %d content items.",
                len(new_reflections["styleRules"]),
                len(new_reflections["content"]),
            )
    except Exception as exc:
        logger.warning("Reflection generation failed: %s", exc)
    
    return {}


def route_artifact_ops_exit(state: OpenCanvasState) -> str:
    """
    Route after artifactOps subgraph completes.
    
    If a recovery message was set, route to replyToGeneralInput.
    Otherwise, proceed to reflect.
    """
    if state.artifact_action_recovery_message:
        return "replyToGeneralInput"
    return "reflect"


# Build the graph
builder = StateGraph(OpenCanvasState)

# Add nodes
builder.add_node("generatePath", generate_path)
builder.add_node("ragRetrieve", rag_graph)
builder.add_node("replyToGeneralInput", reply_to_general_input)
builder.add_node("artifactOps", artifact_ops_graph)  # ArtifactOps subgraph
builder.add_node("cleanState", clean_state)
builder.add_node("reflect", reflect_node)
builder.add_node("generateTitle", generate_title_node)
builder.add_node("summarizer", summarizer_node)
builder.add_node("webSearch", web_search_node)
builder.add_node("routePostWebSearch", route_post_web_search)
builder.add_node("imageProcessing", image_processing)

# Add edges
builder.add_edge(START, "generatePath")

# Initial router - conditional edges from generatePath
builder.add_conditional_edges(
    "generatePath",
    route_node,
    {
        "artifactOps": "ragRetrieve",  # Artifact operations go through RAG first
        "replyToGeneralInput": "ragRetrieve",
        "webSearch": "webSearch",
        "imageProcessing": "imageProcessing",
    },
)

# RAG retrieval routes to either artifactOps or replyToGeneralInput
def route_after_rag(state: OpenCanvasState) -> str:
    """Route after RAG retrieval based on artifact_action presence."""
    if state.artifact_action:
        return "artifactOps"
    return "replyToGeneralInput"

builder.add_conditional_edges(
    "ragRetrieve",
    route_after_rag,
    {
        "artifactOps": "artifactOps",
        "replyToGeneralInput": "replyToGeneralInput",
    },
)

# Web search flow
builder.add_edge("webSearch", "routePostWebSearch")
builder.add_conditional_edges(
    "routePostWebSearch",
    route_node,
    {
        "artifactOps": "ragRetrieve",  # Artifact operations go through RAG after web search
        "replyToGeneralInput": "ragRetrieve",
        "imageProcessing": "imageProcessing",
    },
)

# Reply to general input -> clean state
builder.add_edge("replyToGeneralInput", "cleanState")
builder.add_edge("imageProcessing", "cleanState")

# ArtifactOps subgraph exit -> conditional routing
builder.add_conditional_edges(
    "artifactOps",
    route_artifact_ops_exit,
    {
        "reflect": "reflect",
        "replyToGeneralInput": "replyToGeneralInput",  # Recovery path
    },
)

# Reflect -> clean state
builder.add_edge("reflect", "cleanState")

# Clean state -> conditional title generation or end
builder.add_conditional_edges(
    "cleanState",
    conditionally_generate_title,
    {
        END: END,
        "generateTitle": "generateTitle",
        "summarizer": "summarizer",
    },
)

# End nodes
builder.add_edge("generateTitle", END)
builder.add_edge("summarizer", END)

# Compile the graph
graph = builder.compile()
graph.name = "open_canvas"
