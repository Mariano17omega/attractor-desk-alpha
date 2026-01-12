"""Utilities for injecting RAG context into prompts."""

from __future__ import annotations

from core.graphs.open_canvas.state import OpenCanvasState


def build_rag_prompt(state: OpenCanvasState) -> str:
    if not state.rag_should_retrieve:
        return ""

    prompt_parts: list[str] = []
    if state.rag_context:
        prompt_parts.append(
            "Use the following retrieved context when relevant.\n"
            f"{state.rag_context}"
        )

    if state.rag_grounded is False:
        prompt_parts.append(
            "Grounding check: evidence is insufficient. "
            "Say so explicitly and suggest providing keywords, "
            "expanding scope, or importing the relevant document."
        )

    if not prompt_parts:
        return ""
    return "\n\n" + "\n\n".join(prompt_parts)
