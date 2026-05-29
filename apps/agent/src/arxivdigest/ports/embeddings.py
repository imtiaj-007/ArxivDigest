"""Port: text embedding."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Embedder(Protocol):
    """Turns documents into dense vectors for similarity search + ranking."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of documents. Returns one vector per input, in order."""
        ...
