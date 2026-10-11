---
phase: 05-live-extract-ollama-preflight
plan: 02
subsystem: tracing
tags: [trace, ollama, single-inference, live-extract, tdd, coverage]
status: complete
requires:
  - phase: 05-live-extract-ollama-preflight
    provides: run_live, preflight_ollama, _extract_kwargs, stub Ollama e2e (05-01)
  - phase: 04-stage-wrappers
    provides: model StageRecords with shared in_data per infer call and batch_prompts
provides:
  - check_single_inference(records) enforcing one OllamaLanguageModel.infer with one prompt
  - document length pre-check vs max_char_buffer before preflight/extract
  - run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt) success line
  - TraceExtractRealOllamaTest gated by TRACE_LIVE_OLLAMA=1
  - COVERAGE.md Ollama API decision matrix
affects: [06-annotated-document]
tech-stack:
  added: []
  patterns: [infer-call count via id(in_data), TRACE_LIVE_OLLAMA skipUnless for real Ollama]
key-files:
  created:
    - .planning/phases/05-live-extract-ollama-preflight/COVERAGE.md
    - .planning/phases/05-live-extract-ollama-preflight/05-02-RED-EVIDENCE-task1.json
  modified:
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
    - config.yaml
key-decisions:
  - "Infer calls counted by distinct id(model in_data), not prompt_index==0 alone (WR-05)."
  - "One-chunk pre-check uses document_path text vs config max_char_buffer (post quick-task; sample_text removed)."
  - "max_char_buffer raised to 40000 so example_document.md is one chunk for the real gemma3:4b run."
requirements-completed: [RUN-03, RUN-01]
plan_head_before: d171f77e6bc23a2f00c714b9965722a72b01195d
duration: 4 min
completed: 2026-10-11
actuals:
  tokens: 3353
  tasks: 2
  commits: 3
coverage:
  - id: D1
    description: "Stub e2e run_live ends with the single-call line; /api/tags and /api/generate each hit once"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#TraceExtractGuardTest.test_run_live_ends_with_single_call_line_and_one_generate"
        status: pass
    human_judgment: false
  - id: D2
    description: "check_single_inference rejects 0 calls, 2 calls, and a 2-prompt batch"
    requirement: RUN-03
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractGuardTest.test_check_single_inference_rejects_*"
        status: pass
    human_judgment: false
  - id: D3
    description: "Document longer than max_char_buffer is refused before any Ollama request"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#TraceExtractGuardTest.test_run_live_refuses_document_longer_than_max_char_buffer"
        status: pass
    human_judgment: false
  - id: D4
    description: "Real local gemma3:4b run via TRACE_LIVE_OLLAMA=1 returns 0 with the single-call line"
    requirement: RUN-01
    verification:
      - kind: e2e
        ref: "tests/trace_extract_test.py#TraceExtractRealOllamaTest.test_run_live_completes_against_local_gemma3"
        status: pass
    human_judgment: false
  - id: D5
    description: "COVERAGE.md records /api/tags, /api/generate, and explicit opt-outs"
    requirement: RUN-01
    verification:
      - kind: other
        ref: ".planning/phases/05-live-extract-ollama-preflight/COVERAGE.md"
        status: pass
    human_judgment: false
---

# Phase 5 Plan 02: Single-inference guard & real gemma3:4b Summary

Live runs now fail closed unless Phase 4 recorded exactly one `OllamaLanguageModel.infer` with one prompt, print that contract line on success, refuse over-long documents before any network call, and prove the real `gemma3:4b` path once behind `TRACE_LIVE_OLLAMA=1`.

## What was built

- **Task 1 (TDD):** RED tests for the guard line, 0/2-call and multi-prompt failures, over-long document refusal, and main() exit 1 on guard failure; GREEN adds `check_single_inference`, `_MAX_CHAR_BUFFER` / document pre-check, and the success line in `run_live`.
- **Task 2:** `TraceExtractRealOllamaTest` (skipped unless `TRACE_LIVE_OLLAMA=1`), `COVERAGE.md` decision matrix, `max_char_buffer: 40000` so `data/example_document.md` stays one chunk.

## Commits

| Commit | Message |
|--------|---------|
| 66eff0b | test(05-02): add failing single-inference guard tests |
| 38e781b | feat(05-02): enforce single-inference contract in run_live |
| f0e8850 | feat(05-02): env-gated real gemma3:4b run and Ollama COVERAGE.md |

RED evidence: `05-02-RED-EVIDENCE-task1.json` → `RED_EVIDENCE_OK` (`target_test_failed`). Offline suite: 78 tests, OK (1 skipped). Live test: OK in ~4s against local Ollama.

Non-test Task 1 diff: +42 lines in `scripts/trace_extract.py` (under the 150 budget).

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 1 | 66eff0b | 38e781b | — | Pass |
| 2 | n/a (not tdd) | f0e8850 | — | Pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] `sample_text` → `document_path` after quick 261011-cst**
- **Found during:** Task 1
- **Issue:** Plan still named `config['sample_text']`; quick task removed it in favor of `document_path`.
- **Fix:** Pre-check loads document text and compares `len(document)` to `config.get('max_char_buffer', _MAX_CHAR_BUFFER)`; error text says `document` not `sample_text`.
- **Files modified:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Commit:** 38e781b

**2. [Rule 1 - Bug] Preflight tests hit the length gate on the real 33k document**
- **Found during:** Task 1 GREEN
- **Issue:** `TraceExtractPreflightTest` reused `document_path` from config, so fail-closed tests saw the length error instead of host/model errors.
- **Fix:** Give preflight tests a short temp document and `max_char_buffer: 1000`.
- **Files modified:** `tests/trace_extract_test.py`
- **Commit:** 38e781b

**3. [Rule 2 - Critical] Raise `max_char_buffer` for real one-chunk run**
- **Found during:** Task 2
- **Issue:** `example_document.md` is ~33k chars; with buffer 1000 the new pre-check would refuse the real `TRACE_LIVE_OLLAMA` path.
- **Fix:** Set `max_char_buffer: 40000` in `config.yaml` (quick-task comment already anticipated this).
- **Files modified:** `config.yaml`
- **Commit:** f0e8850

**4. [Rule 1 - Bug] absl logging on stderr broke StartsWith('Error:')**
- **Found during:** Task 1 GREEN
- **Issue:** Provider plugin INFO lines precede the guard `Error:` line when `main([])` runs extract.
- **Fix:** Assert any stderr line starts with `Error:` plus the contract fragment.
- **Files modified:** `tests/trace_extract_test.py`
- **Commit:** 38e781b

**Total deviations:** 4. **Impact:** RUN-03/RUN-01 behavior matches intent; plan wording lagged the quick-task document path.

## Known Stubs

None.

## Threat Flags

None new. T-05-06 (guard + length pre-check), T-05-07 (0 Ollama infers fail), T-05-08 (`request_timeout_s: 300`, live test env-gated) are covered.

## Self-Check: PASSED

- `scripts/trace_extract.py` has `check_single_inference`, `_MAX_CHAR_BUFFER` (≥2), `single-inference contract`; exactly one `lx.extract(`; no non-comment `api/generate`.
- Commits 66eff0b, 38e781b, f0e8850 found; RED precedes GREEN.
- `COVERAGE.md` has `/api/tags`, `/api/generate`, and opt-out rows.
- `TRACE_LIVE_OLLAMA=1` real test OK; offline suite OK with skip.
- No edits under `langextract/` or `examples/`.
