---
phase: 05-live-extract-ollama-preflight
plan: 01
review: style
timestamp: 2026-10-11T07:12:29Z
commit_range: 7ccfea4..HEAD (plus uncommitted style edits at review time)
---

# Style review — 05-01

## Commits under review

- `7ccfea4` test(05-01): add failing live-path and catalog-only tests
- `b802dda` feat(05-01): live lx.extract behind Ollama preflight with --catalog-only
- `b1b9926` test(05-01): add failing fail-closed preflight tests
- `90885ee` feat(05-01): fail closed on Ollama preflight errors
- `99fc48d` docs(05-01): complete live extract and Ollama preflight plan
- `6eab672` fix(05-01): use TemporaryDirectory for preflight tests under pytest

## Files

- `scripts/trace_extract.py`
- `tests/trace_extract_test.py`
- `config.yaml` (no Python style actions)

## R15 — Swallowed exceptions (HITL)

| File | Line | Except | Verdict | Action taken |
|------|------|--------|---------|--------------|
| `scripts/trace_extract.py` | 343 | `Exception as e` (parse stage → error string) | skip for now | deferred; no edit |

Phase 5 preflight handlers re-raise `PreflightError` or print to stderr — not flagged.

## Refactors applied

### `scripts/trace_extract.py`

- **R03:** Split `preflight_ollama` into `_fetch_tags` + `_listed_model_names`; public function stays thin.
- **R01:** Annotated wrapper closures / `traced_outputs` / `trace_probes` return type.
- **R05:** Introduced `_WrapFactory` alias for repeated callable type.
- **R02:** Normalized `:raises:` / `:param:` / `:return:` on `load_config`, `trace_probes`, `run_live`, new helpers.
- **R07:** Removed dead `except SystemExit: raise` before `except Exception` in `_self_check_probe_restore`.

### `tests/trace_extract_test.py`

- **R01:** Annotations on `_StubOllama`, `_StubHandler`, `_closed_port_url`, `_run_main`, `_assert_fail_closed`.

## Remaining findings (report-only)

| File | Rule | Finding | Suggested fix |
|------|------|---------|---------------|
| `scripts/trace_extract.py` | R02 | Many private one-line helpers lack `:param:`/`:return:` | Separate docstring-only task |
| `scripts/trace_extract.py` | R06 | `load_config` does not validate required keys | Validate once at load |
| `scripts/trace_extract.py` | R08 | Hardcoded extract flags / `_MAX_TAGS_BYTES` | Optional config keys |
| `scripts/trace_extract.py` | R11/R16 | Large multi-concern module; string-key config fan-out | Future split / typed config plan |
| `tests/trace_extract_test.py` | — | Stub start duplicated in Live + Preflight `setUp` | Optional `_start_stub` helper |

## Counts

2 files reviewed, 2 refactored, 5+ report-only findings, R15: 0 desired / 0 changeworthy / 1 deferred.
