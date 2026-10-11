---
phase: 03-call-scoped-probe-manager
plan: 02
subsystem: tracing
tags: [trace, probes, wrappers, self-check, tdd]
status: complete
requires:
  - phase: 03-call-scoped-probe-manager
    provides: trace_probes identity wraps, _PROBE_TARGETS, restore helper from 03-01
provides:
  - "wrappers= unknown-key rejection (ValueError)"
  - "characterization tests for partial/empty wrappers and generator/chunk shapes"
  - "_self_check_probe_restore() silent success / stderr+exit-1 failure"
  - "main() post-catalog self-check (D-09..D-12)"
affects: [04-stage-wrappers, 05-live-extract]
tech-stack:
  added: []
  patterns:
    - "wrappers map overlay on _IDENTITY_WRAP_FACTORIES with unknown-key reject"
    - "in-script restore self-check: raise inside with, catch, assert originals, silent OK"
key-files:
  created:
    - .planning/phases/03-call-scoped-probe-manager/03-02-RED-EVIDENCE-task1.json
    - .planning/phases/03-call-scoped-probe-manager/03-02-RED-EVIDENCE-task2.json
  modified:
    - scripts/trace_extract.py
    - tests/trace_extract_test.py
key-decisions:
  - "Unknown wrappers= keys raise ValueError listing sorted labels (T-03-05)"
  - "Self-check stderr wording: 'Error: probe self-check failed: …' + SystemExit(1)"
  - "Expected RuntimeError('probe self-check') is swallowed; any other fault exits 1"
requirements-completed: [CTR-01]
duration: 3min
completed: 2026-10-11
plan_head_before: fe2b3914d6a17650b7aa00345dba564f75e8643a
actuals:
  tokens: 2675
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "Partial/empty wrappers= always installs five targets; unknown keys rejected; generator/chunk identity shapes"
    requirement: CTR-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_partial_wrappers_overlay_and_restore"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_empty_wrappers_installs_identity"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_generator_and_chunk_identity_shapes"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_trace_probes_rejects_unknown_wrapper_keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "Silent restore self-check after catalog; failure → stderr Error + SystemExit(1)"
    requirement: CTR-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_self_check_probe_restore_silent_success"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_self_check_probe_restore_failure_exits"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#test_main_runs_self_check_after_catalog_silently"
        status: pass
      - kind: other
        ref: ".venv/bin/python scripts/trace_extract.py (exit 0, empty stderr, catalog stdout)"
        status: pass
    human_judgment: false
---

# Phase 3 Plan 02: Wrappers injection + restore self-check Summary

Optional `wrappers=` map rejects unknown labels and is covered for partial/empty/generator shapes; every catalog run proves exception-path restore via silent `_self_check_probe_restore()` (stderr + exit 1 on failure).

## Performance

- **Duration:** 3 min
- **Started:** 2026-10-11T06:42:33Z
- **Completed:** 2026-10-11T06:45:33Z
- **Tasks:** 2
- **Files modified:** 2 source/test (+ 2 RED evidence JSON)

## Accomplishments

- Documented and tested D-03/D-06/D-08 wrappers overlay (partial, empty, generator/chunk)
- Reject unknown `wrappers=` keys with `ValueError` (T-03-05)
- Wired `_self_check_probe_restore()` after catalog in `main` (D-09..D-12)

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: wrappers map coverage** - `c82935c` (test)
2. **Task 1 GREEN: reject unknown keys** - `7fd28e3` (feat)
3. **Task 2 RED: restore self-check coverage** - `3fcff27` (test)
4. **Task 2 GREEN: self-check + main wire** - `21ab9c3` (feat)

## Files Created/Modified

- `scripts/trace_extract.py` — unknown-key validation; `_self_check_probe_restore()`; `main` call
- `tests/trace_extract_test.py` — partial/empty/generator/unknown-key + self-check/main tests
- `03-02-RED-EVIDENCE-task1.json` / `03-02-RED-EVIDENCE-task2.json` — TDD RED gate records

## Decisions Made

- Unknown labels → `ValueError('unknown wrapper label(s): …')` with sorted names
- Self-check uses dedicated `RuntimeError('probe self-check')` as the expected exception path signal
- Failure stderr mirrors `load_config`: `Error: probe self-check failed: …`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Unknown-key rejection was the Task 1 GREEN delta**
- **Found during:** Task 1 RED
- **Issue:** Identity fill / partial overlay / generator-chunk shapes already landed in 03-01 (`_IDENTITY_WRAP_FACTORIES` + `factories.update`). Characterization tests for those behaviors were already green; only unknown-key rejection was missing (threat T-03-05).
- **Fix:** RED targeted `test_trace_probes_rejects_unknown_wrapper_keys`; GREEN added validation. Characterization tests committed in the same RED commit for D-03/D-06/D-08 coverage.
- **Files modified:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Commit:** `7fd28e3`

## TDD Gate Compliance

| Task | RED commit | GREEN commit | RED evidence |
|------|------------|--------------|--------------|
| 1 | `c82935c` | `7fd28e3` | `03-02-RED-EVIDENCE-task1.json` → RED_EVIDENCE_OK |
| 2 | `3fcff27` | `21ab9c3` | `03-02-RED-EVIDENCE-task2.json` → RED_EVIDENCE_OK |

## Threat Flags

None — no new trust boundaries beyond the plan threat model (wrappers map + self-check exit).

## Known Stubs

None.

## Self-Check: PASSED

- Found: `scripts/trace_extract.py`, `tests/trace_extract_test.py`, `03-02-SUMMARY.md`
- Found commits: `c82935c`, `7fd28e3`, `3fcff27`, `21ab9c3`
- Found: `def _self_check_probe_restore` (≥2 references including `main` call)
