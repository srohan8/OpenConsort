# Kickoff Brief for Claude Code — Phase 1 Trial, Part 2: Patch Per-Role LLM Wiring

**Context:** Follow-on to the completed MetaGPT trial (see `doc/phase1-trial-report.md` for the full findings). That trial confirmed Ollama works standalone, but found the per-role LLM override in `config2.yaml`'s `roles:` section is dead code — nothing in `context.py` or `role.py` ever reads it to construct a per-role LLM instance. This is a bounded, timeboxed experiment to test whether that gap is patchable, before deciding whether to keep building on MetaGPT or switch to a lighter custom orchestrator.

## Goal of this task

Patch just enough of MetaGPT's role/context wiring to get ONE role (Engineer2, the code-writing role) actually routed to a local Ollama-served model at runtime — a real, working swap, not just a config value that's silently ignored. This is a proof-of-concept, not a production fix.

## Timebox

**Spend no more than ~1 focused session on this.** If the fix turns out to require touching many files, or the dead `roles:` config connects to other tightly-coupled assumptions that would take significantly more work to unwind, stop and report back rather than continuing to dig — that outcome is itself a useful, decisive finding (see "What to report" below).

## Steps

1. **Confirm the exact gap first.** Re-verify where `config2.yaml`'s `roles:` override is parsed/loaded, and trace exactly why it's never used to construct a per-role LLM instance (this should already be mostly known from the prior trial — confirm and get precise line/function references).
2. **Identify the minimal patch point.** Find where a Role's LLM instance is actually constructed/assigned in `role.py`/`context.py`, and figure out the smallest change needed to make it respect a per-role override (e.g., an Ollama-served model for `Engineer2` specifically) instead of using whatever the global/default LLM config is.
3. **Apply the patch, scoped to Engineer2 only.** Don't try to generalize this to all roles yet — just get Engineer2 routed to a local Ollama model (e.g. `qwen2.5-coder:1.5b`, which was already confirmed working standalone in the prior trial).
4. **Re-run the same baseline test** (the "build a CLI to-do list app" prompt or similar) with this patch applied.
5. **Check whether the known Windows bugs still apply** — specifically the `pwd`/Terminal tool issue that silently prevented file writes while reporting success. If it's not directly relevant to this patch, just note whether it's still present; don't fix it as part of this task unless it blocks testing the patch itself.

## What to report back

- **Did the patched swap actually work?** I.e., did Engineer2 genuinely generate code using the local Ollama model (verifiable — e.g., check Ollama's own logs/activity during the run, not just MetaGPT's self-reported success)?
- **How invasive was the patch?** Rough count of files touched / lines changed. This is the key data point for the bigger decision — a small, contained patch is a very different signal than one that cascades into many files.
- **Did anything else break or behave unexpectedly** as a side effect of the patch?
- **Quality check:** if the swap worked, look at the actual code Engineer2 produced using the local model — is it reasonable/correct, or did the smaller local model produce noticeably worse output than whatever cloud model MetaGPT defaults to? (Not a rigorous eval, just a sanity read.)
- **Your honest recommendation:** based on how this went, would you lean toward continuing to build on MetaGPT (patched), or toward a lighter custom orchestrator instead? This is a judgment call worth your direct opinion, not just raw facts.

## What NOT to do

- Don't try to patch per-role routing for all four roles (TeamLeader/RoleZero, PM, Architect, Engineer2) — Engineer2 only, for this test.
- Don't fix the Windows Terminal/`pwd` bug unless it's actively blocking this specific test.
- Don't start building the Design role, the two-tier requirements interview, or Graphify integration — all still deferred, unrelated to this task.
- Don't spend more than the timebox chasing a fix if the dead-code gap turns out to be more deeply entangled than expected — report the finding instead.

## Definition of done

A short report answering the 5 points under "What to report back," plus the actual patch (diff or branch) if it was completed, or a clear explanation of where the attempt stalled and why, if it wasn't.
