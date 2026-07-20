# Phase 1 Trial Report — Part 2: Patching Per-Role LLM Wiring

**Date:** 2026-07-20
**Follow-on to:** `doc/phase1-trial-report.md`, per `doc/kickoff-brief-metagpt-patch.md`.

## 1. Did the patched swap actually work? (verified, not self-reported)

**Yes, the routing itself genuinely worked** — verified two independent ways, deliberately not trusting MetaGPT's own success claims (which the prior trial showed can be false):

- **Unit-level check** before running the full pipeline: constructed `Engineer2(config=engineer2_config)` directly and inspected `e.llm` — confirmed `type(e.llm).__name__ == "OllamaLLM"` with `e.llm.config.base_url == "http://localhost:11434/api"`. This is MetaGPT's own internal LLM provider object, not a log message.
- **System-level check** during the full pipeline run: `ollama ps` (Ollama's own CLI, entirely outside MetaGPT) showed `qwen2.5-coder:1.5b` actually loaded onto the CPU (100% utilization) partway through the run — independent proof Ollama was really invoked, not just referenced in a config file.

So: **the LLM routing itself is fixed and confirmed real.** However, the end-to-end pipeline still did not produce a working `todo.py` — see point 3.

## 2. How invasive was the patch?

**Extremely small: one file, one contiguous ~15-line insertion, one line changed.** Full diff:

```diff
--- metagpt/software_company.py.orig
+++ metagpt/software_company.py
@@ -43,6 +43,21 @@
     if not recover_path:
+        # PATCH: route Engineer2 only to a local Ollama model, independent
+        # of the (dead) config2.yaml `roles:` mechanism.
+        from metagpt.config2 import Config as _Config
+
+        engineer2_config = _Config.from_llm_config(
+            {
+                "api_type": "ollama",
+                "base_url": "http://localhost:11434/api",
+                "model": "qwen2.5-coder:1.5b",
+            }
+        )
+
         company = Team(context=ctx)
         company.hire(
             [
                 TeamLeader(),
                 ProductManager(),
                 Architect(),
-                Engineer2(),
+                Engineer2(config=engineer2_config),
```

**This is the most important finding of this follow-on task.** No framework internals were modified — `context_mixin.py`, `role.py`, `context.py` were all untouched. The mechanism to route a single role's LLM independently of the global config **already exists** in MetaGPT (`ContextMixin.set_config()` → the `llm` property resolves via `self.config.llm`, and `self.config` prefers a role-instance's `private_config` over the shared context config). The prior trial's "dead code" finding was specifically about the *declarative* `config2.yaml` `roles:` list never being read — but the *underlying* per-instance override plumbing it was presumably meant to drive is real, functional, and already wired through `ContextMixin`. The gap is narrowly that nothing translates `config.roles` (parsed YAML) into a role's `config=` constructor kwarg at hire-time — not that per-role LLMs are structurally unsupported.

**Practical implication:** a *general* fix (making the declarative `roles:` YAML section work for any role) would be a small, contained addition too — a single function in `software_company.py` (or wherever roles are hired) that, for each role instance, looks up a matching entry in `config.roles` by class name and calls `role.set_config(Config.from_llm_config(entry.llm))` before/after `hire()`. Rough estimate: another 15–25 lines, still one file, no framework surgery. This lowers the risk of the "per-role LLM routing" gap considerably compared to how the prior trial's finding may have read.

## 3. Did anything else break or behave unexpectedly?

**Yes — a more fundamental problem than the routing gap, and this is the real headline of this task.** The pipeline reached Engineer2, Engineer2's `_think()` genuinely called Ollama's `qwen2.5-coder:1.5b` — and the small model **could not reliably follow RoleZero's strict tool-call JSON protocol**:

- On its first turn, the model responded with plain prose + a fenced Python code block (a normal, reasonable "here's your code" chat answer) instead of the expected `{"command_name": "Engineer2.write_new_code", ...}` JSON command array RoleZero's `_act()` requires.
- MetaGPT's own `parse_commands` repair mechanism tried to fix/re-request this, but the retry made things *worse*: the model got confused by the repair prompt itself and, on the next turn, responded as if it were being asked "please fix this malformed JSON" as a generic task — producing an unrelated, hallucinated answer about "JSON data format" errors, completely detached from writing `todo.py`.
- This ultimately crashed the run: `KeyError: 'command_name'` in `metagpt/utils/role_zero_utils.py:137`, because `parse_commands` assumed every parsed item is a `{"command_name": ...}` dict and the small model's output didn't conform.
- **No file was ever written to disk** — Engineer2 never successfully issued a `write_new_code`/Terminal command, so this run didn't even reach far enough to re-trigger the previously-found Windows `pwd`/`WinError 123` Terminal bug. That bug's status is simply unconfirmed by this run, not resolved.

This is a fundamentally different failure mode than the cloud baseline's issues — it's not an environment/Windows bug, it's a **capability mismatch**: RoleZero's ReAct loop assumes every participating LLM can reliably emit a specific structured tool-call format under all circumstances (including recovering from its own malformed-output repair prompts). A 1.5B model is simply not reliable at this without fine-tuning specifically for that protocol.

## 4. Quality check: was the actual code reasonable?

**Yes, surprisingly good, in isolation.** The Python code `qwen2.5-coder:1.5b` produced (ignoring that it was never picked up by the pipeline) was a coherent, correct `argparse`-based CLI to-do app — subcommands for `add`/`list`/`complete`, sensible structure, no syntax errors. It's meaningfully simpler than what the cloud model produced (no JSON-file persistence across runs, no error handling on invalid indices in one version), but it's a legitimate, working answer to the prompt. **The model's raw coding ability was not the problem — the failure was entirely about adherence to a specific structured-output protocol**, which is a distinct (and arguably more addressable, via fine-tuning or output constraining) issue from "is this model good enough to code."

## 5. Honest recommendation

**Lean toward a lighter custom orchestrator over continuing to force small/local models through MetaGPT's RoleZero/DI architecture — but keep the underlying insight this task surfaced.**

Reasoning:
- The *routing* gap (this task's original target) turned out cheap to fix — a real positive signal for "MetaGPT as scaffolding," and worth remembering if the team later decides to keep building on it for other reasons.
- But the *deeper* problem this test exposed is more serious and directly validates a concern already flagged in the architecture doc: small models need **narrow, simple contracts**, not a shared, complex, one-size-fits-all ReAct tool-calling protocol designed around what large cloud models can reliably do. RoleZero's format (strict JSON tool-call arrays, self-repair via re-prompting, multi-command turns) is exactly the kind of "large-model-shaped call" the project's core thesis is trying to move away from.
- Building a lighter, purpose-built orchestrator means the "contract" between the orchestrator and each small specialist model can be genuinely minimal and forgiving (e.g., "return only a code block, nothing else" — which `qwen2.5-coder:1.5b` handled perfectly well when not also expected to emit tool-call JSON) rather than inheriting a protocol built for GPT-4-class models.
- If MetaGPT is still preferred for its planning/task-decomposition logic (the TeamLeader's plan-building was coherent throughout), a hybrid is worth considering: keep MetaGPT (or something like it) for planning/orchestration roles that stay on a capable cloud model, but don't route small local models through RoleZero's strict tool-protocol roles at all — instead have the orchestrator call small models directly via simple, narrow prompts (bypassing the ReAct/tool-call layer entirely for those roles). That's a materially different integration shape than "swap the Engineer role's config," though.

**Bottom line:** the config-wiring problem was a red herring in terms of difficulty — it was cheap to fix. The real blocker to the local-model vision is architectural: RoleZero's tool-calling contract is not small-model-friendly, and that's a harder, more central problem than a missing config plumb-through.
