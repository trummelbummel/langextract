---
phase: 04-stage-wrappers
plan: 01
subsystem: tracing
tags: [trace, wrappers, stage-record, tdd, offline]
status: complete
requires:
  - phase: 02-extraction-snapshots
    provides: redact(), ExtractionSnapshot (unused here), STAGE_CATALOG headers
provides:
  - StageRecord frozen dataclass (label, in_data, out_data)
  - make_model_wrapper / make_chunk_wrapper / make_prompt_wrapper (original -> replacement)
  - make_stage_wrappers(sink, config) registry for chunk, prompt, model
  - print_stage_records(records, config) with _print_block and _safe_text
  - tests helpers _patch_stages and _run_offline_extract
affects: [04-02-parse-align-wrappers, 04-03-printers-and-trace-probes, 05-live-call]
tech-stack:
  added: []
  patterns: [collect-then-print, original->replacement wrappers, next()-driven iterator wrapper, mock.patch.object via enter_context]
key-files:
  created: []
  modified:
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
key-decisions:
  - "make_stage_wrappers keys are catalog labels; values are original -> replacement callables (A1). This plan registers chunk, prompt, model."
  - "Model records: one per yielded ScoredOutput. out_data.prompt_index is the 0-based position of the yield within that infer call (not a global counter); in_data.batch_size is len(batch_prompts). Phase 5 can count infer calls as model records with prompt_index == 0."
  - "Printer prints sequences of non-empty strings (batch_prompts) as one indented block per item so prompts appear unchanged rather than pformat-wrapped."
requirements-completed: [STG-03, STG-04]
plan_head_before: bb10d38a4b9699e4590d334243ea82a8bf43bf34
duration: 6 min
completed: 2026-10-11
actuals:
  tokens: 3650
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "One offline real lx.extract yields a model StageRecord with full batch prompt in and verbatim raw model text out; out keys are exactly prompt_index, score, raw_model_text"
    requirement: STG-04
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_model_wrapper_records_prompt_and_raw_text_from_offline_extract"
        status: pass
  - id: D2
    description: "print_stage_records prints catalog headers in catalog order, escapes control characters, prints empty raw text as ''"
    requirement: STG-03
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_print_stage_records_escapes_control_characters_in_raw_text"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_print_stage_records_prints_empty_raw_text_explicitly"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_print_stage_records_follows_catalog_order_and_skips_missing"
        status: pass
  - id: D3
    description: "Chunk wrapper yields the same chunks via next() without RecursionError and restores the class attribute"
    requirement: STG-03
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_chunk_wrapper_yields_same_chunks_without_recursion"
        status: pass
  - id: D4
    description: "Prompt record equals model batch_prompts[0] for the same offline extract; chunk, prompt, model print in catalog order"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_prompt_record_matches_model_batch_prompt_from_offline_extract"
        status: pass
      - kind: integration
        ref: "tests/trace_extract_test.py#test_print_stage_records_orders_chunk_prompt_model_from_extract"
        status: pass
---

# Phase 4 Plan 01: Model, chunk and prompt stage wrappers Summary

Record -> wrapper -> printer path proven end-to-end through one real offline `lx.extract` (only `OllamaLanguageModel._ollama_query` faked, one fake HTTP call): model, chunk and prompt wrappers append `StageRecord`s to a caller-owned list and `print_stage_records` prints them under the existing `[label] function — path` headers in catalog order.

## What was built

- `StageRecord(label, in_data, out_data)`, `_safe_text` (keeps newline/tab/printable text, escapes other control characters as `\x1b` etc.).
- `make_model_wrapper(sink, redact_keys)`: reads `batch_prompts` via `inspect.signature(...).bind`, forwards the original args, yields the same `ScoredOutput` lists lazily; kwargs minus `batch_prompts` are stored through `redact(..., keys=)`.
- `make_chunk_wrapper(sink)`: `next(it)` loop (no for-in / yield-from over `original(...)`), yields the same `TextChunk` objects.
- `make_prompt_wrapper(sink)`: calls `build_prompt` exactly once, records chunk_text, document_id, additional_context (None kept explicit), context_window_chars, and the prompt string; returns the prompt unchanged.
- `make_stage_wrappers(sink, config)` -> `{'chunk', 'prompt', 'model'}`; parse/align are 04-02.
- `print_stage_records(records, config)`: catalog order, blank line between sections, `in:` / `out:` blocks, empty strings as `''`. `main()` is unchanged: catalog-only output still has 7 headers and no `in:`/`out:` lines.

## Contract notes for later plans

- `make_stage_wrappers` values are `original -> replacement`; Phase 3 `trace_probes` (not yet landed) should install them the way `_patch_stages` does with `mock.patch.object(cls, attr, wrapper(cls.__dict__[attr]))`.
- Model record granularity: one record per `ScoredOutput`; Phase 5's single-inference guard counts records with `out_data['prompt_index'] == 0`. Records from one infer call share the same `in_data` dict.
- Test helpers: `_patch_stages(test, wrappers, labels)` (uses `_STAGE_TARGETS`, includes parse/align targets for 04-02) and `_run_offline_extract(test, canned)` returning `(document, fake_call_count)`.

## Commits

| Commit | Message |
|--------|---------|
| 9392bae | test(04-01): add failing model-stage tracer tests |
| 5feb6fe | feat(04-01): model-stage tracer wrapper, StageRecord and stage printer |
| 9b8811f | test(04-01): add failing chunk/prompt wrapper tests |
| 8e677db | feat(04-01): chunk and prompt stage wrappers |

Non-test diff: 126 lines (Task 1, one source file) and 83 lines (Task 2, one source file); 209 total, within the 150 per task / 400 per plan budget. Both tasks exceeded the plan's own estimates (~80 and ~45) but not the budget.

## Deviations from Plan

**1. [Rule 1 - Bug] Task 2 test built `ChunkIterator` without `tokenizer_impl`**
- **Found during:** Task 2 GREEN
- **Issue:** The plan's Test E form `ChunkIterator(text=..., max_char_buffer=1000)` raises `TypeError` (`tokenizer_impl` is required in this tree).
- **Fix:** The test passes `tokenizer_impl=tokenizer_lib.RegexTokenizer()` (same default as `annotation.py`).
- **Files modified:** tests/trace_extract_test.py
- **Commit:** 8e677db (RED commit 9b8811f therefore failed first on `KeyError: 'chunk'`, a missing registry entry, before the constructor call was reached).

**2. [Rule 2 - Missing critical] Prompt sequences printed as separate blocks**
- **Issue:** Printing `batch_prompts` through `pformat` would wrap and escape the multi-line few-shot prompt, so it would not appear unchanged (STG-03 "full payloads").
- **Fix:** `_print_block` prints lists/tuples of non-empty strings as one indented, `_safe_text`-escaped block per item; other non-str values still use `pformat`. About 7 extra lines.
- **Commit:** 5feb6fe

**3. [Tooling] `check tdd-red-evidence` cannot classify pytest output**
- The checker only parses Node TAP output, so the pytest RED run for Task 1 returned `INVALID_RED / zero_tests_discovered` (0 tests parsed). I did not reshape the output to satisfy it. RED validity was established manually: the target tests failed on a missing symbol (`AttributeError: module 'trace_extract' has no attribute 'StageRecord'` / `make_stage_wrappers`) after the 11 existing tests passed, which is the failure the plan prescribes. Task 2 RED failed with `KeyError: 'chunk'` for the same reason. No RED-evidence JSON files were committed.

**4. [Process] Dispatch-brief pin guard**
- The first dispatch had a pin guard whose unbound-sentinel arm matched the real pin, so I halted. The regenerated brief was fixed. For this run I wrote the guard logic to a scratch file under /tmp and ran it before every Edit/Write and commit; I shortened only the failure-message text, not the checks.
- The pre-commit isort / pyink hooks reformatted the test file during the first commit of Tasks 1 and 2 (the commit was aborted); I re-staged the reformatted file and committed again, without `--no-verify`.

## Deferred / out of scope

- `.venv` lacks `openai` (and the plugin tests fail): the full `pytest tests -m "not live_api and not integration"` run shows 45 failed / 2 collection errors in `factory_test`, `provider_schema_test`, `create_provider_plugin_test`, `factory_schema_test`, `inference_test`, `test_kwargs_passthrough`. None touch `scripts/trace_extract.py`; 801 passed. `tests/trace_extract_test.py`: 19 passed (11 existing + 8 new). Not fixed.
- Unrelated dirty files left alone: `.gitignore`, `.gsd/dispatch-isolation-sentinel.json`, `.planning/phases/03-.../03-DISCUSS-CHECKPOINT.json`, untracked `amp` and `.gsd/dispatch-04-01-prompt.md`.

## Known Stubs

None.

## Threat Flags

None. T-04-01 (escape control characters), T-04-02 (redact kwargs), T-04-03 (lazy same-object yields, `next()` loop) and T-04-04 (`mock.patch.object`, class attribute restored) are covered by tests.

## Self-Check: PASSED

- scripts/trace_extract.py and tests/trace_extract_test.py exist; commits 9392bae, 5feb6fe, 9b8811f, 8e677db found; RED commits precede GREEN commits.
- Plan verification re-run: 19 passed; catalog-only output shows 7 headers and no `in:`/`out:` lines; no top-level `langextract` import and no for-in/yield-from over `original(...)` in the script.
