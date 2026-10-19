"""The pipeline: ingest() and answer()."""
from __future__ import annotations

import re

from .chunking import chunk_documents
from .config import settings
from .llm import LLM
from .loaders import load_file
from .vectorstore import VectorStore

NO_ANSWER = "I couldn't find anything relevant to that in the uploaded documents."

SYSTEM = (
    "You answer questions using ONLY the provided context. Never use outside knowledge. "
    "If the context does not contain the answer, reply exactly: " + NO_ANSWER + " "
    "Cite every claim inline with the label of the chunk it came from, like [report.pdf#3]. "
    "Be concise."
)

CITE_RE = re.compile(r"\[([^\[\]]+?#\d+)\]")


def ingest(path: str, store: VectorStore, source: str | None = None) -> int:
    docs = load_file(path, source)
    return store.add_documents(chunk_documents(docs))


def answer(question: str, store: VectorStore, llm: LLM, k: int | None = None,
           score_threshold: float | None = None) -> dict:
    k = k or settings.top_k
    thr = settings.score_threshold if score_threshold is None else score_threshold
    hits = store.search(question, k, thr)
    if not hits:  # relevance floor: don't force an answer out of whatever ranked highest
        return {"answer": NO_ANSWER, "grounded": False, "sources": [], "cited": []}

    context = "\n\n".join(f"[{d.metadata['source']}#{d.metadata['chunk_id']}]\n{d.page_content}" for d, _ in hits)
    text = llm.generate(SYSTEM, f"Context:\n{context}\n\nQuestion: {question}")
    sources = [{"id": f"{d.metadata['source']}#{d.metadata['chunk_id']}", "source": d.metadata["source"],
                "chunk_id": d.metadata["chunk_id"], "score": round(s, 3), "text": d.page_content} for d, s in hits]
    cited = set(CITE_RE.findall(text))
    return {"answer": text, "grounded": text.strip() != NO_ANSWER, "sources": sources,
            "cited": sorted(c for c in cited if c in {s["id"] for s in sources})}
