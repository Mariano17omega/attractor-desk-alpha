"""
In-memory store for Open Canvas desktop application.
Provides a simple key-value store compatible with LangGraph's BaseStore interface.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence
from collections import defaultdict


@dataclass
class StoreItem:
    """An item stored in the memory store."""
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, value: Any) -> None:
        """Update the item value."""
        self.value = value
        self.updated_at = datetime.now()


@dataclass
class GetResult:
    """Result from a store get operation."""
    value: Any
    key: str
    namespace: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class InMemoryStore:
    """
    Simple in-memory key-value store for desktop use.
    
    Compatible with LangGraph's store interface but doesn't require
    a separate database or API.
    
    Namespace structure: (namespace_part1, namespace_part2, ...) -> key -> value
    """
    
    def __init__(self):
        # Nested dict: namespace_tuple -> key -> StoreItem
        self._data: dict[tuple[str, ...], dict[str, StoreItem]] = defaultdict(dict)
    
    def _normalize_namespace(self, namespace: Sequence[str]) -> tuple[str, ...]:
        """Convert namespace to tuple for dict key."""
        return tuple(namespace)
    
    def get(
        self,
        namespace: Sequence[str],
        key: str,
    ) -> Optional[GetResult]:
        """
        Get an item from the store.
        
        Args:
            namespace: Namespace path (e.g., ["memories", "assistant_id"])
            key: Item key within namespace
            
        Returns:
            GetResult if found, None otherwise
        """
        ns = self._normalize_namespace(namespace)
        
        if ns not in self._data:
            return None
        
        item = self._data[ns].get(key)
        if item is None:
            return None
        
        return GetResult(
            value=item.value,
            key=key,
            namespace=ns,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
    
    def put(
        self,
        namespace: Sequence[str],
        key: str,
        value: Any,
    ) -> None:
        """
        Store an item.
        
        Args:
            namespace: Namespace path
            key: Item key
            value: Value to store
        """
        ns = self._normalize_namespace(namespace)
        
        existing = self._data[ns].get(key)
        if existing:
            existing.update(value)
        else:
            self._data[ns][key] = StoreItem(value=value)
    
    def delete(
        self,
        namespace: Sequence[str],
        key: str,
    ) -> bool:
        """
        Delete an item from the store.
        
        Args:
            namespace: Namespace path
            key: Item key
            
        Returns:
            True if item was deleted, False if not found
        """
        ns = self._normalize_namespace(namespace)
        
        if ns not in self._data:
            return False
        
        if key in self._data[ns]:
            del self._data[ns][key]
            return True
        
        return False
    
    def list_keys(
        self,
        namespace: Sequence[str],
    ) -> list[str]:
        """
        List all keys in a namespace.
        
        Args:
            namespace: Namespace path
            
        Returns:
            List of keys
        """
        ns = self._normalize_namespace(namespace)
        
        if ns not in self._data:
            return []
        
        return list(self._data[ns].keys())
    
    def list_namespaces(
        self,
        prefix: Optional[Sequence[str]] = None,
    ) -> list[tuple[str, ...]]:
        """
        List all namespaces, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter namespaces
            
        Returns:
            List of namespace tuples
        """
        if prefix is None:
            return list(self._data.keys())
        
        prefix_tuple = self._normalize_namespace(prefix)
        return [
            ns for ns in self._data.keys()
            if ns[:len(prefix_tuple)] == prefix_tuple
        ]
    
    def clear(self) -> None:
        """Clear all data from the store."""
        self._data.clear()
    
    def clear_namespace(self, namespace: Sequence[str]) -> None:
        """Clear all data in a specific namespace."""
        ns = self._normalize_namespace(namespace)
        if ns in self._data:
            del self._data[ns]


# Global store instance
_global_store: Optional[InMemoryStore] = None


def get_store() -> InMemoryStore:
    """Get the global store instance."""
    global _global_store
    if _global_store is None:
        _global_store = InMemoryStore()
    return _global_store


def reset_store() -> None:
    """Reset the global store (useful for testing)."""
    global _global_store
    _global_store = InMemoryStore()
