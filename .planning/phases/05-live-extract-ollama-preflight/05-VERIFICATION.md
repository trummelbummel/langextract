---
phase: 05-live-extract-ollama-preflight
verified: 2026-10-11T15:42:52Z
status: human_needed
score: 10/10 must-haves verified
covered_files:
  - .planning/REQUIREMENTS.md
  - .planning/phases/05-live-extract-ollama-preflight/05-01-PLAN.md
  - .planning/phases/05-live-extract-ollama-preflight/05-01-SUMMARY.md
  - .planning/phases/05-live-extract-ollama-preflight/05-02-PLAN.md
  - .planning/phases/05-live-extract-ollama-preflight/05-02-SUMMARY.md
  - .planning/phases/05-live-extract-ollama-preflight/COVERAGE.md
  - config.yaml
  - data/example_document.md
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
covered_digest: "v1:sha256:81544d951fe6bf752bdf4f40f6c6df6596cd1188f270762adf65e548ea1dd514"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  skipped: true
  reason: "CONTEXT.md missing"
  honored: 0
  total: 0
  not_honored: []
human_verification:
  - test: "With Ollama up and gemma3:4b present, run `.venv/bin/python scripts/trace_extract.py` and read the printed walkthrough plus the final single-call line"
    expected: "Exit 0; stage sections with live in/out; last line `run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt)`"
    why_human: "Harvested from 05-02 PLAN `<human-check>`; readability of the live walkthrough is a judgment call even when automated exit/line checks pass"
  - test: "Stop Ollama (or point model_url at a closed port) and re-run the same command"
    expected: "Exit 1; one `Error:` line on stderr naming the host/fix; empty stdout (no header, no stage sections)"
    why_human: "Harvested from 05-02 PLAN `<human-check>`; confirms the fail-closed UX the developer actually sees"
---

# Phase 5: Live extract & Ollama preflight Verification Report

**Phase Goal:** Developer can run one real `lx.extract()` against local Ollama `gemma3:4b` and get a clear failure if the host or model is missing
**Verified:** 2026-10-11T15:42:52Z
**Status:** human_needed
**Re-verification:** No — initial verification
**Mode:** mvp

> **MVP goal-format note:** ROADMAP goal text is not in `As a …, I want to …, so that ….` form (`user-story.validate` → false). Plans use a valid user story; User Flow Coverage below is framed from the 05-01 PLAN story. Consider `/gsd mvp-phase 5` if the roadmap goal must match the MVP regex.

## User Flow Coverage

User story: «As a developer, I want to run one real `lx.extract()` against local Ollama `gemma3:4b` from `python scripts/trace_extract.py`, so that I can trace a live call — and get a clear failure (not an empty-looking walkthrough) when the host or model is missing.»

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Run live default | `python scripts/trace_extract.py` takes preflight → header → one `lx.extract` → walkthrough | `main()` → `run_live()` (`scripts/trace_extract.py`); stub + real tests | ✓ |
| See traced call | Walkthrough shows stage in/out; ends with single-call line | Live run + `TraceExtractRealOllamaTest` / stub e2e | ✓ |
| Host/model missing | Clear `Error:` on stderr, empty stdout, exit 1 | `TraceExtractPreflightTest` + closed-port probe | ✓ |
| Outcome | Trace a live call **or** get a clear failure (not a fake empty walkthrough) | R1–R3 below | ✓ |

## Goal Achievement

### Observable Truths

ROADMAP success criteria (contract) first, then plan-specific additions.

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| R1 | With Ollama up and `gemma3:4b` present, `python scripts/trace_extract.py` completes one short-document run end-to-end | ✓ VERIFIED | Direct `main([])` against localhost:11434 → exit 0, 627 stdout lines, last line single-call contract. `TRACE_LIVE_OLLAMA=1 … TraceExtractRealOllamaTest::test_run_live_completes_against_local_gemma3` passed (~20s). Stub e2e `test_run_live_walks_one_extract_against_stub` passed. |
| R2 | With Ollama down or `gemma3:4b` missing, script exits with a clear error before printing a fake empty walkthrough | ✓ VERIFIED | `TraceExtractPreflightTest` (unreachable, missing model incl. `gemma3:4b-it-qat`, HTTP 500, malformed tags, timeout) all assert exit 1, empty stdout, one `Error:` stderr line, zero `/api/generate`. Closed-port `main([])` probe: exit 1, empty stdout, `ollama serve` fix text. |
| R3 | The run performs exactly one `lx.extract()` and exactly one model `infer` (no second inference, no cloud providers) | ✓ VERIFIED | Exactly one `lx.extract(` in script (`:1015`) inside `trace_probes`. Stub hits `{"/api/tags": 1, "/api/generate": 1}`. `check_single_inference` + success line; guard tests for 0/2 calls and multi-prompt batch. `_extract_kwargs` omits `model`/`api_key`/`output_schema`/`fence_output`/`language_model_type`; no gemini/openai references. |
| 4 | `--catalog-only` prints header + seven-stage catalog, exit 0, no network | ✓ VERIFIED | `test_main_catalog_only_needs_no_network` (urlopen patched to assert). Verifier re-ran catalog-only: exit 0, all seven `[label]` headers. **Note:** Phase 3 `_self_check_probe_restore` still imports langextract on this path — plan wording “without importing langextract” is unmet by design (documented in 05-01 SUMMARY); network-free catalog behavior holds. |
| 5 | Model matching is exact: `gemma3:4b` or `gemma3:4b:latest` only | ✓ VERIFIED | `preflight_ollama` (`:887–892`); `test_preflight_accepts_latest_tag`; `test_preflight_fails_closed_when_model_missing` (lists `gemma3:4b-it-qat` only → fail). |
| 6 | Non-http(s) / host-less `model_url` rejected before any request | ✓ VERIFIED | Scheme/netloc check before `_fetch_tags` (`:879–883`); `test_preflight_rejects_non_http_url_without_request` (`file://`, scheme-less) with urlopen patched to assert. |
| 7 | Document longer than `max_char_buffer` refused before preflight/extract | ✓ VERIFIED | `_refuse_oversized_document` in `run_live` before `preflight_ollama`; `test_run_live_refuses_document_longer_than_max_char_buffer` (1200 chars vs buffer 1000 → exit 1, empty stdout, zero tags/generate). Config uses `max_char_buffer: 40000` so `data/example_document.md` (~2.2k) stays one chunk. |
| 8 | Successful live run ends with the single-inference contract line; 0/≥2 infers or ≠1 prompt → exit 1 | ✓ VERIFIED | `_SINGLE_CALL_LINE`; `test_run_live_ends_with_single_call_line_and_one_generate`; `test_check_single_inference_rejects_*`; `test_main_returns_1_when_single_inference_guard_fails`. |
| 9 | Against stub Ollama: exactly one `POST /api/generate` and one `GET /api/tags` | ✓ VERIFIED | Stub hit counters in live + guard e2e tests (assertions above). |
| 10 | `COVERAGE.md` records Ollama HTTP surface decisions | ✓ VERIFIED | File present with `/api/tags`, `/api/generate`, and explicit opt-outs (chat/pull/show/ps/warm-up/streaming/auth/cloud). |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `scripts/trace_extract.py` | `PreflightError`, `preflight_ollama`, `_extract_kwargs`, `run_live`, `check_single_inference`, `main` with `--catalog-only` | ✓ VERIFIED | Exists, substantive, wired into CLI entrypoint |
| `config.yaml` | Call constants incl. `prompt_description`, timeouts, document/chunk settings | ✓ VERIFIED | `document_path`, `max_char_buffer: 40000`, examples, `preflight_timeout_s` / `request_timeout_s` (sample_text replaced by document_path — intentional) |
| `tests/trace_extract_test.py` | Stub Ollama e2e, preflight fail-closed, guard + `TRACE_LIVE_OLLAMA` real test | ✓ VERIFIED | `_StubOllama` / `ThreadingHTTPServer`; live/preflight/guard/real classes |
| `.planning/phases/05-live-extract-ollama-preflight/COVERAGE.md` | API coverage matrix | ✓ VERIFIED | Decision table present |

`gsd_run query verify.artifacts` → all_passed for 05-01 and 05-02.

### Key Link Verification

Automated `verify.key-links` reported “Source file not found” because PLAN `from:` values are symbol names, not paths. Manual wiring:

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `main()` | `preflight_ollama()` | live path via `run_live`; `PreflightError` → stderr + return 1 | ✓ WIRED | `:1041–1045`, `:1006–1008` |
| `run_live()` | `lx.extract` | one call inside `trace_probes(wrappers=make_stage_wrappers(...))` | ✓ WIRED | `:1014–1015` |
| stub server | real HTTP `/api/generate` | no mocks of langextract internals | ✓ WIRED | `_StubOllama` + real `lx.extract` in live tests |
| `run_live()` | `check_single_inference()` | after extract, on model-stage records | ✓ WIRED | `:1018–1021` |
| `TraceExtractRealOllamaTest` | local Ollama `gemma3:4b` | `run_live(load_config(...))` when `TRACE_LIVE_OLLAMA=1` | ✓ WIRED | test passed in this session |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Walkthrough stages | `sink: list[StageRecord]` | Phase 4 wrappers during live `lx.extract` | Yes — recorded from real/stub HTTP generate | ✓ FLOWING |
| Document text | `text_or_documents` | `_load_document_text(config['document_path'])` | Yes — file contents | ✓ FLOWING |
| Preflight model list | `/api/tags` JSON | `urllib` GET to Ollama | Yes — live host or stub | ✓ FLOWING |
| Single-call line | `check_single_inference(sink)` | Phase 4 model `in_data` identities | Yes — derived from records | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Stub live e2e | `pytest …::test_run_live_walks_one_extract_against_stub` | 1 passed | ✓ PASS |
| Preflight fail-closed | `pytest …::test_preflight_fails_closed_when_{host_unreachable,model_missing}` | 2 passed | ✓ PASS |
| Single-inference + oversize | `pytest …::TraceExtractGuardTest::{single_call_line,rejects_two_calls,refuses_document…}` | 3 passed | ✓ PASS |
| Real gemma3:4b | `TRACE_LIVE_OLLAMA=1 pytest …::test_run_live_completes_against_local_gemma3` | 1 passed (~20s) | ✓ PASS |
| Closed-port main | ad-hoc `main([])` with unreachable `model_url` | exit 1, empty stdout, `ollama serve` | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No `scripts/*/tests/probe-*.sh`; phase uses pytest/stub + env-gated live test | SKIPPED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| RUN-01 | 05-01, 05-02 | Run against local Ollama `gemma3:4b` for one short document | ✓ SATISFIED | R1 + real/stub e2e |
| RUN-02 | 05-01 | Fail clearly if Ollama down / model missing before fake walkthrough | ✓ SATISFIED | R2 + preflight suite |
| RUN-03 | 05-02 | One `lx.extract` and one model `infer`; no cloud | ✓ SATISFIED | R3 + guard + kwargs pins |

No orphaned Phase 5 requirements in REQUIREMENTS.md (only RUN-01..03 map to Phase 5). STG-07 remains Phase 6 (not orphaned).

### Decision Coverage

No CONTEXT.md — nothing to check (`check.decision-coverage-verify` skipped).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/trace_extract_test.py` (Live/Preflight/Guard) | RUN-01..03 | Yes | Real class only via `skipUnless(TRACE_LIVE_OLLAMA=1)` | No | Behavioral / value | PASS |
| `TraceExtractRealOllamaTest` | RUN-01 | Active when env set; skipped offline by design | Env gate (plan prohibition) | No | Behavioral | PASS — not a disabled-only req proof (stub e2e also covers path) |

**Disabled tests on requirements:** 0 blockers (env gate is intentional CI/offline isolation).
**Circular patterns detected:** 0
**Insufficient assertions:** 0

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX` in phase-modified script | — | — |
| Plan vs code | — | 05-01 truth said `--catalog-only` without importing langextract | ℹ️ Info | Phase 3 self-check imports lx; catalog still network-free |
| `run_live` | finally | Prints partial walkthrough if `lx.extract` raises mid-call | ℹ️ Info | Documented in 05-01 SUMMARY; preflight path still fail-closed with empty stdout |

**Anti-patterns:** 0 blockers.

### Human Verification Required

### 1. Live walkthrough readability (harvested)

**Test:** With Ollama up and `gemma3:4b` present, run `.venv/bin/python scripts/trace_extract.py` and read the walkthrough + final single-call line.
**Expected:** Exit 0; live stage sections; last line `run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt)`.
**Why human:** Layout/readability of the printed walkthrough is a judgment call. (Verifier also ran this successfully for code evidence; operator still confirms UX.)

### 2. Fail-closed UX (harvested)

**Test:** Stop Ollama (or use a closed-port `model_url`) and re-run.
**Expected:** Exit 1; one `Error:` stderr line; empty stdout.
**Why human:** Confirms the developer-visible failure mode. (Automated suite + closed-port probe already pass.)

### Gaps Summary

None for roadmap or plan must-have truths. Automated score is 10/10. Status is `human_needed` solely because of the harvested end-of-phase `<human-check>` items (and judgment-tier prohibition review as part of that UAT).

### Prohibitions (judgment-tier — flag for human)

Plan prohibitions (no edits under `langextract/` / demo; no cloud kwargs; no second generate from script; reuse Phase 3/4 probes/wrappers) were grepped/wired in code. Treat as **unverified-prohibition — human review recommended** during UAT (not silently green).

---

_Verified: 2026-10-11T15:42:52Z_
_Verifier: Claude (gsd-verifier)_
