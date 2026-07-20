# -*- coding: utf-8 -*-
"""Runner for the FastAPI eval suite (fastapi-eval-suite.jsonl).

Given a candidate `code` string (later: emitted by the fine-tuned model) and an eval
record, this execs the code into a FastAPI app and drives it through the record's
`check_spec`, returning (passed: bool, detail: str). This is the programmatic
correctness check the brief requires — no human eyeballing.

check_spec schema (check_type == "http_sequence"):
{
  "steps": [
     {
       "method": "POST",                     # HTTP verb
       "path": "/login",                     # may contain {name} placeholders from saved vars
       "json": {...},                        # optional JSON body (values may contain {name})
       "data": {...},                        # optional form body
       "files": {"file": ["name", "b64orstr", "ctype"]},  # optional upload
       "headers": {"Authorization": "Bearer {token}"},    # optional
       "save": {"token": "$.access_token"},  # extract from JSON response into a variable
       "expect": {
          "status": 200,                     # exact status code
          "json_keys": ["access_token"],     # keys that must be present at top level
          "json_subset": {"token_type": "bearer"},  # key/values that must match
          "json_equals": {...},              # exact JSON equality
          "json_len": {"path": "$", "op": ">=", "value": 1},  # length of list at path
          "header": {"x-total-count": "3"}   # response header equality (case-insensitive)
       }
     }
  ]
}
"""
from __future__ import annotations

import sys
import types
import itertools
from typing import Any, Dict, Tuple

from fastapi.testclient import TestClient

_counter = itertools.count()


def _load_app(code: str):
    mod_name = f"eval_module_{next(_counter)}"
    module = types.ModuleType(mod_name)
    module.__dict__["__name__"] = mod_name
    sys.modules[mod_name] = module
    try:
        exec(compile(code, f"<{mod_name}>", "exec"), module.__dict__)
        app = module.__dict__.get("app")
        if app is None:
            raise RuntimeError("no top-level `app` defined")
        app._eval_module_name = mod_name
        return app
    except Exception:
        sys.modules.pop(mod_name, None)
        raise


def _jsonpath(obj: Any, path: str) -> Any:
    if path in ("$", "$."):
        return obj
    cur = obj
    for part in path.lstrip("$.").split("."):
        if part == "":
            continue
        cur = cur[part]
    return cur


def _fmt(value: Any, variables: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        return value.format(**variables)
    if isinstance(value, dict):
        return {k: _fmt(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_fmt(v, variables) for v in value]
    return value


_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


def run_eval(code: str, record: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (passed, detail). Any exception -> (False, reason)."""
    if record.get("check_type") != "http_sequence":
        return False, f"unsupported check_type {record.get('check_type')!r}"
    mod_name = None
    try:
        app = _load_app(code)
        mod_name = getattr(app, "_eval_module_name", None)
        variables: Dict[str, Any] = {}
        with TestClient(app) as client:
            for i, step in enumerate(record["check_spec"]["steps"]):
                method = step["method"].lower()
                path = _fmt(step["path"], variables)
                kwargs: Dict[str, Any] = {}
                if "json" in step:
                    kwargs["json"] = _fmt(step["json"], variables)
                if "data" in step:
                    kwargs["data"] = _fmt(step["data"], variables)
                if "params" in step:
                    kwargs["params"] = _fmt(step["params"], variables)
                if "headers" in step:
                    kwargs["headers"] = _fmt(step["headers"], variables)
                if "files" in step:
                    files = {}
                    for field, spec in step["files"].items():
                        name, content, ctype = spec
                        if isinstance(content, str):
                            content = content.encode()
                        files[field] = (name, content, ctype)
                    kwargs["files"] = files
                resp = getattr(client, method)(path, **kwargs)

                exp = step.get("expect", {})
                if "status" in exp and resp.status_code != exp["status"]:
                    return False, f"step {i}: expected status {exp['status']}, got {resp.status_code}"
                body = None
                if any(k in exp for k in ("json_keys", "json_subset", "json_equals", "json_len")) or "save" in step:
                    body = resp.json()
                if "json_keys" in exp:
                    missing = [k for k in exp["json_keys"] if k not in body]
                    if missing:
                        return False, f"step {i}: missing keys {missing}"
                if "json_subset" in exp:
                    for k, v in exp["json_subset"].items():
                        if body.get(k) != v:
                            return False, f"step {i}: {k}={body.get(k)!r} != {v!r}"
                if "json_equals" in exp and body != exp["json_equals"]:
                    return False, f"step {i}: body {body!r} != {exp['json_equals']!r}"
                if "json_len" in exp:
                    spec = exp["json_len"]
                    target = _jsonpath(body, spec.get("path", "$"))
                    if not _OPS[spec["op"]](len(target), spec["value"]):
                        return False, f"step {i}: len={len(target)} not {spec['op']} {spec['value']}"
                if "header" in exp:
                    for h, v in exp["header"].items():
                        if resp.headers.get(h) != v:
                            return False, f"step {i}: header {h}={resp.headers.get(h)!r} != {v!r}"
                if "save" in step:
                    for var, jp in step["save"].items():
                        variables[var] = _jsonpath(body, jp)
        return True, "all steps passed"
    except Exception as e:  # noqa: BLE001
        return False, f"exception: {type(e).__name__}: {e}"
    finally:
        if mod_name and mod_name in sys.modules:
            del sys.modules[mod_name]
