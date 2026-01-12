"""
LangSmith tracing integration for Open Canvas.
"""

import os
from typing import Optional

from core.config import get_langsmith_api_key, is_langsmith_enabled


def setup_langsmith_tracing(
    project_name: str = "open-canvas-py",
    enabled: Optional[bool] = None,
) -> bool:
    """
    Set up LangSmith tracing if API key is available.
    
    Args:
        project_name: Name of the LangSmith project
        enabled: Force enable/disable. If None, auto-detect from config.
        
    Returns:
        True if tracing was enabled, False otherwise
    """
    if enabled is False:
        _disable_tracing()
        return False
    
    if enabled is None and not is_langsmith_enabled():
        return False
    
    api_key = get_langsmith_api_key()
    if not api_key:
        return False
    
    # Set environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    print(f"LangSmith tracing enabled for project: {project_name}")
    return True


def _disable_tracing() -> None:
    """Disable LangSmith tracing."""
    os.environ.pop("LANGCHAIN_TRACING_V2", None)
    os.environ.pop("LANGCHAIN_API_KEY", None)


def get_run_url(run_id: str) -> str:
    """Get the LangSmith URL for a specific run."""
    project = os.environ.get("LANGCHAIN_PROJECT", "open-canvas-py")
    return f"https://smith.langchain.com/o/default/projects/p/{project}/r/{run_id}"
