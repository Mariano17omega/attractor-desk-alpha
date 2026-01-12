"""
Message formatting utilities.
"""

from typing import Union

from langchain_core.messages import AIMessage, BaseMessage

from core.constants import OC_WEB_SEARCH_RESULTS_MESSAGE_KEY
from core.types import SearchResult as WebSearchResult


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


def create_ai_message_from_web_results(
    web_results: list[WebSearchResult],
) -> AIMessage:
    """
    Create a hidden AI message containing formatted web search results.
    """
    web_results_str = []
    for index, result in enumerate(web_results):
        metadata = result.metadata
        published_date = metadata.published_date or "Unknown"
        author = metadata.author or "Unknown"
        title = metadata.title or "Unknown title"
        url = metadata.url or "Unknown URL"
        web_results_str.append(
            (
                f'<search-result index="{index}" publishedDate="{published_date}" '
                f'author="{author}">\n'
                f"  [{title}]({url})\n"
                f"  {result.page_content}\n"
                "</search-result>"
            )
        )

    content = (
        "Here is some additional context I found from searching the web. "
        "This may be useful:\n\n"
        + "\n\n".join(web_results_str)
    )

    return AIMessage(
        content=content,
        additional_kwargs={
            OC_WEB_SEARCH_RESULTS_MESSAGE_KEY: True,
            "webSearchResults": [result.model_dump(by_alias=True) for result in web_results],
            "webSearchStatus": "done",
        },
    )
