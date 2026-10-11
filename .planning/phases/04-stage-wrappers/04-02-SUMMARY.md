---
phase: 04-stage-wrappers
plan: 02
subsystem: tracing
tags: [trace, wrappers, parse, empty-parse, format-flags, tdd, offline]
status: complete
requires:
  - phase: 04-stage-wrappers
    provides: StageRecord, make_stage_wrappers registry, print_stage_records, _safe_text, _patch_stages/_run_offline_extract helpers (04-01)
  - phase: 02-extraction-snapshots
    provides: snapshot_extractions / ExtractionSnapshot
provides:
  - make_parse_wrapper(sink) (original -> replacement for Resolver.resolve), registered as 'parse'
  - _format_flags(resolver_self) reading the five flags from Resolver.format_handler
  - _diagnose_empty_parse(original, bound) strict re-run of the unwrapped resolve
  - _parse_callout(parse_error, config) and the callout line in print_stage_records
  - config.yaml empty_list_message
affects: [04-03-printers-and-trace-probes, 05-live-call]
tech-stack:
  added: []
  patterns: [original->replacement wrappers, snapshot-before-return, strict re-run diagnosis, messages from config.yaml]
key-files:
  created: []
  modified:
    - scripts/trace_extract.py
    - config.yaml
    - tests/trace_extract_test.py
key-decisions:
  - "Parse record fields: in_data {raw_model_text, flags, suppress_parse_errors}; out_data {extractions, parse_error}."
  - "flags is a dict with exactly format_type (string .value, never the enum), use_fences, strict_fences, use_wrapper, wrapper_key, read only from self.format_handler."
  - "Callout selection rule: only when out_data['extractions'] is empty. parse_error is a str -> config empty_parse_message plus 'error:' line (escaped via _safe_text); parse_error is None -> config empty_list_message. Non-empty parse prints no callout."
  - "_diagnose_empty_parse takes the BoundArguments of the traced call (defaults applied) instead of (self, args, kwargs), so a positionally passed suppress_parse_errors is handled."
requirements-completed: [STG-03, STG-09]
plan_head_before: 789568ebc2bf07fe073786dac78f3eddedb6ac6f
duration: 4 min
completed: 2026-10-11
actuals:
  tokens: 5400
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "One offline lx.extract yields a parse record whose in holds the raw model text (== model out), suppress_parse_errors and the five format flags; out holds ungrounded snapshots while the document is still grounded"
    requirement: STG-09
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_parse_wrapper_records_raw_text_flags_and_ungrounded_snapshots"
        status: pass
  - id: D2
    description: "[parse] prints header, raw text, flags line and extractions"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_print_stage_records_prints_parse_flags_and_snapshots"
        status: pass
  - id: D3
    description: "Empty parse callout: not json / fenced-with-use_fences=False -> empty_parse_message + error; '{\"extractions\": []}' -> empty_list_message only; '' -> empty_parse_message with 'Empty or invalid input string.'"
    requirement: STG-09
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_parse_callout_follows_raw_text_and_diagnosis_not_json (+ fenced_without_use_fences, valid_empty_list)"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_parse_callout_for_empty_string_reply"
        status: pass
  - id: D4
    description: "Callout and raw text escape control characters; diagnosis adds no StageRecord; non-empty parse records parse_error None and prints no callout; config has empty_list_message"
    requirement: STG-09
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_parse_callout_escapes_control_characters"
        status: pass
      - kind: integration
        ref: "tests/trace_extract_test.py#test_parse_diagnosis_adds_no_extra_records (3 cases)"
        status: pass
      - kind: integration
        ref: "tests/trace_extract_test.py#test_parse_non_empty_records_no_error_and_no_callout"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_config_has_empty_list_message"
        status: pass
---

# Phase 4 Plan 02: Parse stage wrapper and empty-parse callout Summary

`make_parse_wrapper` records, from one real offline `lx.extract`, the raw model text and the format flags the Resolver actually used plus ungrounded parse snapshots; an empty result is diagnosed by a strict re-run of the original `resolve` so `[parse]` says in words whether the chunk was omitted by an error or the model returned a valid empty list.

## What was built

- `make_parse_wrapper(sink)`: calls the original `resolve` (no try/except), binds its arguments with `inspect.signature(...).bind` + `apply_defaults`, appends `StageRecord('parse', ...)` before returning, and returns the original result object unchanged. Snapshots are taken at return, so they stay ungrounded after `align` mutates the live objects.
- `_format_flags`: reads `format_type` (converted to its string `.value`), `use_fences`, `strict_fences`, `use_wrapper`, `wrapper_key` from `self.format_handler`, never from `extract()` arguments.
- `_diagnose_empty_parse(original, bound)`: copies the bound arguments, forces `suppress_parse_errors=False`, calls the unwrapped original in `try/except Exception`; returns `'ErrorType: message'` or `None`. Adds no record; its result is discarded.
- `print_stage_records` prints a `callout:` line (plus an `error:` line for errors) after the `in:` block, next to the raw text and before `out:`. Sentences come only from `config.yaml` (`empty_parse_message`, new `empty_list_message`).

### Parse record fields

| Where | Field | Value |
|-------|-------|-------|
| in | `raw_model_text` | the `input_text` passed to `resolve` |
| in | `flags` | dict of the five format flags (primitives) |
| in | `suppress_parse_errors` | bound value (True from `lx.extract`) |
| out | `extractions` | tuple of `ExtractionSnapshot`, grounding fields None |
| out | `parse_error` | `None` when non-empty or a valid empty list; `str` when an empty result was caused by an error |

## Commits

| Commit | Message |
|--------|---------|
| b2f12f7 | test(04-02): add failing parse-stage tracer tests |
| 21e9014 | feat(04-02): parse-stage wrapper with format flags |
| ea0abec | test(04-02): add failing empty-parse callout tests |
| a51a7eb | feat(04-02): empty-parse diagnosis and callout beside raw text |

Non-test diff: 51 lines (Task 1, one source file) and 40 lines (Task 2: 36 in `scripts/trace_extract.py`, 4 in `config.yaml`); 91 total, within the 150 per task / 400 per plan budget. `tests/trace_extract_test.py`: 31 passed (19 + 12 new; matrix is parameterized).

## Deviations from Plan

**1. [Rule 1 - Bug] Empty-string reply cannot go through the offline e2e path**
- **Found during:** Task 2 GREEN
- **Issue:** The plan's matrix includes canned `''` through model + parse, but `OllamaLanguageModel` raises `InferenceRuntimeError` ("did not include generated text") before `resolve` runs.
- **Fix:** `test_parse_callout_for_empty_string_reply` calls the wrapped `Resolver.resolve('')` directly and prints the record; the other three matrix cases stay e2e. The RED commit ea0abec still contained the e2e `''` case (it failed on the missing `parse_error` key); GREEN a51a7eb moved it.
- **Files modified:** tests/trace_extract_test.py
- **Commit:** a51a7eb

**2. [Rule 2 - CLAUDE.md] Parameterized tests instead of a subTest loop**
- CLAUDE.md requires `parameterized.named_parameters` over loops; `TraceExtractWrapperTest` base class changed from `absltest.TestCase` to `parameterized.TestCase` (one-line change, import added).

**3. [Minor] `_diagnose_empty_parse` signature**
- Takes `(original, bound)` rather than `(original, self, args, kwargs)`; this is the "bind and rebuild" form the plan asked for when `suppress_parse_errors` may be positional.

**4. [Tooling] Test K already green at RED**
- The escape test passes before the callout exists (raw text was already escaped by 04-01's `_safe_text`); it stays as a guard for the new error line (T-04-05).

**Total deviations:** 4 (1 bug-in-plan, 1 CLAUDE.md, 2 minor). **Impact:** none on behavior or scope.

## Deferred / out of scope

- `.venv` lacks `openai`; `pytest tests -m "not live_api and not integration"` stops on 2 collection errors (`provider_schema_test` and another), same pre-existing cause noted in 04-01. Not touched.
- Unrelated dirty files left alone: `.gitignore`, `.gsd/dispatch-isolation-sentinel.json`, `.planning/phases/03-.../03-DISCUSS-CHECKPOINT.json`, untracked `amp`, `.gsd/dispatch-04-0{1,2}-prompt.md`.

## Known Stubs

None.

## Threat Flags

None. T-04-05 (error text through `_safe_text`; escape test), T-04-06 (original result returned, snapshots before return; Test H), T-04-07 (strict re-run distinguishes valid-empty from error; matrix) are covered. T-04-08 accepted (re-run only on empty result).

## Self-Check: PASSED

- scripts/trace_extract.py, config.yaml, tests/trace_extract_test.py exist; commits b2f12f7, 21e9014, ea0abec, a51a7eb found; RED commits precede GREEN.
- `tests/trace_extract_test.py`: 31 passed (≥24). Catalog-only `python scripts/trace_extract.py` prints 7 headers and no `in:`/`out:` lines. No callout sentence literals in the script; no top-level `langextract` import in the script; no edits under `langextract/` or `examples/ollama/demo_ollama.py`.
