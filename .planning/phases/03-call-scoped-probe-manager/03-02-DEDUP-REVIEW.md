# Dedup review — 03-02

- **Mode:** phase
- **Scope:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Timestamp:** 2026-10-11

## Signals

| ID | Result | Notes |
|----|--------|-------|
| S01 | none | Self-check install/restore asserts mirror unit tests by design (in-script vs absl); different audiences |
| S03 | propose-only | Same as 03-01: test `_STAGE_TARGETS` vs `_PROBE_TARGETS` stay separate |
| S06 | propose-only | Script still multi-concern; split deferred |

## Auto-applied

None.

## Propose-only

No blocking consolidations for 03-02.
