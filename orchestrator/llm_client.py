"""Thin LLM client wrapper. Each stage config picks its own backend/model -
no shared "team" config, no per-role override plumbing to fight with."""
import json
import re
import time

from openai import APIStatusError, OpenAI


class StageLLM:
    def __init__(self, name: str, base_url: str, api_key: str, model: str, max_retries: int = 4, retry_wait: float = 5.0, json_mode: bool = False):
        self.name = name
        self.model = model
        self.max_retries = max_retries
        self.retry_wait = retry_wait
        self.json_mode = json_mode  # ask the server for a JSON object (Ollama/OpenAI response_format)
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    **({"response_format": {"type": "json_object"}} if self.json_mode else {}),
                )
                return resp.choices[0].message.content
            except APIStatusError as e:
                last_err = e
                # OmniRoute's combo round-robins across several upstream providers
                # (Cerebras, Cloudflare Workers AI, Pollinations AI, NVIDIA NIM);
                # a provider missing credentials surfaces as HTTP 404 with a
                # nested "[401]: ..." message in the body, not a real 401/404.
                # Retry-on-next-attempt naturally lands on a different provider.
                if e.status_code in (401, 404, 429, 500, 502, 503) and attempt < self.max_retries:
                    wait = self.retry_wait * attempt
                    print(f"  [{self.name}] call failed ({e.status_code}), retrying in {wait:.0f}s (attempt {attempt}/{self.max_retries})...")
                    time.sleep(wait)
                    continue
                raise
        raise last_err


def extract_json(text: str) -> dict:
    """Pull the first fenced ```json ... ``` block, or the first {...} span, and parse it.
    Small models often wrap JSON in prose - this is deliberately forgiving, unlike
    RoleZero's strict command-array parser."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if not candidate:
        brace = re.search(r"(\{.*\})", text, re.DOTALL)
        candidate = brace.group(1) if brace else None
    if not candidate:
        raise ValueError(f"No JSON object found in model output:\n{text[:500]}")
    return json.loads(candidate)


FILE_START_RE = re.compile(r"---\s*FILE:\s*(?P<path>[^\n\r-]+?)\s*---\r?\n")
FILE_END_RE = re.compile(r"\r?\n?---\s*END\s*---")


def extract_files(text: str) -> list[dict]:
    """Parse '---FILE: path---\\n<raw code>\\n---END---' blocks out of free text.
    No JSON, no escaping required - a model writes code exactly as it normally would.
    Anything outside FILE/END markers (prose, reasoning) is ignored.

    Tolerant of a missing ---END--- marker: small models sometimes emit every
    ---FILE:--- opener correctly but drop the closer, especially across many
    files in one response. When no ---END--- is found before the next ---FILE:---
    (or end of text), that point is treated as the implicit end of the block."""
    starts = list(FILE_START_RE.finditer(text))
    files = []
    for i, start_match in enumerate(starts):
        path = start_match.group("path").strip()
        content_from = start_match.end()
        content_to = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        chunk = text[content_from:content_to]
        end_match = FILE_END_RE.search(chunk)
        content = chunk[: end_match.start()] if end_match else chunk.rstrip()
        files.append({"path": path, "content": content})
    if not files:
        raise ValueError(f"No ---FILE: ... --- blocks found in model output:\n{text[:500]}")
    return files
