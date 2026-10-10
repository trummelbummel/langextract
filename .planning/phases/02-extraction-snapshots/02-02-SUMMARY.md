---
phase: 02-extraction-snapshots
plan: 02
subsystem: tracing
tags: [trace, snapshot, grounding, edge-cases, tdd]
status: complete
requires:
  - phase: 02-extraction-snapshots
    provides: ExtractionSnapshot, snapshot_extractions, print_grounding_pair (02-01)
provides:
  - ungrounded_label display constant in config.yaml
  - print_grounding_pair(parse, align, ungrounded_label) with explicit empty and ungrounded rendering
  - Positional pairing guards (TypeError / ValueError) before any output
affects: [04-live-stage-wiring]
tech-stack:
  added: []
  patterns: [validate-before-print, config-driven display constants]
key-files:
  created:
    - .planning/phases/02-extraction-snapshots/02-02-RED-EVIDENCE-task1.json
    - .planning/phases/02-extraction-snapshots/02-02-RED-EVIDENCE-task2.json
  modified:
    - config.yaml
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
key-decisions:
  - "Ungrounded marker applies to the align line only; the parse line keeps raw None (not-yet-grounded contract)"
  - "Pairing is strictly positional; count or (class, text) desync raises instead of printing a partial pair"
requirements-completed: [STG-05, STG-08]
duration: 10 min
completed: 2026-10-10
plan_head_before: fd76f5688ecd65a60eec37c6bb43131f3cfae1c9
actuals:
  tokens: 1500
  tasks: 2
  commits: 4
coverage:
  - deliverable: "Empty Resolver.resolve prints 0 extractions with parse: [] and align: []"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_empty_parse_prints_explicit_empty_lists"
        status: pass
    human_judgment: false
  - deliverable: "Unaligned extraction shows config ungrounded label on align line, None on parse line"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_unaligned_extraction_prints_ungrounded_label"
        status: pass
    human_judgment: false
  - deliverable: "Duplicates and touching spans are paired by position in stable order"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_duplicate_extractions_stay_separate_in_order"
        status: pass
    human_judgment: false
  - deliverable: "Count mismatch, text mismatch and live Extraction input raise before output"
    verification:
      - kind: test
        ref: "tests/trace_extract_test.py#test_count_mismatch_raises_before_printing"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 02: Edge Rendering and Pairing Guards Summary

`print_grounding_pair` now states empty parses and failed groundings explicitly (`parse: []` / `align: []`, align-side `ungrounded` read from `config.yaml`) and refuses desynced or live-object input with `TypeError` / `ValueError` before printing anything.

## Accomplishments

- `ungrounded_label: ungrounded` added to `config.yaml`; no literal `'ungrounded'` in script code.
- Empty pair prints the `0 extractions` header plus explicit `parse: []` and `align: []` lines, verified against a real `Resolver.resolve('not json', suppress_parse_errors=True)` → `[]`.
- Unaligned extraction: parse line `char_interval=None alignment_status=None`, align line `char_interval=ungrounded alignment_status=ungrounded`; grounded `headache` still shows `[18, 26)` / `match_exact`.
- Guards: non-`ExtractionSnapshot` items → `TypeError`; count mismatch → `ValueError` naming both counts; class/text mismatch → `ValueError` naming the 1-based position.
- Duplicates and touching spans stay separate pairs in resolve order.
- `main()` untouched; catalog stdout still has no `grounding pair`, `ungrounded`, or `empty_parse_message` (D-13).

## Task Commits

| Task | Phase | Commit | Message |
|------|-------|--------|---------|
| 1 | RED | 75b9e96 | test(02-02): add failing tests for empty parse and ungrounded align label |
| 1 | GREEN | 2234c1e | feat(02-02): render empty parse and ungrounded align explicitly |
| 2 | RED | 3a1b83d | test(02-02): add failing tests for pairing guards and duplicates |
| 2 | GREEN | d60301a | feat(02-02): guard parse/align pairing by type, count and identity |

RED evidence for both tasks verified with `check tdd-red-evidence` → `RED_EVIDENCE_OK` (`target_test_failed`), stored in `02-02-RED-EVIDENCE-task{1,2}.json`. Task 1 RED failed on signature/config-key errors (feature absent); Task 2 RED failed on real assertions (`ValueError not raised`, `TypeError not raised`).

## Deviations from Plan

None - plan executed exactly as written.

Environment notes (unchanged from 02-01): bare `python` lacks PyYAML, so plan verify commands were run with `.venv/bin/python`; the RED-evidence TAP was written by hand from the real absltest run output (absltest vs node-TAP format). No packages installed.

## Diff budget

- Non-test: `scripts/trace_extract.py` + `config.yaml` = +48/-8 lines total across the plan (Task 1 ≈ 25, Task 2 ≈ 23), 2 source files; within the 150/task and 400/plan limits.
- Nothing under `langextract/` or `examples/` changed.

## Known Stubs

None.

## Threat Flags

None. T-02-04 mitigated: type, count, and identity checks run before any output.

## TDD Gate Compliance

RED (`test(02-02)`) precedes GREEN (`feat(02-02)`) for both tasks, each with `RED_EVIDENCE_OK`.

## Self-Check: PASSED

- FOUND: config.yaml, scripts/trace_extract.py, tests/trace_extract_test.py, both 02-02 RED-EVIDENCE files
- FOUND commits: 75b9e96, 2234c1e, 3a1b83d, d60301a
- 11 tests OK; catalog run exit 0, stdout unchanged
