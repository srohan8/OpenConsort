"""Dependency-free BM25 retrieval over the verified FastAPI backend pairs.

Used to put the 1-2 most similar *verified* task->code examples into the Backend prompt
(dynamic few-shot). Index is built over the training pairs only, never the held-out
eval suite, so eval scores stay honest.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

PAIRS = Path(__file__).resolve().parent.parent / "data-prep" / "fastapi-backend-pairs-v3.jsonl"

_STOP = {"a", "an", "the", "and", "or", "to", "of", "in", "with", "that", "for", "is", "it", "on", "by", "as", "returns", "return"}


def _tokens(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


class Retriever:
    def __init__(self, rows: list, k1: float = 1.5, b: float = 0.75):
        self.rows = rows
        self.k1, self.b = k1, b
        self.docs = [Counter(_tokens(f"{r['task']} {r.get('category', '')}")) for r in rows]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(rows)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    @classmethod
    def from_pairs(cls, path: Path = PAIRS) -> "Retriever":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls([r for r in rows if r.get("verified")])

    def search(self, query: str, k: int = 2) -> list:
        q = _tokens(query)
        scored = []
        for i, doc in enumerate(self.docs):
            score = 0.0
            for t in q:
                f = doc.get(t, 0)
                if f:
                    norm = f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg_len)
                    score += self.idf[t] * f * (self.k1 + 1) / norm
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [self.rows[i] for _, i in scored[:k]]


def examples_text(rows: list) -> str:
    """Format retrieved pairs as a prompt block using the real contract format."""
    if not rows:
        return ""
    blocks = [f"Task: {r['task']}\n{r['output'].strip()}" for r in rows]
    return (
        "Verified reference examples of similar tasks (same output format; adapt, do not copy blindly):\n\n"
        + "\n\n".join(blocks)
    )
