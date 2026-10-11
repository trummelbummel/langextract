---
phase: 05-live-extract-ollama-preflight
plan: 01
subsystem: tracing
tags: [trace, ollama, preflight, live-extract, tdd, stub-server]
status: complete
requires:
  - phase: 03-call-scoped-probe-manager
    provides: trace_probes(wrappers=...) context manager
  - phase: 04-stage-wrappers
    provides: make_stage_wrappers(sink, config), print_stage_records(records, config)
provides:
  - PreflightError and preflight_ollama(model_url, model_id, timeout) (GET /api/tags, exact-name match, fail closed)
  - _extract_kwargs(config) pinned lx.extract kwargs (local Ollama only)
  - run_live(config) preflight -> header -> one lx.extract inside the probes -> walkthrough
  - main(argv) live by default, --catalog-only keeps the Phase 1 catalog
  - config.yaml sample_text, prompt_description, examples, preflight_timeout_s, request_timeout_s
affects: [05-02, 06-annotated-document]
tech-stack:
  added: []
  patterns: [stdlib urllib preflight, lazy langextract import after preflight, stdlib http.server stub Ollama in tests]
key-files:
  created: []
  modified:
    - scripts/trace_extract.py
    - config.yaml
    - tests/trace_extract_test.py
key-decisions:
  - "Preflight accepts exactly model_id or model_id + ':latest'; 'gemma3:4b-it-qat' does not satisfy gemma3:4b."
  - "Non-http(s) or host-less model_url is rejected before any request (blocks file:// via urllib)."
  - "Walkthrough is printed in a finally after the probes exit, so a failing lx.extract still shows the stages captured so far; the exception keeps its traceback."
  - "--catalog-only keeps the Phase 3 D-09 silent restore self-check, so it is not langextract-free."
requirements-completed: [RUN-01, RUN-02]
plan_head_before: 0b9073ef4b5179855c7168dae02cb7b9f2f4c7a7
duration: 25 min
completed: 2026-10-11
actuals:
  tokens: 9000
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "run_live against a stub Ollama preflights (1 GET /api/tags), runs one lx.extract (1 POST /api/generate), prints [model] with the canned raw text and [align], returns 0"
    requirement: RUN-01
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#TraceExtractLiveTest.test_run_live_walks_one_extract_against_stub"
        status: pass
  - id: D2
    description: "_extract_kwargs pins model_id/model_url/extraction_passes=1/debug/show_progress/fetch_urls False/timeout from config and omits model, api_key, output_schema, fence_output, language_model_type"
    requirement: RUN-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractLiveTest.test_extract_kwargs_pins_local_ollama_call"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractLiveTest.test_extract_kwargs_omits_cloud_and_schema_keys"
        status: pass
  - id: D3
    description: "main(['--catalog-only']) prints exactly header + catalog and never calls urlopen"
    requirement: RUN-01
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractLiveTest.test_main_catalog_only_needs_no_network"
        status: pass
  - id: D4
    description: "Unreachable host, timeout, HTTP 500, non-JSON / models-not-a-list body and missing model each return 1 from main() with empty stdout, one 'Error:' stderr line naming the fix, and zero /api/generate hits"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#TraceExtractPreflightTest (test_preflight_fails_closed_*)"
        status: pass
  - id: D5
    description: "gemma3:4b:latest satisfies the preflight; gemma3:4b-it-qat alone does not"
    requirement: RUN-02
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractPreflightTest.test_preflight_accepts_latest_tag"
        status: pass
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractPreflightTest.test_preflight_fails_closed_when_model_missing"
        status: pass
  - id: D6
    description: "file:// and scheme-less model_url raise PreflightError before urlopen is called"
    requirement: RUN-02
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#TraceExtractPreflightTest.test_preflight_rejects_non_http_url_without_request"
        status: pass
---

# Phase 5 Plan 01: Live extract behind a fail-closed Ollama preflight Summary

`python scripts/trace_extract.py` now runs preflight (GET `/api/tags`, stdlib `urllib`), prints the call header, runs one `lx.extract` inside `trace_probes` with the Phase 4 wrappers and prints the walkthrough. Any host or model problem exits 1 with one `Error:` line on stderr and nothing on stdout. `--catalog-only` keeps the Phase 1 catalog.

## What was built

- **Task 1 (tracer):** `config.yaml` call constants; `preflight_ollama` (happy path), `_extract_kwargs`, `run_live`, `main(argv)` with `--catalog-only`. langextract is imported lazily after preflight. The stub-Ollama e2e test (stdlib `ThreadingHTTPServer`, real HTTP, no mocks of langextract internals) drives it.
- **Task 2:** `preflight_ollama` validates the URL scheme and host first, then classifies `HTTPError`, `URLError`/`TimeoutError`/`ConnectionError`, body size (1 MiB cap), malformed JSON and the model match. `main` turns `PreflightError` into `Error: ...` on stderr and exit 1. Errors inside `lx.extract` are not caught.

## Commits

| Commit | Message |
|--------|---------|
| 7ccfea4 | test(05-01): add failing live-path and catalog-only tests |
| b802dda | feat(05-01): live lx.extract behind Ollama preflight with --catalog-only |
| b1b9926 | test(05-01): add failing fail-closed preflight tests |
| 90885ee | feat(05-01): fail closed on Ollama preflight errors |

RED was captured before each GREEN (Task 1: 5 errors; Task 2: 2 failures + 7 errors). `tests/trace_extract_test.py`: 66 tests, OK.

Non-test diff (`git diff --numstat 0b9073e HEAD`): +23 `config.yaml`, +133/-2 `scripts/trace_extract.py` for the plan (Task 1 commit: 122 insertions/2 deletions over two files, Task 2 commit: 46/12 in one file). Within the 150-per-task and 400-per-plan budgets.

## Deviations from Plan

**1. [Rule 3 - Blocking] `python` (system) cannot run `--catalog-only`**
- System python (3.14, Homebrew) has no `yaml`, so `python scripts/trace_extract.py --catalog-only` fails with `ModuleNotFoundError: yaml` at the top-level import that exists since Phase 1. The plan's "under system python" verify/acceptance wording is therefore not achievable without a new dependency story. I verified with `.venv/bin/python` (exit 0, seven stages in order, header first). The preflight and failure path themselves import only stdlib before langextract.

**2. [Plan conflict] `--catalog-only` still runs the Phase 3 restore self-check**
- The plan truth says catalog-only runs "without importing langextract", but Phase 3 D-09 (locked) has `main` run `_self_check_probe_restore()` after the catalog, and that loads langextract. I kept D-09 and its test (`test_main_runs_self_check_after_catalog_silently`, now called with `['--catalog-only']`). Stdout is exactly header + catalog. Making catalog-only langextract-free means revisiting D-09; flagged for the verifier.

**3. [Rule 1 - Bug] Hook conflict on a long import line**
- `from langextract.providers import ollama  # pylint: disable=...` made isort wrap it and pyink unwrap it, so the commit hook could never pass. Fixed by one standalone `# pylint: disable=import-outside-toplevel` line in `_extract_kwargs`.

**4. [Rule 2 - CLAUDE.md] Tests parameterized, fixtures used**
- Failure modes are `parameterized.named_parameters` or one-behavior tests; stub server, temp config and patches are in `setUp` with `addCleanup`/`enter_context`/`create_tempdir`.

**5. [Process] Stale commit ledger**
- `.git/gsd-plan-head-before-05-01` pre-existed pointing at `8b41a14`; reset to `0b9073e` (HEAD at start), so `plan_head_before`/`commits: 4` are measured from the real base.

**Total deviations:** 5. **Impact:** none on RUN-01/RUN-02 behavior.

## Out-of-scope observation

Another session is concurrently editing `scripts/trace_extract.py` (an optional positional `document` argument plus a Usage line) and `Makefile`/`.gitignore`. Those edits are uncommitted and were deliberately excluded from my commits (staged via blob, not `git add`). My tests pass with and without them (66 OK with them present).

## Known Stubs

None.

## Threat Flags

None new. T-05-01 (scheme/host validation before any request, urlopen patched to fail), T-05-02 (5 s timeout, 1 MiB cap, sleeping stub), T-05-03 (empty stdout and zero generate hits asserted) and T-05-04 (no model=/api_key=/cloud names; grep gate returns 0) are covered by tests or grep gates.

## Self-Check: PASSED

- `scripts/trace_extract.py`, `config.yaml`, `tests/trace_extract_test.py` exist; commits 7ccfea4, b802dda, b1b9926, 90885ee found; RED precedes GREEN.
- At HEAD: `lx.extract(` count 1; `except PreflightError` 1; `ollama pull` 1; `ollama serve` 1; forbidden-token grep 0; `api/generate` in script (non-comment) 0; top-level langextract/requests imports 0.
- No edits under `langextract/` or `examples/`.
- `.venv/bin/python scripts/trace_extract.py` against the local Ollama exited 0 and printed the walkthrough (informal check; the formal live check is 05-02).
