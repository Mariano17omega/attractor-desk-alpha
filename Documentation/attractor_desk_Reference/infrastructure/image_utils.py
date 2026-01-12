"""Image utility functions for screen capture processing."""

import base64
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage


def resize_image(image: QImage, max_side: int = 1280) -> QImage:
    """Resize an image to fit within max_side while maintaining aspect ratio.

    Args:
        image: The QImage to resize.
        max_side: Maximum dimension for the longest side.

    Returns:
        Resized QImage (or original if already smaller).
    """
    width = image.width()
    height = image.height()

    if width <= max_side and height <= max_side:
        return image

    if width > height:
        new_width = max_side
        new_height = int(height * (max_side / width))
    else:
        new_height = max_side
        new_width = int(width * (max_side / height))

    return image.scaled(
        new_width,
        new_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def save_image_png(image: QImage, path: Path) -> int:
    """Save a QImage as PNG to disk.

    Args:
        image: The QImage to save.
        path: Destination path.

    Returns:
        File size in bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path), "PNG")
    return path.stat().st_size


def load_image(path: Path) -> QImage:
    """Load an image from disk.

    Args:
        path: Path to the image file.

    Returns:
        Loaded QImage.

    Raises:
        FileNotFoundError: If image file doesn't exist.
        ValueError: If image cannot be loaded.
    """
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    image = QImage(str(path))
    if image.isNull():
        raise ValueError(f"Failed to load image: {path}")

    return image


def image_to_base64(image: QImage, format: str = "PNG") -> str:
    """Convert a QImage to a base64-encoded data URI.

    Args:
        image: The QImage to convert.
        format: Image format (PNG, JPEG, etc.).

    Returns:
        Base64 data URI string (e.g., "data:image/png;base64,...").
    """
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, format)
    buffer.close()

    data = buffer.data().toBase64().data().decode("utf-8")
    mime_type = f"image/{format.lower()}"

    return f"data:{mime_type};base64,{data}"


def get_image_dimensions(image: QImage) -> Tuple[int, int]:
    """Get the dimensions of an image.

    Args:
        image: The QImage.

    Returns:
        Tuple of (width, height).
    """
    return image.width(), image.height()


def image_from_bytes(data: bytes) -> QImage:
    """Create a QImage from raw bytes.

    Args:
        data: Image data bytes.

    Returns:
        QImage loaded from the data.
    """
    image = QImage()
    image.loadFromData(data)
    return image
