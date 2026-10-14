# 261014-g6y senior review

- Verdict: **request changes**
- Scope: `langextract/core/events.py`, `langextract/core/types.py`, `langextract/annotation.py`, `langextract/extraction.py`, `langextract/providers/ollama.py`, `tests/chunk_events_test.py`, `tests/inference_test.py` · commits d074017^..9273a14 · reviewed 2026-10-14 (merged from 3 partial runs)
- Counts: 0 blocker · 6 major · 12 minor · 1 nit
- Routing (primary): fix 13 · test-case 4 · plan-template 0 (+3 secondary) · linter 1 · skill 1 (+1 secondary) · rule 0

## Auto-resolved (step 6)

| ID | Commit(s) |
|---|---|
| SR-6 | `7e083c7` |
| SR-10 | `5077e5d` |
| SR-12 | `52072ab` |
| SR-4 | `e0cf853` |
| SR-5 | `82256cc`, `f1e81d8` |
| SR-15 | `ce5bf3e` |
| SR-16 | `38fa092` |

Held for gate / reopen-decision: SR-1 (duration formula), SR-2, SR-3, SR-7.
Not auto-resolved this pass: SR-8, SR-9, SR-11, SR-13, SR-14, SR-17, SR-18, SR-19.

## Summary
The two latency metrics do not measure what the spec uses them for.
`ChunkFinished.duration_s` starts at one batch-wide timestamp and stops after the
chunk's own resolve, align and observer callbacks. So it includes the earlier
chunks' post-processing and the observer's own time, and it grows with the
chunk's position in the batch. Ollama's `provider_latency_s` is
`total_duration`, which is about 90% model-load time on a cold call. The event
contract has three more gaps: a non-callable `on_event` silently delivers no
events, the stable `name` is a `ClassVar` that `dataclasses.asdict` drops, and
units, `None` meanings and `outcome` values are not documented. The tests do
not encode these behaviors. The AC6/AC8 "result unchanged" tests compare
`[[], []]` to `[[], []]`, the `outcome` and `error_type`/`message` values
survive mutants, and the Ollama type guard is untested. Good: `on_event` is
keyword-only everywhere, never reaches `infer()`, emits from the calling
thread, and the frozen event dataclasses are small and flat.

## Findings
| ID | Sev | Evidence | Where | Defect | Fix | Dest | Cost | Missed by |
|---|---|---|---|---|---|---|---|---|
| SR-1 | major | CONFIRMED | annotation.py:546,611,111; events.py:51-65 | `duration_s` includes sibling chunks' resolve/align time and the observer's callback time, so it grows with batch position | Record `infer_done` once after `list(outputs)`; `duration_s = (infer_done - batch_start) + (now - chunk_post_start)`; document in `Attributes:` | fix (+plan-template) | safe (values change, shape unchanged) | plan-brief value check; test-review |
| SR-2 | major | CONFIRMED | ollama.py:339-345; types.py:71-77 | `provider_latency_s` = Ollama `total_duration`, which includes model load; the spec compares it with `duration_s` as request latency | Map `total_duration - load_duration` when both are present, or document "includes model load time" | fix (+plan-template) | reopen-decision | plan-brief value check |
| SR-3 | major | CONFIRMED | events.py:90-97; annotation.py:387; extraction.py:76 | A non-callable `on_event` is accepted; every emit raises a swallowed `TypeError`, no events arrive, and `active=True` still switches resolve to the unsuppressed path (R30, R52) | Check `callable(on_event)` in `Dispatcher.__init__` (or `annotate_documents`); raise a `langextract.core.exceptions` error naming the value | fix (+plan-template) | reopen-decision | plan (open question chose not to validate); style-review R30 |
| SR-4 | major | CONFIRMED | chunk_events_test.py:347-400, 449-484 | AC6/AC8 "result unchanged" tests compare `[[], []] == [[], []]`; dropped or duplicated extractions cannot be detected | Use `_VALID_YAML` in both runs; assert the baseline is non-empty first | skill | safe | test-review (mutated assertions, not production) |
| SR-5 | major | CONFIRMED | chunk_events_test.py:332,553-554,559-560,583,589 | `outcome` is compared to the same constants the code uses; `error_type`/`message` are only `assertNotEmpty`; two mutants survive the whole file | Assert literals `"ok"`/`"parse_error"`; assert `error_type == type(cause).__name__` and `message == str(ResolverParsingError)` | test-case (+skill) | safe | test-review (no constant/payload mutants) |
| SR-6 | major | CONFIRMED | events.py:42,55,72 | The stable `name` is a `ClassVar`, so `dataclasses.asdict`/JSON sinks drop the key dashboards match on | `name: str = dataclasses.field(default="chunk_started", init=False)`; keeps `ChunkStarted.name` | fix | safe | style-review (contracts) |
| SR-7 | minor | CONFIRMED | types.py:86 | `usage` uses `compare=False` to keep old equality tests green, so `ScoredOutput` `==`/`hash` ignore usage; upcoming OpenAI/Gemini usage tests using `assertEqual` cannot catch wrong usage | Keep `compare=True` and update the 3 equality sites, or document the exclusion | fix | reopen-decision | plan-checker; plan-brief |
| SR-8 | minor | READING | types.py:71-77; events.py:39-80 | No `Attributes:` docs (R02): units of `duration_s`/`provider_latency_s`, when `char_start` is `None`, allowed `outcome` values, whether `output_tokens` includes reasoning (OpenAI yes, Gemini no) or `input_tokens` excludes cached prompt | Add `Attributes:` blocks like `Constraint` | fix | safe | style-review R02 |
| SR-9 | minor | CONFIRMED | annotation.py:612 | `num_extractions` counts per pass before cross-pass merge; with `extraction_passes=2` events sum to 8, the document has 7; undocumented | Document "aligned extractions from this chunk in this pass, before merge" | fix | safe | style-review R02 |
| SR-10 | minor | READING | events.py:26-35,87 | `OUTCOME_*` values callers must match are not in `__all__`; `Dispatcher` is used across modules but not exported (half-public, R60); `outcome: str` is not a `Literal` | Export the outcome values (or a `str` enum); mark `Dispatcher` internal | fix | safe | style-review R60 (its `__all__` trim caused it) |
| SR-11 | minor | CONFIRMED | annotation.py:159-164 | With an observer, schema errors (`ValueError`) are logged as "(parse error)"; without one, "(schema error)"; the warning text is a drifted copy of the resolver's | Pick the label from `error.__cause__`, or move the message into one resolver helper | fix | safe | dedup-review |
| SR-12 | minor | CONFIRMED | events.py:21,107-111 | Stdlib root `logging` instead of `absl.logging`; warning has no traceback (R53) | `from absl import logging`; `exc_info=True` | fix | safe | style-review R53 |
| SR-13 | minor | READING | annotation.py:76-166 | `_resolve_chunk_extractions` takes 12 params + `**kwargs`; `meta`/`pass_index`/`batch_index` travel through 3 helpers; the 6-field event spread is written 3 times (R55, R39, R29) | Move `pass_index`/`batch_index` into `_ChunkEmitMeta`; add `started()`/`finished()`/`parse_failed()` builders | fix | safe | style-review (R39 row covered only events.py) |
| SR-14 | minor | READING | annotation.py:442-443, 653-654 | Private passes default `dispatcher=None` and build a no-op, but the only caller always passes one (R34) | Required keyword-only `dispatcher` | fix | safe | style-review R34 |
| SR-15 | minor | CONFIRMED | ollama.py:331-342 | Token counts accept floats/negatives and truncate (`15.9→15`, `-3` kept); int→float→int round-trip loses precision above 2^53 | `_optional_count` accepting only non-bool `int >= 0`; keep float path for durations | fix | safe | style-review R38 |
| SR-16 | minor | CONFIRMED | inference_test.py:164-237 | Non-numeric/bool guard (threat mitigation T-g6y-03) untested; a no-validation mutant passes all 3 new tests | Parameterized test row below | test-case | safe | test-review (value mutants only) |
| SR-17 | minor | CONFIRMED | chunk_events_test.py:315-345, 441-443, 54-59 | `num_extractions=len(resolved)` or constant 2 passes; `resolve` kwargs never checked for `on_event`; `_VALID_YAML`'s `PATIENT_index` becomes a second extraction | Rows below | test-case | safe | test-review |
| SR-18 | minor | READING | inference_test.py:167-187, 225-229 | New tests copy the 12-key gemma2 response and use deprecated `structured_output_format="json"` (FutureWarning) | Hoist response to a module constant; use `format_type=types.FormatType.JSON` | test-case | safe | dedup-review (tests outside its signal set) |
| SR-19 | nit | READING | chunk_events_test.py:125-130, 420 | Names `p`, `f`, `tid` under 3 characters (R25) | Enable R25 name-length check on tests | linter | safe | style-review |

Dropped as duplicates of earlier gates: event field data-clump (style R39 / `ChunkRef`), Ollama usage test twins (style R18 / TF-008), multi-behavior tests (style R19 / TF-007).

### SR-1 — `duration_s` is position-biased and includes observer time
Probe A, resolver `resolve` sleeps 0.1 s, model sleeps 0.05 s, 4 chunks, `batch_length=4`:
```
chunk_index batch_index duration_s
0 0 0.157
1 0 0.258
2 0 0.36
3 0 0.466
```
Probe B, instant model, observer sleeps 0.2 s on each `chunk_finished`:
```
duration_s per chunk: [0.0, 0.21, 0.41, 0.61]
```
Every chunk costs the same, yet the last reports 3× the first, and in B the
whole value is observer time. Spec rule 2 allows the batch wait, not sibling
post-processing or the observer's own work. A slow exporter inflates the
latency it exports, and p95 shifts with `batch_length`. The only test is
`duration_s >= 0`.

### SR-2 — `provider_latency_s` is mostly model-load time
```
_usage_from_response({'response':'x','eval_count':17,'total_duration':24038204381,
                      'load_duration':21551375738,'eval_duration':1848000000})
→ TokenUsage(input_tokens=None, output_tokens=17, reasoning_tokens=None, provider_latency_s=24.038204381)
```
21.55 s of 24.04 s is load. The spec says to compare batch duration with
`provider_latency_s` to tune `batch_length`/`max_workers`; on a cold call they
are nearly equal, so queueing looks like zero, and p95 spikes whenever
`keep_alive` expires.

### SR-3 — invalid `on_event` fails silently
```
annotate_documents(docs, ..., on_event=[])
WARNING:root:on_event observer failed for chunk_started: 'list' object is not callable
events received: []  docs: 2
```
The likely first-call mistake (`on_event=events` instead of `events.append`)
loses the whole run's events behind one warning that blames the observer. The
broad `except` protects against a *failing* observer, not a misconfigured one.

### SR-4 — AC6/AC8 equality tests are vacuous
`_ValidFakeModel()` defaults to `_EMPTY_YAML`, so the baseline in
`test_raising_observer_does_not_change_result` and
`test_without_on_event_matches_omitted_parameter` is `[[], []]`. An
implementation that drops a chunk's extractions whenever an observer is set
still passes. Proposed `smells.md` row:
`| S14 | Equality-against-baseline on degenerate data (both sides empty/None) | **add-case** with a fixture that yields non-empty output; assert the baseline is non-trivial first |`.

### SR-5 — constant and payload mutants survive
Run against `tests/chunk_events_test.py`, no repo edits:
- `events.OUTCOME_OK = "success"; events.OUTCOME_PARSE_ERROR = "failure"` → `19 passed`.
- `_emit_parse_failed_chunk` with `error=X("?")` → `19 passed`.
The plan said `message == str of the ResolverParsingError`; the test
downgraded it to `assertNotEmpty`. Dashboards alert on these values.

### SR-6 — the stable name is not in the serialized event
```
asdict: {"document_id": "d", "chunk_index": 0, "char_start": 0, "char_end": 5, "pass_index": 0, "batch_index": 0}
```
`json.dumps(dataclasses.asdict(event))` cannot tell `chunk_started` from
`parse_failed`. The `init=False` field variant prints
`{'name': 'chunk_started', 'document_id': 'd', 'chunk_index': 0}`.

### SR-7, SR-15, SR-16 — usage type probes
```
a = ScoredOutput(1.0,'x',usage=TokenUsage(input_tokens=1)); b = ...(input_tokens=999)
a == b, hash(a) == hash(b), len({a, b})  → True True 1
_usage_from_response({'prompt_eval_count': 15.9, 'eval_count': -3, 'total_duration': 'x'})
→ TokenUsage(input_tokens=15, output_tokens=-3, reasoning_tokens=None, provider_latency_s=None)
no-validation mutant of _usage_from_response → Ran 3 tests … OK
```

## Tests: missing cases
| Test name | Input | Expected | Covers |
|---|---|---|---|
| `test_duration_independent_of_batch_position` | 4 chunks, `batch_length=4`, resolver sleeps fixed delay | max/min `duration_s` ratio < 1.5 | SR-1 |
| `test_duration_excludes_observer_time` | 4 chunks, `batch_length=4`, observer sleeps 0.1 s on finish, instant model | every `duration_s < 0.1` | SR-1 |
| `test_ollama_usage_latency_excludes_load` (if subtracting) | gemma2 fixture | `provider_latency_s ≈ 2.486828643` | SR-2 |
| `test_non_callable_on_event_raises` | `on_event=[]` / `"x"` | project exception naming `on_event`, before any inference | SR-3 |
| `test_raising_observer_keeps_extractions` | `_VALID_YAML`, observer always raises | extractions equal an `on_event=None` run; baseline non-empty | SR-4 |
| `test_outcome_wire_values` | valid chunk + broken chunk | literals `"ok"`, `"parse_error"` | SR-5 |
| `test_parse_failed_error_type_and_message` | broken chunk, suppress on | `error_type == type(cause).__name__`; `message == str(ResolverParsingError)` from the unsuppressed run | SR-5 |
| `test_event_asdict_includes_name` | each event class | `asdict(event)["name"] == type(event).name` | SR-6 |
| `test_scored_output_equality_includes_usage` (if flipped) | outputs differing only in usage | `assertNotEqual` | SR-7 |
| `test_schema_error_label_matches_without_observer` | `PATIENT: [1, 2]`, suppress on, with/without observer | same "(schema error)" warning; `error_type == "ValueError"` | SR-11 |
| `test_ollama_usage_rejects_invalid_counts` | `{"prompt_eval_count": 15.9, "eval_count": -3}` | both `None` | SR-15 |
| `test_ollama_usage_non_numeric_fields_are_none` (parameterized) | `{"prompt_eval_count": "15"}`, `{"eval_count": True}`, `{"total_duration": None}` | matching field `None` | SR-16 |
| `test_num_extractions_counts_aligned_per_chunk` | chunk 0 → 2 items, chunk 1 → 0 items | `[2, 0]` | SR-17 |
| `test_on_event_not_forwarded_to_resolver` | spy resolver recording kwargs | no `on_event`/`dispatcher` in `resolve`/`align` kwargs | SR-17 |

## Setup feedback
| Finding | Gate that should have caught it | Why it did not | Destination |
|---|---|---|---|
| SR-1, SR-2 | plan-brief value check | Plan copied spec rules for both metrics without asking what decision each drives or what upstream field it measures | plan-template: "For every metric field: what decision it drives, what it measures upstream, and a counterexample input that would skew it" |
| SR-3, SR-7 | plan / plan-checker | Both were recorded as open questions and resolved toward the convenient choice (no validation; `compare=False` to keep tests green) without a gate | plan-template: "Every user-supplied callable or option gets a rejection row; any choice made to keep old tests green is flagged for the gate" |
| SR-4, SR-5, SR-16, SR-17 | test-review mutation | Scorecard flipped test assertions (`== → !=`) and one value; it never mutated production code, constant values or error payloads, and never checked for degenerate baselines | skill (`mutation.md`): "Mutate production, not assertions: at least one mutant per AC must change the code under test; also mutate exported constant values and error payloads." Plus `smells.md` S14 (SR-4) |
| SR-6, SR-8, SR-9, SR-10, SR-12 | style-review contracts / R02 / R53 / R60 | Diff-scoped review checked shape (frozen, `__all__`) not serialized output or docs; its own `__all__` trim produced SR-10 | fix (one-off); rules exist |
| SR-13, SR-14, SR-15 | style-review R39/R55/R34/R38 | R39 row was raised only for events.py; whole-module parameter flow in annotation.py not checked | fix; rules exist |
| SR-11, SR-18 | dedup-review | Duplicated message text across modules and copied test fixtures are outside its signal set | fix / test-case |
| SR-19 | style-review R25 | Short-name check not run on tests | linter |

## Rule proposals
none. No finding is routed to `rule`; every pattern is covered by an existing rule (missed in review) or belongs in a skill. Checklist rule count unchanged at 65.

## Cited rules
R02, R25, R29, R30, R34, R38, R39, R52, R53, R55, R60

## Open questions
- `annotation.py:557-559`: `InferenceOutputError`, or `infer()` returning fewer outputs than prompts (silent `zip` truncation, predates this change), leaves `chunk_started` with no `chunk_finished` (AC5).
- Custom `AbstractResolver` subclasses that raise a non-`ResolverParsingError` when `suppress_parse_errors=False` would crash only when an observer is attached (`annotation.py:134-139`). Not reproduced.
- Ollama may omit `prompt_eval_count` when the prompt is KV-cached, so `input_tokens=None` may mean "cached", not "unreported"; needs a live server. If true, document under SR-8.
- gpt-oss `eval_count` probably includes Harmony reasoning tokens while `reasoning_tokens` is `None`, overstating output; not verified.
- `annotation.py` reads `scored_outputs[0].usage` directly (style R06 removed the plan's `getattr`); duck-typed third-party outputs without `usage` would raise `AttributeError`.
- Environment: 13 OpenAI tests in `tests/inference_test.py` fail because `openai` is not installed in `.venv`; unrelated. Uncommitted working-tree changes in `tests/chunk_events_test.py` were not reviewed.

## Human gate (2026-10-14)

- **Commit verdict:** approved
- **Auto-resolved (kept):** SR-4, SR-5, SR-6, SR-10, SR-12, SR-15, SR-16
- **Deferred (no steering answer / unanswered):** SR-1, SR-2, SR-3, SR-7, SR-8, SR-9, SR-11, SR-13, SR-14, SR-17, SR-18, SR-19
  - reopen-decision items SR-2, SR-3, SR-7 recorded as `defer (no reason given)` per gate rules
