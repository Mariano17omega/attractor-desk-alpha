"""
Artifact utility functions.
Matches the original TypeScript utils/artifacts.ts.
"""

from typing import Union

from core.types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3


def is_artifact_code_content(content: object) -> bool:
    """Check if content is a code artifact."""
    if not isinstance(content, dict) and not hasattr(content, "type"):
        return False
    
    content_type = content.get("type") if isinstance(content, dict) else getattr(content, "type", None)
    return content_type == "code"


def is_artifact_markdown_content(content: object) -> bool:
    """Check if content is a markdown/text artifact."""
    if not isinstance(content, dict) and not hasattr(content, "type"):
        return False
    
    content_type = content.get("type") if isinstance(content, dict) else getattr(content, "type", None)
    return content_type == "text"


def get_artifact_content(
    artifact: ArtifactV3,
) -> Union[ArtifactCodeV3, ArtifactMarkdownV3]:
    """
    Get the current content from an artifact.
    
    Args:
        artifact: The artifact container
        
    Returns:
        The current artifact content
        
    Raises:
        ValueError: If no artifact is provided
    """
    if not artifact:
        raise ValueError("No artifact found.")
    
    # Find content matching current index
    current_content = None
    for content in artifact.contents:
        if content.index == artifact.current_index:
            current_content = content
            break
    
    # Fallback to last content if not found
    if not current_content:
        current_content = artifact.contents[-1]
    
    return current_content


def format_artifact_content(
    content: Union[ArtifactCodeV3, ArtifactMarkdownV3],
    shorten_content: bool = False,
) -> str:
    """
    Format artifact content for display in prompts.
    
    Args:
        content: The artifact content
        shorten_content: Whether to truncate to 500 chars
        
    Returns:
        Formatted string representation
    """
    if is_artifact_code_content(content):
        artifact_text = content.code if hasattr(content, "code") else content.get("code", "")
    else:
        artifact_text = content.full_markdown if hasattr(content, "full_markdown") else content.get("fullMarkdown", "")
    
    if shorten_content and len(artifact_text) > 500:
        artifact_text = artifact_text[:500]
    
    title = content.title if hasattr(content, "title") else content.get("title", "")
    content_type = content.type if hasattr(content, "type") else content.get("type", "")
    
    return f"Title: {title}\nArtifact type: {content_type}\nContent: {artifact_text}"


def format_artifact_content_with_template(
    template: str,
    content: Union[ArtifactCodeV3, ArtifactMarkdownV3],
    shorten_content: bool = False,
) -> str:
    """
    Format artifact content using a template.
    
    Args:
        template: Template string with {artifact} placeholder
        content: The artifact content
        shorten_content: Whether to truncate content
        
    Returns:
        Formatted template string
    """
    formatted = format_artifact_content(content, shorten_content)
    return template.replace("{artifact}", formatted)
