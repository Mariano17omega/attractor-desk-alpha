"""
Open Canvas main graph definition.
This is the primary graph that handles all conversation and artifact generation.
"""

from typing import Literal, Union
from langgraph.graph import StateGraph, START, END

from core.graphs.open_canvas.state import OpenCanvasState
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
from core.constants import CHARACTER_MAX


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


# Placeholder nodes for graphs not yet fully implemented
async def summarizer_node(state: OpenCanvasState):
    """Placeholder for summarizer graph."""
    # TODO: Implement full summarizer logic
    return {}


async def generate_title_node(state: OpenCanvasState):
    """Placeholder for title generation."""
    # TODO: Implement title generation
    return {}


async def web_search_node(state: OpenCanvasState):
    """Placeholder for web search subgraph."""
    # TODO: Implement web search
    return {"web_search_results": []}


async def route_post_web_search(state: OpenCanvasState):
    """Route after web search completes."""
    has_artifact = state.artifact and len(state.artifact.contents) > 0
    
    if not state.web_search_results:
        return {"next": "rewriteArtifact" if has_artifact else "generateArtifact"}
    
    # Web search returned results
    return {
        "next": "rewriteArtifact" if has_artifact else "generateArtifact",
        "web_search_enabled": False,
    }


async def reflect_node(state: OpenCanvasState):
    """Placeholder for reflection trigger."""
    # TODO: Implement reflection scheduling
    return {}


# Build the graph
builder = StateGraph(OpenCanvasState)

# Add nodes
builder.add_node("generatePath", generate_path)
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
        "replyToGeneralInput": "replyToGeneralInput",
        "generateArtifact": "generateArtifact",
        "rewriteArtifact": "rewriteArtifact",
        "customAction": "customAction",
        "updateHighlightedText": "updateHighlightedText",
        "webSearch": "webSearch",
    },
)

# Artifact generation/modification -> clean state (skip followup for now to fix validation errors)
builder.add_edge("generateArtifact", "cleanState")
builder.add_edge("updateArtifact", "cleanState")
builder.add_edge("updateHighlightedText", "cleanState")
builder.add_edge("rewriteArtifact", "cleanState")
builder.add_edge("rewriteArtifactTheme", "cleanState")
builder.add_edge("rewriteCodeArtifactTheme", "cleanState")
builder.add_edge("customAction", "cleanState")

# Web search flow
builder.add_edge("webSearch", "routePostWebSearch")
builder.add_conditional_edges(
    "routePostWebSearch",
    route_node,
    {
        "generateArtifact": "generateArtifact",
        "rewriteArtifact": "rewriteArtifact",
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
