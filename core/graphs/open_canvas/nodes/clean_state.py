"""
Clean state node - resets transient state fields.
"""

from core.graphs.open_canvas.state import OpenCanvasState, OpenCanvasReturnType
from core.constants import DEFAULT_INPUTS


async def clean_state(state: OpenCanvasState) -> OpenCanvasReturnType:
    """
    Reset transient state fields to their default values.
    """
    return {
        **DEFAULT_INPUTS,
    }
