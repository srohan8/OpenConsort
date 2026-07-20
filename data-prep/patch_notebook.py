"""One-off patch: point the LoRA notebook at the v3 (contract-shaped) dataset
and train on system_prompt/user_prompt/output instead of task/code.
Run once, then delete (or keep for reference/re-application after a notebook
regeneration). Written as a plain .py file deliberately - editing the raw
.ipynb JSON through nested shell/heredoc layers previously corrupted escape
sequences; a single Python file has only one layer of string literals.
"""
import json
from pathlib import Path

NB_PATH = Path(__file__).resolve().parent / "fastapi_lora_qlora_colab.ipynb"

with open(NB_PATH, encoding="utf-8") as f:
    nb = json.load(f)

# --- Cell 6: DATA_PATH -> v3 file ---
cell6 = nb["cells"][6]
src6 = "".join(cell6["source"])
old_path = 'DATA_PATH  = f"{DRIVE_PROJECT_DIR}/fastapi-backend-pairs.jsonl"'
assert old_path in src6, "cell6 anchor not found"
new_path = (
    'DATA_PATH  = f"{DRIVE_PROJECT_DIR}/fastapi-backend-pairs-v3.jsonl"  '
    "# contract-shaped input+output, see RESHAPE-REPORT.md"
)
cell6["source"] = src6.replace(old_path, new_path).splitlines(keepends=True)

# --- Cell 10: format_example -> use real system_prompt/user_prompt/output ---
cell10 = nb["cells"][10]
src10 = "".join(cell10["source"])

old_lines = '''PROMPT_PREFIX = "### Task:\\n{task}\\n\\n### FastAPI code:\\n"

def format_example(ex):
    prompt = PROMPT_PREFIX.format(task=ex["task"])
    completion = ex["code"]
    return {"prompt": prompt, "completion": completion}
'''
assert old_lines in src10, "cell10 old block not found verbatim"

new_lines = '''# v3 rows carry the REAL orchestrator prompt shape (see reshape_to_orchestrator_input.py):
# system_prompt = orchestrator.BACKEND_SYSTEM (imported from orchestrator.py, not retyped)
# user_prompt   = "LockedSpec:\\n<json>\\n\\nDesignTokens:\\n<json>" - identical f-string
#                 template to orchestrator.py:211, ground truth for what the Backend stage
#                 actually receives at inference time
# output        = the delimited-text ---FILE:---/---END--- contract completion
# Falls back to the old task/code shape only for the embedded DUMMY pairs above, which
# predate the reshape and have no system_prompt/user_prompt/output fields.

def format_example(ex):
    if "system_prompt" in ex and "user_prompt" in ex:
        prompt = ex["system_prompt"] + "\\n\\n" + ex["user_prompt"] + "\\n\\n### Response:\\n"
        completion = ex["output"]
    else:
        prompt = "### Task:\\n" + ex["task"] + "\\n\\n### FastAPI code:\\n"
        completion = ex["code"]
    return {"prompt": prompt, "completion": completion}
'''
cell10["source"] = src10.replace(old_lines, new_lines).splitlines(keepends=True)

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")

print("Patched cells 6 and 10.")
