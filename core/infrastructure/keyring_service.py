"""
Secure credential storage using OS keyring.

Provides cross-platform secure storage for API keys using the system's
credential manager (GNOME Keyring, macOS Keychain, Windows Credential Locker).
"""

import logging
import os
import warnings
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class KeyringService:
    """
    Secure credential storage using OS keyring.
    
    Provides unified interface for storing and retrieving API keys
    in the operating system's secure credential vault.
    """
    
    SERVICE_NAME = "attractor_desk"
    
    CREDENTIAL_NAMES = {
        "openrouter": "openrouter_api_key",
        "exa": "exa_api_key",
        "firecrawl": "firecrawl_api_key",
        # Note: LangSmith is excluded - it's a dev-only tool that reads from API_KEY.txt/env
    }
    
    # Environment variable names for fallback
    ENV_VAR_NAMES = {
        "openrouter": "OPENROUTER_API_KEY",
        "exa": "EXA_API_KEY",
        "firecrawl": "FIRECRAWL_API_KEY",
        # Note: LangSmith excluded - not stored in keyring
    }
    
    def __init__(self) -> None:
        """Initialize KeyringService and check availability."""
        self._available: Optional[bool] = None
        self._keyring_module = None
    
    @property
    def is_available(self) -> bool:
        """
        Check if keyring backend is available.
        
        Returns:
            True if keyring can be used, False otherwise.
        """
        if self._available is not None:
            return self._available
        
        try:
            import keyring
            from keyring.backends.fail import Keyring as FailKeyring
            
            self._keyring_module = keyring
            
            # Check if we have a working backend (not FailKeyring)
            backend = keyring.get_keyring()
            if isinstance(backend, FailKeyring):
                logger.warning(
                    "No secure keyring backend available. "
                    "Consider installing a backend like 'keyrings.alt' for headless environments."
                )
                self._available = False
            else:
                logger.debug(f"Using keyring backend: {type(backend).__name__}")
                self._available = True
        except ImportError:
            logger.warning("keyring library not installed")
            self._available = False
        except Exception as e:
            logger.warning(f"Failed to initialize keyring: {e}")
            self._available = False
        
        return self._available
    
    def _get_keyring(self):
        """Get the keyring module, importing if needed."""
        if self._keyring_module is not None:
            return self._keyring_module
        
        if self.is_available:
            return self._keyring_module
        return None
    
    def _get_credential_name(self, name: str) -> str:
        """
        Get the full credential name for storage.
        
        Args:
            name: Short name (e.g., 'openrouter') or full name
            
        Returns:
            Full credential name for keyring storage
        """
        return self.CREDENTIAL_NAMES.get(name.lower(), name)
    
    def store_credential(self, name: str, value: str) -> bool:
        """
        Store a credential in the keyring.
        
        Args:
            name: Credential name (e.g., 'openrouter' or 'openrouter_api_key')
            value: The credential value to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.is_available:
            logger.warning("Keyring not available, cannot store credential")
            return False
        
        try:
            keyring = self._get_keyring()
            credential_name = self._get_credential_name(name)
            keyring.set_password(self.SERVICE_NAME, credential_name, value)
            logger.debug(f"Stored credential: {credential_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential {name}: {e}")
            return False
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Retrieve a credential from the keyring.
        
        Falls back to environment variables if keyring is unavailable.
        
        Args:
            name: Credential name (e.g., 'openrouter' or 'openrouter_api_key')
            
        Returns:
            The credential value, or None if not found
        """
        credential_name = self._get_credential_name(name)
        
        # Try keyring first
        if self.is_available:
            try:
                keyring = self._get_keyring()
                value = keyring.get_password(self.SERVICE_NAME, credential_name)
                if value:
                    return value
            except Exception as e:
                logger.warning(f"Failed to get credential from keyring: {e}")
        
        # Fall back to environment variable
        normalized_name = name.lower()
        env_var = self.ENV_VAR_NAMES.get(normalized_name)
        if env_var:
            value = os.environ.get(env_var)
            if value:
                logger.debug(f"Using {env_var} from environment")
                return value
        
        return None
    
    def delete_credential(self, name: str) -> bool:
        """
        Delete a credential from the keyring.
        
        Args:
            name: Credential name to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            keyring = self._get_keyring()
            credential_name = self._get_credential_name(name)
            keyring.delete_password(self.SERVICE_NAME, credential_name)
            logger.debug(f"Deleted credential: {credential_name}")
            return True
        except Exception as e:
            # keyring raises PasswordDeleteError if not found
            logger.debug(f"Could not delete credential {name}: {e}")
            return False
    
    def has_credential(self, name: str) -> bool:
        """
        Check if a credential exists in the keyring.
        
        Args:
            name: Credential name to check
            
        Returns:
            True if credential exists, False otherwise
        """
        return self.get_credential(name) is not None
    
    def migrate_from_file(self, file_path: Path) -> dict[str, bool]:
        """
        Migrate credentials from a legacy API_KEY.txt file to keyring.
        
        Args:
            file_path: Path to the API_KEY.txt file
            
        Returns:
            Dictionary mapping credential names to migration success (True/False)
        """
        results: dict[str, bool] = {}
        
        if not file_path.exists():
            logger.info(f"No legacy file found at {file_path}")
            return results
        
        if not self.is_available:
            logger.warning("Keyring not available, cannot migrate credentials")
            return results
        
        # Parse the file
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue
                    
                    if "=" not in line:
                        continue
                    
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Map file key names to our credential names
                    # Note: LANGSMITH_API_KEY excluded - dev-only, stays in API_KEY.txt
                    key_mapping = {
                        "OPENROUTER_API_KEY": "openrouter",
                        "EXA_API_KEY": "exa",
                        "FIRECRAWL_API_KEY": "firecrawl",
                    }
                    
                    credential_name = key_mapping.get(key)
                    if credential_name and value:
                        # Only migrate if not already in keyring
                        if not self.has_credential(credential_name):
                            success = self.store_credential(credential_name, value)
                            results[credential_name] = success
                            if success:
                                logger.info(f"Migrated {key} to keyring")
                        else:
                            logger.debug(f"Credential {credential_name} already in keyring, skipping")
                            results[credential_name] = True
        
        except Exception as e:
            logger.error(f"Failed to migrate from {file_path}: {e}")
        
        return results
    
    def get_all_credentials(self) -> dict[str, Optional[str]]:
        """
        Get all known credentials.
        
        Returns:
            Dictionary mapping credential names to their values (or None if not set)
        """
        return {
            name: self.get_credential(name)
            for name in self.CREDENTIAL_NAMES
        }
    
    def has_any_credentials(self) -> bool:
        """Check if any credentials are stored."""
        return any(self.has_credential(name) for name in self.CREDENTIAL_NAMES)


# Global singleton instance
_keyring_service: Optional[KeyringService] = None


def get_keyring_service() -> KeyringService:
    """
    Get the global KeyringService instance.
    
    Returns:
        The shared KeyringService instance
    """
    global _keyring_service
    if _keyring_service is None:
        _keyring_service = KeyringService()
    return _keyring_service
