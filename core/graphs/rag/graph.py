"""RAG subgraph for retrieval."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from core.graphs.open_canvas.state import OpenCanvasState
from core.graphs.rag.nodes import (
    decide_retrieve,
    select_scope,
    rewrite_query,
    global_rag_node,
    local_rag_node,
)


def _route_after_decide(state: OpenCanvasState) -> str:
    return "selectScope" if state.rag_should_retrieve else END


def _route_after_rewrite(state: OpenCanvasState) -> str:
    mode = state.conversation_mode or "normal"
    if mode == "chatpdf" or state.active_pdf_document_id:
        return "localRag"
    return "globalRag"


builder = StateGraph(OpenCanvasState)

builder.add_node("decideRetrieve", decide_retrieve)
builder.add_node("selectScope", select_scope)
builder.add_node("rewriteQuery", rewrite_query)
builder.add_node("globalRag", global_rag_node)
builder.add_node("localRag", local_rag_node)

builder.add_edge(START, "decideRetrieve")
builder.add_conditional_edges(
    "decideRetrieve",
    _route_after_decide,
    {"selectScope": "selectScope", END: END},
)
builder.add_edge("selectScope", "rewriteQuery")
builder.add_conditional_edges(
    "rewriteQuery",
    _route_after_rewrite,
    {"globalRag": "globalRag", "localRag": "localRag"},
)
builder.add_edge("globalRag", END)
builder.add_edge("localRag", END)

graph = builder.compile()
graph.name = "rag_subgraph"
