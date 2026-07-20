# Kickoff Brief for Claude Code — Phase 1 Trial

**Context:** This is the first concrete step from a larger architecture plan (see `democratized-ai-coding-architecture.md` for full background — attach or paste that doc for context). Don't try to build the whole system described there yet. This task is scoped narrowly to one proof-of-concept.

## Goal of this task

Validate whether MetaGPT can be used as orchestration scaffolding for a multi-agent AI coding system that eventually routes each agent role to a small, locally-hosted fine-tuned model (via Ollama) instead of a large cloud LLM.

## Steps

1. **Clone MetaGPT** — `github.com/FoundationAgents/MetaGPT` (MIT licensed). Install it (`pip install metagpt` or from source).
2. **Run one baseline project** using MetaGPT's default cloud-model config (whatever's easiest to get working first — doesn't need to be a real product, a simple test prompt like "build a CLI to-do list app" is fine). Goal: observe firsthand how it structures its roles (Product Manager, Architect, Project Manager, Engineer) and how it hands off documents/output between them.
3. **Identify the Ollama swap point** — MetaGPT supports Ollama as an LLM backend via config. Find exactly where/how a role's model backend is configured.
4. **Attempt the swap on ONE role only** — pick the Engineer role specifically. Point just that role's config at a local Ollama-served model (any available model is fine for this test — doesn't need to be the final fine-tuned specialist yet). Leave the other roles (PM, Architect, Project Manager) on the default cloud config for this test.
5. **Report back on:**
   - Did the single-role Ollama swap work without breaking the pipeline?
   - What format does MetaGPT expect for role handoffs (markdown docs vs. structured JSON)? This matters for later — we plan to use strict versioned contracts, not just documents.
   - Does MetaGPT ask the user any clarifying questions during the process, or does it go straight from a one-line prompt to output? (Expectation based on prior research: it does NOT ask — confirm or correct this.)
   - Any friction points that suggest MetaGPT's assumptions (cloud-model-shaped calls, document-based handoffs) fight against a local/small-model, strict-contract design.

## What NOT to do yet

- Don't build the Design role (doesn't exist in MetaGPT — that's a later task).
- Don't implement the two-tier requirements interview (delta vs. full re-plan) — that's explicitly deferred per the working doc.
- Don't integrate Graphify or any dependency-graph tooling yet.
- Don't attempt to swap all four roles to local models — just the one (Engineer), to keep this a clean, isolated test.

## Definition of done for this task

A short report (a few paragraphs is fine) answering the 4 questions in step 5, plus whatever code/config changes were needed to get the single-role Ollama swap working, saved somewhere reviewable (e.g. a forked branch or a diff).
