---
phase: 261011-p2z
plan: 01
subsystem: extraction
tags: [drop_ungrounded, grounding, extract, char_interval]

requires:
  - phase: library-extract-api
    provides: lx.extract return paths and AnnotatedDocument.extractions
provides:
  - Opt-in drop_ungrounded keyword on lx.extract with _drop_ungrounded helper
  - Offline AC tests for string/documents paths and INFO log
affects: [callers wanting grounded-only extractions]

actuals:
  tokens: 2631
  tasks: 2
  commits: 3

plan_head_before: e6c846e16ee9dbadd9755b1f9d1ac7f43d6d3841

tech-stack:
  added: []
  patterns: [post-annotate filter helper on both extract return paths]

key-files:
  created:
    - tests/extract_drop_ungrounded_test.py
  modified:
    - langextract/extraction.py
    - README.md

key-decisions:
  - "Locked Option B: keyword-only drop_ungrounded=False; filter in extraction.py only"
  - "INFO log only when removed_count > 0; mutate doc.extractions in place on AnnotatedDocument"

patterns-established:
  - "Grounding guardrail as optional post-filter after annotate_text / annotate_documents"

requirements-completed: [QUICK-DROP-UNGROUNDED-01]

coverage:
  - id: D1
    description: drop_ungrounded=True keeps only extractions with char_interval set (string path)
    requirement: QUICK-DROP-UNGROUNDED-01
    verification:
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_true_keeps_grounded_only_on_string_path
        status: pass
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_false_keeps_both_on_string_path
        status: pass
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_default_keeps_both_on_string_path
        status: pass
    human_judgment: false
  - id: D2
    description: drop_ungrounded=True filters documents path AnnotatedDocument list
    requirement: QUICK-DROP-UNGROUNDED-01
    verification:
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_true_filters_documents_path
        status: pass
    human_judgment: false
  - id: D3
    description: INFO log reports removed count when > 0; no ungrounded INFO when nothing removed
    requirement: QUICK-DROP-UNGROUNDED-01
    verification:
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_true_logs_removed_count
        status: pass
      - kind: unit
        ref: tests/extract_drop_ungrounded_test.py::ExtractDropUngroundedTest::test_drop_ungrounded_true_no_log_when_nothing_removed
        status: pass
    human_judgment: false
  - id: D4
    description: README Grounding note documents drop_ungrounded=True
    requirement: QUICK-DROP-UNGROUNDED-01
    verification:
      - kind: other
        ref: "python -c assert 'drop_ungrounded' in README.md"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-11
status: complete
---

# Phase 261011-p2z Plan 01: drop_ungrounded Summary

**Opt-in `drop_ungrounded=True` on `lx.extract()` drops `char_interval is None` extractions on both return paths, with an INFO count log and unchanged default behavior.**

## Performance

- **Duration:** 2min
- **Started:** 2026-10-11T16:05:38Z
- **Completed:** 2026-10-11T16:08:00Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Keyword-only `drop_ungrounded: bool = False` plus `_drop_ungrounded` helper in `langextract/extraction.py`
- String and documents return paths filter when True; INFO logs removed count only when > 0
- Offline mocked AC suite (6 tests) and README Grounding note document the flag

## Task Commits

1. **Task 1 (RED): failing drop_ungrounded AC tests** - `68d405c` (test)
2. **Task 1 (GREEN): drop_ungrounded filter on extract return paths** - `23fae50` (feat)
3. **Task 2: README Grounding note** - `d84f459` (docs)

## TDD Gate Compliance

- **RED:** `test_drop_ungrounded_true_keeps_grounded_only_on_string_path` failed with `TypeError: unexpected keyword argument 'drop_ungrounded'`; `check tdd-red-evidence` → `RED_EVIDENCE_OK`
- **GREEN:** `_drop_ungrounded` + both return paths; 6/6 tests pass
- **REFACTOR:** none

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pylint import-outside-toplevel in no-log test**
- **Found during:** Task 2 verify
- **Issue:** `import logging` inside the test method failed pylint (C0415)
- **Fix:** Moved `import logging` to module top
- **Files modified:** `tests/extract_drop_ungrounded_test.py`
- **Commit:** `d84f459`

## Decisions Made

- Locked Option B as planned: filter stays in `extraction.py`; Annotator/Resolver untouched; default False

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: `langextract/extraction.py` (`drop_ungrounded`, `_drop_ungrounded`)
- FOUND: `tests/extract_drop_ungrounded_test.py`
- FOUND: `README.md` contains `drop_ungrounded`
- FOUND commits: `68d405c`, `23fae50`, `d84f459`
