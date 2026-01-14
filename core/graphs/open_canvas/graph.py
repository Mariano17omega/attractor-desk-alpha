"""
Open Canvas main graph definition.
This is the primary graph that handles all conversation and artifact generation.
"""

from datetime import datetime
from typing import Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.config import RunnableConfig
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from core.constants import CHARACTER_MAX, OC_SUMMARIZED_MESSAGE_KEY
from core.graphs.open_canvas.nodes import (
    generate_path,
    generate_artifact,
    rewrite_artifact,
    reply_to_general_input,
    generate_followup,
    clean_state,
    rewrite_artifact_theme,
    rewrite_code_artifact_theme,
    update_artifact,
    update_highlighted_text,
    custom_action,
)
from core.graphs.open_canvas.prompts import (
    WEB_SEARCH_CLASSIFIER_PROMPT,
    WEB_SEARCH_QUERY_PROMPT,
    SUMMARIZER_PROMPT,
    SUMMARY_MESSAGE_TEMPLATE,
    TITLE_SYSTEM_PROMPT,
    TITLE_USER_PROMPT,
)
from core.graphs.open_canvas.state import OpenCanvasState, is_summary_message
from core.graphs.rag.graph import graph as rag_graph
from core.llm import get_chat_model
from core.persistence import Database, SessionRepository
from core.providers.exa_search import ExaSearchProvider
from core.providers.search import SearchResult as ProviderSearchResult
from core.types import ExaMetadata, SearchResult as WebSearchResult
from core.utils.artifacts import get_artifact_content, is_artifact_code_content, is_artifact_markdown_content
from core.utils.messages import create_ai_message_from_web_results, format_messages, get_string_from_content


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

    print(f"[DEBUG] Summary generated ({len(summary_content)} chars).")

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
        print("[DEBUG] Title generation skipped: no tool call returned.")
        return {}

    repo = SessionRepository(Database())
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
        print(f"[DEBUG] Session title updated: {title}")

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
        print("[DEBUG] Web search skipped: no user message.")
        return {"web_search_results": []}

    user_message = get_string_from_content(last_user_message.content).strip()
    if not user_message:
        print("[DEBUG] Web search skipped: empty user message.")
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
        print(f"[DEBUG] Web search classification failed: {exc}")

    if not should_search:
        print("[DEBUG] Web search not required for this message.")
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
        print("[DEBUG] Web search skipped: query generation failed.")
        return {"web_search_results": []}

    provider_name = configurable.get("web_search_provider", "exa") or "exa"
    num_results = int(configurable.get("web_search_num_results", 5))
    results: list[ProviderSearchResult] = []

    if provider_name == "exa":
        provider = ExaSearchProvider(api_key=configurable.get("exa_api_key"))
        try:
            results = provider.search_sync(query, num_results=num_results)
        except Exception as exc:
            print(f"[DEBUG] Exa search failed: {exc}")
    else:
        print(f"[DEBUG] Web search provider not supported: {provider_name}")

    converted_results = _to_web_search_results(results)
    print(f"[DEBUG] Web search results: {len(converted_results)}")
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


async def reflect_node(state: OpenCanvasState):
    """Placeholder for reflection trigger."""
    # TODO: Implement reflection scheduling
    return {}


# Build the graph
builder = StateGraph(OpenCanvasState)

# Add nodes
builder.add_node("generatePath", generate_path)
builder.add_node("ragRetrieve", rag_graph)
builder.add_node("replyToGeneralInput", reply_to_general_input)
builder.add_node("rewriteArtifact", rewrite_artifact)
builder.add_node("rewriteArtifactTheme", rewrite_artifact_theme)
builder.add_node("rewriteCodeArtifactTheme", rewrite_code_artifact_theme)
builder.add_node("updateArtifact", update_artifact)
builder.add_node("updateHighlightedText", update_highlighted_text)
builder.add_node("generateArtifact", generate_artifact)
builder.add_node("customAction", custom_action)
builder.add_node("generateFollowup", generate_followup)
builder.add_node("cleanState", clean_state)
builder.add_node("reflect", reflect_node)
builder.add_node("generateTitle", generate_title_node)
builder.add_node("summarizer", summarizer_node)
builder.add_node("webSearch", web_search_node)
builder.add_node("routePostWebSearch", route_post_web_search)

# Add edges
builder.add_edge(START, "generatePath")

# Initial router - conditional edges from generatePath
builder.add_conditional_edges(
    "generatePath",
    route_node,
    {
        "updateArtifact": "updateArtifact",
        "rewriteArtifactTheme": "rewriteArtifactTheme",
        "rewriteCodeArtifactTheme": "rewriteCodeArtifactTheme",
        "replyToGeneralInput": "ragRetrieve",
        "generateArtifact": "ragRetrieve",
        "rewriteArtifact": "ragRetrieve",
        "customAction": "customAction",
        "updateHighlightedText": "updateHighlightedText",
        "webSearch": "webSearch",
    },
)

builder.add_conditional_edges(
    "ragRetrieve",
    route_node,
    {
        "replyToGeneralInput": "replyToGeneralInput",
        "generateArtifact": "generateArtifact",
        "rewriteArtifact": "rewriteArtifact",
    },
)

# Artifact generation/modification -> generateFollowup (for follow-up messages)
builder.add_edge("generateArtifact", "generateFollowup")
builder.add_edge("updateArtifact", "generateFollowup")
builder.add_edge("updateHighlightedText", "generateFollowup")
builder.add_edge("rewriteArtifact", "generateFollowup")
builder.add_edge("rewriteArtifactTheme", "generateFollowup")
builder.add_edge("rewriteCodeArtifactTheme", "generateFollowup")
builder.add_edge("customAction", "generateFollowup")

# Web search flow
builder.add_edge("webSearch", "routePostWebSearch")
builder.add_conditional_edges(
    "routePostWebSearch",
    route_node,
    {
        "generateArtifact": "ragRetrieve",
        "rewriteArtifact": "ragRetrieve",
        "replyToGeneralInput": "ragRetrieve",
        "updateArtifact": "updateArtifact",
        "rewriteArtifactTheme": "rewriteArtifactTheme",
        "rewriteCodeArtifactTheme": "rewriteCodeArtifactTheme",
        "customAction": "customAction",
        "updateHighlightedText": "updateHighlightedText",
    },
)

# Reply to general input -> clean state
builder.add_edge("replyToGeneralInput", "cleanState")

# Followup -> reflect -> clean state
builder.add_edge("generateFollowup", "reflect")
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
