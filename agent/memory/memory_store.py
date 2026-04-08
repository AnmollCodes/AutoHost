"""Persistent Long-Term Memory using ChromaDB.

Stores embeddings of past tasks, user preferences, and knowledge
so the agent can recall relevant context across sessions.
"""

import os
import time
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Lazy-loaded singleton to avoid import-time crashes
_memory_store_instance = None


class MemoryStore:
    """Persistent Long-Term Memory using ChromaDB.

    Uses ChromaDB's built-in embedding function (all-MiniLM-L6-v2)
    for fast, local-only vector similarity search.
    """

    def __init__(self, persist_dir: str | None = None, client=None, collection_name: str = "autohost_memory"):
        import chromadb

        if client is not None:
            self.client = client
        else:
            if persist_dir is None:
                persist_dir = os.path.join(
                    str(Path.home()), ".autohost", "memory"
                )
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir)

        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )
        logger.info("memory_store_initialized", path=persist_dir or "ephemeral")

    def store(
        self,
        content: str,
        type: str = "knowledge",
        metadata: dict | None = None,
    ) -> str:
        """Store a new memory and return its ID."""
        doc_id = str(uuid.uuid4())
        meta = {"timestamp": time.time(), "type": type}
        if metadata:
            meta.update(metadata)

        self.collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )
        logger.info("memory_stored", type=type, id=doc_id)
        return doc_id

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        type_filter: str | None = None,
    ) -> list[dict]:
        """Retrieve the top-k most relevant memories for a query."""
        try:
            where_filter = {"type": type_filter} if type_filter else None
            n = min(top_k, self.collection.count())
            if n == 0:
                return []
            results = self.collection.query(
                query_texts=[query],
                n_results=n,
                where=where_filter,
            )
            memories = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = (
                        results["metadatas"][0][i]
                        if results["metadatas"]
                        else {}
                    )
                    memories.append({"content": doc, "metadata": meta})
            return memories
        except Exception as e:
            logger.error("memory_retrieve_error", error=str(e))
            return []


def get_memory_store() -> MemoryStore:
    """Get or create the global MemoryStore singleton (lazy)."""
    global _memory_store_instance
    if _memory_store_instance is None:
        try:
            _memory_store_instance = MemoryStore()
        except Exception as e:
            logger.error("memory_store_init_failed", error=str(e))
            return None
    return _memory_store_instance
