"""
Message formatting utilities.
"""

from typing import Union
from langchain_core.messages import BaseMessage


def format_messages(messages: list[BaseMessage]) -> str:
    """
    Format a list of messages for prompt injection.
    
    Args:
        messages: List of LangChain messages
        
    Returns:
        Formatted string with XML-like tags
    """
    formatted = []
    for idx, msg in enumerate(messages):
        msg_type = msg.type if hasattr(msg, "type") else "unknown"
        
        # Get content as string
        content = msg.content
        if not isinstance(content, str):
            # Handle complex content (list of dicts)
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
            content = "\n".join(text_parts)
        
        formatted.append(f'<{msg_type} index="{idx}">\n{content}\n</{msg_type}>')
    
    return "\n".join(formatted)


def get_string_from_content(content: Union[str, list]) -> str:
    """
    Extract string content from message content.
    
    Args:
        content: String or list of content parts
        
    Returns:
        Extracted string content
    """
    if isinstance(content, str):
        return content
    
    text_parts = []
    for part in content:
        if isinstance(part, dict) and "text" in part:
            text_parts.append(part["text"])
    
    return "\n".join(text_parts)
