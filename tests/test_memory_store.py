"""Tests for in-memory store behavior."""

from core.store.memory_store import InMemoryStore, get_store, reset_store


def test_in_memory_store_put_get_update_delete() -> None:
    store = InMemoryStore()
    store.put(["workspace"], "key", "value")

    result = store.get(["workspace"], "key")
    assert result is not None
    assert result.value == "value"
    assert result.key == "key"
    assert result.namespace == ("workspace",)

    store.put(["workspace"], "key", "new-value")
    updated = store.get(["workspace"], "key")
    assert updated is not None
    assert updated.value == "new-value"
    assert updated.updated_at >= result.updated_at

    assert store.delete(["workspace"], "key") is True
    assert store.delete(["workspace"], "missing") is False


def test_in_memory_store_listing_and_clearing() -> None:
    store = InMemoryStore()
    store.put(["alpha"], "one", 1)
    store.put(["alpha", "beta"], "two", 2)
    store.put(["gamma"], "three", 3)

    assert set(store.list_keys(["alpha"])) == {"one"}
    assert set(store.list_namespaces(prefix=["alpha"])) == {("alpha",), ("alpha", "beta")}

    store.clear_namespace(["alpha"])
    assert store.get(["alpha"], "one") is None
    assert store.list_keys(["alpha"]) == []


def test_global_store_reset() -> None:
    store = get_store()
    store.put(["global"], "key", 123)
    assert store.get(["global"], "key") is not None

    reset_store()
    new_store = get_store()
    assert new_store.get(["global"], "key") is None
