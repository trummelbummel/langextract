# Style review — 03-02

- **Mode:** phase
- **Commits:** `c82935c` … `a5cb578`
- **Files:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Timestamp:** 2026-10-11

## R15 swallowed exceptions

| Site | Verdict | Notes |
|------|---------|-------|
| `_self_check_probe_restore` expected `RuntimeError('probe self-check')` | skipped | Designed probe; verified then continues |
| `_self_check_probe_restore` outer `except Exception` → stderr + `SystemExit(1)` | skipped | CLI boundary; surfaces failure (not silent success) |
| Prior 03-01 sites | unchanged | `_diagnose_empty_parse` remains **desired** |

## Refactors applied

None — new code already matches 03-01 style (typed helpers, `:param` docs, restore helper reuse).

## Remaining findings (report-only)

| Rule | Finding |
|------|---------|
| R11 | Nested try in `_self_check_probe_restore` is readable for a short self-check; leave |

## Tests

Post-merge wave gate: 955 passed.
