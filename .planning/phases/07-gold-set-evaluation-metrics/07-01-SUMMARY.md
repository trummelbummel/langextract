---
phase: 07-gold-set-evaluation-metrics
plan: 01
subsystem: evaluation
tags: [metrics, precision, recall, f1, evaluation, tdd]

requires: []
provides:
  - "Frozen ClassScore + prf_from_counts (empty→0.0, hand-worked 2/3)"
  - "EvaluationReport + report_from_counts (micro from global counts, sorted keys)"
  - "langextract.evaluation package registered in setuptools"
affects:
  - 07-02-span-iou-matching
  - 07-04-evaluate-api

actuals:
  tokens: 2141
  tasks: 2
  commits: 4

plan_head_before: b71471ecd696d1614ebff42fd2cd12e9cb91dde1

tech-stack:
  added: []
  patterns:
    - "Frozen ClassScore + mutable EvaluationReport (prompt_validation analog)"
    - "prf_from_counts / report_from_counts pure helpers before evaluate()"

key-files:
  created:
    - langextract/evaluation/__init__.py
    - langextract/evaluation/metrics.py
    - tests/evaluation_test.py
    - .planning/phases/07-gold-set-evaluation-metrics/07-01-RED-EVIDENCE-task1.json
    - .planning/phases/07-gold-set-evaluation-metrics/07-01-RED-EVIDENCE-task2.json
  modified:
    - pyproject.toml

key-decisions:
  - "Empty TP=FP=FN=0 yields P=R=F1=0.0 (not NaN/raise)"
  - "Micro from global count triple via one prf_from_counts call"
  - "per_class keys sorted alphabetically in report_from_counts"

patterns-established:
  - "Evaluation metrics layer is pure counts→floats; no core.data import yet"
  - "Package stub re-exports metrics symbols; evaluate lands in 07-04"

requirements-completed: [EVAL-01, EVAL-04]

coverage:
  - id: D1
    description: "prf_from_counts returns ClassScore with hand-worked P/R/F1 including empty→0.0 and F1=2/3"
    requirement: EVAL-04
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#MetricsPrfTest.test_prf_from_counts"
        status: pass
    human_judgment: false
  - id: D2
    description: "EvaluationReport aggregates per_class + micro from count triples; micro is global not mean of class F1"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#MetricsReportTest.test_report_from_counts_micro_vs_per_class"
        status: pass
    human_judgment: false
  - id: D3
    description: "langextract.evaluation listed in pyproject.toml setuptools packages"
    requirement: EVAL-01
    verification:
      - kind: other
        ref: "grep langextract.evaluation pyproject.toml"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-11
status: complete
---

# Phase 07 Plan 01: Gold-set evaluation metrics Summary

**Frozen ClassScore / EvaluationReport with hand-worked P/R/F1 (empty→0.0, micro from global counts) as the Phase 7 tracer foundation.**

## Performance

- **Duration:** 2min
- **Started:** 2026-10-11T18:03:03Z
- **Completed:** 2026-10-11T18:05:09Z
- **Tasks:** 2
- **Files modified:** 4 source/config + 1 test (+ 2 RED-evidence JSON)

## Accomplishments

- `prf_from_counts` and frozen `ClassScore` with empty→0.0 and hand-worked 2/3 F1
- `EvaluationReport` + `report_from_counts` with alphabetical per-class keys and micro from global TP/FP/FN
- Package `langextract.evaluation` registered in `pyproject.toml`

## Task Commits

Each task was committed atomically (TDD RED→GREEN):

1. **Task 1 RED: MetricsPrfTest** - `b7e9085` (test)
2. **Task 1 GREEN: ClassScore + prf_from_counts** - `c99a42f` (feat)
3. **Task 2 RED: MetricsReportTest** - `0deb14d` (test)
4. **Task 2 GREEN: EvaluationReport + report_from_counts** - `cac3cdd` (feat)

_Note: TDD tasks have test → feat commit pairs_

## Files Created/Modified

- `langextract/evaluation/metrics.py` - ClassScore, EvaluationReport, prf_from_counts, report_from_counts
- `langextract/evaluation/__init__.py` - Package stub re-exporting metrics symbols
- `tests/evaluation_test.py` - absltest + parameterized hand-worked rows
- `pyproject.toml` - Added `langextract.evaluation` to setuptools packages
- `07-01-RED-EVIDENCE-task1.json` / `task2.json` - TDD RED evidence (TAP from absltest)

## Decisions Made

- Empty counts → 0.0 for P, R, and F1 (A1 / plan assumption)
- Micro is one `prf_from_counts` on the global triple, never mean of per-class F1
- `report_from_counts` sorts class keys alphabetically for stable reports

## Deviations from Plan

None - plan executed exactly as written.

Environment note: `check tdd-red-evidence` expects node-style TAP; absltest `[ FAILED ]` lines were converted to TAP in the persisted RED-evidence records (same pattern as Phase 02/03). Command, exit code, and failure messages are from the real runs.

## TDD Gate Compliance

| Task | RED | GREEN | Evidence |
|------|-----|-------|----------|
| 1 | `b7e9085` | `c99a42f` | RED_EVIDENCE_OK (`test_prf_from_counts_perfect_one_tp`) |
| 2 | `0deb14d` | `cac3cdd` | RED_EVIDENCE_OK (`test_report_from_counts_micro_vs_per_class`) |

## Diff budget

- Task 1 GREEN: 80 non-test lines across 3 files (`metrics.py`, `__init__.py`, `pyproject.toml`) ≤150
- Task 2 GREEN: 34 non-test lines across 2 files ≤40 target
- Plan total ~114 non-test lines; within CLAUDE.md limits

## Known Stubs

None. No evaluate/matching/IoU yet (intentionally deferred to 07-02..07-04).

## Threat Flags

None new. T-07-01 mitigated by frozen hand-worked metric rows in tests.

## Next

Ready for 07-02 (span IoU / matching criteria composing into these count helpers).

## Self-Check: PASSED

- FOUND: langextract/evaluation/metrics.py, langextract/evaluation/__init__.py, tests/evaluation_test.py, pyproject.toml entry, both RED-EVIDENCE files
- FOUND commits: b7e9085, c99a42f, 0deb14d, cac3cdd
- `.venv/bin/python tests/evaluation_test.py` → OK (9 tests); package imports ClassScore, prf_from_counts, EvaluationReport, report_from_counts
