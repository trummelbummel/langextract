---
phase: 05-live-extract-ollama-preflight
plan: 02
review: style
timestamp: 2026-10-11T07:26:26Z
commit_range: 66eff0b..1c05c18
---

# Style review — 05-02

## Commits under review

- `66eff0b` test(05-02): add failing single-inference guard tests
- `38e781b` feat(05-02): enforce single-inference contract in run_live
- `f0e8850` feat(05-02): env-gated real gemma3:4b run and Ollama COVERAGE.md
- `f009ae3` docs(05-02): complete single-inference guard and live Ollama plan
- `1c05c18` docs(05-02): mark phase ready for verification

## Files

- `scripts/trace_extract.py`
- `tests/trace_extract_test.py`
- `config.yaml` (no Python style actions)

## R15 — Swallowed exceptions (HITL)

AskUserQuestion UI unavailable in this subagent run. Same candidate as 05-01; deferred again.

| File | Line | Except | Verdict | Action taken |
|------|------|--------|---------|--------------|
| `scripts/trace_extract.py` | 346 | `Exception as e` (`_diagnose_empty_parse` → error string) | skip for now | deferred; no edit |

**Skipped as intentional (not candidates):**

- `StopIteration` in chunk wrapper — iterator protocol
- `trace_probes` install `except Exception` then restore + re-raise
- `_self_check_probe_restore` `except Exception` → stderr + `SystemExit(1)`
- Narrow `PreflightError` / `HTTPError` / `URLError` handlers that surface errors

## Refactors applied

### `scripts/trace_extract.py`

- **R03:** Extracted `_refuse_oversized_document` so `run_live` stays a thin sequence of named steps.

### `tests/trace_extract_test.py`

- **R05:** Removed duplicate `_SINGLE_CALL_LINE`; assertions use `trace._SINGLE_CALL_LINE`.
- **R01:** Annotated `_model_record` parameters and return type.

## Remaining findings (report-only)

| File | Rule | Finding | Suggested fix |
|------|------|---------|---------------|
| `scripts/trace_extract.py` | R05 | `run_live` loads the document, then `_extract_kwargs` loads it again | Pass text into kwargs builder or cache once at composition root |
| `scripts/trace_extract.py` | R11/R16 | Module still multi-concern; string-key config fan-out in `_extract_kwargs` | Future split / typed config (carry-over from 05-01) |
| `scripts/trace_extract.py` | R08 | `_MAX_CHAR_BUFFER` / `_MAX_TAGS_BYTES` / pinned extract flags | Optional config keys if they need tuning |
| `tests/trace_extract_test.py` | — | Live / Preflight / Guard `setUp` each start `_StubOllama` | Optional shared `_start_stub(test)` helper |

## Counts

2 files reviewed, 2 refactored, 4 report-only findings, R15: 0 desired / 0 changeworthy / 1 deferred.
