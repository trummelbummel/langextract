# Roadmap: LangExtract pipeline trace

## Overview

Build `scripts/trace_extract.py` — a one-call printed walkthrough of `lx.extract()` against local Ollama `gemma3:4b`. Phases grow the script in reviewable slices (CLAUDE.md: ~150 non-test lines / ≤3 source files per task; one script file). Each phase leaves a runnable check: catalog without a model, snapshot distinguishability, safe probes, live stage capture, then one real extract and a matching `AnnotatedDocument`. No library API changes; `examples/ollama/demo_ollama.py` untouched.

## Milestones

- 🚧 **v1.0 MVP** — Script-only pipeline trace (Phases 1–6)

## Phases

- [x] **Phase 1: Stage catalog & contracts** - Script skeleton with stable stage labels, owners, and script-only boundaries (completed 2026-10-10)
- [x] **Phase 2: Extraction snapshots** - Field copies that keep parse (ungrounded) distinct from align (grounded) (completed 2026-10-10)
- [x] **Phase 3: Call-scoped probe manager** - Install and restore five class wraps in `finally` before any live call (completed 2026-10-11)
- [x] **Phase 4: Stage wrappers** - Capture chunk → prompt → infer → resolve → align with live in/out records (completed 2026-10-11)
- [ ] **Phase 5: Live extract & Ollama preflight** - One `lx.extract()` against `gemma3:4b` with clear preflight failure
- [ ] **Phase 6: AnnotatedDocument & walkthrough close** - Print the returned document and verify the full stage dump

## Phase Details

### Phase 1: Stage catalog & contracts

**Goal:** As a library maintainer, I want to run the script and see the stage contract (ordered labels + owning function/file) plus a static call header from config.yaml, so that I know which code owns each extract stage without touching the library or the Ollama demo.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** CTR-01, CTR-02, STG-01, STG-02
**Success Criteria** (what must be TRUE):

  1. Running `python scripts/trace_extract.py` prints the seven stage labels in order: prompt-template, chunk, prompt, model, parse, align, annotated-document
  2. Each printed stage names an owning function and a repo-relative file path
  3. Diffs under this phase touch only `scripts/trace_extract.py` and repo-root `config.yaml` (and tests if any) — no edits under `langextract/` and no edits to `examples/ollama/demo_ollama.py`

**Plans:** 2/2 plans complete

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking skeleton: config.yaml call constants + runnable seven-stage catalog

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — empty_parse_message + redact_keys in config; redact() stub in script

### Phase 2: Extraction snapshots

**Goal:** Developer can print ungrounded vs grounded extraction field copies so parse and align stay a before/after pair even after align mutates objects
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** STG-05, STG-08
**Success Criteria** (what must be TRUE):

  1. A snapshot of parse-time extractions shows `char_interval` / `alignment_status` still empty (including empty lists)
  2. A later align snapshot of the same logical extractions shows grounding fields populated (or explicitly ungrounded) without overwriting the parse snapshot
  3. Printed output presents parse and align as a before/after grounding pair for those extractions

**Plans:** 2/2 plans complete

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Tracer: snapshot at resolve + align, print the pair (real Resolver offline)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Empty lists, config `ungrounded` label, positional pairing guards

### Phase 3: Call-scoped probe manager

**Goal:** Developer can install observation wraps for one call and always get original class attributes back afterward (success or exception)
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** —
**Success Criteria** (what must be TRUE):

  1. Entering the probe context installs wraps on the five methods `extract` already calls (`ChunkIterator.__iter__`, `ContextAwarePromptBuilder.build_prompt`, `OllamaLanguageModel.infer`, `Resolver.resolve`, `Resolver.align`)
  2. Exiting normally restores the original class attributes so a second call outside the context is unwrapped
  3. An exception raised inside the context still restores the original class attributes (`finally` path)

**Plans:** 2/2 plans complete

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Tracer: `trace_probes()` installs five identity wraps; finally restore; re-entry + mid-install rollback

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Optional `wrappers=` partial-fill; in-script restore self-check wired after catalog in `main`

### Phase 4: Stage wrappers

**Goal:** Developer can see live data in/out for chunk through align, with raw model text, empty-parse callouts, and format flags — without requiring a warm model yet
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** STG-03, STG-04, STG-06, STG-09
**Success Criteria** (what must be TRUE):

  1. Exercising the wrappers produces stage records with live data in and data out for each instrumented stage (full payloads for a short sample)
  2. Model-stage output shows raw model text separately from parsed extractions
  3. Align-stage output shows spans, status, chunk offsets (even when 0), and source slice or `ungrounded`
  4. Empty parse is called out in words next to the raw model text, and parse inputs include format/fence/wrapper flags

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Tracer: StageRecord + model wrapper + stage printer via offline lx.extract; chunk and prompt wrappers

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Parse wrapper with format/fence/wrapper flags; truthful empty-parse callout (empty_list_message)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-03-PLAN.md — Align wrapper with offsets/slices/ungrounded; five-stage walkthrough; trace_probes integration (Phase 3 landed; UAT covered restore path)

### Phase 5: Live extract & Ollama preflight

**Goal:** Developer can run one real `lx.extract()` against local Ollama `gemma3:4b` and get a clear failure if the host or model is missing
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** RUN-01, RUN-02, RUN-03
**Success Criteria** (what must be TRUE):

  1. With Ollama up and `gemma3:4b` present, `python scripts/trace_extract.py` completes one short-document run end-to-end
  2. With Ollama down or `gemma3:4b` missing, the script exits with a clear error before printing a fake empty walkthrough
  3. The run performs exactly one `lx.extract()` and exactly one model `infer` (no second inference, no cloud providers)

**Plans:** 2 plans

Plans:
**Wave 1**

- [ ] 05-01-PLAN.md — Tracer: preflight → one lx.extract inside probes → walkthrough (stub Ollama); fail-closed preflight

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 05-02-PLAN.md — Single-inference guard + one-chunk pre-check; real gemma3:4b run; COVERAGE.md

### Phase 6: AnnotatedDocument & walkthrough close

**Goal:** Developer can read the `AnnotatedDocument` from that same `extract()` call as the final stage and trust the printed walkthrough matches it
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** STG-07
**Success Criteria** (what must be TRUE):

  1. The final stage prints the `AnnotatedDocument` returned by the same `extract()` call that drove the probes
  2. Document-level extractions are consistent with the last align snapshots for that call (same texts / grounding story)
  3. A full successful run prints all seven stages in order with owners, live in/out, and the final document

**Plans:** TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stage catalog & contracts | 2/2 | Complete    | 2026-10-10 |
| 2. Extraction snapshots | 2/2 | Complete    | 2026-10-10 |
| 3. Call-scoped probe manager | 2/2 | Complete    | 2026-10-11 |
| 4. Stage wrappers | 3/3 | Complete    | 2026-10-11 |
| 5. Live extract & Ollama preflight | 0/2 | In progress | - |
| 6. AnnotatedDocument & walkthrough close | 0/TBD | Not started | - |

## Coverage map

| Requirement | Phase |
|-------------|-------|
| RUN-01 | Phase 5 |
| RUN-02 | Phase 5 |
| RUN-03 | Phase 5 |
| STG-01 | Phase 1 |
| STG-02 | Phase 1 |
| STG-03 | Phase 4 |
| STG-04 | Phase 4 |
| STG-05 | Phase 2 |
| STG-06 | Phase 4 |
| STG-07 | Phase 6 |
| STG-08 | Phase 2 |
| STG-09 | Phase 4 |
| CTR-01 | Phase 1 |
| CTR-02 | Phase 1 |

**Coverage:** 14/14 v1 requirements mapped ✓

## Notes for planning

- Primary deliverable: `scripts/trace_extract.py` plus repo-root `config.yaml` (Phase 1 D-10/D-12). Respect CLAUDE.md per-task budget; Phase 4 may need multiple plans if wrappers exceed ~150 lines.
- Phase 3 has no REQ-ID (restore discipline / Pitfall 7) but is a hard gate before live Ollama.
- Deeper research at plan time: Phase 4 method signatures/generators; Phase 5 cold-load timeout on this machine.
- v2 deferred: STG-10 (two-chunk), STG-11 (prompt-validation), STG-12 (WordAligner parameter echo).
