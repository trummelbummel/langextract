---
phase: 03-call-scoped-probe-manager
plan: 01
subsystem: tracing
tags: [trace, probes, contextmanager, monkeypatch, tdd]
status: complete
requires:
  - phase: 02-extraction-snapshots
    provides: scripts/trace_extract.py stage helpers and test loader patterns
provides:
  - "trace_probes() call-scoped context manager"
  - "_PROBES_ACTIVE re-entry flag"
  - "_PROBE_TARGETS lazy five-target table"
  - "identity wrap factories (return / yield / chunk return-self)"
affects: [03-02, 04-stage-wrappers, 05-live-extract]
tech-stack:
  added: []
  patterns:
    - "class-attribute save/assign/finally restore (no mock.patch in script)"
    - "lazy langextract import for probe targets"
    - "mid-install except rollback before re-raise"
key-files:
  created:
    - .planning/phases/03-call-scoped-probe-manager/03-01-RED-EVIDENCE-task1.json
    - .planning/phases/03-call-scoped-probe-manager/03-01-RED-EVIDENCE-task2.json
  modified:
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
key-decisions:
  - "Chunk identity returns original iterator (ChunkIterator.__iter__ returns self; yield-from would recurse)"
  - "Model/align identity use yield from; prompt/parse use return"
  - "No functools.wraps on Phase 3 identity replacements (D-07)"
  - "_PROBE_TARGETS populated lazily via _load_probe_targets() so catalog import stays light"
requirements-completed: [CTR-01]
duration: 4 min
completed: 2026-10-11
plan_head_before: c3eb8118427976abf2eb0f28aabc07088e7d11aa
actuals:
  tokens: 2926
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "with trace_probes(): installs five distinct identity wraps and restores on exception"
    requirement: CTR-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_installs_five_and_restores_on_exception"
        status: pass
    human_judgment: false
  - id: D2
    description: "Identity wraps passthrough with no stdout side effects"
    requirement: CTR-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_identity_passthrough_no_side_effects"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nested with raises RuntimeError (already active); mid-install rolls back; normal exit restores"
    requirement: CTR-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_nested_trace_probes_rejected_with_already_active"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_mid_install_failure_restores_partial_wraps"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_normal_exit_restores_and_clears_flag"
        status: pass
    human_judgment: false
---

# Phase 3 Plan 01: Call-scoped probe manager Summary

`with trace_probes():` installs distinct identity passthroughs on the five extract class attributes and always restores them in `finally` (exception path, normal exit, and mid-install failure), with one-shot re-entry rejected via `_PROBES_ACTIVE`.

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-11T06:31:30Z
- **Completed:** 2026-10-11T06:35:41Z
- **Tasks:** 2
- **Files modified:** 2 (`scripts/trace_extract.py`, `tests/trace_extract_test.py`)

## Accomplishments

- Added `trace_probes()`, `_PROBES_ACTIVE`, lazy `_PROBE_TARGETS` / `_load_probe_targets()`, and identity wrap factories in `scripts/trace_extract.py` (~102 non-test lines across the plan; no top-level `langextract` import).
- Exception exit, normal exit, and mid-install failure all restore originals by identity; nested `with` raises `RuntimeError` mentioning `already active`.
- Identity proven against real chunk/prompt/model/parse/align call shapes with empty stdout from the wraps.
- `main()` unchanged (catalog-only); no edits under `langextract/` or `examples/`.

## Task Commits

| Task | Phase | Commit | Message |
|------|-------|--------|---------|
| 1 (tracer) | RED | 036c16e | test(03-01): add failing probes for call-scoped identity wraps |
| 1 (tracer) | GREEN | 402a78e | feat(03-01): add call-scoped trace_probes with identity wraps |
| 2 | RED | 6bf846e | test(03-01): cover re-entry, normal exit, and mid-install rollback |
| 2 | GREEN | cefbd37 | feat(03-01): harden re-entry guard and mid-install rollback |

RED evidence (`check tdd-red-evidence` → `RED_EVIDENCE_OK`, `target_test_failed`) in `03-01-RED-EVIDENCE-task1.json` and `03-01-RED-EVIDENCE-task2.json`. Task 1 RED: missing `trace_probes`. Task 2 RED: missing `_PROBE_TARGETS` (re-entry/mid-install/normal-exit assertions were already green from Task 1).

## Tracer gate

Tracer `<verify>` re-run after Task 1 (`tests/trace_extract_test.py` → OK) before Task 2 expansion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Identity test fixture used PromptTemplateStructured as generator**
- **Found during:** Task 1 GREEN
- **Issue:** `ContextAwarePromptBuilder` requires a `QAPromptGenerator`; first fixture raised `AttributeError: 'PromptTemplateStructured' object has no attribute 'render'`. Fake `_ollama_query` also needed `prompt=` keyword arg name.
- **Fix:** Build `QAPromptGenerator` with `OLLAMA_FORMAT_HANDLER`; align fake_query signature with provider call.
- **Files modified:** `tests/trace_extract_test.py`
- **Commit:** 402a78e

**2. [Rule 2 - Missing critical] `_PROBE_TARGETS` deferred from Task 1 into Task 2**
- **Found during:** Task 2 RED
- **Issue:** Plan artifacts require `_PROBE_TARGETS`; Task 1 shipped only `_load_probe_targets()` without the module table.
- **Fix:** Lazy-populate `_PROBE_TARGETS` in `_load_probe_targets()`; explicit mid-install `except` restore before re-raise.
- **Files modified:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Commit:** cefbd37

**3. [Environment] RED evidence adapter**
- `check tdd-red-evidence` expects node-style TAP; absltest output converted to TAP for the persisted record (same pattern as Phase 02). Command, exit code, and failure message are from the real run.

**Total deviations:** 2 auto-fixed (Rules 1–2), 1 environment note. **Impact:** none on phase goal.

## Diff budget

- Task 1 GREEN: +88 lines on `scripts/trace_extract.py` (≤150).
- Task 2 GREEN: +18/−2 lines on `scripts/trace_extract.py` (≤40 target).
- Plan total ~102 non-test lines in 1 source file; tests excluded. No `langextract/` or `examples/` diffs.

## Acceptance Criteria

All PASS: `def trace_probes` ×1; `_PROBES_ACTIVE` present; 0 top-level `langextract` imports; `already active` in message; install/exception/normal/re-entry/mid-install covered by absltests; suite OK.

## Known Stubs

None.

## Threat Flags

None new. T-03-01 (mid-install rollback) and T-03-03 (`cls.__dict__` save/restore) mitigated; T-03-02 (re-entry) mitigated via `_PROBES_ACTIVE` + RuntimeError.

## Next

Ready for 03-02 (in-script restore self-check + `main` wire per D-09–D-12).

## TDD Gate Compliance

RED (`test(03-01)`) precedes GREEN (`feat(03-01)`) for both tasks; both with `RED_EVIDENCE_OK`.

## Self-Check: PASSED

- FOUND: scripts/trace_extract.py, tests/trace_extract_test.py, both RED-EVIDENCE files, 03-01-SUMMARY.md
- FOUND commits: 036c16e, 402a78e, 6bf846e, cefbd37
