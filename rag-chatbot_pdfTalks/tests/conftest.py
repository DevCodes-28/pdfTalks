import pytest

from src.vectorstore import VectorStore
from tests.fakes import FakeLLM


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def store(tmp_path, llm):
    return VectorStore(str(tmp_path / "chroma"), llm)
