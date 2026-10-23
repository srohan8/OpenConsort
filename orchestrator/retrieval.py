"""Dependency-free BM25 retrieval for dynamic few-shot prompting.

- Backend: the most similar *verified* task->code pairs (training pairs only, never the
  held-out eval suite, so eval scores stay honest).
- Planning: the most similar example plans from data-prep/planning-examples.jsonl.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data-prep"
PAIRS = DATA / "fastapi-backend-pairs-v3.jsonl"
PLANNING_EXAMPLES = DATA / "planning-examples.jsonl"

_STOP = {"a", "an", "the", "and", "or", "to", "of", "in", "with", "that", "for", "is", "it", "on", "by", "as", "returns", "return"}


def _tokens(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


class Retriever:
    def __init__(self, rows: list, key: str = "task", k1: float = 1.5, b: float = 0.75):
        self.rows = rows
        self.k1, self.b = k1, b
        self.docs = [Counter(_tokens(f"{r[key]} {r.get('category', '')}")) for r in rows]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(rows)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    @classmethod
    def from_pairs(cls, path: Path = PAIRS) -> "Retriever":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls([r for r in rows if r.get("verified")])

    @classmethod
    def from_planning_examples(cls, path: Path = PLANNING_EXAMPLES) -> "Retriever":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(rows, key="idea")

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


def planning_examples_text(idea: str, k: int = 2) -> str:
    """The k example plans closest to `idea` as a prompt block. Falls back to the first
    examples when nothing overlaps, so the model always sees the format at least once."""
    if k <= 0 or not PLANNING_EXAMPLES.exists():
        return ""
    retriever = Retriever.from_planning_examples()
    rows = retriever.search(idea, k)
    for row in retriever.rows:
        if len(rows) >= k:
            break
        if row not in rows:
            rows.append(row)
    blocks = [f"Example idea: {r['idea']}\n{r['plan']}" for r in rows]
    header = "Examples of good plans for other ideas (same format; write a plan for YOUR idea, do not copy):"
    return header + "\n\n" + "\n\n".join(blocks)
