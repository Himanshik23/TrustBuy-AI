"""Report duplicate detection (docs/USER_FLOWS.md §5.4, API_DOCUMENTATION.md
§4). Exact-normalized-text hashing - real and working, but honestly not
semantic: two reports describing the same scam in different words won't
match. Embedding-based near-duplicate detection (ChromaDB, per
ARCHITECTURE.md's vector-store design) is the documented upgrade once
Phase 3 wires up the shared Chroma instance already running in
docker-compose - not silently promised here as done.
"""

from __future__ import annotations

import hashlib
import re


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
