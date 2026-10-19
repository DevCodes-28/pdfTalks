import csv

from fastapi.testclient import TestClient

from app import create_app
from src import rag
from src.chunking import chunk_documents, count_tokens, split_prose
from src.loaders import load_file
from tests.fakes import FakeLLM


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_prose_split_respects_token_budget_and_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    parts = split_prose(text, 100, 20)
    assert len(parts) > 4
    assert all(count_tokens(p) <= 105 for p in parts)
    assert parts[0].split()[-1] in parts[1]  # overlap carried over


def test_csv_rows_are_atomic(tmp_path):
    p = tmp_path / "p.csv"
    with p.open("w", newline="") as f:
        csv.writer(f).writerows([("sku", "name"), ("A1", "x " * 3000), ("A2", "y")])
    chunks = chunk_documents(load_file(p), chunk_tokens=50, overlap=5)
    assert len(chunks) == 2  # long row NOT split
    assert [c.metadata["chunk_id"] for c in chunks] == [0, 1]


def test_loaders_txt_and_unsupported(tmp_path):
    assert load_file(write(tmp_path, "a.txt", "hello"))[0].metadata["source"] == "a.txt"
    try:
        load_file(write(tmp_path, "a.docx", "x"))
        assert False
    except ValueError:
        pass


def test_answer_cites_and_filters(tmp_path, store, llm):
    rag.ingest(str(write(tmp_path, "policy.txt", "Passwords must be rotated every 180 days.")), store)
    rag.ingest(str(write(tmp_path, "menu.txt", "Pizza margherita costs eight dollars.")), store)
    r = rag.answer("How often are passwords rotated?", store, llm, score_threshold=0.2)
    assert r["grounded"] and r["cited"] == ["policy.txt#0"]
    assert all(s["source"] == "policy.txt" for s in r["sources"])


def test_below_threshold_says_unknown_without_calling_llm(tmp_path, store, llm):
    rag.ingest(str(write(tmp_path, "policy.txt", "Passwords must be rotated every 180 days.")), store)
    r = rag.answer("quantum chromodynamics lagrangian", store, llm, score_threshold=0.25)
    assert not r["grounded"] and r["answer"] == rag.NO_ANSWER and r["sources"] == []
    assert llm.generate_calls == 0


def test_reupload_replaces_chunks(tmp_path, store):
    p = write(tmp_path, "a.txt", "alpha beta")
    rag.ingest(str(p), store)
    rag.ingest(str(p), store)
    assert store.list_sources() == [{"name": "a.txt", "chunks": 1}]


def test_api_flow(tmp_path):
    client = TestClient(create_app(FakeLLM(), str(tmp_path / "c")))
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200
    up = client.post("/api/upload", files=[
        ("files", ("policy.txt", b"Passwords must be rotated every 180 days.", "text/plain")),
        ("files", ("bad.exe", b"x", "application/octet-stream"))])
    res = up.json()["results"]
    assert res[0]["chunks"] == 1 and "Unsupported" in res[1]["error"]
    chat = client.post("/api/chat", json={"question": "How often are passwords rotated?"}).json()
    assert chat["grounded"] and chat["sources"][0]["source"] == "policy.txt"
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert client.delete("/api/documents/policy.txt").json()["documents"] == []
    assert client.post("/api/chat", json={"question": "anything"}).json()["grounded"] is False
