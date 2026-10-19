"""Golden Q&A harness (needs GEMINI_API_KEY; not part of pytest).   python -m eval.run_eval"""
import json
import tempfile
from pathlib import Path

from src import rag
from src.llm import GeminiLLM
from src.vectorstore import VectorStore

ROOT = Path(__file__).resolve().parent


def main():
    llm = GeminiLLM()
    with tempfile.TemporaryDirectory() as tmp:
        store = VectorStore(tmp, llm)
        for f in (ROOT.parent / "data" / "sample").iterdir():
            if f.suffix in {".pdf", ".txt", ".csv"}:
                rag.ingest(str(f), store)
        passed = 0
        cases = json.loads((ROOT / "golden.json").read_text())
        for c in cases:
            r = rag.answer(c["q"], store, llm)
            if c["expect"] is None:  # out-of-scope question: must refuse
                ok = not r["grounded"]
            else:
                ok = c["expect"].lower() in r["answer"].lower() and any(s["source"] == c["source"] for s in r["sources"])
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  {c['q']}\n      -> {r['answer'][:110]!r}")
        print(f"\n{passed}/{len(cases)} passed")


if __name__ == "__main__":
    main()
