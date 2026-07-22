# -*- coding: utf-8 -*-
"""Scoring runner for fastapi-eval-suite-v3.jsonl against the trained Backend
specialist LoRA adapter. Per doc/kickoff-brief-eval-scoring.md.

Reuses (does not reimplement):
- `_jsonpath`/`_fmt`/`_OPS` from eval_runner.py (the original single-file checker)
- `extract_files` from orchestrator/llm_client.py (the REAL production parser)

Adds: a multi-file-capable app loader (production output can be >1 file, unlike
the original single-`code`-string eval_runner.py, which predates the Frontend
stage / multi-file backend outputs), prompt construction matching the exact
v3 training format, and a scoring loop over the full 31-task suite.

This module has NO model-loading/generation code of its own - it takes a
`generate_fn: str -> str` callback so it can be:
  (a) unit-tested here with a fake generate_fn returning known-good/bad code
      (no GPU needed - validates the CHECKER logic, not the model)
  (b) driven from the Colab notebook with a real generate_fn wrapping the
      trained model + LoRA adapter (see the new notebook cell added alongside
      this file - that part needs the GPU/adapter and cannot run here)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import itertools
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from eval_runner import _fmt, _jsonpath, _OPS  # reuse, don't reimplement

from fastapi.testclient import TestClient

_ORCHESTRATOR_DIR = Path(__file__).resolve().parent.parent / "orchestrator"
if str(_ORCHESTRATOR_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCHESTRATOR_DIR))
from llm_client import extract_files  # noqa: E402  (real production parser)

_counter = itertools.count()


def load_app_from_files(files: List[Dict[str, str]]):
    """Write files to a temp dir (so relative imports between them work,
    unlike the original single-exec-blob `_load_app`), add it to sys.path,
    import whichever module defines a top-level `app`, and return it."""
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"eval_v3_{next(_counter)}_"))
    for f in files:
        target = tmp_dir / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")

    sys.path.insert(0, str(tmp_dir))
    imported_names = []
    try:
        app = None
        # Prefer a file that actually defines `app = ...` textually, then fall
        # back to trying every .py file - handles any entrypoint filename.
        py_files = sorted(tmp_dir.rglob("*.py"))
        candidates = [f for f in py_files if "app" in f.read_text(encoding="utf-8")]
        for f in candidates + [f for f in py_files if f not in candidates]:
            mod_name = f.relative_to(tmp_dir).with_suffix("").as_posix().replace("/", ".")
            try:
                module = __import__(mod_name)
                imported_names.append(mod_name)
                candidate_app = getattr(sys.modules[mod_name], "app", None)
                if candidate_app is not None:
                    app = candidate_app
                    break
            except Exception:
                continue
        if app is None:
            raise RuntimeError(f"no top-level `app` found in generated files: {[f['path'] for f in files]}")
        return app, tmp_dir, imported_names
    except Exception:
        for name in imported_names:
            sys.modules.pop(name, None)
        raise


def run_check_spec(app, check_spec: Dict[str, Any]) -> Tuple[bool, str]:
    """Drive an already-loaded FastAPI `app` through a check_spec's http_sequence
    steps (status/json_keys/json_subset/json_equals/json_len/header/save),
    handling $.field capture and {var} substitution between steps. Reuses
    _fmt/_jsonpath/_OPS from eval_runner.py - same semantics as the original
    single-file checker, just decoupled from how the app got loaded."""
    variables: Dict[str, Any] = {}
    with TestClient(app) as client:
        for i, step in enumerate(check_spec["steps"]):
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
                up = {}
                for field, spec in step["files"].items():
                    name, content, ctype = spec
                    if isinstance(content, str):
                        content = content.encode()
                    up[field] = (name, content, ctype)
                kwargs["files"] = up
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


def run_eval_multifile(files: List[Dict[str, str]], record: Dict[str, Any]) -> Tuple[bool, str]:
    """Multi-file-aware equivalent of eval_runner.run_eval: load_app_from_files
    (`load_app_from_files`) + run_check_spec, with cleanup. Loads from real
    files on disk (not one exec'd blob) so multi-file output can use relative
    imports correctly - the capability the original single-file eval_runner.py
    predates (it was written before the Frontend stage / multi-file outputs)."""
    if record.get("check_type") != "http_sequence":
        return False, f"unsupported check_type {record.get('check_type')!r}"
    if not files:
        return False, "no files parsed from model output"
    tmp_dir = None
    imported_names: List[str] = []
    try:
        app, tmp_dir, imported_names = load_app_from_files(files)
        return run_check_spec(app, record["check_spec"])
    except Exception as e:  # noqa: BLE001
        return False, f"exception: {type(e).__name__}: {e}"
    finally:
        for name in imported_names:
            sys.modules.pop(name, None)
        if tmp_dir and str(tmp_dir) in sys.path:
            sys.path.remove(str(tmp_dir))


def build_prompt(record: Dict[str, Any]) -> str:
    """Identical shape to training: system_prompt + user_prompt + '### Response:\\n'."""
    return f"{record['system_prompt']}\n\n{record['user_prompt']}\n\n### Response:\n"


def score_task(generate_fn: Callable[[str], str], record: Dict[str, Any]) -> Dict[str, Any]:
    """Run one eval task end-to-end: prompt -> generate -> parse -> check_spec.
    A parse failure is an automatic fail for that task (per the brief)."""
    prompt = build_prompt(record)
    raw = generate_fn(prompt)
    try:
        files = extract_files(raw)
    except ValueError as e:
        return {
            "task": record["task"],
            "category": record["category"],
            "passed": False,
            "detail": f"parse failure: {e}",
            "raw_output": raw,
        }
    passed, detail = run_eval_multifile(files, record)
    return {
        "task": record["task"],
        "category": record["category"],
        "passed": passed,
        "detail": detail,
        "files": [f["path"] for f in files],
    }


def score_all(generate_fn: Callable[[str], str], eval_suite_path: str) -> Dict[str, Any]:
    """Score every task in the suite. Returns overall + per-category breakdown."""
    records = [json.loads(line) for line in Path(eval_suite_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    results = [score_task(generate_fn, r) for r in records]

    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    category_summary = {
        cat: {"passed": sum(1 for r in rs if r["passed"]), "total": len(rs)}
        for cat, rs in by_category.items()
    }

    return {
        "results": results,
        "overall_passed": sum(1 for r in results if r["passed"]),
        "overall_total": len(results),
        "by_category": category_summary,
    }


def print_report(summary: Dict[str, Any]) -> None:
    print(f"\n=== Eval Suite Score: {summary['overall_passed']}/{summary['overall_total']} ===\n")
    print("By category:")
    for cat, s in sorted(summary["by_category"].items()):
        print(f"  {cat:20s} {s['passed']}/{s['total']}")
    print("\nFailures:")
    for r in summary["results"]:
        if not r["passed"]:
            print(f"  [{r['category']}] {r['task'][:70]}... -> {r['detail']}")


def score_from_precomputed(eval_suite_path: str, results_path: str) -> Dict[str, Any]:
    """CLI/scripted path for when generation already happened elsewhere (e.g. a
    Colab run saved raw model outputs) - results_path is a JSON list of raw
    output strings, one per eval-suite row, in the same order."""
    raw_outputs = json.loads(Path(results_path).read_text(encoding="utf-8"))
    it = iter(raw_outputs)
    return score_all(lambda _prompt: next(it), eval_suite_path)


def _smoke_test() -> bool:
    """No GPU needed: validates the CHECKER logic (load_app_from_files,
    run_check_spec, cross-file imports, parse-failure handling) against
    hand-written correct/incorrect reference solutions, same standard used to
    validate the original eval_runner.py. Run via: python eval_runner_v3.py --smoke-test"""
    task0 = {
        "task": "smoke-test bookmarks",
        "category": "crud",
        "system_prompt": "smoke-test system prompt",
        "user_prompt": "smoke-test user prompt",
        "check_type": "http_sequence",
        "check_spec": {
            "steps": [
                {"method": "POST", "path": "/bookmarks", "json": {"url": "http://a.com", "title": "A"},
                 "save": {"bid": "$.id"}, "expect": {"status": 201, "json_keys": ["id", "url", "title"]}},
                {"method": "GET", "path": "/bookmarks/{bid}", "expect": {"status": 200, "json_subset": {"title": "A"}}},
            ]
        },
    }
    single_file_correct = (
        '---FILE: app.py---\n'
        'from fastapi import FastAPI\n'
        'from pydantic import BaseModel\n'
        'app = FastAPI()\n'
        'bookmarks = {}\n'
        'next_id = 1\n'
        'class Bookmark(BaseModel):\n'
        '    url: str\n'
        '    title: str\n'
        '@app.post("/bookmarks", status_code=201)\n'
        'def create(b: Bookmark):\n'
        '    global next_id\n'
        '    bid = next_id; next_id += 1\n'
        '    bookmarks[bid] = {"id": bid, "url": b.url, "title": b.title}\n'
        '    return bookmarks[bid]\n'
        '@app.get("/bookmarks/{bookmark_id}")\n'
        'def get(bookmark_id: int):\n'
        '    return bookmarks[bookmark_id]\n'
        '---END---'
    )
    multi_file_correct = (
        '---FILE: models.py---\n'
        'from pydantic import BaseModel\n'
        'class Bookmark(BaseModel):\n'
        '    url: str\n'
        '    title: str\n'
        '---END---\n\n'
        '---FILE: app.py---\n'
        'from fastapi import FastAPI\n'
        'from models import Bookmark\n'
        'app = FastAPI()\n'
        'bookmarks = {}\n'
        'next_id = 1\n'
        '@app.post("/bookmarks", status_code=201)\n'
        'def create(b: Bookmark):\n'
        '    global next_id\n'
        '    bid = next_id; next_id += 1\n'
        '    bookmarks[bid] = {"id": bid, "url": b.url, "title": b.title}\n'
        '    return bookmarks[bid]\n'
        '@app.get("/bookmarks/{bookmark_id}")\n'
        'def get(bookmark_id: int):\n'
        '    return bookmarks[bookmark_id]\n'
        '---END---'
    )
    deliberately_wrong = single_file_correct.replace('status_code=201', '')
    garbled = "Sure, here's your app:\n\ndef hello(): pass"

    cases = [
        ("single-file correct", single_file_correct, True),
        ("multi-file correct (cross-file import)", multi_file_correct, True),
        ("deliberately wrong (missing 201)", deliberately_wrong, False),
        ("garbled / unparseable", garbled, False),
    ]
    all_ok = True
    for label, raw, expected_pass in cases:
        result = score_task(lambda _p, r=raw: r, task0)
        ok = result["passed"] == expected_pass
        all_ok = all_ok and ok
        print(f"  [{'OK' if ok else 'MISMATCH'}] {label}: passed={result['passed']} (expected {expected_pass}) - {result['detail']}")
    return all_ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true", help="run the no-GPU-needed checker self-test")
    parser.add_argument("--eval-suite", help="path to an eval suite JSONL file")
    parser.add_argument("--results", help="path to a JSON list of pre-computed raw model outputs, same order as --eval-suite")
    args = parser.parse_args()

    if args.smoke_test:
        ok = _smoke_test()
        print("\nSMOKE TEST:", "PASSED" if ok else "FAILED")
        sys.exit(0 if ok else 1)
    elif args.eval_suite and args.results:
        summary = score_from_precomputed(args.eval_suite, args.results)
        print_report(summary)
    else:
        parser.print_help()
