# Style review — 03-01

- **Mode:** phase
- **Commits:** `036c16e` … `68732e5` (+ style refactor commit)
- **Files:** `scripts/trace_extract.py`, `tests/trace_extract_test.py`
- **Timestamp:** 2026-10-11

## R15 swallowed exceptions

| Site | Verdict | Notes |
|------|---------|-------|
| `scripts/trace_extract.py:334` `_diagnose_empty_parse` broad `except Exception` → return message | **desired** | Phase 2 diagnostic boundary; keep |
| `trace_probes` mid-install `except Exception` + rollback + `raise` | skipped | Not swallowed |
| Chunk `StopIteration` / test `RuntimeError` asserts | skipped | Intentional |

## Refactors applied

| Rule | Change |
|------|--------|
| R01 | Annotated nested identity callables (`self`/`*args`/`**kwargs`/return) |
| R05 | Extracted `_restore_probe_attrs` for duplicated reverse-restore loops |
| R09 | Imported `Iterator` from `collections.abc` for yield wrap return type |

## Remaining findings (report-only)

| Rule | Finding |
|------|---------|
| R11 | `trace_probes` body mixes install orchestration with install loop — acceptable for a short contextmanager; leave until Phase 4 wraps wiring expands it |
| R03 | Identity factories are already thin; no further extraction needed |

## Tests

`TraceExtractProbeTest`: 7 passed after refactor.
