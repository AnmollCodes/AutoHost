"""Tests for the Long-Term Memory Store."""

import uuid

import chromadb
import pytest

from agent.memory.memory_store import MemoryStore


@pytest.fixture
def mem_store():
    """Create a fresh in-memory MemoryStore with unique collection for each test."""
    client = chromadb.Client()  # ephemeral, no file locks
    unique_name = f"test_{uuid.uuid4().hex[:8]}"
    store = MemoryStore(client=client, collection_name=unique_name)
    return store


def test_store_returns_id(mem_store):
    """Storing a memory should return a valid UUID string."""
    doc_id = mem_store.store("User likes Python", type="preference")
    assert isinstance(doc_id, str)
    assert len(doc_id) > 0


def test_store_and_retrieve(mem_store):
    """Stored memory should be retrievable by semantic similarity."""
    mem_store.store("User likes Python programming", type="preference")
    results = mem_store.retrieve("What language does user like?", top_k=1)

    assert len(results) > 0
    assert "Python" in results[0]["content"]


def test_retrieve_empty_collection(mem_store):
    """Retrieving from an empty collection should return empty list, not crash."""
    results = mem_store.retrieve("anything")
    assert results == []


def test_retrieve_with_type_filter(mem_store):
    """Type filter should only return memories of that type."""
    mem_store.store("Secret key is 123", type="secret")
    mem_store.store("User prefers dark mode", type="preference")

    results = mem_store.retrieve("dark mode", type_filter="preference")
    assert any("dark mode" in r["content"] for r in results)


def test_metadata_includes_timestamp(mem_store):
    """Stored metadata should include a numeric timestamp."""
    mem_store.store("Test memory", type="knowledge")
    results = mem_store.retrieve("Test memory", top_k=1)

    assert len(results) == 1
    assert "timestamp" in results[0]["metadata"]
    assert isinstance(results[0]["metadata"]["timestamp"], float)


def test_store_custom_metadata(mem_store):
    """Custom metadata should be preserved."""
    mem_store.store(
        "AWS creds at ~/.aws",
        type="knowledge",
        metadata={"category": "cloud"},
    )
    results = mem_store.retrieve("AWS credentials", top_k=1)

    assert len(results) == 1
    assert results[0]["metadata"]["category"] == "cloud"
