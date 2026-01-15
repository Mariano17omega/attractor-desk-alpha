"""
Unit tests for KeyringService.

Tests credential storage using mocked keyring backend.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


class TestKeyringService:
    """Tests for KeyringService class."""
    
    @pytest.fixture
    def mock_keyring(self):
        """Mock keyring module."""
        with patch("core.infrastructure.keyring_service.KeyringService._get_keyring") as mock:
            keyring_mock = MagicMock()
            mock.return_value = keyring_mock
            # Storage for mocked credentials
            keyring_mock._storage = {}
            
            def get_password(service, name):
                return keyring_mock._storage.get((service, name))
            
            def set_password(service, name, value):
                keyring_mock._storage[(service, name)] = value
            
            def delete_password(service, name):
                if (service, name) in keyring_mock._storage:
                    del keyring_mock._storage[(service, name)]
                else:
                    raise Exception("Password not found")
            
            keyring_mock.get_password = get_password
            keyring_mock.set_password = set_password
            keyring_mock.delete_password = delete_password
            
            yield keyring_mock
    
    @pytest.fixture
    def service(self, mock_keyring):
        """Create a KeyringService with mocked backend."""
        from core.infrastructure.keyring_service import KeyringService
        svc = KeyringService()
        svc._available = True
        svc._keyring_module = mock_keyring
        return svc
    
    def test_store_and_get_credential(self, service):
        """Test storing and retrieving a credential."""
        assert service.store_credential("openrouter", "test-key-123")
        assert service.get_credential("openrouter") == "test-key-123"
    
    def test_get_credential_not_found(self, service):
        """Test getting a non-existent credential."""
        assert service.get_credential("openrouter") is None
    
    def test_has_credential(self, service):
        """Test checking credential existence."""
        assert not service.has_credential("openrouter")
        service.store_credential("openrouter", "test-key")
        assert service.has_credential("openrouter")
    
    def test_delete_credential(self, service):
        """Test deleting a credential."""
        service.store_credential("openrouter", "test-key")
        assert service.has_credential("openrouter")
        assert service.delete_credential("openrouter")
        assert not service.has_credential("openrouter")
    
    def test_delete_nonexistent_credential(self, service):
        """Test deleting a credential that doesn't exist."""
        assert not service.delete_credential("openrouter")
    
    def test_credential_name_normalization(self, service):
        """Test that credential names are normalized."""
        service.store_credential("openrouter", "key1")
        service.store_credential("OPENROUTER", "key2")  # Should overwrite
        assert service.get_credential("openrouter") == "key2"
    
    def test_env_var_fallback(self, service):
        """Test environment variable fallback when keyring is unavailable."""
        service._available = False
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-123"}):
            assert service.get_credential("openrouter") == "env-key-123"
    
    def test_env_var_used_when_keyring_empty(self, service):
        """Test that env var is used when key not in keyring."""
        # Keyring available but key not set
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-456"}):
            assert service.get_credential("openrouter") == "env-key-456"
    
    def test_keyring_takes_precedence_over_env(self, service):
        """Test that keyring value takes precedence over env var."""
        service.store_credential("openrouter", "keyring-key")
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}):
            assert service.get_credential("openrouter") == "keyring-key"
    
    def test_get_all_credentials(self, service):
        """Test getting all credentials."""
        service.store_credential("openrouter", "key1")
        service.store_credential("exa", "key2")
        
        all_creds = service.get_all_credentials()
        assert all_creds["openrouter"] == "key1"
        assert all_creds["exa"] == "key2"
        assert all_creds["firecrawl"] is None
        # Note: langsmith is not in keyring storage (dev-only, uses API_KEY.txt)
    
    def test_has_any_credentials(self, service):
        """Test checking if any credentials exist."""
        assert not service.has_any_credentials()
        service.store_credential("openrouter", "key")
        assert service.has_any_credentials()


class TestKeyringServiceMigration:
    """Tests for migrate_from_file functionality."""
    
    @pytest.fixture
    def mock_keyring(self):
        """Mock keyring module for migration tests."""
        with patch("core.infrastructure.keyring_service.KeyringService._get_keyring") as mock:
            keyring_mock = MagicMock()
            mock.return_value = keyring_mock
            keyring_mock._storage = {}
            
            def get_password(service, name):
                return keyring_mock._storage.get((service, name))
            
            def set_password(service, name, value):
                keyring_mock._storage[(service, name)] = value
            
            keyring_mock.get_password = get_password
            keyring_mock.set_password = set_password
            
            yield keyring_mock
    
    @pytest.fixture
    def service(self, mock_keyring):
        """Create a KeyringService with mocked backend."""
        from core.infrastructure.keyring_service import KeyringService
        svc = KeyringService()
        svc._available = True
        svc._keyring_module = mock_keyring
        return svc
    
    def test_migrate_from_file(self, service, tmp_path):
        """Test migrating credentials from API_KEY.txt."""
        api_key_file = tmp_path / "API_KEY.txt"
        api_key_file.write_text("""
# API Keys file
OPENROUTER_API_KEY=sk-openrouter-123
EXA_API_KEY="exa-456"
FIRECRAWL_API_KEY='fc-789'
""")
        
        results = service.migrate_from_file(api_key_file)
        
        assert results["openrouter"] is True
        assert results["exa"] is True
        assert results["firecrawl"] is True
        
        assert service.get_credential("openrouter") == "sk-openrouter-123"
        assert service.get_credential("exa") == "exa-456"
        assert service.get_credential("firecrawl") == "fc-789"
    
    def test_migrate_skips_existing(self, service, tmp_path):
        """Test that migration doesn't overwrite existing credentials."""
        # Pre-store a credential
        service.store_credential("openrouter", "existing-key")
        
        api_key_file = tmp_path / "API_KEY.txt"
        api_key_file.write_text("OPENROUTER_API_KEY=new-key")
        
        results = service.migrate_from_file(api_key_file)
        
        # Should be marked as success but value unchanged
        assert results["openrouter"] is True
        assert service.get_credential("openrouter") == "existing-key"
    
    def test_migrate_nonexistent_file(self, service, tmp_path):
        """Test migrating from a file that doesn't exist."""
        results = service.migrate_from_file(tmp_path / "nonexistent.txt")
        assert results == {}
    
    def test_migrate_empty_file(self, service, tmp_path):
        """Test migrating from an empty file."""
        api_key_file = tmp_path / "API_KEY.txt"
        api_key_file.write_text("")
        
        results = service.migrate_from_file(api_key_file)
        assert results == {}
    
    def test_migrate_ignores_unknown_keys(self, service, tmp_path):
        """Test that unknown keys are not migrated."""
        api_key_file = tmp_path / "API_KEY.txt"
        api_key_file.write_text("UNKNOWN_KEY=value123")
        
        results = service.migrate_from_file(api_key_file)
        assert "unknown" not in results


class TestKeyringAvailability:
    """Tests for keyring availability detection."""
    
    def test_unavailable_when_import_fails(self):
        """Test that service handles missing keyring lib gracefully."""
        from core.infrastructure.keyring_service import KeyringService
        
        with patch.dict("sys.modules", {"keyring": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                svc = KeyringService()
                svc._available = None  # Reset cached value
                # Force re-check
                with patch("core.infrastructure.keyring_service.KeyringService.is_available", False):
                    assert not svc.store_credential("test", "value")
    
    def test_store_fails_gracefully_when_unavailable(self):
        """Test that store_credential fails gracefully when keyring unavailable."""
        from core.infrastructure.keyring_service import KeyringService
        
        svc = KeyringService()
        svc._available = False
        
        assert not svc.store_credential("openrouter", "key")
    
    def test_delete_fails_gracefully_when_unavailable(self):
        """Test that delete_credential fails gracefully when keyring unavailable."""
        from core.infrastructure.keyring_service import KeyringService
        
        svc = KeyringService()
        svc._available = False
        
        assert not svc.delete_credential("openrouter")
