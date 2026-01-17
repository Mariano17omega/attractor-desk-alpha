"""
Configuration loader for Attractor Desk.

Loads API keys and settings using a priority chain:
1. OS keyring (secure storage)
2. Environment variables (CI/CD support)
3. Legacy API_KEY.txt file (migration, deprecated)
"""

import logging
import os
import warnings
from pathlib import Path
from typing import Optional

from core.infrastructure.keyring_service import KeyringService, get_keyring_service

# Global configuration storage
_config: dict[str, str] = {}
_config_loaded: bool = False
_keyring_service: Optional[KeyringService] = None
logger = logging.getLogger(__name__)


def _get_keyring() -> KeyringService:
    """Get the keyring service instance."""
    global _keyring_service
    if _keyring_service is None:
        _keyring_service = get_keyring_service()
    return _keyring_service


def get_config_path() -> Path:
    """Get the path to the API_KEY.txt file."""
    module_dir = Path(__file__).parent.parent
    return module_dir / "API_KEY.txt"


def load_config(config_path: Optional[Path] = None) -> dict[str, str]:
    """
    Load configuration from API_KEY.txt file.
    
    DEPRECATED: This function is for backwards compatibility only.
    Use get_openrouter_api_key(), get_exa_api_key(), etc. instead.
    
    Format: KEY=VALUE, one per line
    Lines starting with # are comments
    Empty lines are ignored
    
    Args:
        config_path: Optional path to config file. Defaults to API_KEY.txt
        
    Returns:
        Dictionary of configuration values
    """
    global _config, _config_loaded
    
    if _config_loaded and config_path is None:
        return _config
    
    path = config_path or get_config_path()
    
    # First, try to get keys from keyring
    keyring = _get_keyring()
    config = {}
    
    # Load from keyring if available
    if keyring.is_available:
        all_creds = keyring.get_all_credentials()
        if all_creds.get("openrouter"):
            config["OPENROUTER_API_KEY"] = all_creds["openrouter"]
        if all_creds.get("exa"):
            config["EXA_API_KEY"] = all_creds["exa"]
        if all_creds.get("firecrawl"):
            config["FIRECRAWL_API_KEY"] = all_creds["firecrawl"]
        if all_creds.get("langsmith"):
            config["LANGSMITH_API_KEY"] = all_creds["langsmith"]
    
    # Supplement with environment variables
    env_config = _load_from_env()
    for key, value in env_config.items():
        if key not in config:
            config[key] = value
    
    # If we still don't have keys, try the legacy file
    if not config and path.exists():
        warnings.warn(
            f"Loading API keys from {path} is deprecated. "
            "Please migrate to OS keyring storage via Settings.",
            DeprecationWarning,
            stacklevel=2
        )
        file_config = _load_from_file(path)
        config.update(file_config)
    
    _config = config
    _config_loaded = True
    
    # Validate if we have any keys
    if config:
        _validate_config(config)
    
    return config


def _load_from_file(path: Path) -> dict[str, str]:
    """Load configuration from a file."""
    config = {}
    
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Parse KEY=VALUE
            if "=" not in line:
                logger.warning("Invalid line %s in %s: %s", line_num, path, line)
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
        # Don't raise, just warn - the user might set keys via settings UI
        logger.warning("Missing API keys: %s", ", ".join(missing_required))
        logger.info("You can configure these in Settings.")
    
    missing_optional = [k for k in optional_keys if k not in config]
    if missing_optional:
        logger.info("Optional keys not configured: %s", ", ".join(missing_optional))


def get_api_key(key_name: str) -> Optional[str]:
    """
    Get a specific API key from configuration.
    
    Priority: keyring → env var → legacy file
    
    Args:
        key_name: Name of the key (e.g., "OPENROUTER_API_KEY")
        
    Returns:
        The API key value, or None if not found
    """
    keyring = _get_keyring()
    
    # Map key names to credential names (excludes LangSmith - dev-only)
    key_mapping = {
        "OPENROUTER_API_KEY": "openrouter",
        "EXA_API_KEY": "exa",
        "FIRECRAWL_API_KEY": "firecrawl",
    }
    
    credential_name = key_mapping.get(key_name)
    
    # Try keyring first (includes env var fallback)
    if credential_name:
        value = keyring.get_credential(credential_name)
        if value:
            return value
    
    # Also check env var directly for key_name
    env_value = os.environ.get(key_name)
    if env_value:
        return env_value
    
    # Last resort: legacy file
    config_path = get_config_path()
    if config_path.exists():
        try:
            file_config = _load_from_file(config_path)
            if key_name in file_config:
                warnings.warn(
                    f"Reading {key_name} from API_KEY.txt is deprecated. "
                    "Please migrate to OS keyring storage via Settings.",
                    DeprecationWarning,
                    stacklevel=3
                )
                return file_config[key_name]
        except Exception:
            pass
    
    return None


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
            "Please configure it in Settings or set the environment variable."
        )
    return key


def get_langsmith_api_key() -> Optional[str]:
    """
    Get the LangSmith API key (optional, dev-only).
    
    Note: LangSmith is intentionally NOT stored in keyring.
    It reads from environment variable or API_KEY.txt only.
    """
    # Check environment variable first
    env_value = os.environ.get("LANGSMITH_API_KEY")
    if env_value:
        return env_value
    
    # Fall back to API_KEY.txt (no deprecation warning for LangSmith)
    config_path = get_config_path()
    if config_path.exists():
        try:
            file_config = _load_from_file(config_path)
            return file_config.get("LANGSMITH_API_KEY")
        except Exception:
            pass
    
    return None


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


def store_api_key(key_name: str, value: str) -> bool:
    """
    Store an API key in the keyring.
    
    Args:
        key_name: Name of the key (e.g., "OPENROUTER_API_KEY" or "openrouter")
        value: The API key value to store
        
    Returns:
        True if stored successfully, False otherwise
    """
    keyring = _get_keyring()
    
    # Normalize key name
    key_mapping = {
        "OPENROUTER_API_KEY": "openrouter",
        "EXA_API_KEY": "exa",
        "FIRECRAWL_API_KEY": "firecrawl",
        "LANGSMITH_API_KEY": "langsmith",
    }
    
    credential_name = key_mapping.get(key_name, key_name.lower())
    return keyring.store_credential(credential_name, value)


def clear_config_cache() -> None:
    """Clear the cached configuration. Useful for testing."""
    global _config, _config_loaded
    _config = {}
    _config_loaded = False
