# Kickoff Brief for Claude Code — Custom Orchestrator Prototype

**Context:** Follow-on to the MetaGPT trials (see `doc/phase1-trial-report.md` and `doc/phase1-patch-report.md`). Both are now historical/reference material, not the implementation base. MetaGPT's per-role LLM routing was successfully patched, but the pipeline still failed because RoleZero's strict tool-calling protocol isn't forgiving of small local models' natural (prose + code) responses. Decision made: build a lighter, purpose-built orchestrator instead. Reference `doc/architecture.md` for full background.

## Goal of this task

Sketch and prototype a minimal orchestrator for the actual Phase 1 pipeline — Planning → Design → Backend → Frontend — where each specialist receives a simple, direct contract (not open-ended multi-step tool-calling) and returns a simple, direct output. No RoleZero-style strict JSON tool-call protocol required — this is the core lesson from the MetaGPT trials.

## Why this should be simpler than MetaGPT

MetaGPT solves a more general problem (simulating an entire software company, arbitrary tasks, arbitrary tool use) than this project needs. The actual Phase 1 requirement is a fixed, known sequence of stages, each with a well-defined input and output:

```
Planning/Requirements → Locked Spec + User Flow
      ↓
Design → Design Tokens (consumes Locked Spec + User Flow)
      ↓
Backend Specialist → Code (consumes Locked Spec + Design Tokens)
Frontend Specialist → Code (consumes Locked Spec + Design Tokens + User Flow)
      ↓
Integration/Verification → pass/fail + affected-file report
```

This is a **fixed pipeline with structured handoffs**, not a dynamic multi-agent negotiation. It doesn't need a general tool-calling protocol at all — each stage can be a straightforward function call: "here is your structured input, return your structured output," validated against a schema after each step.

## Steps

1. **Define the exact contract schema for each handoff** (a first pass — will evolve). At minimum:
   - Planning → Design/Backend/Frontend: the Locked Spec (product type, stack, features) + User Flow (steps/screens/transitions) as structured JSON
   - Design → Backend/Frontend: Design Tokens (colors, typography, spacing, component variants) as structured JSON
   - Backend/Frontend → Integration: generated code + a manifest of files created/modified
2. **Build a minimal Python orchestrator** that:
   - Calls each stage's model (or a stand-in prompt/model for now, if specialists aren't trained yet) with its defined input
   - Validates the output against the expected schema before passing it to the next stage (fail loudly and stop if a stage's output doesn't match the schema, rather than passing through and letting errors cascade)
   - Logs each stage's input/output for debuggability
3. **No tool-calling / ReAct loop needed for a specialist's own turn** — each specialist gets one clear input and produces one clear output in a single pass. (This can be revisited later if a specialist genuinely needs multi-step reasoning within its own stage — but don't build that complexity in from day one.)
4. **Test with a placeholder/cloud model first** (to validate the orchestration logic itself, independent of whether local specialists are ready), then swap in the local Ollama-served models (the ones already validated — e.g. `qwen2.5-coder:1.5b`, or eventually the fine-tuned FastAPI adapter) once the orchestration shape is confirmed to work.
5. **Confirm the local small model actually completes a full Backend stage run** end-to-end with this simpler contract — i.e., verify the core hypothesis from the MetaGPT trial: that small models fail on strict tool-call protocols but succeed with a simple, direct task→code contract.

## What to explicitly avoid

- Don't build a general-purpose agent framework — this is a fixed pipeline, not an open-ended agent system.
- Don't require any specialist to emit structured tool-call JSON as part of *doing its job* — only the orchestrator needs structure (validating what comes back), not the specialist's own generation process.
- Don't try to replicate MetaGPT's SOP/role generality — reuse only the idea of role separation and staged handoffs, not its implementation.
- Don't implement the two-tier requirements interview or Graphify integration yet — still separately deferred/tracked items.

## Definition of done

- A defined (even if provisional) JSON schema for each inter-stage contract
- A working minimal orchestrator script that runs Planning → Design → Backend (Frontend can follow once Backend is proven) using placeholder/cloud models first
- A repeated test using the local Ollama model for the Backend stage specifically, confirming it completes a simple task→code request without needing to navigate a tool-calling protocol
- A short report: did this confirm the hypothesis that small models work fine with simple, direct contracts? Any friction found, and how it compares to the MetaGPT experience.
