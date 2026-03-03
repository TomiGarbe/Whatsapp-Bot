"""Retrieval structures for tenant-scoped hybrid RAG context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalResult:
    """Basic retrieval payload used to enrich AI generation."""

    matched_items: list[dict[str, Any]]
    all_items: list[dict[str, Any]]
    match_confidence: str  # "single" | "multiple" | "none"

