# -*- coding: utf-8 -*-
"""Emit fastapi_lora_qlora_colab.ipynb — a valid, Colab-uploadable QLoRA notebook.

Runs end-to-end on dummy data (a few Task-2 pairs embedded inline, plus optional
load of fastapi-backend-pairs.jsonl if uploaded alongside). Uses transformers +
peft (LoRA) + bitsandbytes (4-bit QLoRA) on a small 1-3B model.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}


def code(*lines):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _src(lines)}


def _src(lines):
    text = "\n".join(lines)
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


cells = []

cells.append(md(
    "# FastAPI Backend Specialist — QLoRA Fine-Tuning (Colab Pro)",
    "",
    "LoRA / QLoRA (4-bit) fine-tuning of a small 1-3B base model on FastAPI",
    "task->code pairs, per the *democratized AI coding* architecture (Phase 1 =",
    "FastAPI backend specialist).",
    "",
    "**Runtime:** Colab Pro, GPU runtime (T4/L4/A100). `Runtime -> Change runtime",
    "type -> GPU`.",
    "",
    "**This notebook runs end-to-end on DUMMY data** (a handful of verified pairs",
    "embedded below). Point it at the real `fastapi-backend-pairs.jsonl` later by",
    "uploading the file — the loader picks it up automatically.",
    "",
    "> Do **not** treat the tiny dummy run as a real training run — it exists only to",
    "> prove the pipeline executes. Real training uses the full verified dataset.",
))

cells.append(md("## 1. Install dependencies"))
cells.append(code(
    "# Colab already ships torch. Pin the fine-tuning stack.",
    "!pip install -q -U \"transformers>=4.44\" \"peft>=0.12\" \"accelerate>=0.33\" \\",
    "    \"bitsandbytes>=0.43\" \"datasets>=2.20\"",
))

cells.append(md("## 2. Configuration"))
cells.append(code(
    "import torch",
    "",
    "# Small base model (1-3B). Swap for another candidate (e.g. a MiniCPM / Qwen",
    "# coder variant) when comparing base models per the architecture doc.",
    "MODEL_ID   = \"Qwen/Qwen2.5-Coder-1.5B\"   # ~1.5B, permissive, strong on code",
    "OUTPUT_DIR = \"fastapi-backend-lora\"",
    "MAX_LEN    = 1024",
    "",
    "# 4-bit QLoRA requires a CUDA GPU. Fall back to a CPU-friendly path if none.",
    "USE_4BIT = torch.cuda.is_available()",
    "print(\"CUDA available:\", torch.cuda.is_available(), \"| 4-bit QLoRA:\", USE_4BIT)",
))

cells.append(md(
    "## 3. Load the dataset",
    "",
    "Uses `fastapi-backend-pairs.jsonl` if present (upload it via the Files pane),",
    "otherwise falls back to a small embedded dummy set so the notebook always runs.",
))
cells.append(code(
    "import json, os",
    "",
    "DUMMY_PAIRS = [",
    "    {\"task\": \"Create a FastAPI app with a GET /items endpoint that returns all items.\",",
    "     \"code\": \"from fastapi import FastAPI\\napp = FastAPI()\\nitems = [{'id': 1, 'name': 'apple'}]\\n\\n@app.get('/items')\\ndef list_items():\\n    return items\\n\"},",
    "    {\"task\": \"Create a FastAPI GET /items/{item_id} endpoint returning 404 if missing.\",",
    "     \"code\": \"from fastapi import FastAPI, HTTPException\\napp = FastAPI()\\nitems = {1: {'id': 1, 'name': 'apple'}}\\n\\n@app.get('/items/{item_id}')\\ndef get_item(item_id: int):\\n    if item_id not in items:\\n        raise HTTPException(status_code=404, detail='Item not found')\\n    return items[item_id]\\n\"},",
    "    {\"task\": \"Create a FastAPI POST /items endpoint that returns 201 with an id.\",",
    "     \"code\": \"from fastapi import FastAPI, status\\nfrom pydantic import BaseModel\\napp = FastAPI()\\n_db = {}\\n\\nclass ItemIn(BaseModel):\\n    name: str\\n\\n@app.post('/items', status_code=status.HTTP_201_CREATED)\\ndef create_item(item: ItemIn):\\n    new = {'id': len(_db) + 1, 'name': item.name}\\n    _db[new['id']] = new\\n    return new\\n\"},",
    "]",
    "",
    "DATA_PATH = \"fastapi-backend-pairs.jsonl\"",
    "if os.path.exists(DATA_PATH):",
    "    pairs = [json.loads(l) for l in open(DATA_PATH, encoding='utf-8')]",
    "    print(f\"Loaded {len(pairs)} real pairs from {DATA_PATH}\")",
    "else:",
    "    pairs = DUMMY_PAIRS",
    "    print(f\"No {DATA_PATH} found — using {len(pairs)} embedded DUMMY pairs\")",
))

cells.append(md(
    "## 4. Prompt formatting",
    "",
    "A simple instruction template. The frozen contract from planning (the future",
    "input to this specialist) would replace the free-text task later; the shape",
    "stays task -> code.",
))
cells.append(code(
    "PROMPT_TEMPLATE = (",
    "    \"### Task:\\n{task}\\n\\n### FastAPI code:\\n{code}\"",
    ")",
    "",
    "def format_example(ex):",
    "    return {\"text\": PROMPT_TEMPLATE.format(task=ex[\"task\"], code=ex[\"code\"])}",
    "",
    "from datasets import Dataset",
    "raw_ds = Dataset.from_list(pairs).map(format_example)",
    "print(raw_ds[0][\"text\"][:300])",
))

cells.append(md("## 5. Tokenizer & 4-bit base model (QLoRA)"))
cells.append(code(
    "from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig",
    "",
    "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)",
    "if tokenizer.pad_token is None:",
    "    tokenizer.pad_token = tokenizer.eos_token",
    "",
    "if USE_4BIT:",
    "    bnb_config = BitsAndBytesConfig(",
    "        load_in_4bit=True,",
    "        bnb_4bit_quant_type=\"nf4\",",
    "        bnb_4bit_compute_dtype=torch.bfloat16,",
    "        bnb_4bit_use_double_quant=True,",
    "    )",
    "    model = AutoModelForCausalLM.from_pretrained(",
    "        MODEL_ID, quantization_config=bnb_config, device_map=\"auto\"",
    "    )",
    "else:",
    "    # CPU fallback (no bitsandbytes) so the notebook still runs anywhere.",
    "    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)",
    "",
    "model.config.use_cache = False",
))

cells.append(md("## 6. Tokenize"))
cells.append(code(
    "def tokenize(batch):",
    "    out = tokenizer(",
    "        batch[\"text\"], truncation=True, max_length=MAX_LEN, padding=\"max_length\"",
    "    )",
    "    out[\"labels\"] = out[\"input_ids\"].copy()",
    "    return out",
    "",
    "tokenized_ds = raw_ds.map(tokenize, batched=True, remove_columns=raw_ds.column_names)",
))

cells.append(md("## 7. Attach LoRA adapters"))
cells.append(code(
    "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training",
    "",
    "if USE_4BIT:",
    "    model = prepare_model_for_kbit_training(model)",
    "",
    "lora_config = LoraConfig(",
    "    r=16,",
    "    lora_alpha=32,",
    "    lora_dropout=0.05,",
    "    bias=\"none\",",
    "    task_type=\"CAUSAL_LM\",",
    "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",",
    "                    \"gate_proj\", \"up_proj\", \"down_proj\"],",
    ")",
    "model = get_peft_model(model, lora_config)",
    "model.print_trainable_parameters()",
))

cells.append(md(
    "## 8. Train",
    "",
    "Tiny settings for the dummy run (1 epoch, a few steps). For real training,",
    "raise `num_train_epochs` (2-3), use the full dataset, and enable eval.",
))
cells.append(code(
    "from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling",
    "",
    "args = TrainingArguments(",
    "    output_dir=OUTPUT_DIR,",
    "    per_device_train_batch_size=1,",
    "    gradient_accumulation_steps=4,",
    "    num_train_epochs=1,",
    "    learning_rate=2e-4,",
    "    logging_steps=1,",
    "    save_strategy=\"epoch\",",
    "    fp16=USE_4BIT,",
    "    optim=\"paged_adamw_8bit\" if USE_4BIT else \"adamw_torch\",",
    "    report_to=\"none\",",
    ")",
    "",
    "collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)",
    "trainer = Trainer(",
    "    model=model,",
    "    args=args,",
    "    train_dataset=tokenized_ds,",
    "    data_collator=collator,",
    ")",
    "trainer.train()",
))

cells.append(md("## 9. Save the adapter"))
cells.append(code(
    "model.save_pretrained(OUTPUT_DIR)",
    "tokenizer.save_pretrained(OUTPUT_DIR)",
    "print(\"Adapter saved to:\", OUTPUT_DIR)",
    "# The LoRA adapter is only tens of MB — download it and run base+adapter locally.",
))

cells.append(md("## 10. Quick inference sanity check"))
cells.append(code(
    "prompt = \"### Task:\\nCreate a FastAPI GET /health endpoint returning {'status':'ok'}.\\n\\n### FastAPI code:\\n\"",
    "inputs = tokenizer(prompt, return_tensors=\"pt\").to(model.device)",
    "model.config.use_cache = True",
    "out = model.generate(**inputs, max_new_tokens=128, do_sample=False,",
    "                     pad_token_id=tokenizer.pad_token_id)",
    "print(tokenizer.decode(out[0], skip_special_tokens=True))",
))

cells.append(md(
    "## Notes for scaling up",
    "",
    "- Upload the full `fastapi-backend-pairs.jsonl` (cell 3 auto-detects it).",
    "- Compare base models (Qwen coder / MiniCPM etc.) by re-running with a different",
    "  `MODEL_ID` and scoring each against `fastapi-eval-suite.jsonl` using",
    "  `eval_runner.py`.",
    "- Iterate on **dataset quality** first, hyperparameters second (per the brief).",
    "- Keep `use_cache=False` during training, `True` for generation (handled above).",
))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

path = os.path.join(HERE, "fastapi_lora_qlora_colab.ipynb")
with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("wrote", path, "with", len(cells), "cells")
