"""Keyring service for secure credential storage."""

from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class KeyringService:
    """Service for secure storage of sensitive credentials using system keyring."""
    
    SERVICE_NAME = "attractor_desk"
    API_KEY_ACCOUNT = "openrouter_api_key"
    
    def __init__(self):
        """Initialize the keyring service."""
        self._available = KEYRING_AVAILABLE
        if not self._available:
            import warnings
            warnings.warn(
                "keyring library not available. API keys will not be stored securely.",
                RuntimeWarning,
            )
    
    @property
    def is_available(self) -> bool:
        """Check if keyring is available."""
        return self._available
    
    def store_api_key(self, api_key: str) -> bool:
        """Store the API key securely.
        
        Args:
            api_key: The API key to store.
            
        Returns:
            True if stored successfully, False otherwise.
        """
        if not self._available:
            return False
        try:
            keyring.set_password(self.SERVICE_NAME, self.API_KEY_ACCOUNT, api_key)
            return True
        except Exception:
            return False
    
    def get_api_key(self) -> Optional[str]:
        """Retrieve the stored API key.
        
        Returns:
            The API key if found, None otherwise.
        """
        if not self._available:
            return None
        try:
            return keyring.get_password(self.SERVICE_NAME, self.API_KEY_ACCOUNT)
        except Exception:
            return None
    
    def delete_api_key(self) -> bool:
        """Delete the stored API key.
        
        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self._available:
            return False
        try:
            keyring.delete_password(self.SERVICE_NAME, self.API_KEY_ACCOUNT)
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception:
            return False
    
    def has_api_key(self) -> bool:
        """Check if an API key is stored.
        
        Returns:
            True if an API key exists.
        """
        return self.get_api_key() is not None
