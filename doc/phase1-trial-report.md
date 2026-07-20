# Phase 1 Trial Report — MetaGPT Single-Role Ollama Swap

**Date:** 2026-07-20
**Environment:** Windows, Python 3.11.9 venv, MetaGPT cloned from `FoundationAgents/MetaGPT` main branch (commit `11cdf46`, 2026-01-21), Ollama 0.32.1 with `qwen2.5-coder:1.5b` (986MB), cloud LLM via a local Omniroute router (OpenAI-compatible endpoint).

## Headline finding

**MetaGPT's installed (current main-branch) version is architecturally different from what the kickoff brief assumed.** It does not run the classic four-role SOP pipeline (Product Manager → Architect → Project Manager → Engineer) with document handoffs. Instead, `metagpt.software_company` invokes a **TeamLeader/RoleZero** ReAct-style single-agent system (`metagpt/roles/di/`) that classifies the request, plans tasks, and assigns them to named personas (e.g. "Alex") — but the actual code-writing role is a class called **`Engineer2`**, not `Engineer`. This is a real, load-bearing discovery: any customization work built against the classic role names/docs described in `democratized-ai-coding-architecture.md` needs to target this newer architecture instead.

## Answers to the 4 questions

### 1. Did the single-role Ollama swap work without breaking the pipeline?

**No — and importantly, not because of an Ollama-specific failure.** Investigation of the codebase found that MetaGPT's documented per-role LLM override mechanism (`config2.yaml`'s `roles:` list, backed by `RoleCustomConfig`) is **not actually wired up** anywhere in the current codebase for DI/RoleZero-style roles. Confirmed by code search:
- `metagpt/context.py`'s `llm()` factory only ever reads `self.config.llm` (the top-level/default LLM config) — no per-role lookup.
- `metagpt/roles/role.py` only stores `role_id` as a field; nothing in the codebase reads `Config.roles` to construct a role-specific LLM instance.
- The only files referencing `RoleCustomConfig` are its own definition and `config2.py`'s schema — it's declared but effectively dead code for this execution path.

Setting `roles: [{role: "Engineer2", llm: {api_type: ollama, ...}}]` in `config2.yaml` had no effect — `Engineer2._think()` still called the default (Omniroute/cloud) LLM client, which errored with a 401 on that particular run (likely an unrelated transient auth/rate issue on the router, not a symptom of reaching Ollama).

**Practical implication:** the clean, config-driven single-role swap described in the brief and in MetaGPT's example config is not currently achievable via config alone on this codebase version. A working swap would require either (a) patching `Context.llm()` / role instantiation to actually consult `config.roles`, or (b) constructing an `Engineer2` instance directly with an explicit `Config.from_llm_config({"api_type": "ollama", ...})` object rather than relying on the global config file. This is a meaningful build item, not a quick config tweak — directly relevant to the project's premise that this should be "a config/adapter change, not a framework rewrite" (per the architecture doc). Ollama itself was independently confirmed reachable and serving `qwen2.5-coder:1.5b` (`curl http://localhost:11434/api/tags` returned 200), so the model/runtime side is ready whenever the code-side wiring is fixed.

### 2. What format does MetaGPT expect for role handoffs?

**Neither clean markdown documents nor strict schema-validated JSON** — the actual format observed is a single continuous ReAct transcript per "turn," mixing:
- Free-form markdown reasoning/thought text
- Embedded ` ```json ` blocks containing arrays of **tool-call commands** (e.g. `Plan.append_task`, `TeamLeader.publish_message`, `Engineer2.write_new_code`, `Terminal.run_command`, `RoleZero.reply_to_human`), each a `{"command_name": ..., "args": {...}}` dict
- Occasional malformed JSON that MetaGPT's own `parse_code`/`parse_commands` utility has to catch and "attempt to repair" (observed directly in the log — the LLM emitted `` ```json [...] `` `` with a stray space, which failed strict regex parsing and triggered a repair path)

This is a real, useful data point for the strict-contract design goal: the current handoff format is **loosely-structured tool-call JSON embedded in free text**, not the strict versioned schema envisioned in the architecture doc. Building the intended strict contract layer would mean intercepting/replacing this ReAct command-loop format entirely, not adapting an existing document-passing convention.

### 3. Does MetaGPT ask clarifying questions, or go straight from prompt to output?

**Confirmed: no clarifying questions.** In both runs, the agent classified the one-line prompt as `Response Category: TASK`, then went straight to planning and code generation without pausing to ask the user anything. This matches the brief's stated expectation exactly.

### 4. Friction points suggesting MetaGPT's assumptions fight the local/small-model, strict-contract design

Several concrete issues surfaced, beyond the architecture mismatch and dead per-role-config issue above:

- **Dependency pinning is stale.** MetaGPT pins `typer==0.9.0` but doesn't pin `click`; a fresh install pulls a `click` version incompatible with that `typer`, crashing the CLI entrypoint (`TypeError: Secondary flag is not valid for non-boolean flag`). Fixed by pinning `click==8.1.7`.
- **Windows console encoding bug.** MetaGPT streams raw LLM output (including Unicode characters like `✓`) directly to stdout via `print()`. On a default Windows console (cp1252), this crashes with `UnicodeEncodeError` mid-run, killing the process before it finishes. Workaround: `PYTHONIOENCODING=utf-8` / `PYTHONUTF8=1`. This is a real robustness issue for any Windows-based local deployment — exactly the kind of consumer-PC-friendliness gap that matters for this project's goals.
- **Terminal tool assumes Unix shell semantics.** The agent's `Terminal.run_command` tool issued a Unix `pwd` command (not native to `cmd.exe`); the resulting garbled/ANSI-escaped output was then misinterpreted as a file path, causing `OSError: [WinError 123]` and silently failing to write the generated `todo.py` to disk — even though the agent's final chat response claimed the file was created and fully functional. **This means the pipeline can report success while producing no actual code artifact on Windows.** This is a significant correctness gap for a local-first, cross-platform-consumer-PC target.
- **Cost/token accounting doesn't recognize custom model names.** Router/custom model strings (e.g. `My-combo`) aren't in MetaGPT's built-in `tiktoken`/`TOKEN_COSTS` tables, producing warnings on every call. Cosmetic, but noisy, and would need a fix for any locally-hosted model naming scheme.
- **Positive note:** the underlying reasoning/planning quality of the agent (task classification, plan decomposition, code logic) was coherent and sensible even when it hit environment-level bugs — the friction found is almost entirely in framework/environment integration (Windows support, config wiring), not core agent behavior.

## Overall verdict for the "build on MetaGPT" decision

The core value proposition — reusing MetaGPT's orchestration to avoid building a framework from scratch — is **still plausible but needs re-scoping**: the actual orchestration primitive worth reusing here is the ReAct/tool-command loop and role-persona structure, not a clean documented per-role model-swap surface (which doesn't work as documented) or the classic 4-role SOP pipeline (which isn't what runs by default anymore). Any further work should budget real engineering time for: (a) wiring up genuine per-role LLM routing (the dead `config.roles` mechanism), (b) Windows-specific hardening (encoding, terminal tool), and (c) deciding whether the loose ReAct-JSON handoff format is adaptable to the strict-contract goal or needs a bespoke replacement layer.
