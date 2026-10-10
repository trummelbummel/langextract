---
phase: 02-extraction-snapshots
plan: 01
subsystem: tracing
tags: [trace, snapshot, resolver, alignment, tdd]
status: complete
requires:
  - phase: 01-stage-catalog-contracts
    provides: scripts/trace_extract.py catalog, config loading, redact
provides:
  - ExtractionSnapshot frozen dataclass
  - snapshot_extractions() parse/align field-copy helper
  - print_grounding_pair() before/after printer
affects: [02-02, 04-live-stage-wiring]
tech-stack:
  added: []
  patterns: [snapshot-before-mutation, duck-typed field copy, positional zip pairing]
key-files:
  created:
    - tests/trace_extract_test.py
    - .planning/phases/02-extraction-snapshots/02-01-RED-EVIDENCE-task1.json
    - .planning/phases/02-extraction-snapshots/02-01-RED-EVIDENCE-task2.json
  modified:
    - scripts/trace_extract.py
key-decisions:
  - "Snapshots are duck-typed field copies; langextract is never imported by the script"
  - "Attributes copied one level deep (list values re-listed) instead of copy.deepcopy"
  - "Helpers are exposed but not called from main(); live wiring is Phase 4"
requirements-completed: [STG-05, STG-08]
duration: 9 min
completed: 2026-10-10
plan_head_before: 156e9f2608f5436cbe978aae59e1b9c398b5e71e
actuals:
  tokens: 1800
  tasks: 2
  commits: 4
coverage:
  - deliverable: "Parse snapshot of real Resolver.resolve output stays ungrounded after Resolver.align mutates the live objects"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_parse_snapshot_survives_align_mutation"
        status: pass
    human_judgment: false
  - deliverable: "print_grounding_pair prints a parse line directly followed by an align line per extraction"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_print_grounding_pair_orders_parse_before_align"
        status: pass
    human_judgment: false
  - deliverable: "Snapshots are independent of later mutation of attributes, intervals and status"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_snapshot_independent_of_later_mutation"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 01: Extraction Snapshots Summary

Frozen `ExtractionSnapshot` field copies taken at `Resolver.resolve` and `Resolver.align` time, plus a `print_grounding_pair` printer, so the parse record stays ungrounded even though `Resolver.align` mutates the same `Extraction` objects in place.

## Accomplishments

- `ExtractionSnapshot`, `snapshot_extractions()` and `print_grounding_pair()` added to `scripts/trace_extract.py` (+79 lines non-test, 0 imports of langextract at module top, no `deepcopy`).
- Offline end-to-end proof against the real resolver: `OLLAMA_FORMAT_HANDLER` resolver on canned JSON → parse snapshot → `align` → align snapshot (`[18, 26)` / `match_exact`; unaligned one stays `None`). The test also asserts the live object was mutated while the parse snapshot was not.
- Printed block pairs `parse:` then `align:` per extraction.
- Snapshot attributes copied one level deep; later list appends / key additions / interval and status writes on live objects do not leak in.
- `main()` untouched: catalog stdout is unchanged (no `grounding pair` in output).

## Task Commits

| Task | Phase | Commit | Message |
|------|-------|--------|---------|
| 1 (tracer) | RED | 4d58b88 | test(02-01): add failing tests for extraction snapshot and grounding pair |
| 1 (tracer) | GREEN | ad42767 | feat(02-01): add ExtractionSnapshot, snapshot_extractions, print_grounding_pair |
| 2 | RED | 5dac03c | test(02-01): add failing test for snapshot independence from live mutation |
| 2 | GREEN | 0c2a46c | feat(02-01): copy snapshot attributes so later mutation cannot leak in |

RED evidence (`check tdd-red-evidence` → `RED_EVIDENCE_OK`, `target_test_failed`) is persisted in `02-01-RED-EVIDENCE-task1.json` and `02-01-RED-EVIDENCE-task2.json`. Task 1's RED was a missing-attribute error (feature absent); Task 2's RED was a real assertion failure (`{'dose': ['5mg', '10mg'], 'route': 'oral'} != {'dose': ['5mg']}`).

## Tracer gate

Tracer `<verify>` re-run end-to-end after Task 1 (tests OK, catalog stdout intact, stage-order and align-helper assertions pass) before Task 2 started.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test loader must register the module in `sys.modules`**
- **Found during:** Task 1 GREEN
- **Issue:** `dataclasses.dataclass` on a module loaded via `spec_from_file_location` with `from __future__ import annotations` raised `AttributeError: 'NoneType' object has no attribute '__dict__'` because the module was not in `sys.modules`.
- **Fix:** `sys.modules[spec.name] = module` before `exec_module` in the test's loader (3 lines).
- **Files modified:** `tests/trace_extract_test.py`
- **Commit:** ad42767

**2. [Environment] Plan verify uses bare `python`, which lacks PyYAML here**
- **Found during:** Task 1 verify
- **Issue:** `python scripts/trace_extract.py` (Homebrew python 3.14) fails with `ModuleNotFoundError: yaml` — pre-existing since Phase 1 (`import yaml` at module top), not caused by this plan.
- **Handling:** Ran the identical catalog assertions with `.venv/bin/python`. No package installed. Out of scope; not changed.

**3. [Environment] RED evidence adapter**
- `check tdd-red-evidence` parses node-style TAP, while this project uses absltest and has no pytest in `.venv`. A throwaway script (kept in `/tmp`, not committed) ran the real test file and converted its `[ OK ]` / `[ FAILED ]` lines to TAP for the record. The command, exit code, and failure message are from the real run.

**Total deviations:** 1 auto-fixed (Rule 3), 2 environment notes. **Impact:** none on scope or behavior.

## Diff budget

- `scripts/trace_extract.py`: +79 lines (≤150/task, ≤400/plan), 1 source file; tests excluded.
- Only `scripts/trace_extract.py` and `tests/trace_extract_test.py` changed; nothing under `langextract/` or `examples/`.

## Acceptance Criteria

All PASS: one each of `class ExtractionSnapshot` / `def snapshot_extractions` / `def print_grounding_pair`; 0 `deepcopy`; 0 top-level `langextract` imports in the script; live-mutation and unchanged-parse asserted in the same test; test for `test_snapshot_independent_of_later_mutation` present.

## Known Stubs

None.

## Threat Flags

None. T-02-01 / T-02-02 mitigated: field copies only, objects handed to `Resolver.align` untouched, parse snapshot proven ungrounded after align.

## Next

Ready for 02-02 (empty/unaligned/duplicate edge rendering and mismatch guards).

## TDD Gate Compliance

RED (`test(02-01)`) precedes GREEN (`feat(02-01)`) for both tasks; both with `RED_EVIDENCE_OK`.

## Self-Check: PASSED

- FOUND: scripts/trace_extract.py, tests/trace_extract_test.py, both RED-EVIDENCE files
- FOUND commits: 4d58b88, ad42767, 5dac03c, 0c2a46c
