"""Reusable verification harness for FastAPI task->code pairs.

Each *candidate* is a dict:
    {
      "task": str,              # natural-language task description
      "category": str,          # one of the categories in task-categories.md
      "code": str,              # a self-contained FastAPI snippet defining `app`
      "check": callable,        # check(client: TestClient) -> str (notes) ; raises on failure
    }

`verify_candidate` execs the code into a fresh module namespace, locates the FastAPI
`app`, wraps it in a starlette/fastapi TestClient, and runs the check. If the check
returns without raising, the pair is considered VERIFIED and the returned string is
stored as `verification_notes`. Any exception (import error, syntax error, failed
assertion, unexpected status) marks the pair FAILED with the traceback captured as the
reason.

This module is deliberately dependency-light and importable so it can be reused when the
dataset is scaled up.
"""
from __future__ import annotations

import itertools
import sys
import traceback
import types
from typing import Any, Callable, Dict, List, Tuple

from fastapi.testclient import TestClient

_counter = itertools.count()


def _load_app(code: str) -> Any:
    """Exec `code` in a fresh module namespace and return the object named `app`.

    The module is registered in ``sys.modules`` under a unique name so that
    Pydantic (and typing) can resolve class ``__module__`` references when it
    rebuilds models for request bodies (Optional/Field/EmailStr/nested/Enum
    models otherwise fail with 'class not fully defined' when exec'd into an
    unregistered namespace).
    """
    mod_name = f"candidate_module_{next(_counter)}"
    module = types.ModuleType(mod_name)
    module.__dict__["__name__"] = mod_name
    sys.modules[mod_name] = module
    try:
        exec(compile(code, f"<{mod_name}>", "exec"), module.__dict__)
    finally:
        # Keep it registered during the request lifecycle; caller cleans up via
        # returned module reference. We drop it after use in verify_candidate.
        pass
    app = module.__dict__.get("app")
    if app is None:
        raise RuntimeError("snippet did not define a top-level `app`")
    app._candidate_module_name = mod_name  # for cleanup
    return app


def verify_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Run one candidate through the harness. Returns a result record."""
    task = candidate["task"]
    category = candidate["category"]
    code = candidate["code"]
    check: Callable[[TestClient], str] = candidate["check"]

    result: Dict[str, Any] = {
        "task": task,
        "category": category,
        "code": code,
        "verified": False,
        "verification_notes": "",
    }
    mod_name = None
    try:
        app = _load_app(code)
        mod_name = getattr(app, "_candidate_module_name", None)
        # `with TestClient` triggers startup/shutdown events too.
        with TestClient(app) as client:
            notes = check(client)
        result["verified"] = True
        result["verification_notes"] = notes or "check passed"
    except Exception:  # noqa: BLE001 - we want to capture *any* failure as signal
        tb = traceback.format_exc(limit=6)
        # Compress to the final, most informative lines for the log.
        last = tb.strip().splitlines()
        reason = " | ".join(last[-3:]) if last else "unknown error"
        result["verified"] = False
        result["verification_notes"] = reason
        result["_traceback"] = tb
    finally:
        if mod_name and mod_name in sys.modules:
            del sys.modules[mod_name]
    return result


def run_all(candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Verify every candidate; return (passed, failed) lists of result records."""
    passed, failed = [], []
    for cand in candidates:
        res = verify_candidate(cand)
        (passed if res["verified"] else failed).append(res)
    return passed, failed
