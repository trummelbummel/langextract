---
gsd_state_version: "1.0"
milestone: v1.0
milestone_name: MVP
current_phase: 07
current_phase_name: Gold-set evaluation metrics
current_plan: 5
status: ready
stopped_at: Phase 7 complete, ready to plan Phase 5
last_updated: "2026-10-11T18:52:54.415Z"
last_activity: 2026-10-11
last_activity_desc: Phase 7 complete, transitioned to Phase 5
state_head: 49226ec0959f9bab686a3d9deb4a452dc09befda
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 16
  completed_plans: 16
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-11)

**Core value:** You can follow one `lx.extract()` call from the prompt through to an `AnnotatedDocument` and see which function owns each stage.
**Current focus:** Phase 05 — Live extract & Ollama preflight

## Current Position

Phase: 07 (Gold-set evaluation metrics) — COMPLETE
Current Plan: 5/5
Total Plans in Phase: 5
Status: Phase complete — verified
Last activity: 2026-10-14 - Completed quick task 261014-g6y: Per-chunk observability for extraction

Progress: [████████░░] 83%


## Performance Metrics

**Velocity:**

- Total plans completed: 16
- Average duration: 2.5min
- Total execution time: 0.08 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-stage-catalog-contracts | 2 | 5min | 2.5min |
| 1 | 2 | - | - |
| 2 | 2 | - | - |
| 03 | 2 | - | - |
| 4 | 3 | - | - |
| 7 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: 3min, 2min
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01-stage-catalog-contracts P01 | 3min | 2 tasks | 2 files |
| Phase 01-stage-catalog-contracts P02 | 2min | 2 tasks | 2 files |
| Phase 02 P01 | 9 min | 2 tasks | 2 files |
| Phase 02 P02 | 10 min | 2 tasks | 3 files |
| Phase 04 P01 | 6min | 2 tasks | 2 files |
| Phase 04 P02 | 4 min | 2 tasks | 3 files |
| Phase 04 P03 | 10 min | 1 tasks | 3 files |
| Phase 03 P01 | 4min | 2 tasks | 2 files |
| Phase 03 P02 | 3min | 2 tasks | 2 files |
| Phase 05 P01 | 25 min | 2 tasks | 3 files |
| Phase 261011-cst P01 | 2min | 2 tasks | 4 files |
| Phase 05 P02 | 4min | 2 tasks | 4 files |
| Phase 261011-d60 P01 | 2min | 2 tasks | 2 files |
| Phase 07 P01 | 2min | 2 tasks | 4 files |
| Phase 07 P02 | 2min | 2 tasks | 4 files |
| Phase 07 P03 | 4min | 2 tasks | 3 files |
| Phase 07 P04 | 2min | 2 tasks | 4 files |
| Phase 07 P05 | 2min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Script-only deliverable under `scripts/trace_extract.py`; no library API changes
- Call-scoped class-attribute probes (not parallel Annotator/Resolver path)
- Local Ollama `gemma3:4b` only; snapshot before align mutates extractions
- MVP roadmap: 6 incremental script slices matching research build order
- [Phase 1]: Call header prints full model_url plus host= netloc for D-09 clarity
- [Phase 1]: load_config exposed for missing-path testing without deleting real config
- [Phase 1]: Phase 1 config holds only model_id/model_url/provider (empty_parse/redact deferred to 01-02)
- [Phase 1]: empty_parse_message uses PATTERNS wording; catalog path still omits it
- [Phase 1]: redact() accepts explicit keys for tests; defaults to config redact_keys
- [Phase 1]: Nested redact one level deep; non-matching values keep original types
- [Phase 02]: Snapshots are duck-typed field copies (attributes copied one level deep, no deepcopy); helpers not wired into main() until Phase 4 — Resolver.align mutates resolve's objects in place; parse record must be copied at resolve return
- [Phase 04]: [Phase 04-01]: make_stage_wrappers keys are catalog labels with original->replacement values; model records are one per ScoredOutput with prompt_index (0-based yield position per infer call) and batch_size
- [Phase 04]: 04-02: parse record = in{raw_model_text,flags,suppress_parse_errors} out{extractions,parse_error}; callout picks empty_parse_message (error str) vs empty_list_message (None) from config
- [Phase 04]: Offline five-stage wrappers + printers (chunk→align); empty-parse callouts; UAT 15/15 after Phase 3 `trace_probes` landed
- [Phase 04]: Advisory WR-01–WR-05 (prompt_index guard, empty-list callout truth, print layout) deferred to Phase 5
- [Phase 03]: Chunk identity returns original iterator (ChunkIterator.__iter__ returns self)
- [Phase 03]: Model/align identity use yield from; prompt/parse use return; no functools.wraps
- [Phase 03]: _PROBE_TARGETS populated lazily so catalog import stays light
- [Phase 03]: Unknown wrappers= keys raise ValueError with sorted labels
- [Phase 03]: Self-check stderr 'Error: probe self-check failed' + SystemExit(1); expected RuntimeError swallowed
- [Phase 05]: 05-01: preflight matches exact model id or :latest only; non-http(s) model_url rejected before any request
- [Phase 05]: 05-01: --catalog-only keeps Phase 3 D-09 self-check (not langextract-free); system python lacks yaml so verify with .venv
- [Phase 05]: Quick 261011-cst: document_path + chunk kwargs from config; CLI document positional removed
- [Phase 05]: 05-02: Infer calls counted by distinct id(model in_data), not prompt_index==0 alone (WR-05)
- [Phase 05]: 05-02: One-chunk pre-check uses document_path text vs config max_char_buffer; buffer raised to 40000 for example_document.md
- [Phase 05]: Chunk printout uses ##########/*******/%%%%%% titles; document_id only under percent marker
- [Quick 261011-p2z]: Keyword-only drop_ungrounded=False; _drop_ungrounded filters both extract return paths; INFO when removals > 0
- [Phase 07]: Empty TP=FP=FN=0 yields P=R=F1=0.0
- [Phase 07]: Micro from global count triple via one prf_from_counts call
- [Phase 07]: per_class keys sorted alphabetically in report_from_counts
- [Phase 07]: span_iou uses half-open exclusive end_pos; end < start → 0.0
- [Phase 07]: SpanIoU matches with >= threshold (default 0.5)
- [Phase 07]: TextMatch requires text_eval_func: Callable[[str, str], bool]
- [Phase 07]: Sort key exactly (-score, pred_index, gold_index); lower indices win IoU ties
- [Phase 07]: Default score_fn=span_iou; criteria failure omits pair even if IoU high
- [Phase 07]: evaluate pairs by document_id then greedy_match; TP/FP from pred class, FN from gold
- [Phase 07]: criteria= XOR non-default convenience flags; lazy lx.evaluation only (no top-level evaluate)
- [Phase 07]: Document report.micro.f1 (shipped ClassScore field), not plan f1_score name
- [Phase 07]: README Gold-set evaluation subsection links docs/examples/evaluation_ci.md

### Roadmap Evolution

- Phase 7 added: Gold-set evaluation metrics (`evaluate(predicted, gold)` — IoU + greedy 1:1 + P/R/F1; modular `langextract/evaluation/` package)

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 5 needs local Ollama serving `gemma3:4b` (cold-load timeout to validate on this machine)
- Phase 5 single-inference guard must not rely on `prompt_index == 0` alone (WR-05)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261011-cst | make the script read from config the file in filepath data/example_document.md , make the chunking configurable in the config and load it in the script | 2026-10-11 | d70aa60 | [261011-cst-make-the-script-read-from-config-the-fil](./quick/261011-cst-make-the-script-read-from-config-the-fil/) |
| 261011-d60 | Mark chunk walkthrough input/output/file id with distinctive delimiter runs | 2026-10-11 | 98b6587 | [261011-d60-the-input-output-and-chunk-chunkiterator](./quick/261011-d60-the-input-output-and-chunk-chunkiterator/) |
| 261011-p2z | Drop ungrounded extractions via opt-in drop_ungrounded on lx.extract() | 2026-10-11 | d84f459 | [261011-p2z-drop-extractions-whose-char-interval-is-](./quick/261011-p2z-drop-extractions-whose-char-interval-is-/) |
| 261012-922 | Reduce the number of classes in langextract.evaluation: put everything in one file and consolidate into one class as much as possible while keeping public API and tests green. | 2026-10-12 | 3d88338 | [261012-922-reduce-the-number-of-classes-in-langextr](./quick/261012-922-reduce-the-number-of-classes-in-langextr/) |
| 261012-9pt | write a small script with synthetic data that calls the evaluator and writes the report, also annotate the ground truth data in the script with expected results for the evaluator | 2026-10-12 | 8b8b87f | [261012-9pt-write-a-small-script-with-synthetic-data](./quick/261012-9pt-write-a-small-script-with-synthetic-data/) |
| 261013-but | Token-counting wrapper around extract: per-call and running tokenizer-token usage (TokenCountingExtractor) | 2026-10-13 | 0499459 | [261013-but-implement-a-wrapper-around-extract-that-](./quick/261013-but-implement-a-wrapper-around-extract-that-/) |
| 261013-kzb | Fallback provider: ordered ModelConfigs, transient retry + backoff, same-format chain, served_model_ids (no core edits) | 2026-10-13 | 20c6777 | [261013-kzb-primary-model-failures-rate-limits-timeo](./quick/261013-kzb-primary-model-failures-rate-limits-timeo/) |
| 261014-g6y | Per-chunk observability for extraction: on_event callback with chunk_started/finished, parse_failed, model_call_failed; TokenUsage on ScoredOutput; slices 1→3→5 (events plumbing, parse failures, Ollama usage); follow-ups 2/4/5b/c | 2026-10-14 | 0d79f88 | [261014-g6y-per-chunk-observability-for-extraction-o](./quick/261014-g6y-per-chunk-observability-for-extraction-o/) |

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| v2 | STG-10 two-chunk input | Deferred | 2026-10-10 | v1.0 MVP |
| v2 | STG-11 prompt-validation line | Deferred | 2026-10-10 | v1.0 MVP |
| v2 | STG-12 WordAligner parameter echo | Deferred | 2026-10-10 | v1.0 MVP |

## Session Continuity

Last session: 2026-10-11T18:48:50.515Z
Stopped at: Phase 7 complete, ready to plan Phase 5
Resume file: None
