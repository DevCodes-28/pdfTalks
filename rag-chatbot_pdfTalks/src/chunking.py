"""Type-aware chunking.

Prose (PDF/TXT) is split by TOKEN count with overlap (tiktoken). Token count is what
determines context-window usage, not character count. CSV rows stay atomic: one row = one
chunk, since splitting a row by length would sever a record's fields from each other.
"""
from __future__ import annotations

import re

from langchain_core.documents import Document

from .config import settings


class _Tokenizer:
    """tiktoken when available; falls back to whitespace tokens if its vocab can't be fetched."""

    def __init__(self):
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            self.encode, self.decode = enc.encode, enc.decode
            self.name = "tiktoken"
        except Exception:
            self.encode = lambda t: re.findall(r"\S+\s*", t)
            self.decode = lambda toks: "".join(toks)
            self.name = "whitespace-fallback"


_tok = _Tokenizer()


def count_tokens(text: str) -> int:
    return len(_tok.encode(text))


def split_prose(text: str, chunk_tokens: int, overlap: int) -> list[str]:
    if overlap >= chunk_tokens:
        raise ValueError("overlap must be smaller than chunk_tokens")
    toks = _tok.encode(text)
    step = chunk_tokens - overlap
    out = []
    for start in range(0, len(toks), step):
        piece = _tok.decode(toks[start : start + chunk_tokens]).strip()
        if piece:
            out.append(piece)
        if start + chunk_tokens >= len(toks):
            break
    return out


def chunk_documents(docs: list[Document], chunk_tokens: int | None = None, overlap: int | None = None) -> list[Document]:
    chunk_tokens = chunk_tokens or settings.chunk_tokens
    overlap = settings.chunk_overlap if overlap is None else overlap
    chunks: list[Document] = []
    counters: dict[str, int] = {}

    def add(source: str, text: str, meta: dict):
        cid = counters.get(source, 0)
        counters[source] = cid + 1
        chunks.append(Document(page_content=text, metadata={**meta, "source": source, "chunk_id": cid}))

    for d in docs:
        src = d.metadata["source"]
        if d.metadata.get("kind") == "csv_row":
            add(src, d.page_content, d.metadata)  # atomic
        else:
            for piece in split_prose(d.page_content, chunk_tokens, overlap):
                add(src, piece, d.metadata)
    return chunks
