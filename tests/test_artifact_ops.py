"""
Tests for the ArtifactOps subgraph and artifact_action_dispatch node.
"""

import pytest
from unittest.mock import MagicMock

from core.graphs.open_canvas.state import OpenCanvasState
from core.graphs.open_canvas.artifact_ops import (
    artifact_action_dispatch,
    ArtifactOpsError,
    VALID_ARTIFACT_ACTIONS,
    ACTIONS_REQUIRING_ARTIFACT,
    ACTIONS_REQUIRING_HIGHLIGHT,
)
from core.types import ArtifactV3, ArtifactMarkdownV3, TextHighlight


def create_minimal_state(**kwargs) -> OpenCanvasState:
    """Create a minimal OpenCanvasState for testing."""
    defaults = {
        "messages": [],
        "internal_messages": [],
    }
    defaults.update(kwargs)
    return OpenCanvasState(**defaults)


def create_artifact_with_content() -> ArtifactV3:
    """Create a mock artifact with valid content."""
    content = ArtifactMarkdownV3(
        index=0,
        type="text",
        title="Test Artifact",
        full_markdown="# Test Content",
    )
    return ArtifactV3(
        contents=[content],
        current_index=0,
    )


class TestArtifactActionDispatch:
    """Tests for artifact_action_dispatch node."""

    @pytest.mark.asyncio
    async def test_missing_action_raises_error(self):
        """When artifact_action is None, should raise ArtifactOpsError."""
        state = create_minimal_state(artifact_action=None)
        
        with pytest.raises(ArtifactOpsError) as exc_info:
            await artifact_action_dispatch(state)
        
        assert "No artifact action specified" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unknown_action_raises_error(self):
        """When artifact_action is not in VALID_ARTIFACT_ACTIONS, should raise."""
        state = create_minimal_state(artifact_action="invalidAction")
        
        with pytest.raises(ArtifactOpsError) as exc_info:
            await artifact_action_dispatch(state)
        
        assert "Unknown artifact action" in str(exc_info.value)
        assert "invalidAction" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_artifact_routes_without_existing_artifact(self):
        """generateArtifact should succeed even without an existing artifact."""
        state = create_minimal_state(
            artifact_action="generateArtifact",
            artifact=None,
        )
        
        result = await artifact_action_dispatch(state)
        
        assert result["next"] == "generateArtifact"
        assert "artifact_action_recovery_message" not in result

    @pytest.mark.asyncio
    async def test_rewrite_artifact_requires_artifact(self):
        """rewriteArtifact without artifact should set recovery message."""
        state = create_minimal_state(
            artifact_action="rewriteArtifact",
            artifact=None,
        )
        
        result = await artifact_action_dispatch(state)
        
        assert result["next"] == "__recovery__"
        assert "no artifact to modify" in result["artifact_action_recovery_message"]

    @pytest.mark.asyncio
    async def test_rewrite_artifact_with_artifact_succeeds(self):
        """rewriteArtifact with valid artifact should route correctly."""
        state = create_minimal_state(
            artifact_action="rewriteArtifact",
            artifact=create_artifact_with_content(),
        )
        
        result = await artifact_action_dispatch(state)
        
        assert result["next"] == "rewriteArtifact"
        assert "artifact_action_recovery_message" not in result

    @pytest.mark.asyncio
    async def test_update_highlighted_text_requires_highlight(self):
        """updateHighlightedText without highlight should set recovery message."""
        state = create_minimal_state(
            artifact_action="updateHighlightedText",
            artifact=create_artifact_with_content(),
            highlighted_text=None,
            highlighted_code=None,
        )
        
        result = await artifact_action_dispatch(state)
        
        assert result["next"] == "__recovery__"
        assert "select the text" in result["artifact_action_recovery_message"]

    @pytest.mark.asyncio
    async def test_update_highlighted_text_with_highlight_succeeds(self):
        """updateHighlightedText with highlight should route correctly."""
        highlight = TextHighlight(
            full_markdown="# Test Content",
            markdown_block="# Test Content",
            selected_text="Test",
        )
        state = create_minimal_state(
            artifact_action="updateHighlightedText",
            artifact=create_artifact_with_content(),
            highlighted_text=highlight,
        )
        
        result = await artifact_action_dispatch(state)
        
        assert result["next"] == "updateHighlightedText"
        assert "artifact_action_recovery_message" not in result

    @pytest.mark.asyncio
    async def test_all_valid_actions_recognized(self):
        """All VALID_ARTIFACT_ACTIONS should be recognized without error."""
        highlight = TextHighlight(
            full_markdown="# Test Content",
            markdown_block="# Test Content",
            selected_text="Test",
        )
        for action in VALID_ARTIFACT_ACTIONS:
            state = create_minimal_state(
                artifact_action=action,
                artifact=create_artifact_with_content(),
                highlighted_text=highlight,
            )
            
            # Should not raise ArtifactOpsError for unknown action
            result = await artifact_action_dispatch(state)
            
            # Should either route to action or recovery
            assert result["next"] in (action, "__recovery__")


class TestValidationConstants:
    """Tests for validation constants."""

    def test_actions_requiring_artifact_subset_of_valid(self):
        """ACTIONS_REQUIRING_ARTIFACT should be subset of VALID_ARTIFACT_ACTIONS."""
        assert ACTIONS_REQUIRING_ARTIFACT.issubset(VALID_ARTIFACT_ACTIONS)

    def test_actions_requiring_highlight_subset_of_requiring_artifact(self):
        """ACTIONS_REQUIRING_HIGHLIGHT should be subset of ACTIONS_REQUIRING_ARTIFACT."""
        assert ACTIONS_REQUIRING_HIGHLIGHT.issubset(ACTIONS_REQUIRING_ARTIFACT)
