"""RAG subgraph nodes."""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig

from core.persistence import Database, RagRepository
from core.services.rag_service import RagRetrievalSettings, RagService
from core.graphs.open_canvas.state import OpenCanvasState
from core.utils.messages import get_string_from_content


def decide_retrieve(state: OpenCanvasState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    rag_enabled = bool(configurable.get("rag_enabled", False))
    query = _last_user_message(state.messages or [])
    should_retrieve = bool(rag_enabled and query and len(query.strip()) > 2)
    return {
        "rag_enabled": rag_enabled,
        "rag_should_retrieve": should_retrieve,
        "rag_query": query if should_retrieve else None,
    }


def select_scope(state: OpenCanvasState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    scope = configurable.get("rag_scope", "session") or "session"
    session_id = configurable.get("session_id")
    if scope == "session" and not session_id:
        scope = "workspace"
    return {"rag_scope": scope}


def rewrite_query(state: OpenCanvasState, config: RunnableConfig) -> dict:
    if not state.rag_should_retrieve or not state.rag_query:
        return {}
    configurable = config.get("configurable", {})
    enable_rewrite = bool(configurable.get("rag_enable_query_rewrite", False))
    queries = [state.rag_query.strip()]
    if enable_rewrite:
        rewritten = _simple_rewrite(state.rag_query)
        if rewritten and rewritten not in queries:
            queries.append(rewritten)
    return {"rag_queries": queries}


def retrieve_context(state: OpenCanvasState, config: RunnableConfig) -> dict:
    if not state.rag_should_retrieve or not state.rag_query:
        return {
            "rag_context": "",
            "rag_candidates": [],
            "rag_citations": [],
            "rag_grounded": False,
            "rag_selected_chunk_ids": [],
            "rag_retrieval_debug": {},
        }
    configurable = config.get("configurable", {})
    settings = RagRetrievalSettings(
        scope=state.rag_scope or configurable.get("rag_scope", "session") or "session",
        k_lex=int(configurable.get("rag_k_lex", 8)),
        k_vec=int(configurable.get("rag_k_vec", 8)),
        rrf_k=int(configurable.get("rag_rrf_k", 60)),
        max_candidates=int(configurable.get("rag_max_candidates", 12)),
        max_context_chunks=int(configurable.get("rag_max_context_chunks", 6)),
        max_context_chars=int(configurable.get("rag_max_context_chars", 6000)),
        enable_llm_rerank=bool(configurable.get("rag_enable_llm_rerank", False)),
    )
    embedding_model = configurable.get("rag_embedding_model") or None
    api_key = configurable.get("api_key")

    repository = RagRepository(Database())
    service = RagService(repository)
    result = service.retrieve(
        query=state.rag_query,
        queries=state.rag_queries,
        settings=settings,
        workspace_id=configurable.get("workspace_id"),
        session_id=configurable.get("session_id"),
        embedding_model=embedding_model,
        api_key=api_key,
    )
    return {
        "rag_context": result.context,
        "rag_candidates": result.candidates,
        "rag_citations": result.citations,
        "rag_grounded": result.grounded,
        "rag_selected_chunk_ids": result.selected_chunk_ids,
        "rag_retrieval_debug": result.debug,
    }


def _last_user_message(messages: list[BaseMessage]) -> Optional[str]:
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            return get_string_from_content(message.content)
    return None


def _simple_rewrite(query: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", query.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
