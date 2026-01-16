"""RAG subgraph nodes."""

from __future__ import annotations

import logging
import re
from typing import Optional

from langchain_core.messages import BaseMessage
from langgraph.config import RunnableConfig

from core.persistence import Database, RagRepository
from core.services.rag_service import RagRetrievalSettings, RagService
from core.graphs.open_canvas.state import OpenCanvasState
from core.utils.messages import get_string_from_content

logger = logging.getLogger(__name__)


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
    scope = configurable.get("rag_scope", "global") or "global"
    mode = _resolve_conversation_mode(state, configurable)
    active_pdf = _resolve_active_pdf_document(state, configurable)
    if mode == "chatpdf" or active_pdf:
        scope = "session"
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


def global_rag_node(state: OpenCanvasState, config: RunnableConfig) -> dict:
    return _retrieve_with_scope(state, config, rag_used="global")


def local_rag_node(state: OpenCanvasState, config: RunnableConfig) -> dict:
    return _retrieve_with_scope(state, config, rag_used="local", force_scope="session")


def _retrieve_with_scope(
    state: OpenCanvasState,
    config: RunnableConfig,
    rag_used: str,
    force_scope: Optional[str] = None,
) -> dict:
    if not state.rag_should_retrieve or not state.rag_query:
        return {
            "rag_context": "",
            "rag_candidates": [],
            "rag_citations": [],
            "rag_grounded": False,
            "rag_selected_chunk_ids": [],
            "rag_retrieval_debug": {},
            "rag_used": None,
        }
    configurable = config.get("configurable", {})
    scope = force_scope or state.rag_scope or configurable.get("rag_scope", "global") or "global"
    settings = RagRetrievalSettings(
        scope=scope,
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
    mode = _resolve_conversation_mode(state, configurable)
    active_pdf = _resolve_active_pdf_document(state, configurable)
    reason = f"mode={mode}"
    if active_pdf:
        reason = f"{reason}, active_pdf={active_pdf}"
    logger.info("%s -> %s", reason, f"{rag_used}_rag_node")
    debug = dict(result.debug)
    debug.update({"scope": scope, "rag_used": rag_used})
    return {
        "rag_context": result.context,
        "rag_candidates": result.candidates,
        "rag_citations": result.citations,
        "rag_grounded": result.grounded,
        "rag_selected_chunk_ids": result.selected_chunk_ids,
        "rag_retrieval_debug": debug,
        "rag_used": rag_used,
        "rag_route_debug": {
            "mode": mode,
            "active_pdf_document_id": active_pdf,
            "selected_node": f"{rag_used}_rag_node",
            "scope": scope,
        },
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


def _resolve_conversation_mode(state: OpenCanvasState, configurable: dict) -> str:
    return (
        state.conversation_mode
        or configurable.get("conversation_mode")
        or "normal"
    )


def _resolve_active_pdf_document(state: OpenCanvasState, configurable: dict) -> Optional[str]:
    return state.active_pdf_document_id or configurable.get("active_pdf_document_id")
