"""Long-term agent memory backed by lightweight vector embeddings."""

from __future__ import annotations

import hashlib
import math
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

EMBEDDING_DIMENSION = 256
MAX_ENTRIES = 5000
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _local_embedding(text: str, dimension: int) -> list[float]:
    """Deterministic hashed bag-of-tokens embedding used when no API key is set."""
    tokens = _TOKEN_RE.findall(text.lower())
    grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    vector = [0.0] * dimension
    for gram in grams:
        digest = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        vector[digest % dimension] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class MemoryStore:
    """Stores agent experiences as embedded entries and supports semantic search."""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _embed(self, text: str) -> list[float]:
        if os.environ.get("OPENAI_API_KEY"):
            try:
                from openai import OpenAI

                client = OpenAI()
                response = client.embeddings.create(model="text-embedding-3-small", input=text[:8000])
                return list(response.data[0].embedding)
            except Exception:
                pass
        return _local_embedding(text, self.dimension)

    @staticmethod
    def _public(entry: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in entry.items() if key != "embedding"}

    def store(self, agent_id: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Embed and persist a memory for an agent."""
        entry = {
            "id": uuid.uuid4().hex,
            "agent_id": agent_id,
            "content": content,
            "metadata": metadata or {},
            "embedding": self._embed(content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > MAX_ENTRIES:
                self._entries = self._entries[-MAX_ENTRIES:]
        return self._public(entry)

    def recall(self, agent_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return an agent's most recent memories, newest first."""
        with self._lock:
            matching = [self._public(entry) for entry in reversed(self._entries) if entry["agent_id"] == agent_id]
        return matching[:limit]

    def search(self, agent_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic search over an agent's memories using cosine similarity."""
        if not query.strip():
            return self.recall(agent_id, limit=top_k)
        query_vector = self._embed(query)
        with self._lock:
            candidates = [
                (entry, _cosine(query_vector, entry["embedding"]))
                for entry in self._entries
                if entry["agent_id"] == agent_id
            ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        results: list[dict[str, Any]] = []
        for entry, score in candidates[:top_k]:
            public = self._public(entry)
            public["score"] = round(score, 4)
            results.append(public)
        return results
