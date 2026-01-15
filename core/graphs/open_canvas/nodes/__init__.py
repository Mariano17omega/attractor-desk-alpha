"""Nodes for the Open Canvas graph."""

from core.graphs.open_canvas.nodes.generate_path import generate_path
from core.graphs.open_canvas.nodes.generate_artifact import generate_artifact
from core.graphs.open_canvas.nodes.rewrite_artifact import rewrite_artifact
from core.graphs.open_canvas.nodes.reply_to_general_input import reply_to_general_input
from core.graphs.open_canvas.nodes.generate_followup import generate_followup
from core.graphs.open_canvas.nodes.clean_state import clean_state
from core.graphs.open_canvas.nodes.rewrite_artifact_theme import rewrite_artifact_theme
from core.graphs.open_canvas.nodes.rewrite_code_artifact_theme import rewrite_code_artifact_theme
from core.graphs.open_canvas.nodes.update_artifact import update_artifact
from core.graphs.open_canvas.nodes.update_highlighted_text import update_highlighted_text
from core.graphs.open_canvas.nodes.custom_action import custom_action

from core.graphs.open_canvas.nodes.image_processing import image_processing

__all__ = [
    "generate_path",
    "generate_artifact",
    "rewrite_artifact",
    "reply_to_general_input",
    "generate_followup",
    "clean_state",
    "rewrite_artifact_theme",
    "rewrite_code_artifact_theme",
    "update_artifact",
    "update_highlighted_text",
    "custom_action",
    "image_processing",
]
