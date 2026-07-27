# MiniCPM5-1B vs. Qwen2.5-Coder-1.5B — Preparation Report

**Date:** 2026-07-23
**Scope:** Per `doc/kickoff-brief-minicpm-comparison.md`. **This is explicitly a Colab/GPU task** — the brief itself says so, and this local session has no GPU and no Colab access (same limitation documented in `doc/eval-scoring-report.md` for the original eval-scoring task). What follows is everything preparable *without* a GPU: the duplicate notebook, the exact required changes, and a load-bearing nuance found while researching MiniCPM5-1B's thinking-mode mechanism that the brief specifically asked to confirm before training. **Actually running training + eval scoring still requires you to execute this notebook in Colab.**

## What was prepared

`data-prep/fastapi_lora_qlora_colab_minicpm.ipynb` — a duplicate of the working Qwen notebook, per step 1. The original (`fastapi_lora_qlora_colab.ipynb`) is untouched, per the brief's explicit "don't discard" instruction.

**Changes made, exactly as specified:**
1. **`MODEL_ID`** → `"openbmb/MiniCPM5-1B"` (was `"Qwen/Qwen2.5-Coder-1.5B"`).
2. **`OUTPUT_DIR`** → `f"{DRIVE_PROJECT_DIR}/fastapi-backend-lora-minicpm"` (distinct from the Qwen adapter's path — won't overwrite it).
3. **Everything else in the training recipe is untouched**: same 3 epochs, same batch size/gradient accumulation, same label-masking logic (section 6, unmodified), same LoRA config (`r=16`, `target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`) — per the brief's "don't over-tune differently per model" instruction, this is a true apples-to-apples swap of one variable.

**Confirmed via research (not assumed) before touching training config, per step 3:**
MiniCPM5-1B's model card confirms a **standard `LlamaForCausalLM` architecture**. The existing LoRA `target_modules` list already targets exactly the module names (`q_proj`/`k_proj`/`v_proj`/`o_proj`/`gate_proj`/`up_proj`/`down_proj`) that a standard Llama-family model exposes — no changes needed there. The notebook still calls `model.print_trainable_parameters()` immediately after attaching LoRA (unchanged from the Qwen version), which is the brief's own suggested sanity check that this isn't silently zero.

## The genuine nuance found (step 4) — read this before running

Researched MiniCPM5-1B's actual model card (huggingface.co/openbmb/MiniCPM5-1B) rather than assuming the mechanism. Confirmed:

- **`enable_thinking` is exclusively a parameter to `tokenizer.apply_chat_template(messages, ..., enable_thinking=False)`.** The model card documents no other control (no `/no_think` text suffix or similar raw-prompt marker) — Think/No-Think is a chat-template-level switch only, nothing else.
- **This notebook's entire pipeline never calls `apply_chat_template` anywhere** — section 4's `format_example` does plain string concatenation (`system_prompt + "\n\n" + user_prompt + "\n\n### Response:\n"`), identical to the Qwen run, and training/inference both tokenize that raw string directly. This is deliberate and correct for a fair comparison (it's the exact same prompting shape used for Qwen), but it means **the documented `enable_thinking` knob has no hook to attach to in this pipeline as written** — there's nothing to "set to False" in code that currently exists, because the mechanism that flag controls is never invoked.

**What this leaves genuinely open:** whether MiniCPM5-1B's default completion behavior (no chat template, no explicit instruction either way) spontaneously emits `<think>...</think>` reasoning anyway, as a pretrained/SFT prior baked into the checkpoint independent of the chat template. This can't be resolved by reading documentation further — it's an empirical question about this specific model's behavior under this specific (non-standard, template-free) prompting style, and I have no way to test it without the GPU/model access this task explicitly requires.

**What was done about it:** added a new **section 5a** to the notebook — a verification cell that runs immediately after the base model loads (before any LoRA training), generating from the *untrained* base model using the exact same raw prompt+completion style the rest of the pipeline uses, and checking the output for a literal `<think>` tag. This directly fulfills the brief's "confirm how to disable this correctly... before training" instruction: since there's no documented raw-text equivalent to flip, an empirical pre-training check is the correct substitute for a config change that doesn't exist, not a guess or an assumption that raw prompting is automatically safe.

The cell's markdown also states the fallback reasoning if `<think>` *does* appear: LoRA fine-tuning for 3 epochs against this dataset's non-thinking completions (full loss weight on completion tokens, prompt fully masked) should substantially override any such default for the *trained adapter's* behavior specifically, even if the base checkpoint reasons unprompted — but this should be re-confirmed with the existing section 10 sanity check after training, not assumed.

## What still needs to happen in Colab (cannot be done from here)

1. Open `fastapi_lora_qlora_colab_minicpm.ipynb` in Colab (same Drive-mounted setup as the Qwen run).
2. Run through section 5a and read its output — confirms or refutes the thinking-mode concern empirically before you commit GPU time to training.
3. Run training (section 8) — expect a similar step count (~70 steps for 93 rows) and a healthy downward loss trend; exact loss values will differ from Qwen's since it's a different base model, that's expected and not itself a signal of a problem.
4. Run the section 10 sanity check — confirms the pipeline works on this model before the full eval run, and re-checks for `<think>` in the *trained* adapter's output if section 5a flagged a concern.
5. Run section 11 onward (Postgres setup, scoring cell) exactly as done for Qwen — `OUTPUT_DIR`/`MODEL_ID` are already parameterized from the config cell, so the scoring cell will automatically load the MiniCPM adapter without further edits.
6. Bring back the overall score (X/31) and category breakdown.

## Recommendation on next steps

I can't produce the actual comparison table or a build-vs-Qwen recommendation yet — that requires the real trained numbers, which don't exist until this notebook is run in Colab. Once you have the MiniCPM5-1B score, share it (or the notebook's saved outputs) and I'll do the direct comparison against the Qwen result, write up the category-by-category breakdown, and give a recommendation exactly as the brief's definition of done specifies.
