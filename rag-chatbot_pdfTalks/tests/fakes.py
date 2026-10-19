"""Offline stand-ins for the LLM/embeddings so tests never hit the network."""
import hashlib
import math
import re


class FakeLLM:
    api_key = "fake"
    DIM = 512

    def __init__(self):
        self.generate_calls = 0

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.DIM
        for w in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)

    def generate(self, system, prompt):
        self.generate_calls += 1
        label = re.search(r"\[([^\[\]]+#\d+)\]", prompt)
        return f"Based on the documents. [{label.group(1)}]" if label else "no label"
