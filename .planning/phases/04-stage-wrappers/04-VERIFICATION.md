---
phase: 04-stage-wrappers
verified: 2026-10-11T07:03:01Z
status: passed
score: 16/17 must-haves verified
covered_files:

  - .planning/REQUIREMENTS.md
  - .planning/phases/04-stage-wrappers/04-01-PLAN.md
  - .planning/phases/04-stage-wrappers/04-01-SUMMARY.md
  - .planning/phases/04-stage-wrappers/04-02-PLAN.md
  - .planning/phases/04-stage-wrappers/04-02-SUMMARY.md
  - .planning/phases/04-stage-wrappers/04-03-PLAN.md
  - .planning/phases/04-stage-wrappers/04-03-SUMMARY.md
  - config.yaml
  - scripts/trace_extract.py
  - tests/trace_extract_test.py

covered_digest: "v1:sha256:532c71a64abada6beb9427a74bd656e9866191e1e48e4572a2cf9dfe750f7c9c"
behavior_unverified: 0
overrides_applied: 0
deferred:

  - truth: "Same walkthrough produced through trace_probes(wrappers=make_stage_wrappers(sink, config)); originals restored on success and on exception (04-03 Task 2, Tests R-T, T-04-11)"
    addressed_in: "Phase 3 (trace_probes, incomplete) / Phase 5 (installs wrappers for the live call)"
    evidence: "04-03 Task 2 precondition HALTed by design: `def trace_probes` absent from scripts/trace_extract.py, no 03-*-SUMMARY.md. 04-03 success_criteria: 'HALT there is not a phase-requirement failure'. ROADMAP Phase 4 success criteria do not mention trace_probes. Phase 5 plan 05-01 'one lx.extract inside probes'."
human_verification:

  - test: "Read the printed five-stage walkthrough from one offline extract (e.g. the _patch_stages path used by test_five_stage_walkthrough_prints_sections_in_catalog_order, or an ad-hoc script that wraps the five targets and calls print_stage_records) for the canned reply, for 'not json', and for '{\"extractions\": []}'"
    expected: "Raw model text appears only under [model] (and as input under [parse]); flags + callout are under [parse] next to the raw text; offsets/slices/ungrounded are under [align]; the output is readable (see IN-04: pformat continuation lines for flags/snapshots are not indented; bare `extractions:` for empty tuples, WR-02)."
    why_human: "Readability/layout of terminal output is a judgment call. This is the `<human-check>` harvested from 04-03 Task 2 (deferred with that task); it was not performed by a human. The verifier ran the output and found it structurally correct (details below)."
---

# Phase 4: Stage wrappers Verification Report

**Phase Goal:** Developer can see live data in/out for chunk through align, with raw model text, empty-parse callouts, and format flags — without requiring a warm model yet
**Verified:** 2026-10-11T07:03:01Z
**Status:** passed
**Re-verification:** Closeout — UAT 15/15 passed after Phase 3 landed; covered_digest refreshed; operator marked phase complete

## Goal Achievement

Verified against code, not SUMMARY claims. I ran `.venv/bin/python -m pytest tests/trace_extract_test.py` (39 passed) and a separate ad-hoc offline script (`/tmp/verify_walk.py`). The script wraps all five targets with `make_stage_wrappers`, patches only `OllamaLanguageModel._ollama_query`, calls the real `lx.extract`, and prints with `print_stage_records`. It was run for three replies: the canned reply, `not json` and `{"extractions": []}`. Each run made exactly 1 fake HTTP call and returned the same document as unwrapped (2, 0 and 0 extractions).

### Observable Truths

ROADMAP success criteria (the contract) first, then plan-specific truths.

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| R1 | Wrappers produce stage records with live data in and out for each instrumented stage (full payloads for a short sample) | ✓ VERIFIED | Ad-hoc run printed `[chunk]`, `[prompt]`, `[model]`, `[parse]`, `[align]` sections, each with `in:` and `out:`. Full document text, full few-shot prompt and full raw reply appear with no truncation. Tests `test_five_stage_walkthrough_prints_sections_in_catalog_order`, `test_model_wrapper_records_prompt_and_raw_text_from_offline_extract`. |
| R2 | Model-stage output shows raw model text separately from parsed extractions | ✓ VERIFIED | `[model]` out keys are exactly `prompt_index, score, raw_model_text` (asserted in test). No snapshots appear under `[model]` in the printed run. `[parse]` out holds the snapshots. |
| R3 | Align output shows spans, status, chunk offsets (even when 0), and source slice or `ungrounded` | ✓ VERIFIED | Printed: `offsets: token_offset=0  char_offset=0  (chunk start in the document)`, `span=[18, 26)  status=match_exact  slice='headache'`, `span=ungrounded status=ungrounded slice=ungrounded`. `test_align_section_uses_document_coordinates_minus_offset_offsets_5_100` covers span [118, 126) with offsets 5/100; `…_char_offset_omitted` covers 0, not None. |
| R4 | Empty parse is called out in words next to the raw model text; parse inputs include format/fence/wrapper flags | ✓ VERIFIED | `not json` run: `[parse]` prints `in:` (raw text + `flags` with format_type/use_fences/strict_fences/use_wrapper/wrapper_key) then `callout: Chunk omitted on parse or schema error…` and `error: ResolverParsingError: …`. Valid empty list prints the different `empty_list_message`. Both sentences come from `config.yaml`. |
| 5  | Prompt record string equals `model.batch_prompts[0]`; prompt wrapper calls `build_prompt` once | ✓ VERIFIED | `test_prompt_record_matches_model_batch_prompt_from_offline_extract`; wrapper body (`scripts/trace_extract.py:280-293`) calls `original` once. |
| 6  | Chunk wrapper drives `next()` (no RecursionError), yields same chunks, restores class attribute | ✓ VERIFIED | Code at `:236-262` uses a `next(it)` loop. `test_chunk_wrapper_yields_same_chunks_without_recursion` asserts `ChunkIterator.__dict__['__iter__']` is restored. |
| 7  | Raw text goes through an escaper (ESC visible, `café` verbatim); empty reply prints `raw_model_text: ''` | ✓ VERIFIED | `test_print_stage_records_escapes_control_characters_in_raw_text`, `test_print_stage_records_prints_empty_raw_text_explicitly` (asserts the exact line `  raw_model_text: ''`). |
| 8  | Sections print in STAGE_CATALOG order regardless of capture order; unrecorded stages print nothing | ✓ VERIFIED | `test_print_stage_records_follows_catalog_order_and_skips_missing`; printer iterates `STAGE_CATALOG` (`:520`). |
| 9  | Model records are one per `ScoredOutput`, with `prompt_index` and `batch_size`; forwarded kwargs redacted | ✓ VERIFIED | Code `:196-213`. `test_model_wrapper_redacts_forwarded_kwargs` (`api_key → <REDACTED>`). Printed run shows `kwargs: {'max_workers': 10}`. (Caveat: WR-05 on the `prompt_index == 0` guard semantics, advisory.) |
| 10 | Catalog-only `python scripts/trace_extract.py` output unchanged (7 headers, no in:/out:) | ✓ VERIFIED | Ran it: 7 headers in catalog order; the `^ *(in|out|offsets):` grep matched nothing. `main()` not wired. |
| 11 | Parse record: raw text == model out; flags read from `Resolver.format_handler` as primitives; `suppress_parse_errors` recorded; snapshots ungrounded even though the document is grounded | ✓ VERIFIED | Printed run: parse snapshots `char_interval=None alignment_status=None`; align snapshots grounded; document has 2 extractions. `format_type: 'json'` is a str. `test_parse_wrapper_records_raw_text_flags_and_ungrounded_snapshots`, `test_parse_snapshot_survives_align_mutation`. |
| 12 | Empty-parse matrix: `not json` → empty_parse_message + error; `{"extractions": []}` → empty_list_message only; fenced reply with `use_fences=False` → empty_parse_message; `''` → "Empty or invalid input string." | ✓ VERIFIED | Matrix tests (`…not_json`, `…valid_empty_list`, `…fenced_without_use_fences`, `test_parse_callout_for_empty_string_reply`). Ad-hoc run reproduced the first two. The `''` case is a direct `resolve('')` call because Ollama raises first (documented deviation, reasonable). |
| 13 | Diagnosis re-run calls the unwrapped original, adds no record, and does not change the returned result | ✓ VERIFIED | `_diagnose_empty_parse` (`:318-336`) calls `original`. `test_parse_diagnosis_adds_no_extra_records_*` (3 cases). Wrapper returns `out` unchanged. |
| 14 | Align record: `source_text`, `token_offset`, `char_offset` (None → 0), `n_extractions`; out snapshots taken at generator exhaustion (same objects yielded) | ✓ VERIFIED | Code `:390-410`. `test_align_wrapper_records_chunk_inputs_from_offline_extract`, `test_align_wrapper_snapshots_the_extractions_it_yielded`. |
| 15 | Empty parse still writes an align record (0 extractions); parse→align pair reuses `print_grounding_pair` | ✓ VERIFIED | Ad-hoc `not json` run printed `n_extractions: 0`, `grounding pair (parse → align): 0 extractions`, `parse: []`, `align: []`. `_print_align_section` calls the existing `print_grounding_pair` (`:507`). |
| 16 | Prohibitions: no top-level langextract import; no edits under `langextract/` or `examples/`; no print inside wrappers; no list()/rebuild of ScoredOutput; messages come from config | ✓ VERIFIED | `grep '^(import\|from) langextract' scripts/trace_extract.py` → none. `git diff bb10d38^..HEAD -- langextract examples` → empty. No `print(` in lines 179-415. The only `for … in original(` is the align generator (`:404`), which is not forbidden and has no recursion hazard. Callout sentences are not literals in the script. |
| 17 | Walkthrough also produced via `trace_probes(wrappers=make_stage_wrappers(...))`, originals restored on success/exception (04-03 Task 2, Tests R–T, T-04-11) | ⏭ DEFERRED (by design) | `trace_probes` does not exist; Task 2 HALTed on its own precondition. Not counted in the 16 verified. Not a requirement gap: see Deferred Items. |

**Score:** 16/17 truths verified (0 behavior-unverified; 1 deferred by design).

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | Walkthrough through `trace_probes(wrappers=…)` + restore-on-exception proof (Task 2, Tests R–T, T-04-11) | Phase 3 (incomplete; hard gate before live Ollama per ROADMAP notes) and Phase 5 (live call installs wrappers) | The plan itself states STG coverage is "satisfied after Task 1 (and plans 04-01/04-02) via `_patch_stages` / offline `lx.extract` — Phase 3 need not be merged". ROADMAP Phase 4 SCs 1-4 do not mention `trace_probes`. |

Note: Phase 3 is an *earlier* phase, so this is not a "later phase covers it" deferral in the usual sense. I am accepting it on the strength of the plan and ROADMAP wording and the instruction from the orchestrator. Nothing installs the wrappers outside tests today (see IN-02 of the review): the production installer is a Phase 3 / Phase 5 dependency. Phase 4's goal explicitly says "without requiring a warm model" and is satisfied through the offline path.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `scripts/trace_extract.py` | StageRecord, `_safe_text`, five `make_*_wrapper`, `make_stage_wrappers`, `print_stage_records`, `_diagnose_empty_parse`, `_source_slice` | ✓ VERIFIED | All defined (`:161-535`), substantive and tested. |
| `config.yaml` | `empty_list_message`, `chunk_offset_caption` | ✓ VERIFIED | Both keys present and read in the printers. |
| `tests/trace_extract_test.py` | `_patch_stages`, `_run_offline_extract`, wrapper/printer tests | ✓ VERIFIED | 39 tests (11 pre-existing + 28 new). Uses `enter_context`, `named_parameters`, no network. |
| `.planning/phases/04-stage-wrappers/COVERAGE.md` | No-external-API declaration | ✓ VERIFIED | Exists. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `make_stage_wrappers` | the five library methods | `original -> replacement` installed by test helper `_patch_stages` (`mock.patch.object(cls, attr, wrappers[label](cls.__dict__[attr]))`) | ✓ WIRED (test path only) | No production installer yet (`trace_probes` absent; deferred). |
| model wrapper | `redact()` | `redact(extra, keys=keys)` (`:202`) | ✓ WIRED | Test D equivalent passes. |
| parse wrapper | `snapshot_extractions` | called on result before return (`:362`) | ✓ WIRED | |
| `_diagnose_empty_parse` | original `Resolver.resolve` | strict re-run, `suppress_parse_errors=False` | ✓ WIRED | The plan's literal pattern `suppress_parse_errors': False` is spelled with a different quote style, but the behavior is present. |
| `print_stage_records` | `STAGE_CATALOG`, `config['empty_*_message']`, `print_grounding_pair` | direct calls | ✓ WIRED | |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `[model]` raw text | `scored.output` | real `OllamaLanguageModel.infer` with `_ollama_query` faked at the HTTP boundary | Yes (real pipeline objects) | ✓ FLOWING |
| `[parse]` flags | `self.format_handler` | Resolver instance built by real `lx.extract` | Yes | ✓ FLOWING |
| `[align]` offsets/slices | bound `align` args + grounded Extractions | real `Resolver.align` | Yes (`[18, 26)` / `'headache'` matches the source) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Tracer suite | `.venv/bin/python -m pytest tests/trace_extract_test.py -q` | 39 passed | ✓ PASS |
| Real offline `lx.extract`, three replies, all five wrappers | `/tmp/verify_walk.py` | 1 HTTP call each; document identical in extraction count; sections as listed above | ✓ PASS |
| Valid-but-all-empty item `{"extractions": [{}]}` | `/tmp/edge.py` | Prints "valid empty extraction list; nothing was omitted" (see WR-03) | ⚠ MISLEADING (advisory) |
| Catalog-only output | `.venv/bin/python scripts/trace_extract.py` | 7 headers, no in/out/offsets lines | ✓ PASS |
| Wrapper print-free / no library edits | grep + `git diff` | clean | ✓ PASS |

Full non-live suite was not run (the environment lacks `openai`, pre-existing and unrelated, per the SUMMARYs). Only the tracer test file was run.

### Probe Execution

Step 7c: SKIPPED. No `scripts/*/tests/probe-*.sh` exist and no plan declares one.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| STG-03 | 04-01, 04-02, 04-03 | Each stage prints live data in and out (full payloads for the short input) | ✓ SATISFIED | R1, truths 5-8, 14-15, ad-hoc walkthrough |
| STG-04 | 04-01 | Model stage shows raw model text separate from parsed extractions | ✓ SATISFIED | R2, truth 7 |
| STG-06 | 04-03 | Align shows spans, status, chunk offsets (even 0), source slice or `ungrounded` | ✓ SATISFIED | R3, truth 14 |
| STG-09 | 04-02 | Empty parse called out next to raw model text; parse inputs include format/fence/wrapper flags | ✓ SATISFIED | R4, truths 11-13. Caveat: WR-03 (callout can overstate "nothing was omitted" when the list holds empty items). |

Every ID in the PLAN frontmatter (STG-03, STG-04, STG-06, STG-09) is accounted for. REQUIREMENTS.md maps exactly these four to Phase 4, so there are no orphaned requirements. The `[x]` boxes and "Complete" traceability rows match the evidence.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK in `scripts/trace_extract.py` or `config.yaml`. No stubs. The findings below come from the code review. I reproduced the items marked ✓.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `scripts/trace_extract.py` | 463 (callout error line), 500 (align line) | Model-derived text with newlines is printed unindented, so it can spoof a column-0 `[label]` header (WR-01) | ⚠️ Warning | Not a must-have failure: tests cover ESC escaping, not newline injection. The plan's T-04-05/T-04-09 "mitigated" claim is only partly true. |
| `scripts/trace_extract.py` | 447 | Empty tuple prints as bare `extractions:` (WR-02, ✓ reproduced in the `not json` run) | ⚠️ Warning | The callout still says the parse was empty, so STG-09 holds. The "explicit empty value" intent is not met for tuples. |
| `scripts/trace_extract.py` | 318-336 | `{"extractions": [{}]}` is called "valid empty list; nothing was omitted" (WR-03, ✓ reproduced) | ⚠️ Warning | Misleading trace; weakens the truthfulness of STG-09 in a corner case. |
| `scripts/trace_extract.py` | 197, 398, 407-409 | Tracer can alter or abort the traced call for one-shot iterables, unsized `extractions`, or a raising snapshot in `finally` (WR-04) | ⚠️ Warning | Real `Annotator` passes lists, so no current failure. |
| `scripts/trace_extract.py` | 205-213 | `prompt_index == 0` counts records, not infer calls, when a prompt has several ScoredOutputs (WR-05) | ⚠️ Warning | Phase 5's single-inference guard must not rely on it as documented. Fix before Phase 5 uses it. |
| `config.yaml`, script docstring | 6, 16 | Stale comments (IN-03) | ℹ️ Info | |
| `scripts/trace_extract.py` | 453 | Multi-line pformat not indented (IN-04, visible in the ad-hoc output for `flags` and snapshots) | ℹ️ Info | Feeds the human-verification item. |

### Human Verification Required

#### 1. Read the five-stage printed walkthrough

**Test:** Print the walkthrough from one offline extract (via `_patch_stages` or an equivalent script) for three replies: the canned reply, `not json`, and `{"extractions": []}`.
**Expected:** Raw model text appears under `[model]`, and again as input to `[parse]`; flags and the callout sit in `[parse]` next to it; offsets, spans and slices or `ungrounded` sit under `[align]`; the layout is readable and acceptable to you.
**Why human:** Readability is subjective. This is the `<human-check>` from the deferred 04-03 Task 2, and no human has done it. The verifier confirmed the content is correct, but not the layout. Known layout nits are IN-04 (unindented pformat continuation lines) and WR-02 (bare `extractions:`).

### Gaps Summary

No blocking gaps. All four ROADMAP success criteria and all four requirement IDs (STG-03, STG-04, STG-06, STG-09) are met in the code and in a verifier-run offline walkthrough. Real `lx.extract` made one fake HTTP call and returned the same document with the wrappers on.

## Acknowledged Gaps

Closeout 2026-10-11: operator marked phase complete after UAT 15/15 (including walkthrough via `trace_probes` once Phase 3 landed). Prior `human_needed` items accepted as covered by that UAT. Covered digest refreshed to match post–Phase-3 `scripts/trace_extract.py` / tests. Advisory WR-01–WR-05 remain Phase 5 follow-ups, not Phase 4 blockers.

Recommended follow-ups, none blocking Phase 4. Do them before or during Phase 5:

- Fix WR-05 first, because Phase 5's single-inference guard depends on it. Add a per-call id, or count distinct `in_data`.
- Fix WR-03 so the callout does not claim "nothing was omitted" for `[{}]`.
- Fix WR-02 and WR-01: make empties explicit and indent or `repr` model-derived text.
- Phase 3 `trace_probes` landed; UAT #15 covered Task 2 restore path.

---

_Verified: 2026-10-11T07:03:01Z_
_Verifier: Claude (gsd-verifier) + operator closeout_
