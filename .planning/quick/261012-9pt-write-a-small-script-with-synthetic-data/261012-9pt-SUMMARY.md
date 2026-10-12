---
phase: 261012-9pt
plan: 01
subsystem: evaluation
tags: [evaluation, synthetic, scripts, makefile, ClassScore]

requires:
  - phase: 07-gold-set-evaluation-metrics
    provides: lx.evaluation.evaluate / ClassScore (f1, tp, fp, fn)
provides:
  - Offline synthetic evaluate demo script with EXPECTED annotations
  - make evaluate-synthetic phony target
affects: [evaluator demos, gold-set metrics docs]

estimate:
  tokens: 25000
  tasks: 2
actuals:
  tokens: 1514
  tasks: 2
  commits: 2
plan_head_before: 9b0aa3d1a05b0d2120af8310cef8ec3f2a22b516

tech-stack:
  added: []
  patterns:
    - "Synthetic predicted/gold AnnotatedDocuments + EXPECTED ClassScore dicts beside cases"
    - "Makefile phony target mirrors trace → $(VENV)/bin/python scripts/…"

key-files:
  created:
    - scripts/evaluate_synthetic.py
  modified:
    - Makefile

key-decisions:
  - "Two docs (doc-perfect, doc-miss) with condition TP×2 and medication FP/FN → micro f1=2/3"
  - "EXPECTED asserts tp/fp/fn/f1 only (precision/recall printed but not required in EXPECTED)"
  - "Makefile target name evaluate-synthetic via $(VENV)/bin/python"

patterns-established:
  - "Offline evaluate demos live under scripts/ with structured EXPECTED + exit-1 mismatch"

requirements-completed: [QUICK-EVAL-SYNTHETIC-01]

coverage:
  - id: D1
    description: Offline synthetic evaluate script prints report and asserts EXPECTED
    requirement: QUICK-EVAL-SYNTHETIC-01
    verification:
      - kind: other
        ref: ".venv/bin/python scripts/evaluate_synthetic.py"
        status: pass
    human_judgment: false
  - id: D2
    description: make evaluate-synthetic invokes the script through $(VENV)/bin/python
    requirement: QUICK-EVAL-SYNTHETIC-01
    verification:
      - kind: other
        ref: "make -n evaluate-synthetic"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-10-12
status: complete
---

# Phase 261012-9pt Plan 01: Synthetic evaluate script Summary

**Offline `scripts/evaluate_synthetic.py` builds synthetic predicted/gold docs, runs `lx.evaluation.evaluate`, prints/writes the report, and exits non-zero if live ClassScore fields disagree with in-script EXPECTED.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-12T05:02:23Z
- **Completed:** 2026-10-12T05:07:50Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- Runnable offline synthetic evaluate demo under `scripts/` with `document_id` + exclusive `CharInterval`
- Structured EXPECTED micro/per-class `tp`/`fp`/`fn`/`f1` checked after evaluate (exit 0/1)
- Optional `--output PATH` writes the same report text as stdout
- `make evaluate-synthetic` runs the script via `$(VENV)/bin/python`

## Task Commits

Each task was committed atomically:

1. **Task 1: Synthetic evaluate script with EXPECTED annotations** - `e6b4484` (feat)
2. **Task 2: Makefile target for synthetic evaluate** - `8b8b87f` (chore)

**Plan metadata:** skipped (orchestrator docs commit; SUMMARY/STATE/PLAN not committed by executor)

## EXPECTED scenario (hand-checked)

| Class | tp | fp | fn | f1 |
|-------|----|----|----|-----|
| condition | 2 | 0 | 0 | 1.0 |
| medication | 0 | 1 | 1 | 0.0 |
| micro | 2 | 1 | 1 | 2/3 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected CharInterval offsets for diabetes/ibuprofen**
- **Found during:** Task 1
- **Issue:** Hand-written `start_pos`/`end_pos` for `diabetes` and `ibuprofen` did not match `miss_text.index(...)`
- **Fix:** Used `[18, 26)` and `[41, 50)` from the live string
- **Files modified:** `scripts/evaluate_synthetic.py`
- **Commit:** `e6b4484`

**2. [Rule 3 - Blocking] Pre-commit pyink/isort aborted first commit**
- **Found during:** Task 1 commit
- **Issue:** First `git commit` failed after hooks reformatted the file
- **Fix:** Restaged formatted file and created a new commit (no amend)
- **Files modified:** `scripts/evaluate_synthetic.py`
- **Commit:** `e6b4484`

### Other deviations

- Script landed at 158 lines after pyink (plan soft target ~120; within ~150 diff-budget tolerance including Apache header). Dropped optional EXPECTED `precision`/`recall` keys to stay near budget; report print still includes them.

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None — no new trust-boundary surface beyond plan threat model (local `--output` write; synthetic demo strings).

## Self-Check: PASSED

- FOUND: `scripts/evaluate_synthetic.py`
- FOUND: commit `e6b4484`
- FOUND: commit `8b8b87f`
- FOUND: `Makefile` contains `evaluate-synthetic`
- VERIFIED: `.venv/bin/python scripts/evaluate_synthetic.py` exit 0
- VERIFIED: no `langextract/` files in plan commits
