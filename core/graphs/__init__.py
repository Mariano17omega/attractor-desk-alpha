"""Graphs package for Open Canvas."""

# Import individual graphs
from core.graphs.open_canvas import graph as open_canvas_graph
from core.graphs.open_canvas.state import OpenCanvasState

__all__ = [
    "open_canvas_graph",
    "OpenCanvasState",
]
