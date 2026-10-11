# Dedup review — 03-01

- **Mode:** phase
- **Scope:** `scripts/trace_extract.py`, `tests/trace_extract_test.py` (+ one-hop: none beyond `_load_script_module`)
- **Timestamp:** 2026-10-11

## Signals

| ID | Result | Notes |
|----|--------|-------|
| S01 | none | Identity wraps are unique; stage wrappers (`make_*_wrapper`) are recording, not identity |
| S02 | none | No duplicate classes |
| S03 | propose-only | Test `_STAGE_TARGETS` mirrors script `_PROBE_TARGETS` labels — intentional test independence so catalog/probe tables cannot drift silently via shared import; keep separate |
| S04–S05 | none | |
| S06 | propose-only | `scripts/trace_extract.py` is a multi-concern script (catalog + wrappers + probes). Split deferred until Phase 4/5 land recording walkthrough; out of 03-01 scope |
| S07–S09 | none | |

## Auto-applied

None beyond style-review’s in-file `_restore_probe_attrs` DRY (already committed under style).

## Propose-only (no block)

1. Keep test `_STAGE_TARGETS` separate from `_PROBE_TARGETS` until a shared constant would reduce real drift risk without coupling tests to private script state.
2. Module split of `trace_extract.py` is a later cleanup, not a 03-01 consolidation.
