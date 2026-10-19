"""FastAPI backend + static web UI.   Run:  uvicorn app:app --reload"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import rag
from src.config import ROOT, settings
from src.llm import LLM, GeminiLLM
from src.loaders import SUPPORTED
from src.vectorstore import VectorStore


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=settings.top_k, ge=1, le=12)


def create_app(llm: LLM | None = None, persist_dir: str | None = None) -> FastAPI:
    llm = llm or GeminiLLM()
    store = VectorStore(persist_dir or settings.persist_dir, llm)
    app = FastAPI(title="RAG Chatbot for Documents")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "gemini_key_set": bool(getattr(llm, "api_key", True)),
                "chat_model": settings.chat_model, "score_threshold": settings.score_threshold}

    @app.get("/api/documents")
    def documents():
        return {"documents": store.list_sources()}

    @app.post("/api/upload")
    def upload(files: list[UploadFile] = File(...)):
        results = []
        for f in files:
            name = Path(f.filename or "").name
            if Path(name).suffix.lower() not in SUPPORTED:
                results.append({"name": name, "error": "Unsupported type. Upload PDF, TXT or CSV."})
                continue
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / name
                with dest.open("wb") as out:
                    shutil.copyfileobj(f.file, out)
                if dest.stat().st_size > settings.max_upload_mb * 1024 * 1024:
                    results.append({"name": name, "error": f"Larger than {settings.max_upload_mb} MB."})
                    continue
                try:
                    n = rag.ingest(str(dest), store, source=name)
                    results.append({"name": name, "chunks": n} if n else {"name": name, "error": "No readable text found."})
                except Exception as e:  # surface provider / parse errors to the UI
                    results.append({"name": name, "error": f"Could not index: {e}"})
        return {"results": results, "documents": store.list_sources()}

    @app.delete("/api/documents/{name}")
    def delete(name: str):
        store.delete_source(name)
        return {"documents": store.list_sources()}

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        try:
            return rag.answer(req.question, store, llm, k=req.top_k)
        except RuntimeError as e:  # e.g. missing API key
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Model request failed: {e}")

    static = ROOT / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
