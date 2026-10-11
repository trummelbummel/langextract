---
phase: 07-gold-set-evaluation-metrics
plan: 04
subsystem: evaluation
tags: [evaluate, greedy-match, lazy-export, import-linter, tdd]

requires:
  - phase: 07-03
    provides: "greedy_match + MatchCriterion criteria + report_from_counts"
provides:
  - "evaluate() orchestrator pairing docs → greedy_match → EvaluationReport"
  - "Lazy lx.evaluation via _LAZY_MODULES (no top-level lx.evaluate)"
  - "import-linter contracts for evaluation layering"
affects:
  - 07-05-docs-ci-example

actuals:
  tokens: 4703
  tasks: 2
  commits: 4

plan_head_before: 9c7a3513934b71ba3b763a03828e8cfdae7d6e08

tech-stack:
  added: []
  patterns:
    - "criteria= XOR non-default convenience flags → ValueError"
    - "document_id indexing rejects duplicates; identical sets required"

key-files:
  created:
    - .planning/phases/07-gold-set-evaluation-metrics/07-04-RED-EVIDENCE-task1.json
    - .planning/phases/07-gold-set-evaluation-metrics/07-04-RED-EVIDENCE-task2.json
  modified:
    - langextract/evaluation/__init__.py
    - langextract/__init__.py
    - pyproject.toml
    - tests/evaluation_test.py

key-decisions:
  - "TP/FP use predicted.extraction_class; FN use gold.extraction_class"
  - "Default criteria SameClass+SpanIoU; AttributesEqual/TextMatch via flags"
  - "No top-level lx.evaluate — lazy submodule only (A4)"

patterns-established:
  - "evaluate indexes by document_id then greedy_match per doc"
  - "import-linter: evaluation must not import pipeline; core must not import evaluation"

requirements-completed: [EVAL-01, EVAL-02, EVAL-03, EVAL-04]

coverage:
  - id: D1
    description: "evaluate perfect-match and empty lists via lx.evaluation.evaluate"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateTracerTest.test_perfect_match_micro_and_per_class_are_one"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateTracerTest.test_empty_lists_yield_micro_zeros"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateTracerTest.test_lazy_lx_evaluation_evaluate_is_same_callable"
        status: pass
    human_judgment: false
  - id: D2
    description: "RESEARCH hand-worked e2e matrix + match_attributes/text_eval_func alter TP/FP"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateE2ETest.test_hand_worked_micro"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateE2ETest.test_match_attributes_true_rejects_unequal_attributes"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateE2ETest.test_text_eval_func_reject_yields_zeros"
        status: pass
    human_judgment: false
  - id: D3
    description: "criteria= XOR convenience flags; document_id set/duplicate errors"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateConfigTest.test_criteria_with_nondefault_iou_threshold_raises"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#EvaluateConfigTest.test_mismatched_document_id_sets_raise"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-11
status: complete
---

# Phase 07 Plan 04: evaluate() Public API Summary

**Public `evaluate(predicted, gold)` scores gold-set extractions end-to-end via doc pairing → greedy_match → per-class/micro PRF, exposed as lazy `lx.evaluation.evaluate`.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-10-11T18:37:51Z
- **Completed:** 2026-10-11T18:39:40Z
- **Tasks:** 2
- **Files modified:** 4 source/config + tests + 2 RED-evidence records

## Accomplishments

- `evaluate()` pairs AnnotatedDocuments by `document_id`, runs `greedy_match`, aggregates TP/FP/FN into `EvaluationReport`
- Default criteria `SameClass` + `SpanIoU(0.5)`; optional `match_attributes` / `text_eval_func`; `criteria=` XOR convenience flags
- Lazy `lx.evaluation` via `_LAZY_MODULES` (no top-level `lx.evaluate`); import-linter guards evaluation layering
- Full RESEARCH hand-worked e2e matrix green (perfect, IoU below/above, class mismatch, duplicates, empty, unaligned, micro vs per-class)

## Task Commits

Each task was committed atomically (TDD RED→GREEN):

1. **Task 1 RED:** `49120f0` — `test(07-04): add failing EvaluateTracerTest for evaluate API`
2. **Task 1 GREEN:** `8452285` — `feat(07-04): implement evaluate and lazy lx.evaluation export`
3. **Task 2 RED:** `0666d38` — `test(07-04): add failing evaluate e2e matrix and XOR config tests`
4. **Task 2 GREEN:** `0a6da7f` — `feat(07-04): enforce criteria XOR and evaluation import-linter contracts`

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 1 Tracer evaluate + lazy export | ✓ `49120f0` | ✓ `8452285` | — | Pass |
| 2 E2E matrix + XOR + import-linter | ✓ `0666d38` | ✓ `0a6da7f` | — | Pass |

RED evidence: `07-04-RED-EVIDENCE-task1.json` / `task2.json` — both `RED_EVIDENCE_OK` (`target_test_failed`).

## Files Created/Modified

- `langextract/evaluation/__init__.py` — `evaluate()` + helpers; re-export in `__all__`
- `langextract/__init__.py` — `"evaluation"` in `__all__` and `_LAZY_MODULES`
- `pyproject.toml` — evaluation layering import-linter contracts
- `tests/evaluation_test.py` — EvaluateTracerTest, EvaluateE2ETest, EvaluateConfigTest

## Decisions Made

- TP/FP counted under predicted class; FN under gold class (RESEARCH Pitfall 8)
- Duplicate `document_id` within a side raises (no first-wins)
- ClassScore field names unchanged (`tp`/`fp`/`fn`/`f1`)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — mitigations T-07-09 (e2e + XOR + ID raise) and T-07-10 (import-linter) implemented as planned.

## Self-Check: PASSED

- FOUND: `langextract/evaluation/__init__.py` (`def evaluate`)
- FOUND: lazy export `"evaluation": "langextract.evaluation"` in `langextract/__init__.py`
- FOUND: no top-level `def evaluate` in `langextract/__init__.py`
- FOUND: commits `49120f0`, `8452285`, `0666d38`, `0a6da7f`
- FOUND: `.venv/bin/python tests/evaluation_test.py` → OK (55 tests)
