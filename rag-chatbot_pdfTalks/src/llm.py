"""The ONLY module that talks to the model provider (Google Gemini).

Swap providers by re-implementing `GeminiLLM` with the same two methods.
"""
from __future__ import annotations

from typing import Protocol

from .config import settings


class LLM(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    def generate(self, system: str, prompt: str) -> str: ...


class GeminiLLM:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types
        out: list[list[float]] = []
        for i in range(0, len(texts), 100):  # API batch limit
            res = self.client.models.embed_content(
                model=settings.embed_model,
                contents=texts[i : i + 100],
                config=types.EmbedContentConfig(task_type=task_type),
            )
            out.extend(e.values for e in res.embeddings)
        return out

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def generate(self, system: str, prompt: str) -> str:
        from google.genai import types
        res = self.client.models.generate_content(
            model=settings.chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.1),
        )
        return (res.text or "").strip()
