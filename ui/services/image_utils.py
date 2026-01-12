"""Image helper utilities."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path


def file_path_to_data_url(path: str | Path) -> str:
    """Convert an image file into a data URL for multimodal prompts."""
    path_obj = Path(path)
    image_bytes = path_obj.read_bytes()
    mime_type, _ = mimetypes.guess_type(path_obj.name)
    mime_type = mime_type or "image/png"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
