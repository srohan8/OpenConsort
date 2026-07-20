# -*- coding: utf-8 -*-
"""Run every candidate through the verification harness and emit the dataset.

Outputs (all in data-prep/):
  - fastapi-backend-pairs.jsonl : one verified pair per line (json.loads-able)
  - verification-log.jsonl      : full pass/fail record for every candidate
  - verification-log.md         : human-readable summary of what passed/failed and why
"""
import json
import os
from collections import Counter

from verify_pairs import verify_candidate
from candidates_a import CANDIDATES as CAND_A
from candidates_b import CANDIDATES as CAND_B

HERE = os.path.dirname(os.path.abspath(__file__))
ALL = CAND_A + CAND_B


def main():
    results = [verify_candidate(c) for c in ALL]
    passed = [r for r in results if r["verified"]]
    failed = [r for r in results if not r["verified"]]

    # 1. dataset JSONL (verified only, clean schema)
    pairs_path = os.path.join(HERE, "fastapi-backend-pairs.jsonl")
    with open(pairs_path, "w", encoding="utf-8") as f:
        for r in passed:
            rec = {
                "task": r["task"],
                "code": r["code"].strip() + "\n",
                "category": r["category"],
                "verified": True,
                "verification_notes": r["verification_notes"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2. full verification log JSONL
    log_path = os.path.join(HERE, "verification-log.jsonl")
    with open(log_path, "w", encoding="utf-8") as f:
        for r in results:
            rec = {
                "task": r["task"],
                "category": r["category"],
                "verified": r["verified"],
                "verification_notes": r["verification_notes"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 3. human-readable markdown log
    by_cat = Counter(r["category"] for r in ALL)
    passed_by_cat = Counter(r["category"] for r in passed)
    md_path = os.path.join(HERE, "verification-log.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Verification Log\n\n")
        f.write(f"- Candidates generated: **{len(ALL)}**\n")
        f.write(f"- Verified (kept): **{len(passed)}**\n")
        f.write(f"- Failed (culled): **{len(failed)}**\n\n")
        f.write("## Per-category (verified / total)\n\n")
        f.write("| Category | Verified | Total |\n|---|---|---|\n")
        for cat in sorted(by_cat):
            f.write(f"| {cat} | {passed_by_cat.get(cat, 0)} | {by_cat[cat]} |\n")
        f.write("\n## Failures (reason)\n\n")
        if not failed:
            f.write("None — all candidates passed.\n")
        else:
            for r in failed:
                f.write(f"- **[{r['category']}]** {r['task']}\n")
                f.write(f"  - reason: `{r['verification_notes']}`\n")

    print(f"candidates={len(ALL)} verified={len(passed)} failed={len(failed)}")
    if failed:
        print("\nFAILURES:")
        for r in failed:
            print(f"  [{r['category']}] {r['task'][:70]}")
            print(f"      -> {r['verification_notes']}")
    return len(failed)


if __name__ == "__main__":
    raise SystemExit(0 if main() == 0 else 0)  # always exit 0; failures are logged
