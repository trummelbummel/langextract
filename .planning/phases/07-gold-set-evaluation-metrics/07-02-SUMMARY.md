---
phase: 07-gold-set-evaluation-metrics
plan: 02
subsystem: evaluation
tags: [span-iou, match-criterion, SameClass, SpanIoU, AttributesEqual, TextMatch, tdd]

requires:
  - phase: 07-01
    provides: "langextract.evaluation package + metrics exports"
provides:
  - "MatchCriterion Protocol + exclusive-end span_iou"
  - "SameClass, SpanIoU(threshold=0.5), AttributesEqual, TextMatch(text_eval_func)"
affects:
  - 07-03-greedy-match
  - 07-04-evaluate-api

actuals:
  tokens: 3417
  tasks: 2
  commits: 4

plan_head_before: 272c03d510f90d5bb898db05b881f55a4640e598

tech-stack:
  added: []
  patterns:
    - "typing.Protocol MatchCriterion with frozen dataclass callables"
    - "TextMatch injects Callable[[str, str], bool] — no Evaluation ABC"

key-files:
  created:
    - langextract/evaluation/criteria.py
    - .planning/phases/07-gold-set-evaluation-metrics/07-02-RED-EVIDENCE-task1.json
    - .planning/phases/07-gold-set-evaluation-metrics/07-02-RED-EVIDENCE-task2.json
  modified:
    - langextract/evaluation/__init__.py
    - tests/evaluation_test.py

key-decisions:
  - "span_iou uses half-open exclusive end_pos; end < start → 0.0"
  - "SpanIoU matches with >= threshold (default 0.5)"
  - "TextMatch requires text_eval_func: Callable[[str, str], bool]"

patterns-established:
  - "criteria.py imports only langextract.core.data (D-05)"
  - "Yes/no MatchCriterion separate from greedy ranking score span_iou (D-02)"

requirements-completed: [EVAL-02, EVAL-04]

coverage:
  - id: D1
    description: "span_iou hand-worked exclusive-end floats (1.0, 2/18, 0.8) plus None/partial/inverted/touching → 0.0"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#CriteriaSpanIoUTest.test_span_iou"
        status: pass
    human_judgment: false
  - id: D2
    description: "SameClass + SpanIoU(threshold) with ≥ 0.5 default and exact-0.5 match"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#CriteriaSpanIoUTest.test_span_iou_criterion"
        status: pass
    human_judgment: false
  - id: D3
    description: "AttributesEqual (== including None) and TextMatch(fn) injection"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#CriteriaOptionalTest"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-11
status: complete
---

# Phase 07 Plan 02: Gold-set evaluation metrics Summary

**MatchCriterion protocol with exclusive-end `span_iou` and frozen SameClass / SpanIoU / AttributesEqual / TextMatch callables for gold-set matching.**

## Performance

- **Duration:** 2min
- **Started:** 2026-10-11T18:10:38Z
- **Completed:** 2026-10-11T18:12:22Z
- **Tasks:** 2
- **Files modified:** 3 source + 1 test (+ 2 RED-evidence JSON)

## Accomplishments

- `span_iou` half-open IoU with RESEARCH floats (1.0, 2/18, 0.8) and guards → 0.0
- `SameClass` + `SpanIoU(threshold=0.5)` with ≥ semantics including exact 0.5
- `AttributesEqual` and `TextMatch(text_eval_func)` Protocol callables; package re-exports

## Task Commits

Each task was committed atomically (TDD RED→GREEN):

1. **Task 1 RED: CriteriaSpanIoUTest** - `428c03e` (test)
2. **Task 1 GREEN: span_iou + SameClass + SpanIoU** - `82fe72d` (feat)
3. **Task 2 RED: CriteriaOptionalTest** - `b0686b1` (test)
4. **Task 2 GREEN: AttributesEqual + TextMatch** - `7fe0ef1` (feat)

_Note: TDD tasks have test → feat commit pairs_

## Files Created/Modified

- `langextract/evaluation/criteria.py` - MatchCriterion, span_iou, SameClass, SpanIoU, AttributesEqual, TextMatch
- `langextract/evaluation/__init__.py` - Re-exports criteria symbols
- `tests/evaluation_test.py` - CriteriaSpanIoUTest + CriteriaOptionalTest
- `07-02-RED-EVIDENCE-task1.json` / `task2.json` - TDD RED evidence (TAP)

## Decisions Made

- Exclusive-end IoU; inverted intervals return 0.0 before inter/union math
- Threshold contract is ≥ (not strict >); default 0.5
- TextMatch requires injected `Callable[[str, str], bool]` — no Evaluation ABC (D-03)

## Deviations from Plan

None - plan executed exactly as written.

Environment note: `check tdd-red-evidence` expects node-style TAP; absltest failures converted to TAP in persisted RED-evidence records (same pattern as 07-01).

## TDD Gate Compliance

| Task | RED | GREEN | Evidence |
|------|-----|-------|----------|
| 1 | `428c03e` | `82fe72d` | RED_EVIDENCE_OK (`test_span_iou_perfect_identical`) |
| 2 | `b0686b1` | `7fe0ef1` | RED_EVIDENCE_OK (`test_text_match_delegates_to_injected_callable`) |

## Diff budget

- Task 1 GREEN: 83 non-test lines across 2 files ≤150
- Task 2 GREEN: 27 non-test lines across 2 files ≤50 target
- Plan total ~110 non-test lines; within CLAUDE.md limits

## Known Stubs

None. Greedy matching / `evaluate()` deferred to 07-03 / 07-04.

## Threat Flags

None new. T-07-04 mitigated by hand-worked IoU + None→0.0; T-07-05 by core.data-only imports.

## Next

Ready for 07-03 (greedy_match composing these criteria + span_iou ranking).

## Self-Check: PASSED

- FOUND: langextract/evaluation/criteria.py, updated __init__.py, tests/evaluation_test.py, both RED-EVIDENCE files
- FOUND commits: 428c03e, 82fe72d, b0686b1, 7fe0ef1
- `.venv/bin/python tests/evaluation_test.py` → OK (28 tests)
- Exports: span_iou, SameClass, SpanIoU, AttributesEqual, TextMatch, MatchCriterion
