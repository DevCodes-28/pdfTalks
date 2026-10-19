"""Chroma persistence + relevance-score filtering (cosine similarity)."""
from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from .llm import LLM


class VectorStore:
    def __init__(self, persist_dir: str, llm: LLM, collection: str = "docs"):
        self.llm = llm
        self._client = chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))
        self._col = self._client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    @staticmethod
    def _id(meta: dict) -> str:
        return f"{meta['source']}#{meta['chunk_id']}"

    def add_documents(self, chunks: list[Document]) -> int:
        if not chunks:
            return 0
        self.delete_source(chunks[0].metadata["source"])  # re-upload replaces old version
        embeds = self.llm.embed_documents([c.page_content for c in chunks])
        metas = [{k: v for k, v in c.metadata.items() if isinstance(v, (str, int, float, bool))} for c in chunks]
        self._col.add(ids=[self._id(m) for m in metas], embeddings=embeds,
                      documents=[c.page_content for c in chunks], metadatas=metas)
        return len(chunks)

    def search(self, query: str, k: int, score_threshold: float) -> list[tuple[Document, float]]:
        """Top-k chunks whose cosine similarity >= threshold, best first."""
        if self._col.count() == 0:
            return []
        res = self._col.query(query_embeddings=[self.llm.embed_query(query)],
                              n_results=min(k, self._col.count()))
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            score = 1.0 - dist  # chroma cosine distance -> similarity
            if score >= score_threshold:
                hits.append((Document(page_content=text, metadata=meta), score))
        return hits

    def list_sources(self) -> list[dict]:
        data = self._col.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for m in data["metadatas"]:
            counts[m["source"]] = counts.get(m["source"], 0) + 1
        return [{"name": n, "chunks": c} for n, c in sorted(counts.items())]

    def delete_source(self, source: str) -> None:
        self._col.delete(where={"source": source})

    def clear(self) -> None:
        for s in self.list_sources():
            self.delete_source(s["name"])
