---
phase: 04-stage-wrappers
plan: 03
subsystem: tracing
tags: [trace, wrappers, align, offsets, source-slice, tdd, offline]
status: complete-with-deferred-task2
requires:
  - phase: 04-stage-wrappers
    provides: StageRecord, make_stage_wrappers registry, print_stage_records, make_parse_wrapper, _patch_stages/_run_offline_extract helpers (04-01, 04-02)
  - phase: 02-extraction-snapshots
    provides: snapshot_extractions, print_grounding_pair, _format_interval
provides:
  - make_align_wrapper(sink) (original -> replacement for Resolver.align), registered as 'align'
  - _source_slice(source_text, snap, char_offset, ungrounded_label)
  - _print_align_section and the [align] block in print_stage_records
  - config.yaml chunk_offset_caption
  - make_stage_wrappers now has all five keys: chunk, prompt, model, parse, align
affects: [05-live-call]
tech-stack:
  added: []
  patterns: [original->replacement wrappers, lazy same-object generator with snapshot in finally, messages from config.yaml]
key-files:
  created: []
  modified:
    - scripts/trace_extract.py
    - config.yaml
    - tests/trace_extract_test.py
key-decisions:
  - "Align record fields: in_data {source_text, token_offset, char_offset (None -> 0), n_extractions}; out_data {extractions: snapshots taken in finally at generator exhaustion/close}."
  - "The [align] section pairs the i-th align record with the i-th parse record (single-chunk v1, A6); when no parse record exists at that position the pair is skipped rather than raising."
  - "Ungrounded extractions print config ungrounded_label for span, status and slice."
requirements-completed: [STG-03, STG-06]
plan_head_before: 096a1f434dea5b652bc49cc109d97b573f85641e
duration: 10 min
completed: 2026-10-11
actuals:
  tokens: 6000
  tasks: 1
  commits: 2
coverage:
  - id: D1
    description: "One offline lx.extract with all five wrappers yields an align record with chunk source_text, token_offset 0, char_offset 0 (int, not None) and n_extractions 2"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_align_wrapper_records_chunk_inputs_from_offline_extract"
        status: pass
  - id: D2
    description: "Align out snapshots equal the returned document's extractions (same objects yielded): headache (18, 26) match_exact, purple elephant ungrounded"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_align_wrapper_snapshots_the_extractions_it_yielded"
        status: pass
  - id: D3
    description: "Five sections print in catalog order chunk, prompt, model, parse, align from one offline call"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_five_stage_walkthrough_prints_sections_in_catalog_order"
        status: pass
  - id: D4
    description: "[align] prints offsets line with config caption, span/status/slice per extraction, config ungrounded_label for ungrounded, and the parse->align pair"
    requirement: STG-06
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_align_section_prints_offsets_spans_slices_and_ungrounded"
        status: pass
      - kind: integration
        ref: "tests/trace_extract_test.py#test_align_section_prints_parse_to_align_pair"
        status: pass
  - id: D5
    description: "Direct align call with token_offset=5, char_offset=100 prints span [118, 126) and slice 'headache'; omitted char_offset prints 0, never None"
    requirement: STG-06
    verification:
      - kind: unit
        ref: "tests/trace_extract_test.py#test_align_section_uses_document_coordinates_minus_offset (offsets_5_100, char_offset_omitted)"
        status: pass
  - id: D6
    description: "Empty parse still writes an align record (n_extractions 0, extractions ()) and prints parse: [] / align: []"
    requirement: STG-03
    verification:
      - kind: integration
        ref: "tests/trace_extract_test.py#test_align_with_empty_parse_records_zero_and_prints_empty_pair"
        status: pass
  - id: D7
    description: "Same walkthrough through trace_probes(wrappers=make_stage_wrappers(sink, config)) with originals restored on success and exception (Tests R-T)"
    requirement: STG-03
    verification:
      - kind: other
        ref: "Task 2 deferred: blocked on Phase 3 (trace_probes not present)"
        status: deferred
---

# Phase 4 Plan 03: Align stage wrapper and five-stage walkthrough Summary

`make_align_wrapper` records the chunk offsets and a snapshot of every yielded extraction (taken in a `finally` over a lazy same-object generator), and the `[align]` printer shows offsets, span, status and the source slice or `ungrounded` for each extraction, followed by the existing parse -> align pair. One offline `lx.extract` now prints chunk -> prompt -> model -> parse -> align with live in/out. Task 2 (the `trace_probes` hand-off) is deferred because Phase 3 has not landed.

## Plan status: complete-with-deferred-task2

- **Task 1 (tracer): complete.** RED then GREEN committed.
- **Task 2: HALTED** per its precondition: "04-03 Task 2 blocked on Phase 3 (trace_probes)". `grep -c 'def trace_probes' scripts/trace_extract.py` returned 0 and `.planning/phases/03-call-scoped-probe-manager/` has no `*-SUMMARY.md` (only `03-DISCUSS-CHECKPOINT.json`). No `trace_probes`, adapter or Tests R-T were written. As the plan states, this is not a phase-requirement failure: STG-03/04/06/09 coverage is satisfied via `_patch_stages` and offline `lx.extract`.

## What was built

- `make_align_wrapper(sink)`: non-generator replacement that binds arguments (`inspect.signature(...).bind` + `apply_defaults`), builds `in_data` (`char_offset or 0`, `n_extractions = len(extractions)`) and returns an inner generator. The generator loops lazily over `original(...)`, yields the same objects and appends the record in `finally`, so empty input and early close still record. `WordAligner` is not wrapped, nothing is deep-copied, nothing is snapshotted at call time.
- `_source_slice`: `repr(_safe_text(source_text[start - char_offset : end - char_offset]))`, or `ungrounded_label` when the span is None.
- `_print_align_section`: `offsets: token_offset=T  char_offset=C  (<chunk_offset_caption>)`, one `[i] class: 'text'  span=...  status=...  slice=...` line per extraction, then `print_grounding_pair(parse_out, align_out, ungrounded_label)` with the parse record at the same position. No new pair printer.
- `config.yaml`: `chunk_offset_caption: chunk start in the document`.
- `make_stage_wrappers` registers all five keys. `main()` is unchanged: catalog-only output still has the 7 headers and no `in:`/`out:`/`offsets:`/pair lines.

Example output for the canned reply:

```
offsets: token_offset=0  char_offset=0  (chunk start in the document)
  [1] symptom: 'headache'  span=[18, 26)  status=match_exact  slice='headache'
  [2] symptom: 'purple elephant'  span=ungrounded  status=ungrounded  slice=ungrounded
grounding pair (parse → align): 2 extractions
```

## Phase 5 entry points

- Today (works without Phase 3): `sink = []`, `wrappers = make_stage_wrappers(sink, config)`, install each `wrappers[label](cls.__dict__[attr])` via `mock.patch.object` the way `_patch_stages` does (targets in `_STAGE_TARGETS` of the test module), run `lx.extract(...)`, then `print_stage_records(sink, config)`.
- Intended (once Phase 3 lands): `with trace_probes(wrappers=make_stage_wrappers(sink, config)): lx.extract(...)`, then `print_stage_records(sink, config)` in `finally`.
- Adapter: not yet determined. Whether Phase 3's contract matches A1 (keys = labels, values = original -> replacement) can only be checked when Phase 3 exists; Task 2 adds a <=10-line adapter if not.

## Commits

| Commit | Message |
|--------|---------|
| 3c594df | test(04-03): add failing align-stage tracer tests |
| cae4c4b | feat(04-03): align-stage wrapper and align section completing five-stage walkthrough |

Non-test diff: 98 lines (95 in `scripts/trace_extract.py` after the pyink hook, 3 in `config.yaml`), two source files; within the 150 per task / 400 per plan budget (plan estimate ~65). Plan 04 non-test total: 209 + 91 + 98 = 398 lines across the three plans. `tests/trace_extract_test.py`: 39 passed (31 + 8 new; the offset case is parameterized).

## Deviations from Plan

**1. [Rule 1 - Bug] RED/GREEN tests matched `pformat` noise**
- **Found during:** Task 1 GREEN
- **Issue:** The first version of three tests picked lines by `"'headache'" in line` / `startswith("  [2] symptom")`, which also match the `out:` block's pformat lines (`extraction_text='headache',`) and the grounding-pair lines.
- **Fix:** Tests select align lines by the `  span=` marker (`_span_lines` helper). Assertions otherwise unchanged. Fixed before the GREEN commit; the RED commit's failure (`KeyError: 'align'`) is unaffected.
- **Files modified:** tests/trace_extract_test.py
- **Commit:** cae4c4b

**2. [Rule 2 - CLAUDE.md] Plan's single Test N split into several tests**
- CLAUDE.md requires one behavior per test and parameterization. Test N became five tests (record inputs, snapshots vs document, catalog order, offsets/slice/ungrounded lines, parse -> align pair); Tests O and Q became one `named_parameters` test; Test P is its own test. Shared setup lives in `_run_five_stages` / `_direct_align_section` helpers.

**3. [Process] Dispatch pin guard run from an extracted copy**
- The guard text was extracted verbatim from the dispatch brief to `/tmp/pin04_03.sh` and run before the first Edit/Write and before every commit; it passed each time and was not edited. The isort/pyink hooks reformatted the staged files during the first commit attempt of both commits; I re-staged and re-committed without `--no-verify`.

**Total deviations:** 3 (1 test bug, 1 CLAUDE.md, 1 process). **Impact:** none on behavior or scope.

## Deferred / out of scope

- **Task 2 / Tests R-T** (trace_probes integration, exception-path restore, walkthrough order via trace_probes): blocked on Phase 3. The plan's `human-check` for the five-stage walkthrough belongs to Task 2 and is not done; the equivalent output was inspected from the `_patch_stages` path (see example above).
- Plan verification thresholds: `>= 28 passed` for Task 1 alone is met (39 passed); `>= 31` is the Task 2 figure and is met numerically only because 04-02 already had 31, so it does not evidence Task 2.
- Full non-live suite not re-run: `.venv` lacks `openai` (pre-existing, noted in 04-01/04-02), which fails collection in unrelated test modules. `tests/trace_extract_test.py` is green.
- Unrelated dirty files left alone: `.gitignore`, `.gsd/dispatch-isolation-sentinel.json`, `.planning/phases/03-.../03-DISCUSS-CHECKPOINT.json`, untracked `amp` and `.gsd/dispatch-04-0{1,2,3}-prompt.md`.

## Known Stubs

None. `trace_probes` was not stubbed or invented; Task 2 is simply not executed.

## Threat Flags

None new. T-04-09 (slice and extraction text through `repr`/`_safe_text`) and T-04-10 (lazy same-object yields, snapshot in `finally`, document-vs-snapshot comparison) are covered by tests. T-04-11 (restore of the five class attributes through `trace_probes`) is **not verified** because it belongs to deferred Task 2; the existing `mock.patch.object` cleanup covers the `_patch_stages` path only. T-04-12 accepted.

## Self-Check: PASSED

- scripts/trace_extract.py, config.yaml, tests/trace_extract_test.py exist; commits 3c594df and cae4c4b found; RED precedes GREEN.
- `tests/trace_extract_test.py`: 39 passed. Catalog-only `python scripts/trace_extract.py` prints the 7 headers in order with no `in:`/`out:`/`offsets:`/pair lines.
- No edits under `langextract/` or `examples/ollama/demo_ollama.py`; no top-level `langextract` import added to the script; no `WordAligner` wrapping.
