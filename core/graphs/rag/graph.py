"""RAG subgraph for retrieval."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from core.graphs.open_canvas.state import OpenCanvasState
from core.graphs.rag.nodes import decide_retrieve, select_scope, rewrite_query, retrieve_context


def _route_after_decide(state: OpenCanvasState) -> str:
    return "selectScope" if state.rag_should_retrieve else END


builder = StateGraph(OpenCanvasState)

builder.add_node("decideRetrieve", decide_retrieve)
builder.add_node("selectScope", select_scope)
builder.add_node("rewriteQuery", rewrite_query)
builder.add_node("retrieveContext", retrieve_context)

builder.add_edge(START, "decideRetrieve")
builder.add_conditional_edges(
    "decideRetrieve",
    _route_after_decide,
    {"selectScope": "selectScope", END: END},
)
builder.add_edge("selectScope", "rewriteQuery")
builder.add_edge("rewriteQuery", "retrieveContext")
builder.add_edge("retrieveContext", END)

graph = builder.compile()
graph.name = "rag_subgraph"
