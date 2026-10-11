---
phase: 07-gold-set-evaluation-metrics
plan: 03
subsystem: evaluation
tags: [greedy-match, span-iou, one-to-one, tie-break, tdd]

requires:
  - phase: 07-02
    provides: "MatchCriterion + span_iou + SameClass/SpanIoU"
provides:
  - "greedy_match 1:1 assignment with (-score, pred_index, gold_index) sort"
  - "Re-export greedy_match from langextract.evaluation"
affects:
  - 07-04-evaluate-api

actuals:
  tokens: 2362
  tasks: 2
  commits: 4

plan_head_before: 6c678eb0fb6c3865dedb412c05c4ddd8bde6352b

tech-stack:
  added: []
  patterns:
    - "Filter by all MatchCriterion then rank with separate score_fn (default span_iou)"
    - "Deterministic greedy walk with used_pred/used_gold sets"

key-files:
  created:
    - langextract/evaluation/matching.py
    - .planning/phases/07-gold-set-evaluation-metrics/07-03-RED-EVIDENCE-task1.json
    - .planning/phases/07-gold-set-evaluation-metrics/07-03-RED-EVIDENCE-task2.json
  modified:
    - langextract/evaluation/__init__.py
    - tests/evaluation_test.py

key-decisions:
  - "Sort key exactly (-score, pred_index, gold_index); lower indices win IoU ties"
  - "Default score_fn=span_iou; criteria failure omits pair even if IoU high"
  - "Empty predicted or gold short-circuits to []"

patterns-established:
  - "matching.py imports core.data + evaluation.criteria only (D-05)"
  - "Return list[(pred_idx, gold_idx)] in greedy walk order"

requirements-completed: [EVAL-03, EVAL-04]

coverage:
  - id: D1
    description: "Perfect overlap and crossing IoU assign 1:1 without reusing indices"
    requirement: EVAL-03
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#GreedyMatchTest.test_perfect_overlap_matches_single_pair"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#GreedyMatchTest.test_crossing_iou_prefers_higher_score_pairs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Duplicate preds match a single gold at most once"
    requirement: EVAL-04
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#GreedyMatchTest.test_duplicate_preds_match_gold_at_most_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "Equal-IoU tie-break prefers lower pred then gold index; empty inputs → []"
    requirement: EVAL-03
    verification:
      - kind: unit
        ref: "tests/evaluation_test.py#GreedyMatchTest.test_equal_iou_prefers_lower_pred_then_gold_index"
        status: pass
      - kind: unit
        ref: "tests/evaluation_test.py#GreedyMatchTest.test_empty_predicted_or_gold_returns_empty"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-11
status: complete
---

# Phase 07 Plan 03: Greedy match Summary

**Deterministic greedy 1:1 matching via `greedy_match` with IoU-desc ranking and index tie-break.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-11T18:25:00Z
- **Completed:** 2026-10-11T18:29:00Z
- **Tasks:** 2
- **Files modified:** 3 source/test (+ 2 RED evidence JSON)

## Accomplishments

- Implemented `greedy_match` with criteria filter, `span_iou` ranking, and used-set walk
- Enforced 1:1 uniqueness so duplicate predictions cannot double-match one gold
- Locked equal-IoU order to `(-score, pred_index, gold_index)`; empty lists return `[]`

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED:** `92aaba0` — `test(07-03): add failing greedy_match 1:1 tests`
2. **Task 1 GREEN:** `811f394` — `feat(07-03): implement greedy_match 1:1 assignment`
3. **Task 2 RED:** `f11b799` — `test(07-03): add failing tie-break and empty match tests`
4. **Task 2 GREEN:** `b972463` — `feat(07-03): restore (-score, pred, gold) tie-break sort`

## Files Created/Modified

- `langextract/evaluation/matching.py` — `greedy_match` implementation
- `langextract/evaluation/__init__.py` — re-export `greedy_match`
- `tests/evaluation_test.py` — `GreedyMatchTest` behaviors
- `07-03-RED-EVIDENCE-task1.json` / `task2.json` — TDD RED evidence (TAP)

## Decisions Made

- Sort key is exactly `(-score, pred_index, gold_index)` (Pitfall 4)
- Score stays separate from yes/no criteria (D-02)
- No Hungarian/optimal matching

## Deviations from Plan

### Auto-fixed Issues

None that changed product behavior beyond the plan.

### Process notes

**1. [Process] Task 2 intentional RED via temporary gold-index inversion**
- **Found during:** Task 2
- **Issue:** Task 1 GREEN already used the correct sort key, so new tie-break tests would have been unexpected GREEN
- **Fix:** Temporary `(-score, pred, -gold)` sort for RED assertion failures; GREEN restored `(-score, pred, gold)` and documented it
- **Files modified:** `langextract/evaluation/matching.py`
- **Commits:** `f11b799` (RED), `b972463` (GREEN)

Environment note: `check tdd-red-evidence` expects node-style TAP; absltest failures converted to TAP in persisted RED-evidence records (same pattern as 07-01/07-02).

## TDD Gate Compliance

| Task | RED | GREEN | Evidence |
|------|-----|-------|----------|
| 1 | `92aaba0` | `811f394` | RED_EVIDENCE_OK (`test_perfect_overlap_matches_single_pair`) |
| 2 | `f11b799` | `b972463` | RED_EVIDENCE_OK (`test_equal_iou_prefers_lower_pred_then_gold_index`) |

## Diff budget

- Task 1 GREEN: 67 non-test lines across 2 files ≤150
- Task 2 GREEN: 7 non-test lines in 1 file ≤20 target
- Plan total ~74 non-test lines; within CLAUDE.md limits

## Known Stubs

None. `evaluate()` / document pairing deferred to 07-04.

## Threat Flags

None new. T-07-07 mitigated by deterministic sort + 1:1 used sets; T-07-08 accepted (O(n·m) documented).

## Self-Check: PASSED

- FOUND: `langextract/evaluation/matching.py` (`def greedy_match` ×1)
- FOUND: commits `92aaba0`, `811f394`, `f11b799`, `b972463`
- VERIFY: `.venv/bin/python tests/evaluation_test.py` → OK (35 tests)
