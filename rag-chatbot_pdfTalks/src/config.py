"""Central settings, read from environment / .env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    chat_model: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.8-flash")
    embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    persist_dir: str = os.getenv("CHROMA_DIR", str(ROOT / "storage" / "chroma"))
    chunk_tokens: int = int(os.getenv("CHUNK_TOKENS", "400"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "60"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    score_threshold: float = float(os.getenv("SCORE_THRESHOLD", "0.25"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))


settings = Settings()
