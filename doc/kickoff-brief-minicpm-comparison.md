# Kickoff Brief — Head-to-Head: MiniCPM5-1B vs. Qwen2.5-Coder-1.5B

**Context:** MiniCPM5-1B was identified early in this project as the strongest benchmarked candidate in the ≤1B model class (Artificial Analysis Intelligence Index leader, strong agentic/code benchmarks) — but the actual working notebook defaulted to `Qwen/Qwen2.5-Coder-1.5B` instead, and no explicit decision was ever made to prefer one over the other. `architecture.md`'s own base-model-selection principle says to fine-tune each candidate on the same dataset and compare real eval results, not benchmark reputation alone — that comparison has never actually happened. This closes that gap.

**This is a Colab task, not a Claude Code task** — it needs the GPU. Run this in your existing notebook (or a duplicate of it).

## Goal

Fine-tune `openbmb/MiniCPM5-1B` on the exact same 93-row dataset (`fastapi-backend-pairs-v3.jsonl`) used for the current Qwen adapter, score it against the exact same 31-task eval suite (`fastapi-eval-suite-v3.jsonl`) using `eval_runner_v3.py`, and compare the resulting score directly against the current Qwen result (12-13/31 range, exact number depends on which rescore you're comparing against).

## Steps

1. **Duplicate your existing working notebook** (recommended over editing in place, so you keep the Qwen version intact for reference) — e.g. `fastapi_lora_qlora_colab_minicpm.ipynb`.

2. **Change exactly one line** in the Configuration cell:
   ```python
   MODEL_ID = "openbmb/MiniCPM5-1B"   # was "Qwen/Qwen2.5-Coder-1.5B"
   ```
   Also change `OUTPUT_DIR` to a distinct path so it doesn't overwrite the Qwen adapter:
   ```python
   OUTPUT_DIR = f"{DRIVE_PROJECT_DIR}/fastapi-backend-lora-minicpm"
   ```

3. **Check the LoRA target modules still apply.** MiniCPM5-1B is confirmed dense and built on the standard `LlamaForCausalLM` architecture, so the existing `target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` should work unchanged — but verify this after loading the model (e.g., print the model's named modules, or just proceed and check `model.print_trainable_parameters()` gives a sane result, not zero trainable params).

4. **Check tokenizer/chat-template differences.** MiniCPM5-1B ships with a built-in `<think>` chat template and a `enable_thinking` toggle (Think / No Think modes from the same checkpoint). For this comparison, use **No Think mode** (`enable_thinking=False`) to keep it a fair, direct comparison against Qwen's plain completion style — thinking mode would add reasoning tokens that change the nature of the comparison. Confirm how to disable this correctly (likely via the tokenizer's chat template application, or it may not engage at all if you're not using the chat template format — check MiniCPM5-1B's model card / quickstart for the exact mechanism before training).

5. **Run training as-is** (same 3 epochs, same batch size/gradient accumulation, same label masking from section 6 — do not skip or alter the masking fix). Expect a similar step count (~70 steps) and watch for a healthy loss curve (should trend down similarly to the Qwen run, though the exact starting/ending loss values may differ since it's a different base model).

6. **Run the held-out inference sanity check** (section 10) before moving to full eval scoring — confirms the basic pipeline works on this new model before committing to the full 31-task run.

7. **Run the full eval scoring** (section 11 onward — Postgres setup, passlib install, the scoring cell) exactly as done for Qwen, pointed at this new adapter's `OUTPUT_DIR`.

8. **Compare the results directly:**
   - Overall score (X/31) vs. Qwen's most recent comparable score
   - Category-by-category breakdown — does MiniCPM5-1B do notably better/worse on any specific categories (e.g., does its "strong agentic/code" reputation show up specifically in categories like `dependency-injection` or `auth-jwt`, or is it uniform)?
   - Any new or different failure patterns not seen with Qwen

## What NOT to do

- Don't modify the dataset or eval suite for this comparison — must be identical inputs to both models for a fair test.
- Don't enable Thinking mode for this comparison (see step 4) — keep it apples-to-apples.
- Don't discard the Qwen adapter or delete its results — keep both for reference regardless of outcome.
- Don't over-tune hyperparameters differently per model for this first pass — use identical training settings so the comparison isolates the base model itself, not the training recipe. (A follow-up round could tune per-model if one candidate clearly wins and is worth optimizing further.)

## Definition of done

- A trained MiniCPM5-1B LoRA adapter, saved separately from the Qwen adapter
- A full eval score (X/31) with category breakdown, run the same way as the Qwen comparison
- A direct comparison table: Qwen vs. MiniCPM5-1B, overall and by category
- A recommendation: does MiniCPM5-1B's benchmark reputation translate into a better real score on this specific task, or does Qwen (already proven, already the basis of two augmentation rounds) remain the better practical choice going forward?
