---
phase: 05-live-extract-ollama-preflight
reviewed: 2026-10-11T15:38:56Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
  - config.yaml
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues
---

# Phase 5: Code Review Report

**Reviewed:** 2026-10-11T15:38:56Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues

## Summary

Reviewed the Phase 5 live path: `preflight_ollama` / `_fetch_tags` / `_listed_model_names`, `_extract_kwargs`, `run_live`, `check_single_inference`, the one-chunk document gate, `config.yaml` call constants, and the stub / fail-closed / guard / env-gated live tests. Read both PLAN/SUMMARY pairs and CLAUDE.md first. COVERAGE.md was context only (not scored).

Preflight fail-closed behavior is sound: scheme/host validation before `urlopen`, `HTTPError` before `URLError`, 1 MiB body cap, exact `model_id` / `model_id:latest` match, empty stdout on `PreflightError`, and no top-level `langextract` import. The single-inference guard correctly counts calls via `id(in_data)`. No Critical issues. Warnings are path/file handling, exception masking in `finally`, live-test marker hygiene, and the live path still shipping model text through the Phase 4 printer spoofing gap.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `document_path` can read any readable local file (absolute or `../` escape)

**File:** `scripts/trace_extract.py:895-909`
**Issue:** `_load_document_text` resolves relative paths against the repo root, then `path.resolve()`, but never checks that the result stays under `_REPO_ROOT`. Absolute paths and repo-escaping relatives both work. Reproduced: a temp file outside the repo loaded via a `../…` relative path returned `SECRET_OUTSIDE`. That text becomes `text_or_documents` and is sent to whatever host `model_url` names. Config is developer-edited, but a malicious or mistaken `document_path` is a local file disclosure into the inference request (adjacent to T-05-04).
**Fix:** After resolve, require the file to stay in-repo (and keep rejecting non-files):

```python
path = path.resolve()
try:
  path.relative_to(_REPO_ROOT.resolve())
except ValueError:
  print(f'Error: document_path escapes repo root: {path}', file=sys.stderr)
  raise SystemExit(1)
```

Add a regression test with a temp file outside the repo and a `../` relative path; expect exit 1 and no extract.

### WR-02: Non-UTF-8 documents raise `UnicodeDecodeError` instead of a clean `Error:` exit

**File:** `scripts/trace_extract.py:909`
**Issue:** `path.read_text(encoding='utf-8')` has no handler. A binary or non-UTF-8 document produces a traceback from `run_live` / `_extract_kwargs`, not the one-line `Error:` pattern used for missing files, oversize docs, and preflight. Reproduced with a temp file containing `\xff\xfe`.
**Fix:** Catch `UnicodeDecodeError` (and optionally `OSError`) next to the missing-file branch and exit 1 with `Error: document is not valid UTF-8: {path}`.

### WR-03: `print_stage_records` in `finally` can mask the real `lx.extract` failure

**File:** `scripts/trace_extract.py:1013-1017`
**Issue:** Walkthrough printing runs in `finally` so partial traces survive extract failures (SUMMARY deviation). If `print_stage_records` itself raises (Phase 4 pair mismatch, bad intervals, etc.), Python replaces the original extract exception with the printer exception. Reproduced the language semantics: `ValueError('extract boom')` in `try` + `RuntimeError('print boom')` in `finally` → only `RuntimeError` surfaces. That turns a real pipeline failure into a tracer/printer stack trace.
**Fix:** Isolate printer errors:

```python
extract_exc: BaseException | None = None
try:
  with trace_probes(wrappers=make_stage_wrappers(sink, config)):
    lx.extract(**_extract_kwargs(config))
except BaseException as exc:
  extract_exc = exc
  raise
finally:
  try:
    print_stage_records(sink, config)
  except Exception as print_exc:
    if extract_exc is not None:
      raise extract_exc from print_exc
    raise
```

Or print inside the `try` after extract and accept losing the walkthrough on extract failure (closer to RUN-02’s empty-stdout spirit for failures).

### WR-04: Env-gated real Ollama test is not marked `live_api` / `integration`

**File:** `tests/trace_extract_test.py:1366-1383`
**Issue:** `TraceExtractRealOllamaTest` uses `@absltest.skipUnless(TRACE_LIVE_OLLAMA == '1', …)` only. `make test` runs `pytest -m "not live_api and not integration"`, which excludes marked tests — not env-gated unmarked ones. With `TRACE_LIVE_OLLAMA=1` in the environment (local shell, CI secret leakage, etc.), `make test` will hit real Ollama and can fail or hang on `request_timeout_s: 300`. CLAUDE.md asks external-resource tests to use the registered markers.
**Fix:** Add `@pytest.mark.integration` (or `live_api`) on the class/method in addition to `skipUnless`, matching `tests/test_ollama_integration.py`, so `make test` drops it regardless of env.

### WR-05: Live walkthrough still allows model-controlled fake stage headers

**File:** `scripts/trace_extract.py:599-625` (consumer: `run_live` at `:1017`)
**Issue:** Phase 5 makes the primary UX a real `lx.extract` whose raw text and extraction fields flow through `print_stage_records`. Phase 4 REVIEW WR-01 remains open: `_safe_text` keeps newlines, and `_print_align_section` interpolates model-derived `extraction_class` without `repr`/indent, so a class like `"x\n[model] FAKE"` can inject a column-0 fake stage header. Threat rows T-05-03 / T-04-05 assume walkthrough integrity; the live path newly exercises this with real model output.
**Fix:** Apply the Phase 4 fix (inline `!r` / indented continuations) before treating RUN-01 walkthrough output as trustworthy. Add a regression with a stub generate body whose JSON key contains `\n[model] `.

## Info

### IN-01: Document text is loaded twice per live run

**File:** `scripts/trace_extract.py:1001`, `:936`
**Issue:** `run_live` reads the document for the length gate; `_extract_kwargs` reads it again for `text_or_documents`. Same path today (style review already noted). A TOCTOU grow past `max_char_buffer` would be caught by `check_single_inference`, so this is maintainability, not a silent multi-infer hole.
**Fix:** Pass the already-loaded string into kwargs construction (or a thin helper) so one read feeds both checks.

### IN-02: `_MAX_CHAR_BUFFER` is not the live ceiling anymore

**File:** `scripts/trace_extract.py:48-49`, `:1002-1003`; `config.yaml:25`
**Issue:** Comment still frames `_MAX_CHAR_BUFFER = 1000` as the one-chunk ceiling, but the gate uses `config.get('max_char_buffer', _MAX_CHAR_BUFFER)` and config sets `40000` for `example_document.md`. Easy to misread as “always refuse >1000”.
**Fix:** Rename or recomment (e.g. “library default fallback when config omits max_char_buffer”).

### IN-03: Missing-document uses `SystemExit`; oversize / preflight / guard return `1`

**File:** `scripts/trace_extract.py:906-908` vs `:1004-1005`, `:1041-1045`, `:1019-1021`
**Issue:** Callers of `run_live` that expect an `int` status get `SystemExit` for a missing file but `1` for oversize and guard failures. CLI still exits non-zero; the split is awkward for tests and reuse.
**Fix:** Prefer `return 1` after printing `Error:` (same shape as `_refuse_oversized_document`), or document that `run_live` may raise `SystemExit`.

---

_Reviewed: 2026-10-11T15:38:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
