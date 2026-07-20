"""Thin LLM client wrapper. Each stage config picks its own backend/model -
no shared "team" config, no per-role override plumbing to fight with."""
import json
import re
import time

from openai import APIStatusError, OpenAI


class StageLLM:
    def __init__(self, name: str, base_url: str, api_key: str, model: str, max_retries: int = 4, retry_wait: float = 5.0):
        self.name = name
        self.model = model
        self.max_retries = max_retries
        self.retry_wait = retry_wait
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


FILE_BLOCK_RE = re.compile(
    r"---\s*FILE:\s*(?P<path>[^\n\r-]+?)\s*---\r?\n(?P<content>.*?)\r?\n?---\s*END\s*---",
    re.DOTALL,
)


def extract_files(text: str) -> list[dict]:
    """Parse '---FILE: path---\\n<raw code>\\n---END---' blocks out of free text.
    No JSON, no escaping required - a model writes code exactly as it normally would.
    Anything outside FILE/END markers (prose, reasoning) is ignored."""
    # models sometimes wrap the whole thing in a ```...``` fence - strip fences if present,
    # markers still get found either way since we search the raw text directly.
    files = []
    for m in FILE_BLOCK_RE.finditer(text):
        path = m.group("path").strip()
        content = m.group("content")
        files.append({"path": path, "content": content})
    if not files:
        raise ValueError(f"No ---FILE: ... --- / ---END--- blocks found in model output:\n{text[:500]}")
    return files
