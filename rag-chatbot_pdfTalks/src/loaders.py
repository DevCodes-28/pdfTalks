"""PDF / TXT / CSV -> LangChain Documents."""
from __future__ import annotations

import csv
from pathlib import Path

from langchain_core.documents import Document

SUPPORTED = {".pdf", ".txt", ".csv"}


def load_file(path: str | Path, source: str | None = None) -> list[Document]:
    path = Path(path)
    source = source or path.name
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _load_pdf(path, source)
    if ext == ".txt":
        return _load_txt(path, source)
    if ext == ".csv":
        return _load_csv(path, source)
    raise ValueError(f"Unsupported file type '{ext}'. Use PDF, TXT or CSV.")


def _load_pdf(path: Path, source: str) -> list[Document]:
    from pypdf import PdfReader
    docs = []
    for n, page in enumerate(PdfReader(str(path)).pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(Document(page_content=text, metadata={"source": source, "kind": "prose", "page": n}))
    return docs


def _load_txt(path: Path, source: str) -> list[Document]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return [Document(page_content=text, metadata={"source": source, "kind": "prose"})] if text else []


def _load_csv(path: Path, source: str) -> list[Document]:
    docs = []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        for row_no, row in enumerate(csv.DictReader(f), start=1):
            body = "; ".join(f"{k}: {v}" for k, v in row.items() if k and v not in (None, ""))
            if body:
                docs.append(Document(page_content=body, metadata={"source": source, "kind": "csv_row", "row": row_no}))
    return docs
