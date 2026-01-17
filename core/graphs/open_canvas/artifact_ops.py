"""
Artifact Operations Subgraph.

This subgraph centralizes all artifact mutation operations (generate, rewrite, update, etc.)
with a single entry point for validation and dispatch. This improves testability and
makes artifact operation routing explicit.
"""

from langgraph.graph import StateGraph, END

from core.graphs.open_canvas.state import OpenCanvasState
from core.graphs.open_canvas.nodes import (
    generate_artifact,
    rewrite_artifact,
    rewrite_artifact_theme,
    rewrite_code_artifact_theme,
    update_artifact,
    update_highlighted_text,
    custom_action,
    generate_followup,
)


# Valid artifact actions handled by this subgraph
VALID_ARTIFACT_ACTIONS = {
    "generateArtifact",
    "rewriteArtifact",
    "rewriteArtifactTheme",
    "rewriteCodeArtifactTheme",
    "updateArtifact",
    "updateHighlightedText",
    "customAction",
}

# Actions that require an existing artifact
ACTIONS_REQUIRING_ARTIFACT = {
    "rewriteArtifact",
    "rewriteArtifactTheme",
    "rewriteCodeArtifactTheme",
    "updateArtifact",
    "updateHighlightedText",
    "customAction",
}

# Actions that require a highlight selection
ACTIONS_REQUIRING_HIGHLIGHT = {
    "updateHighlightedText",
}


class ArtifactOpsError(Exception):
    """Hard-fail exception for invariant violations in artifact dispatch."""
    pass


async def artifact_action_dispatch(state: OpenCanvasState) -> dict:
    """
    Validates artifact action prerequisites and routes to the appropriate action node.
    
    Soft failures (missing artifact or highlight): Sets a recovery message and routes
    to replyToGeneralInput for user guidance.
    
    Hard failures (unknown action or invalid artifact): Raises ArtifactOpsError.
    """
    import logging
    
    action = state.artifact_action
    
    # Hard-fail: Unknown or missing action
    if not action:
        logging.error("[ArtifactOps] artifact_action is None - invariant violation")
        raise ArtifactOpsError("No artifact action specified. This is an internal error.")
    
    if action not in VALID_ARTIFACT_ACTIONS:
        logging.error(f"[ArtifactOps] Unknown artifact action: {action}")
        raise ArtifactOpsError(f"Unknown artifact action: {action}")
    
    # Soft-fail: Action requires artifact but none exists
    if action in ACTIONS_REQUIRING_ARTIFACT:
        if not state.artifact or not state.artifact.contents:
            logging.warning(f"[ArtifactOps] Action '{action}' requires an artifact but none exists")
            return {
                "artifact_action_recovery_message": (
                    "I'd be happy to help with that, but there's no artifact to modify yet. "
                    "Would you like me to create one first?"
                ),
                "next": "__recovery__",
            }
        
        # Hard-fail: Artifact exists but has invalid structure
        if not hasattr(state.artifact, "contents"):
            logging.error(f"[ArtifactOps] Invalid artifact structure for action: {action}")
            raise ArtifactOpsError("The artifact has an invalid structure.")
    
    # Soft-fail: Action requires highlight selection but none provided
    if action in ACTIONS_REQUIRING_HIGHLIGHT:
        if not state.highlighted_text and not state.highlighted_code:
            logging.warning(f"[ArtifactOps] Action '{action}' requires a highlight selection")
            return {
                "artifact_action_recovery_message": (
                    "I need to know which part of the artifact you'd like me to update. "
                    "Please select the text you want to modify."
                ),
                "next": "__recovery__",
            }
    
    # All validations passed - route to the action
    return {"next": action}


def route_artifact_action(state: OpenCanvasState) -> str:
    """Route based on the 'next' field set by artifact_action_dispatch."""
    if not state.next:
        raise ValueError("'next' state field not set in artifact dispatch.")
    
    # Check for recovery route
    if state.next == "__recovery__":
        return "__recovery__"
    
    return state.next


# Build the ArtifactOps subgraph
builder = StateGraph(OpenCanvasState)

# Entry point: validation and dispatch
builder.add_node("artifactActionDispatch", artifact_action_dispatch)

# Artifact action nodes
builder.add_node("generateArtifact", generate_artifact)
builder.add_node("rewriteArtifact", rewrite_artifact)
builder.add_node("rewriteArtifactTheme", rewrite_artifact_theme)
builder.add_node("rewriteCodeArtifactTheme", rewrite_code_artifact_theme)
builder.add_node("updateArtifact", update_artifact)
builder.add_node("updateHighlightedText", update_highlighted_text)
builder.add_node("customAction", custom_action)

# Follow-up generation (included in subgraph)
builder.add_node("generateFollowup", generate_followup)

# Entry edge
builder.set_entry_point("artifactActionDispatch")

# Conditional routing from dispatch
builder.add_conditional_edges(
    "artifactActionDispatch",
    route_artifact_action,
    {
        "generateArtifact": "generateArtifact",
        "rewriteArtifact": "rewriteArtifact",
        "rewriteArtifactTheme": "rewriteArtifactTheme",
        "rewriteCodeArtifactTheme": "rewriteCodeArtifactTheme",
        "updateArtifact": "updateArtifact",
        "updateHighlightedText": "updateHighlightedText",
        "customAction": "customAction",
        "__recovery__": END,  # Recovery routes back to main graph
    },
)

# All artifact actions flow to generateFollowup, then end
builder.add_edge("generateArtifact", "generateFollowup")
builder.add_edge("rewriteArtifact", "generateFollowup")
builder.add_edge("rewriteArtifactTheme", "generateFollowup")
builder.add_edge("rewriteCodeArtifactTheme", "generateFollowup")
builder.add_edge("updateArtifact", "generateFollowup")
builder.add_edge("updateHighlightedText", "generateFollowup")
builder.add_edge("customAction", "generateFollowup")

# Followup ends the subgraph
builder.add_edge("generateFollowup", END)

# Compile the subgraph
artifact_ops_graph = builder.compile()
artifact_ops_graph.name = "artifact_ops"
