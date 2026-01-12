"""
Configuration loader for Open Canvas.
Loads API keys and settings from API_KEY.txt file.
"""

import os
from pathlib import Path
from typing import Optional

# Global configuration storage
_config: dict[str, str] = {}
_config_loaded: bool = False


def get_config_path() -> Path:
    """Get the path to the API_KEY.txt file."""
    # Look in the open-canvas-py directory
    module_dir = Path(__file__).parent.parent
    return module_dir / "API_KEY.txt"


def load_config(config_path: Optional[Path] = None) -> dict[str, str]:
    """
    Load configuration from API_KEY.txt file.
    
    Format: KEY=VALUE, one per line
    Lines starting with # are comments
    Empty lines are ignored
    
    Args:
        config_path: Optional path to config file. Defaults to API_KEY.txt
        
    Returns:
        Dictionary of configuration values
        
    Raises:
        FileNotFoundError: If config file doesn't exist and no env fallback
    """
    global _config, _config_loaded
    
    if _config_loaded and config_path is None:
        return _config
    
    path = config_path or get_config_path()
    
    if not path.exists():
        # Try environment variables as fallback
        _config = _load_from_env()
        if not _config:
            raise FileNotFoundError(
                f"Configuration file not found: {path}\n"
                f"Please create {path} with your API keys.\n"
                f"See API_KEY.txt.example for format."
            )
        _config_loaded = True
        return _config
    
    config = {}
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Parse KEY=VALUE
            if "=" not in line:
                print(f"Warning: Invalid line {line_num} in {path}: {line}")
                continue
                
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            config[key] = value
    
    _config = config
    _config_loaded = True
    
    # Validate required keys
    _validate_config(config)
    
    return config


def _load_from_env() -> dict[str, str]:
    """Load configuration from environment variables as fallback."""
    env_keys = [
        "OPENROUTER_API_KEY",
        "LANGSMITH_API_KEY",
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
    ]
    
    config = {}
    for key in env_keys:
        value = os.environ.get(key)
        if value:
            config[key] = value
    
    return config


def _validate_config(config: dict[str, str]) -> None:
    """
    Validate that required configuration is present.
    Logs warnings for optional missing keys.
    """
    required_keys = ["OPENROUTER_API_KEY"]
    optional_keys = ["LANGSMITH_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY"]
    
    missing_required = [k for k in required_keys if k not in config]
    if missing_required:
        raise ValueError(
            f"Missing required configuration keys: {', '.join(missing_required)}\n"
            f"Please add them to API_KEY.txt"
        )
    
    missing_optional = [k for k in optional_keys if k not in config]
    if missing_optional:
        print(f"Note: Optional keys not configured: {', '.join(missing_optional)}")


def get_api_key(key_name: str) -> Optional[str]:
    """
    Get a specific API key from configuration.
    
    Args:
        key_name: Name of the key (e.g., "OPENROUTER_API_KEY")
        
    Returns:
        The API key value, or None if not found
    """
    if not _config_loaded:
        try:
            load_config()
        except FileNotFoundError:
            return None
    
    return _config.get(key_name)


def get_openrouter_api_key() -> str:
    """
    Get the OpenRouter API key.
    
    Returns:
        The OpenRouter API key
        
    Raises:
        ValueError: If key is not configured
    """
    key = get_api_key("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY not configured. "
            "Please add it to API_KEY.txt"
        )
    return key


def get_langsmith_api_key() -> Optional[str]:
    """Get the LangSmith API key (optional)."""
    return get_api_key("LANGSMITH_API_KEY")


def get_exa_api_key() -> Optional[str]:
    """Get the Exa API key (optional)."""
    return get_api_key("EXA_API_KEY")


def get_firecrawl_api_key() -> Optional[str]:
    """Get the FireCrawl API key (optional)."""
    return get_api_key("FIRECRAWL_API_KEY")


def is_langsmith_enabled() -> bool:
    """Check if LangSmith tracing is enabled."""
    return get_langsmith_api_key() is not None


def is_web_search_enabled() -> bool:
    """Check if web search is available (Exa configured)."""
    return get_exa_api_key() is not None


def is_firecrawl_enabled() -> bool:
    """Check if FireCrawl scraping is available."""
    return get_firecrawl_api_key() is not None
